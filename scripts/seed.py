"""Synthetic data: the core bank, merchant orders and 300 disputes with their expected decisions.

Deterministic: the same seed always produces the same data, so evals stay comparable.

    uv run python -m scripts.seed dataset    # rewrite evals/datasets/disputes_v1.jsonl
    uv run python -m scripts.seed database   # load everything into DATABASE_URL, once

Every case has a rule an analyst can check in the data, and the dataset records it as evidence:

| Scenario               | Expected | The data that proves it                                   |
|------------------------|----------|-----------------------------------------------------------|
| duplicate_charge       | approve  | a twin charge: same card, merchant and amount, minutes away |
| repeat_purchase        | deny     | the earlier charge is days away: two separate purchases     |
| card_fraud             | approve  | first charge ever from that merchant, at night, high amount |
| forgotten_subscription | deny     | the card pays that merchant the same amount every month     |
| order_not_delivered    | approve  | the merchant has no proof of delivery                       |
| order_delivered        | deny     | the merchant has a tracking code and a delivery date        |
"""

import argparse
import asyncio
import json
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from dispute_analyst.bootstrap.settings import get_settings
from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.entities.card import Card
from dispute_analyst.domain.entities.customer import Customer
from dispute_analyst.domain.entities.transaction import Transaction
from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.value_objects.approval_limit import ApprovalLimit
from dispute_analyst.domain.value_objects.cpf import Cpf
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.infrastructure.core_banking import seed as fixed
from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import (
    CardModel,
    CustomerModel,
    MerchantOrderModel,
    TransactionModel,
)
from dispute_analyst.infrastructure.persistence.sqlalchemy.unit_of_work import (
    SqlAlchemyUnitOfWork,
)

SEED = 42
CUSTOMERS = 50
CASES_PER_SCENARIO = 50
# The limit the analysis will use: approvals above it wait for a human.
APPROVAL_LIMIT = ApprovalLimit(Money.of("500.00"))
HISTORY_START = datetime(2026, 7, 1, tzinfo=UTC)
HISTORY_DAYS = 90
DATASET_PATH = Path(__file__).resolve().parents[1] / "evals" / "datasets" / "disputes_v1.jsonl"

FIRST_NAMES = (
    "Ana",
    "Bruno",
    "Carla",
    "Daniel",
    "Eduarda",
    "Felipe",
    "Gabriela",
    "Henrique",
    "Isabela",
    "João",
    "Larissa",
    "Marcos",
    "Natália",
    "Otávio",
    "Paula",
    "Rafael",
    "Sofia",
    "Thiago",
    "Vitória",
    "William",
)
LAST_NAMES = (
    "Almeida",
    "Barbosa",
    "Cardoso",
    "Dias",
    "Ferreira",
    "Gomes",
    "Lima",
    "Martins",
    "Nunes",
    "Oliveira",
    "Pereira",
    "Ribeiro",
    "Santos",
    "Teixeira",
    "Vieira",
)
STORES = (
    "Supermercado Bom Preço",
    "Farmácia Saúde",
    "Posto Avenida",
    "Padaria Central",
    "Restaurante Sabor",
    "Livraria Página",
    "Loja de Esportes Ativa",
    "Cinema Plaza",
)
SUBSCRIPTIONS = ("Streaming Plus", "Music Max", "Cloud Drive", "Gym Club", "News Daily")
ONLINE_SHOPS = ("Online Store", "Tech Shop Online", "Moda Express", "Casa & Decor Online")
UNKNOWN_MERCHANTS = (
    "Global Electronics Ltd",
    "Lucky Bet Games",
    "Crypto Exchange Prime",
    "Luxury Watches Intl",
    "Gift Cards World",
)

DESCRIPTIONS = {
    DisputeReason.DUPLICATE_CHARGE: (
        "Fui cobrado duas vezes pela mesma compra.",
        "Apareceram duas cobranças iguais na minha fatura, só fiz uma compra.",
        "A compra foi lançada em duplicidade no meu cartão.",
    ),
    DisputeReason.UNRECOGNIZED_CHARGE: (
        "Não reconheço essa compra, não fui eu que fiz.",
        "Apareceu uma cobrança que eu não reconheço na fatura.",
        "Não sei de onde veio essa cobrança, acho que clonaram meu cartão.",
    ),
    DisputeReason.NOT_DELIVERED: (
        "Comprei pela internet e o produto nunca chegou.",
        "Paguei o pedido e até hoje não recebi nada.",
        "A loja cobrou mas não entregou o produto.",
    ),
}


@dataclass(frozen=True, slots=True)
class MerchantOrder:
    """What the merchant knows about an online order."""

    id: UUID
    transaction_id: UUID
    merchant: str
    delivery_status: str
    tracking_code: str | None
    delivered_at: datetime | None


@dataclass(frozen=True, slots=True)
class Case:
    """One dispute to open, and the decision an analyst should reach."""

    case_id: str
    scenario: str
    customer_id: UUID
    transaction_id: UUID
    reason: DisputeReason
    description: str
    disputed_amount: Money
    expected_outcome: ProposalOutcome
    expected_amount: Money | None
    expected_status: DisputeStatus
    evidence: str

    def to_json(self) -> dict[str, Any]:
        """One line of the dataset."""
        return {
            "case_id": self.case_id,
            "scenario": self.scenario,
            "customer_id": str(self.customer_id),
            "transaction_id": str(self.transaction_id),
            "reason": self.reason.value,
            "description": self.description,
            "disputed_amount": str(self.disputed_amount.amount),
            "currency": self.disputed_amount.currency,
            "expected": {
                "outcome": self.expected_outcome.value,
                "amount": None
                if self.expected_amount is None
                else str(self.expected_amount.amount),
                "status": self.expected_status.value,
            },
            "evidence": self.evidence,
        }


@dataclass
class SyntheticData:
    """Everything the generator produces, in the order it must be loaded."""

    customers: list[Customer] = field(default_factory=list)
    cards: list[Card] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    orders: list[MerchantOrder] = field(default_factory=list)
    cases: list[Case] = field(default_factory=list)


class _Generator:
    """Builds the data with one random generator, so a seed always gives the same result."""

    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)
        self.data = SyntheticData()
        self._cpfs: set[str] = set()

    # --- building blocks ---------------------------------------------------------

    def uuid(self) -> UUID:
        return UUID(int=self.rng.getrandbits(128), version=4)

    def money(self, low: str, high: str) -> Money:
        cents = self.rng.randint(int(Decimal(low) * 100), int(Decimal(high) * 100))
        return Money(Decimal(cents).scaleb(-2))

    def moment(self, *, last_day: int = HISTORY_DAYS) -> datetime:
        day = self.rng.randint(0, last_day - 1)
        hour, minute = self.rng.randint(8, 21), self.rng.randint(0, 59)
        return HISTORY_START + timedelta(days=day, hours=hour, minutes=minute)

    def cpf(self) -> Cpf:
        while True:
            digits = [self.rng.randint(0, 9) for _ in range(9)]
            for size in (9, 10):
                weights = range(size + 1, 1, -1)
                total = sum(digit * weight for digit, weight in zip(digits, weights, strict=True))
                digits.append(total * 10 % 11 % 10)
            text = "".join(map(str, digits))
            if len(set(text)) > 1 and text not in self._cpfs:
                self._cpfs.add(text)
                return Cpf(text)

    def charge(self, card: Card, merchant: str, amount: Money, when: datetime) -> Transaction:
        transaction = Transaction(self.uuid(), card.id, amount, merchant, when)
        self.data.transactions.append(transaction)
        return transaction

    def merchants_of(self, card: Card) -> set[str]:
        return {t.merchant for t in self.data.transactions if t.card_id == card.id}

    def monthly(
        self, card: Card, merchant: str, amount: Money, *, months: int
    ) -> list[Transaction]:
        day = self.rng.randint(1, 28)
        return [
            self.charge(card, merchant, amount, datetime(2026, 7 + month, day, 6, tzinfo=UTC))
            for month in range(months)
        ]

    # --- customers and their normal spending ---------------------------------------

    def add_fixed_customers(self) -> None:
        """Ana and Bruno keep the ids the API examples use, with their cards and charges."""
        self.data.customers += [
            Customer(fixed.CUSTOMER_ANA, "Ana Souza", Cpf("52998224725")),
            Customer(fixed.CUSTOMER_BRUNO, "Bruno Lima", Cpf("11144477735")),
        ]
        self._cpfs |= {"52998224725", "11144477735"}
        self.data.cards += fixed.CARDS
        self.data.transactions += fixed.TRANSACTIONS

    def add_customer(self) -> Card:
        name = f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}"
        customer = Customer(self.uuid(), name, self.cpf())
        self.data.customers.append(customer)
        card = Card(self.uuid(), customer.id, f"{self.rng.randint(0, 9999):04d}")
        self.data.cards.append(card)
        for merchant in self.rng.sample(SUBSCRIPTIONS, k=self.rng.randint(1, 2)):
            self.monthly(card, merchant, self.money("19.90", "89.90"), months=3)
        for _ in range(self.rng.randint(3, 8)):
            self.charge(card, self.rng.choice(STORES), self.money("8.00", "350.00"), self.moment())
        return card

    # --- the six scenarios: each returns False when the card does not fit -----------

    def add_case(
        self,
        scenario: str,
        transaction: Transaction,
        reason: DisputeReason,
        outcome: ProposalOutcome,
        evidence: str,
    ) -> bool:
        card = next(card for card in self.data.cards if card.id == transaction.card_id)
        amount = transaction.amount
        approve = outcome is ProposalOutcome.APPROVE
        if not approve:
            status = DisputeStatus.DENIED
        elif APPROVAL_LIMIT.requires_human(amount):
            status = DisputeStatus.AWAITING_APPROVAL
        else:
            status = DisputeStatus.APPROVED
        self.data.cases.append(
            Case(
                case_id=f"case-{len(self.data.cases) + 1:03d}",
                scenario=scenario,
                customer_id=card.customer_id,
                transaction_id=transaction.id,
                reason=reason,
                description=self.rng.choice(DESCRIPTIONS[reason]),
                disputed_amount=amount,
                expected_outcome=outcome,
                expected_amount=amount if approve else None,
                expected_status=status,
                evidence=evidence,
            )
        )
        return True

    def duplicate_charge(self, card: Card) -> bool:
        merchant = self.rng.choice(ONLINE_SHOPS + STORES)
        amount = self.money("20.00", "700.00")
        first = self.charge(card, merchant, amount, self.moment())
        minutes = self.rng.randint(1, 5)
        twin = self.charge(card, merchant, amount, first.occurred_at + timedelta(minutes=minutes))
        evidence = (
            f"Charge {first.id} has the same card, merchant and amount, {minutes} min earlier."
        )
        reason, outcome = DisputeReason.DUPLICATE_CHARGE, ProposalOutcome.APPROVE
        return self.add_case("duplicate_charge", twin, reason, outcome, evidence)

    def repeat_purchase(self, card: Card) -> bool:
        merchant = self.rng.choice(STORES)
        amount = self.money("20.00", "400.00")
        first = self.charge(card, merchant, amount, self.moment(last_day=HISTORY_DAYS - 25))
        days = self.rng.randint(3, 20)
        again = self.charge(card, merchant, amount, first.occurred_at + timedelta(days=days))
        evidence = f"The earlier charge {first.id} is {days} days apart: two separate purchases."
        reason, outcome = DisputeReason.DUPLICATE_CHARGE, ProposalOutcome.DENY
        return self.add_case("repeat_purchase", again, reason, outcome, evidence)

    def card_fraud(self, card: Card) -> bool:
        unknown = [m for m in UNKNOWN_MERCHANTS if m not in self.merchants_of(card)]
        if not unknown:
            return False
        merchant = self.rng.choice(unknown)
        when = self.moment().replace(hour=self.rng.randint(1, 4))
        charge = self.charge(card, merchant, self.money("150.00", "1800.00"), when)
        evidence = f"First charge ever from {merchant} on this card, at {when:%H:%M}."
        reason, outcome = DisputeReason.UNRECOGNIZED_CHARGE, ProposalOutcome.APPROVE
        return self.add_case("card_fraud", charge, reason, outcome, evidence)

    def forgotten_subscription(self, card: Card) -> bool:
        new_to_card = [m for m in SUBSCRIPTIONS if m not in self.merchants_of(card)]
        if not new_to_card:
            return False
        merchant = self.rng.choice(new_to_card)
        series = self.monthly(card, merchant, self.money("19.90", "89.90"), months=4)
        since = f"{series[0].occurred_at:%Y-%m}"
        evidence = f"The card has paid {merchant} the same amount every month since {since}."
        reason, outcome = DisputeReason.UNRECOGNIZED_CHARGE, ProposalOutcome.DENY
        return self.add_case("forgotten_subscription", series[-1], reason, outcome, evidence)

    def online_order(self, card: Card, *, delivered: bool) -> bool:
        merchant = self.rng.choice(ONLINE_SHOPS)
        when = self.moment(last_day=HISTORY_DAYS - 10)
        charge = self.charge(card, merchant, self.money("40.00", "1200.00"), when)
        if delivered:
            tracking = f"BR{self.rng.randint(10**8, 10**9 - 1)}"
            delivered_at = when + timedelta(days=self.rng.randint(2, 7))
            order = MerchantOrder(
                self.uuid(), charge.id, merchant, "delivered", tracking, delivered_at
            )
            evidence = (
                f"The merchant shows tracking {tracking}, delivered on {delivered_at:%Y-%m-%d}."
            )
            scenario, outcome = "order_delivered", ProposalOutcome.DENY
        else:
            order = MerchantOrder(self.uuid(), charge.id, merchant, "not_delivered", None, None)
            evidence = "The merchant has no tracking code and no delivery date for this order."
            scenario, outcome = "order_not_delivered", ProposalOutcome.APPROVE
        self.data.orders.append(order)
        return self.add_case(scenario, charge, DisputeReason.NOT_DELIVERED, outcome, evidence)


def generate(seed: int = SEED) -> SyntheticData:
    """Build the whole dataset. Pure: no I/O, same seed, same data."""
    generator = _Generator(seed)
    generator.add_fixed_customers()
    cards = [generator.add_customer() for _ in range(CUSTOMERS)]
    scenarios: list[Callable[[Card], bool]] = [
        generator.duplicate_charge,
        generator.repeat_purchase,
        generator.card_fraud,
        generator.forgotten_subscription,
        lambda card: generator.online_order(card, delivered=False),
        lambda card: generator.online_order(card, delivered=True),
    ]
    for scenario in scenarios:
        added = 0
        while added < CASES_PER_SCENARIO:
            # A scenario may refuse a card (it already knows every merchant); try another one.
            if scenario(generator.rng.choice(cards)):
                added += 1
    return generator.data


def write_dataset(data: SyntheticData, path: Path = DATASET_PATH) -> None:
    """One JSON object per line, LF line endings on every OS, so the file diffs cleanly."""
    lines = (json.dumps(case.to_json(), ensure_ascii=False) for case in data.cases)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


async def load(database: Database, data: SyntheticData) -> bool:
    """Load the bank, the orders and the disputes. Returns False if data was already there."""
    async with database.session_factory() as session:
        if await session.scalar(select(func.count()).select_from(CustomerModel)):
            return False
        session.add_all(
            CustomerModel(id=c.id, name=c.name, cpf=c.cpf.digits) for c in data.customers
        )
        await session.flush()
        session.add_all(
            CardModel(id=c.id, customer_id=c.customer_id, last_four=c.last_four) for c in data.cards
        )
        await session.flush()
        session.add_all(
            TransactionModel(
                id=t.id,
                card_id=t.card_id,
                amount=t.amount.amount,
                currency=t.amount.currency,
                merchant=t.merchant,
                occurred_at=t.occurred_at,
            )
            for t in data.transactions
        )
        session.add_all(
            MerchantOrderModel(
                id=o.id,
                transaction_id=o.transaction_id,
                merchant=o.merchant,
                delivery_status=o.delivery_status,
                tracking_code=o.tracking_code,
                delivered_at=o.delivered_at,
            )
            for o in data.orders
        )
        await session.commit()

    # Disputes go through the domain and the unit of work, so the outbox gets real events.
    transactions = {t.id: t for t in data.transactions}
    async with SqlAlchemyUnitOfWork(database.session_factory) as uow:
        for case in data.cases:
            dispute = Dispute.open(
                customer_id=case.customer_id,
                transaction=transactions[case.transaction_id],
                reason=case.reason,
                description=case.description,
                disputed_amount=case.disputed_amount,
            )
            await uow.disputes.add(dispute)
        await uow.commit()
    return True


async def _load_into(url: str, data: SyntheticData) -> None:
    database = Database(url)
    try:
        loaded = await load(database, data)
    finally:
        await database.dispose()
    if loaded:
        print(
            f"Loaded {len(data.customers)} customers, {len(data.transactions)} transactions "
            f"and {len(data.cases)} disputes."
        )
    else:
        print("The database already has data; nothing to do.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("target", choices=("dataset", "database"))
    args = parser.parse_args(argv)
    data = generate()
    if args.target == "dataset":
        write_dataset(data)
        print(f"Wrote {len(data.cases)} cases to {DATASET_PATH}")
        return
    url = get_settings().database_url
    if url is None:
        raise SystemExit("Set DATABASE_URL to load the database, see .env.example")
    asyncio.run(_load_into(url, data))


if __name__ == "__main__":
    main()
