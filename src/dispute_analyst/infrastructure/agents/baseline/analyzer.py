"""BaselineAnalyzer: one model, read-only tools and a tool-calling loop written by hand.

The loop is the whole agent: ask the model, run the tools it calls, give it the results, and
repeat until it calls SubmitDecision. Module 5 replaces it with a LangGraph supervisor, and the
evals compare the two.
"""

import asyncio
import logging
import re
from collections.abc import Sequence
from typing import Literal

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ValidationError, field_validator

from dispute_analyst.application.ports.core_banking import CoreBanking
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.features.disputes.analyze_dispute.exceptions import (
    AnalyzeDisputeUnavailableError,
)
from dispute_analyst.features.disputes.analyze_dispute.gateway import DisputeCaseDto
from dispute_analyst.infrastructure.agents.baseline.prompt import (
    SUBMIT_REMINDER,
    SYSTEM_PROMPT,
    describe,
)
from dispute_analyst.infrastructure.agents.baseline.tools import build_tools
from dispute_analyst.infrastructure.merchants.merchants import Merchants

logger = logging.getLogger(__name__)

_AMOUNT = re.compile(r"[0-9]+(\.[0-9]{1,2})?")


class SubmitDecision(BaseModel):
    """Submit your proposal for this dispute. Call it once, after investigating."""

    outcome: Literal["approve", "deny"]
    justification: str = Field(description="Why, in two or three sentences.")
    citations: list[str] = Field(
        description="The evidence you relied on: transaction:<id> or order:<id>."
    )
    amount: str | None = Field(
        default=None,
        description="Amount to refund when approving, such as 129.90. Null when denying.",
    )

    @field_validator("amount")
    @classmethod
    def _plain_amount(cls, amount: str | None) -> str | None:
        # Checked here, not as a schema pattern: some providers reject the whole call when the
        # model breaks a pattern, while this error goes back to the model to fix.
        if amount is not None and not _AMOUNT.fullmatch(amount):
            raise ValueError("amount must look like 129.90: digits, a dot, up to two decimals")
        return amount

    def to_proposal(self, currency: str) -> DecisionProposal:
        """Translate to the domain. No checks here: the Dispute aggregate judges the proposal."""
        return DecisionProposal(
            outcome=ProposalOutcome(self.outcome),
            justification=self.justification,
            citations=tuple(self.citations),
            amount=None if self.amount is None else Money.of(self.amount, currency),
        )


class BaselineAnalyzer:
    """Implements AnalyzeDisputeGateway with one model and the read-only tools."""

    def __init__(
        self,
        model: BaseChatModel,
        core_banking: CoreBanking,
        merchants: Merchants,
        *,
        callbacks: Sequence[BaseCallbackHandler] = (),
        max_rounds: int = 6,
        timeout_seconds: float = 60,
    ) -> None:
        """Callbacks receive every model and tool call, for tracing (Langfuse)."""
        self._model = model
        self._core_banking = core_banking
        self._merchants = merchants
        self._callbacks = list(callbacks)
        self._max_rounds = max_rounds
        self._timeout_seconds = timeout_seconds

    async def analyze(self, case: DisputeCaseDto) -> DecisionProposal:
        """Investigate and propose. Every failure becomes AnalyzeDisputeUnavailableError."""
        # One root run, so the whole analysis is one trace with every call nested inside.
        run = RunnableLambda(self._investigate, name="analyze_dispute")
        config = RunnableConfig(
            callbacks=self._callbacks,
            metadata={
                "dispute_id": str(case.dispute_id),
                "langfuse_session_id": str(case.dispute_id),
                "langfuse_tags": ["baseline"],
            },
        )
        try:
            async with asyncio.timeout(self._timeout_seconds):
                proposal: DecisionProposal = await run.ainvoke(case, config)
                return proposal
        except AnalyzeDisputeUnavailableError:
            raise
        except TimeoutError as error:
            raise AnalyzeDisputeUnavailableError(
                f"no answer within {self._timeout_seconds:g} seconds"
            ) from error
        except Exception as error:
            # The model, the network or a tool failed: the dispute goes to manual review.
            logger.exception("analysis of dispute %s failed", case.dispute_id)
            raise AnalyzeDisputeUnavailableError(
                f"analysis failed: {type(error).__name__}"
            ) from error

    async def _investigate(self, case: DisputeCaseDto, config: RunnableConfig) -> DecisionProposal:
        tools = {tool.name: tool for tool in build_tools(case, self._core_banking, self._merchants)}
        model = self._model.bind_tools([*tools.values(), SubmitDecision])
        messages: list[BaseMessage] = [SystemMessage(SYSTEM_PROMPT), HumanMessage(describe(case))]

        for _ in range(self._max_rounds):
            reply = await model.ainvoke(messages, config)
            messages.append(reply)
            if not reply.tool_calls:
                messages.append(HumanMessage(SUBMIT_REMINDER))
                continue
            for call in reply.tool_calls:
                if call["name"] == SubmitDecision.__name__:
                    try:
                        decision = SubmitDecision.model_validate(call["args"])
                    except ValidationError as error:
                        # Tell the model what was wrong, so it can fix it in the next round.
                        messages.append(_tool_reply(call, f"Invalid decision: {error}"))
                        continue
                    return decision.to_proposal(case.disputed_amount.currency)
                messages.append(await _run_tool(tools, call, config))

        raise AnalyzeDisputeUnavailableError(f"no decision after {self._max_rounds} rounds")


async def _run_tool(
    tools: dict[str, BaseTool], call: ToolCall, config: RunnableConfig
) -> ToolMessage:
    tool = tools.get(call["name"])
    if tool is None:
        return _tool_reply(call, f"Unknown tool {call['name']!r}.")
    # Called with the whole ToolCall, a LangChain tool answers with a ToolMessage.
    result: ToolMessage = await tool.ainvoke(call, config)
    return result


def _tool_reply(call: ToolCall, content: str) -> ToolMessage:
    return ToolMessage(content=content, tool_call_id=call["id"] or "")
