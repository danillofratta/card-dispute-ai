from datetime import UTC, datetime
from uuid import uuid4

import pytest

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.events.dispute_event import AnalysisStarted, DisputeOpened
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore
from dispute_analyst.infrastructure.persistence.memory.unit_of_work import InMemoryUnitOfWork


def open_dispute() -> Dispute:
    transaction = Transaction(
        id=uuid4(),
        card_id=uuid4(),
        amount=Money.of("800"),
        merchant="Online Store",
        occurred_at=datetime(2026, 10, 1, 10, tzinfo=UTC),
    )
    return Dispute.open(
        customer_id=uuid4(),
        transaction=transaction,
        reason=DisputeReason.DUPLICATE_CHARGE,
        description="I was charged twice.",
    )


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


async def test_commit_saves_the_dispute_and_moves_its_events_to_the_outbox(
    store: InMemoryStore,
) -> None:
    dispute = open_dispute()

    async with InMemoryUnitOfWork(store) as uow:
        await uow.disputes.add(dispute)
        await uow.commit()

    assert dispute.id in store.disputes
    [event] = store.outbox
    assert isinstance(event, DisputeOpened)


async def test_nothing_is_saved_without_commit(store: InMemoryStore) -> None:
    async with InMemoryUnitOfWork(store) as uow:
        await uow.disputes.add(open_dispute())

    assert store.disputes == {}
    assert store.outbox == []


async def test_nothing_is_saved_when_the_use_case_fails(store: InMemoryStore) -> None:
    with pytest.raises(RuntimeError):
        async with InMemoryUnitOfWork(store) as uow:
            await uow.disputes.add(open_dispute())
            raise RuntimeError("something went wrong before commit")

    assert store.disputes == {}


async def test_changes_to_a_loaded_dispute_need_a_commit(store: InMemoryStore) -> None:
    dispute = open_dispute()
    async with InMemoryUnitOfWork(store) as uow:
        await uow.disputes.add(dispute)
        await uow.commit()

    async with InMemoryUnitOfWork(store) as uow:
        loaded = await uow.disputes.get_by_id(dispute.id)
        assert loaded is not None
        loaded.start_analysis()
    assert store.disputes[dispute.id].status is DisputeStatus.OPEN

    async with InMemoryUnitOfWork(store) as uow:
        loaded = await uow.disputes.get_by_id(dispute.id)
        assert loaded is not None
        loaded.start_analysis()
        await uow.commit()
    assert store.disputes[dispute.id].status is DisputeStatus.UNDER_ANALYSIS
    assert isinstance(store.outbox[-1], AnalysisStarted)


async def test_get_returns_the_same_object_within_one_unit_of_work(store: InMemoryStore) -> None:
    dispute = open_dispute()
    async with InMemoryUnitOfWork(store) as uow:
        await uow.disputes.add(dispute)
        await uow.commit()

    async with InMemoryUnitOfWork(store) as uow:
        assert await uow.disputes.get_by_id(dispute.id) is await uow.disputes.get_by_id(dispute.id)


async def test_get_returns_none_for_an_unknown_id(store: InMemoryStore) -> None:
    async with InMemoryUnitOfWork(store) as uow:
        assert await uow.disputes.get_by_id(uuid4()) is None


async def test_adding_the_same_dispute_twice_is_an_error(store: InMemoryStore) -> None:
    dispute = open_dispute()

    async with InMemoryUnitOfWork(store) as uow:
        await uow.disputes.add(dispute)
        with pytest.raises(ValueError):
            await uow.disputes.add(dispute)
