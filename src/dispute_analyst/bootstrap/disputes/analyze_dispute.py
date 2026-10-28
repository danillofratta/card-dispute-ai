"""Providers of the analyze_dispute slice, which has a port of its own (ADR 0003)."""

from typing import Annotated

from fastapi import Depends

from dispute_analyst.bootstrap.settings import get_settings
from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.features.disputes.analyze_dispute.gateway import AnalyzeDisputeGateway
from dispute_analyst.infrastructure.agents.unavailable_analyzer import UnavailableAnalyzer


def get_dispute_analyzer() -> AnalyzeDisputeGateway:
    """No model yet: every analysis goes to manual review. The LLM agent plugs in here."""
    return UnavailableAnalyzer("no LLM configured")


def get_approval_limit() -> ApprovalLimit:
    """The limit from the settings. Money validates it: >= 0 and at most two decimals."""
    return ApprovalLimit(Money(get_settings().approval_limit))


DisputeAnalyzerDependency = Annotated[AnalyzeDisputeGateway, Depends(get_dispute_analyzer)]
ApprovalLimitDependency = Annotated[ApprovalLimit, Depends(get_approval_limit)]
