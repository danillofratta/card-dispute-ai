from decimal import Decimal

import pytest
from sqlalchemy import select

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.core_banking.seed import CUSTOMER_ANA, TRANSACTIONS
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import (
    DisputeModel,
    OutboxEventModel,
)
from dispute_analyst.infrastructure.persistence.sqlalchemy.unit_of_work import (
    SqlAlchemyUnitOfWork,
)

pytestmark = pytest.mark.integration


def open_dispute() -> Dispute:
    return Dispute.open(
        customer_id=CUSTOMER_ANA,
        transaction=TRANSACTIONS[2],
        reason=DisputeReason.DUPLICATE_CHARGE,
        description="I was charged twice.",
    )


async def save(database: Database, dispute: Dispute) -> None:
    async with SqlAlchemyUnitOfWork(database.session_factory) as uow:
        await uow.disputes.add(dispute)
        await uow.commit()


async def outbox_types(database: Database) -> list[str]:
    async with database.session_factory() as session:
        query = select(OutboxEventModel.event_type).order_by(OutboxEventModel.occurred_at)
        return list(await session.scalars(query))


async def test_commit_saves_the_dispute_and_its_event_together(database: Database) -> None:
    dispute = open_dispute()

    await save(database, dispute)

    async with database.session_factory() as session:
        row = await session.get(DisputeModel, dispute.id)
        event = await session.scalar(select(OutboxEventModel))
    assert row is not None
    assert row.status == "open"
    assert row.disputed_amount == Decimal("129.90")
    assert event is not None
    assert event.event_type == "DisputeOpened"
    assert event.payload["disputed_amount"] == {"amount": "129.90", "currency": "BRL"}


async def test_nothing_is_saved_without_commit(database: Database) -> None:
    async with SqlAlchemyUnitOfWork(database.session_factory) as uow:
        await uow.disputes.add(open_dispute())

    assert await outbox_types(database) == []


async def test_changes_to_a_loaded_dispute_are_saved_on_commit(database: Database) -> None:
    dispute = open_dispute()
    await save(database, dispute)

    async with SqlAlchemyUnitOfWork(database.session_factory) as uow:
        loaded = await uow.disputes.get_by_id(dispute.id)
        assert loaded is not None
        loaded.start_analysis()
        await uow.commit()

    async with database.session_factory() as session:
        row = await session.get(DisputeModel, dispute.id)
    assert row is not None
    assert row.status == "under_analysis"
    assert await outbox_types(database) == ["DisputeOpened", "AnalysisStarted"]


async def test_a_reloaded_dispute_keeps_every_field(database: Database) -> None:
    dispute = open_dispute()
    dispute.start_analysis()
    proposal = DecisionProposal(
        ProposalOutcome.APPROVE, "Duplicate charge.", ("Policy 4.2",), Money.of("100")
    )
    dispute.apply_proposal(proposal, ApprovalLimit(Money.of("500")))
    await save(database, dispute)

    async with SqlAlchemyUnitOfWork(database.session_factory) as uow:
        loaded = await uow.disputes.get_by_id(dispute.id)

    assert loaded is not None
    assert loaded.status is DisputeStatus.APPROVED
    assert loaded.approved_amount == Money.of("100")
    assert loaded.disputed_amount == dispute.disputed_amount
    assert loaded.opened_at == dispute.opened_at
    assert loaded.description == dispute.description
