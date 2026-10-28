import json
from collections import Counter
from datetime import timedelta

import pytest

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.infrastructure.core_banking.seed import CUSTOMER_ANA, CUSTOMER_BRUNO
from dispute_analyst.infrastructure.merchants.seed import ORDERS
from scripts.seed import DATASET_PATH, Case, SyntheticData, generate


@pytest.fixture(scope="module")
def data() -> SyntheticData:
    return generate()


def same_charge(a: Transaction, b: Transaction) -> bool:
    return (a.card_id, a.merchant, a.amount) == (b.card_id, b.merchant, b.amount)


def others_like(data: SyntheticData, transaction: Transaction) -> list[Transaction]:
    return [t for t in data.transactions if t.id != transaction.id and same_charge(t, transaction)]


def cases(data: SyntheticData, scenario: str) -> list[Case]:
    return [case for case in data.cases if case.scenario == scenario]


def test_the_same_seed_always_gives_the_same_data(data: SyntheticData) -> None:
    again = generate()

    assert [case.to_json() for case in again.cases] == [case.to_json() for case in data.cases]
    assert again.transactions == data.transactions


def test_the_committed_dataset_is_up_to_date(data: SyntheticData) -> None:
    """Fails when the generator changed: run `uv run python -m scripts.seed dataset`."""
    committed = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines()]

    assert committed == [case.to_json() for case in data.cases]


def test_300_cases_balanced_by_reason_and_outcome(data: SyntheticData) -> None:
    by_scenario = Counter(case.scenario for case in data.cases)

    assert len(data.cases) == 300
    assert set(by_scenario.values()) == {50}
    assert len(by_scenario) == 6


def test_ana_and_bruno_keep_their_fixed_ids(data: SyntheticData) -> None:
    ids = {customer.id for customer in data.customers}

    assert {CUSTOMER_ANA, CUSTOMER_BRUNO} <= ids


def test_ana_and_bruno_keep_their_fixed_orders(data: SyntheticData) -> None:
    assert set(ORDERS) <= set(data.orders)


def test_every_case_opens_a_valid_dispute(data: SyntheticData) -> None:
    transactions = {t.id: t for t in data.transactions}
    owners = {card.id: card.customer_id for card in data.cards}

    for case in data.cases:
        transaction = transactions[case.transaction_id]
        assert owners[transaction.card_id] == case.customer_id
        Dispute.open(
            customer_id=case.customer_id,
            transaction=transaction,
            reason=case.reason,
            description=case.description,
            disputed_amount=case.disputed_amount,
        )


def test_expected_status_follows_the_approval_limit(data: SyntheticData) -> None:
    for case in data.cases:
        if case.expected_status is DisputeStatus.AWAITING_APPROVAL:
            assert case.expected_amount is not None
            assert case.expected_amount.amount > 500


# --- each scenario's rule can be checked in the data ---------------------------------


def test_duplicate_charges_have_a_twin_minutes_away(data: SyntheticData) -> None:
    transactions = {t.id: t for t in data.transactions}
    for case in cases(data, "duplicate_charge"):
        disputed = transactions[case.transaction_id]
        assert any(
            abs(t.occurred_at - disputed.occurred_at) <= timedelta(minutes=10)
            for t in others_like(data, disputed)
        )


def test_repeat_purchases_have_no_twin_on_the_same_day(data: SyntheticData) -> None:
    transactions = {t.id: t for t in data.transactions}
    for case in cases(data, "repeat_purchase"):
        disputed = transactions[case.transaction_id]
        assert all(
            abs(t.occurred_at - disputed.occurred_at) > timedelta(days=1)
            for t in others_like(data, disputed)
        )


def test_fraud_is_the_first_charge_from_that_merchant(data: SyntheticData) -> None:
    transactions = {t.id: t for t in data.transactions}
    for case in cases(data, "card_fraud"):
        disputed = transactions[case.transaction_id]
        same_merchant = [
            t
            for t in data.transactions
            if t.card_id == disputed.card_id and t.merchant == disputed.merchant
        ]
        assert same_merchant == [disputed]


def test_forgotten_subscriptions_were_paid_every_month_before(data: SyntheticData) -> None:
    transactions = {t.id: t for t in data.transactions}
    for case in cases(data, "forgotten_subscription"):
        disputed = transactions[case.transaction_id]
        earlier = [t for t in others_like(data, disputed) if t.occurred_at < disputed.occurred_at]
        assert len(earlier) >= 3


@pytest.mark.parametrize(
    ("scenario", "status"),
    [("order_delivered", "delivered"), ("order_not_delivered", "not_delivered")],
)
def test_orders_carry_the_delivery_proof(data: SyntheticData, scenario: str, status: str) -> None:
    orders = {order.transaction_id: order for order in data.orders}
    for case in cases(data, scenario):
        order = orders[case.transaction_id]
        assert order.delivery_status == status
        assert (order.tracking_code is not None) == (status == "delivered")
