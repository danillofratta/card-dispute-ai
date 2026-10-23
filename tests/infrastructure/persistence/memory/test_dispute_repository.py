from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.persistence.memory.dispute_repository import (
    InMemoryDisputeRepository,
)
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore


def stored_dispute(store: InMemoryStore, *, day: int, status: DisputeStatus) -> UUID:
    """Rebuild a dispute as the repository would load it, with a fixed opening time."""
    dispute = Dispute(
        dispute_id=uuid4(),
        customer_id=uuid4(),
        transaction_id=uuid4(),
        reason=DisputeReason.NOT_DELIVERED,
        description="The order never arrived.",
        disputed_amount=Money.of("150"),
        status=status,
        opened_at=datetime(2026, 10, day, tzinfo=UTC),
    )
    store.disputes[dispute.id] = dispute
    return dispute.id


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


async def test_lists_oldest_first(store: InMemoryStore) -> None:
    newest = stored_dispute(store, day=3, status=DisputeStatus.OPEN)
    oldest = stored_dispute(store, day=1, status=DisputeStatus.OPEN)
    middle = stored_dispute(store, day=2, status=DisputeStatus.OPEN)

    disputes = await InMemoryDisputeRepository(store).list_by_status(None, limit=10, offset=0)

    assert [dispute.id for dispute in disputes] == [oldest, middle, newest]


async def test_lists_and_counts_one_status(store: InMemoryStore) -> None:
    stored_dispute(store, day=1, status=DisputeStatus.OPEN)
    in_review = stored_dispute(store, day=2, status=DisputeStatus.MANUAL_REVIEW)
    repository = InMemoryDisputeRepository(store)

    disputes = await repository.list_by_status(DisputeStatus.MANUAL_REVIEW, limit=10, offset=0)

    assert [dispute.id for dispute in disputes] == [in_review]
    assert await repository.count_by_status(DisputeStatus.MANUAL_REVIEW) == 1
    assert await repository.count_by_status(None) == 2


async def test_lists_one_page(store: InMemoryStore) -> None:
    ids = [stored_dispute(store, day=day, status=DisputeStatus.OPEN) for day in range(1, 6)]

    disputes = await InMemoryDisputeRepository(store).list_by_status(None, limit=2, offset=2)

    assert [dispute.id for dispute in disputes] == ids[2:4]


async def test_listed_and_loaded_disputes_are_the_same_object(store: InMemoryStore) -> None:
    dispute_id = stored_dispute(store, day=1, status=DisputeStatus.OPEN)
    repository = InMemoryDisputeRepository(store)

    [listed] = await repository.list_by_status(None, limit=10, offset=0)

    assert await repository.get_by_id(dispute_id) is listed
