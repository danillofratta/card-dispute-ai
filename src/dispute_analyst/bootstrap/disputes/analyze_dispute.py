"""Providers of the analyze_dispute slice, which has a gateway of its own (ADR 0003)."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel

from dispute_analyst.bootstrap.dependencies import CoreBankingDependency, DatabaseDependency
from dispute_analyst.bootstrap.settings import Settings, get_settings
from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.features.disputes.analyze_dispute.gateway import AnalyzeDisputeGateway
from dispute_analyst.infrastructure.agents.baseline.analyzer import BaselineAnalyzer
from dispute_analyst.infrastructure.agents.unavailable_analyzer import UnavailableAnalyzer
from dispute_analyst.infrastructure.llm.chat_models import LlmConfig, build_chat_model
from dispute_analyst.infrastructure.merchants.merchants import Merchants
from dispute_analyst.infrastructure.merchants.simulated_merchants import SimulatedMerchants
from dispute_analyst.infrastructure.merchants.sqlalchemy_merchants import SqlAlchemyMerchants
from dispute_analyst.infrastructure.observability.langfuse import langfuse_callback

SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_merchants(database: DatabaseDependency) -> Merchants:
    """The merchants' orders: their schema in Postgres, or fixed synthetic orders in memory."""
    if database is None:
        return _simulated_merchants()
    return SqlAlchemyMerchants(database.session_factory)


MerchantsDependency = Annotated[Merchants, Depends(get_merchants)]


def get_dispute_analyzer(
    settings: SettingsDependency,
    core_banking: CoreBankingDependency,
    merchants: MerchantsDependency,
) -> AnalyzeDisputeGateway:
    """The baseline agent with the configured model. Without one, analyses go to manual review."""
    if settings.llm_provider is None or settings.llm_model is None:
        return UnavailableAnalyzer("no LLM configured")
    api_key = settings.llm_api_key
    config = LlmConfig(
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=None if api_key is None else api_key.get_secret_value(),
        timeout_seconds=settings.llm_timeout_seconds,
    )
    return BaselineAnalyzer(
        _chat_model(config),
        core_banking,
        merchants,
        callbacks=_tracing(settings),
        timeout_seconds=settings.llm_timeout_seconds,
    )


def get_approval_limit() -> ApprovalLimit:
    """The limit from the settings. Money validates it: >= 0 and at most two decimals."""
    return ApprovalLimit(Money(get_settings().approval_limit))


DisputeAnalyzerDependency = Annotated[AnalyzeDisputeGateway, Depends(get_dispute_analyzer)]
ApprovalLimitDependency = Annotated[ApprovalLimit, Depends(get_approval_limit)]


@lru_cache
def _chat_model(config: LlmConfig) -> BaseChatModel:
    """One client per configuration, so HTTP connections are reused across requests."""
    return build_chat_model(config)


def _tracing(settings: Settings) -> list[BaseCallbackHandler]:
    """Langfuse when both keys are set; otherwise nothing is traced."""
    public_key, secret_key = settings.langfuse_public_key, settings.langfuse_secret_key
    if public_key is None or secret_key is None:
        return []
    return [_langfuse(public_key, secret_key.get_secret_value(), settings.langfuse_base_url)]


@lru_cache
def _langfuse(public_key: str, secret_key: str, base_url: str) -> BaseCallbackHandler:
    return langfuse_callback(public_key, secret_key, base_url)


@lru_cache
def _simulated_merchants() -> SimulatedMerchants:
    return SimulatedMerchants()
