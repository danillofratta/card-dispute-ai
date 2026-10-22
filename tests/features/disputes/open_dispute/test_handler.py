from uuid import uuid4

import pytest

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.events.dispute_event import DisputeOpened
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.features.disputes.open_dispute.command import OpenDisputeCommand
from dispute_analyst.features.disputes.open_dispute.exceptions import TransactionNotFoundError
from dispute_analyst.features.disputes.open_dispute.handler import OpenDisputeHandler
from dispute_analyst.infrastructure.core_banking.seed import (
    CUSTOMER_ANA,
    CUSTOMER_BRUNO,
    TX_ANA_STREAMING_AGAIN,
)
from dispute_analyst.infrastructure.core_banking.simulated_core_banking import (
    SimulatedCoreBanking,
)
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore
from dispute_analyst.infrastructure.persistence.memory.unit_of_work import InMemoryUnitOfWork


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def handler(store: InMemoryStore) -> OpenDisputeHandler:
    return OpenDisputeHandler(InMemoryUnitOfWork(store), SimulatedCoreBanking())


def command(**changes: object) -> OpenDisputeCommand:
    values: dict[str, object] = {
        "customer_id": CUSTOMER_ANA,
        "transaction_id": TX_ANA_STREAMING_AGAIN,
        "reason": DisputeReason.DUPLICATE_CHARGE,
        "description": "I was charged twice for the same subscription.",
    }
    values.update(changes)
    return OpenDisputeCommand(**values)  # type: ignore[arg-type]


async def test_opens_and_saves_the_dispute_with_its_event(
    handler: OpenDisputeHandler, store: InMemoryStore
) -> None:
    result = await handler.handle(command())

    assert result.status is DisputeStatus.OPEN
    saved = store.disputes[result.dispute_id]
    assert saved.disputed_amount == Money.of("129.90")
    [event] = store.outbox
    assert isinstance(event, DisputeOpened)


async def test_disputes_part_of_the_transaction(
    handler: OpenDisputeHandler, store: InMemoryStore
) -> None:
    result = await handler.handle(command(disputed_amount=Money.of("50")))

    assert store.disputes[result.dispute_id].disputed_amount == Money.of("50")


async def test_unknown_transaction(handler: OpenDisputeHandler, store: InMemoryStore) -> None:
    with pytest.raises(TransactionNotFoundError):
        await handler.handle(command(transaction_id=uuid4()))

    assert store.disputes == {}


async def test_someone_elses_transaction_looks_unknown(
    handler: OpenDisputeHandler, store: InMemoryStore
) -> None:
    with pytest.raises(TransactionNotFoundError):
        await handler.handle(command(customer_id=CUSTOMER_BRUNO))

    assert store.disputes == {}


async def test_domain_rules_still_apply(handler: OpenDisputeHandler, store: InMemoryStore) -> None:
    with pytest.raises(ValueError):
        await handler.handle(command(disputed_amount=Money.of("500")))

    assert store.disputes == {}
