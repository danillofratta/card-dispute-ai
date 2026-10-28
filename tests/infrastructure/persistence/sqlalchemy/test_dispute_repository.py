from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database
from dispute_analyst.infrastructure.persistence.sqlalchemy.dispute_repository import (
    SqlAlchemyDisputeRepository,
)
from dispute_analyst.infrastructure.persistence.sqlalchemy.unit_of_work import (
    SqlAlchemyUnitOfWork,
)

pytestmark = pytest.mark.integration


async def stored_dispute(database: Database, *, day: int, status: DisputeStatus) -> UUID:
    """Save a dispute rebuilt with a fixed opening time and status."""
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
    async with SqlAlchemyUnitOfWork(database.session_factory) as uow:
        await uow.disputes.add(dispute)
        await uow.commit()
    return dispute.id


async def test_lists_oldest_first_and_pages(database: Database) -> None:
    ids = [await stored_dispute(database, day=day, status=DisputeStatus.OPEN) for day in (3, 1, 2)]
    oldest, middle, newest = ids[1], ids[2], ids[0]

    async with database.session_factory() as session:
        repository = SqlAlchemyDisputeRepository(session)
        everything = await repository.list_by_status(None, limit=10, offset=0)
        page = await repository.list_by_status(None, limit=1, offset=1)

    assert [dispute.id for dispute in everything] == [oldest, middle, newest]
    assert [dispute.id for dispute in page] == [middle]


async def test_filters_and_counts_by_status(database: Database) -> None:
    await stored_dispute(database, day=1, status=DisputeStatus.OPEN)
    in_review = await stored_dispute(database, day=2, status=DisputeStatus.MANUAL_REVIEW)

    async with database.session_factory() as session:
        repository = SqlAlchemyDisputeRepository(session)
        listed = await repository.list_by_status(DisputeStatus.MANUAL_REVIEW, limit=10, offset=0)
        in_review_count = await repository.count_by_status(DisputeStatus.MANUAL_REVIEW)
        total = await repository.count_by_status(None)

    assert [dispute.id for dispute in listed] == [in_review]
    assert (in_review_count, total) == (1, 2)


async def test_listed_and_loaded_disputes_are_the_same_object(database: Database) -> None:
    dispute_id = await stored_dispute(database, day=1, status=DisputeStatus.OPEN)

    async with database.session_factory() as session:
        repository = SqlAlchemyDisputeRepository(session)
        [listed] = await repository.list_by_status(None, limit=10, offset=0)

        assert await repository.get_by_id(dispute_id) is listed
