"""Domain events raised by the Dispute aggregate. Every status change raises one."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.events.domain_event import DomainEvent
from dispute_analyst.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class DisputeOpened(DomainEvent):
    customer_id: UUID
    transaction_id: UUID
    reason: DisputeReason
    disputed_amount: Money


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisStarted(DomainEvent):
    """The dispute was handed to the analysis agent."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRequested(DomainEvent):
    """The proposed amount is above the approval limit: a human must decide."""

    amount: Money


@dataclass(frozen=True, slots=True, kw_only=True)
class SentToManualReview(DomainEvent):
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DisputeApproved(DomainEvent):
    amount: Money
    approved_by: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DisputeDenied(DomainEvent):
    denied_by: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DisputeRefunded(DomainEvent):
    amount: Money


@dataclass(frozen=True, slots=True, kw_only=True)
class RefundFailed(DomainEvent):
    reason: str
