"""Mappers between the domain and the table models. The only place that knows both."""

import dataclasses
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.events.domain_event import DomainEvent
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import (
    DisputeModel,
    OutboxEventModel,
)


def dispute_to_model(dispute: Dispute) -> DisputeModel:
    """Flatten the aggregate into one row. Money becomes an amount column plus a currency."""
    approved = dispute.approved_amount
    return DisputeModel(
        id=dispute.id,
        customer_id=dispute.customer_id,
        transaction_id=dispute.transaction_id,
        reason=dispute.reason.value,
        status=dispute.status.value,
        description=dispute.description,
        currency=dispute.disputed_amount.currency,
        disputed_amount=dispute.disputed_amount.amount,
        approved_amount=None if approved is None else approved.amount,
        opened_at=dispute.opened_at,
    )


def dispute_from_model(model: DisputeModel) -> Dispute:
    """Rebuild the aggregate with its rebuild constructor: no events are raised."""
    approved = model.approved_amount
    return Dispute(
        dispute_id=model.id,
        customer_id=model.customer_id,
        transaction_id=model.transaction_id,
        reason=DisputeReason(model.reason),
        description=model.description,
        disputed_amount=Money(model.disputed_amount, model.currency),
        status=DisputeStatus(model.status),
        opened_at=model.opened_at,
        approved_amount=None if approved is None else Money(approved, model.currency),
    )


def event_to_outbox(event: DomainEvent) -> OutboxEventModel:
    """Store the event as JSON, waiting for the relay to publish it (module 10)."""
    return OutboxEventModel(
        id=uuid4(),
        dispute_id=event.dispute_id,
        event_type=type(event).__name__,
        payload=_to_json(dataclasses.asdict(event)),
        occurred_at=event.occurred_at,
        published_at=None,
    )


def _to_json(value: Any) -> Any:
    """Turn what asdict returns into JSON-safe values. Amounts stay text, never floats."""
    if isinstance(value, dict):
        return {key: _to_json(item) for key, item in value.items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value
