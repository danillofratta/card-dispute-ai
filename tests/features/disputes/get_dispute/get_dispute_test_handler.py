from uuid import uuid4

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.features.disputes.get_dispute.handler import GetDisputeHandler
from dispute_analyst.features.disputes.get_dispute.query import GetDisputeQuery
from dispute_analyst.infrastructure.core_banking.seed import CUSTOMER_ANA, TRANSACTIONS
from dispute_analyst.infrastructure.core_banking.simulated_core_banking import (
    SimulatedCoreBanking,
)
from dispute_analyst.infrastructure.persistence.memory.dispute_repository import (
    InMemoryDisputeRepository,
)
from dispute_analyst.infrastructure.persistence.memory.store import InMemoryStore


def stored_dispute(store: InMemoryStore) -> Dispute:
    dispute = Dispute.open(
        customer_id=CUSTOMER_ANA,
        transaction=TRANSACTIONS[0],
        reason=DisputeReason.NOT_DELIVERED,
        description="The order never arrived.",
    )
    store.disputes[dispute.id] = dispute
    return dispute


async def test_adds_the_merchant_and_card_from_the_bank() -> None:
    store = InMemoryStore()
    dispute = stored_dispute(store)
    handler = GetDisputeHandler(InMemoryDisputeRepository(store), SimulatedCoreBanking())

    result = await handler.handle(GetDisputeQuery(dispute_id=dispute.id))

    assert result is not None
    assert result.id == dispute.id
    assert result.merchant == "Online Store"
    assert result.card_last_four == "4242"


async def test_unknown_dispute_is_none() -> None:
    store = InMemoryStore()
    handler = GetDisputeHandler(InMemoryDisputeRepository(store), SimulatedCoreBanking())

    assert await handler.handle(GetDisputeQuery(dispute_id=uuid4())) is None


async def test_missing_bank_data_leaves_those_fields_empty() -> None:
    store = InMemoryStore()
    dispute = stored_dispute(store)
    bank = SimulatedCoreBanking(cards=[], transactions=[])
    handler = GetDisputeHandler(InMemoryDisputeRepository(store), bank)

    result = await handler.handle(GetDisputeQuery(dispute_id=dispute.id))

    assert result is not None
    assert result.merchant is None
    assert result.card_last_four is None
