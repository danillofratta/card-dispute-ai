"""Postgres tables as SQLAlchemy models. Infrastructure only: the domain never sees them."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, MetaData, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# The core bank lives in its own schema: another bounded context, reached only through CoreBanking.
CORE_BANKING_SCHEMA = "core_banking"

# Merchants know whether an order was delivered: another bounded context, linked by id only.
MERCHANTS_SCHEMA = "merchants"

# Predictable constraint names, so migrations can always find them again.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base of every table model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {  # noqa: RUF012 - SQLAlchemy reads this class attribute
        datetime: DateTime(timezone=True),
        Decimal: Numeric(12, 2),
    }


class CustomerModel(Base):
    """A core bank customer."""

    __tablename__ = "customers"
    __table_args__ = {"schema": CORE_BANKING_SCHEMA}  # noqa: RUF012

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str]
    cpf: Mapped[str] = mapped_column(String(11), unique=True)


class CardModel(Base):
    """A card; only the last four digits are stored."""

    __tablename__ = "cards"
    __table_args__ = {"schema": CORE_BANKING_SCHEMA}  # noqa: RUF012

    id: Mapped[UUID] = mapped_column(primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{CORE_BANKING_SCHEMA}.customers.id"), index=True
    )
    last_four: Mapped[str] = mapped_column(String(4))


class TransactionModel(Base):
    """A charge on a card."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),
        {"schema": CORE_BANKING_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    card_id: Mapped[UUID] = mapped_column(ForeignKey(f"{CORE_BANKING_SCHEMA}.cards.id"), index=True)
    amount: Mapped[Decimal]
    currency: Mapped[str] = mapped_column(String(3))
    merchant: Mapped[str]
    occurred_at: Mapped[datetime]


class DisputeModel(Base):
    """The current state of a Dispute aggregate.

    No foreign keys to core_banking: the bank is another bounded context, linked by id only.
    """

    __tablename__ = "disputes"
    __table_args__ = (Index("ix_disputes_queue", "status", "opened_at", "id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(index=True)
    transaction_id: Mapped[UUID] = mapped_column(index=True)
    reason: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    description: Mapped[str]
    currency: Mapped[str] = mapped_column(String(3))
    disputed_amount: Mapped[Decimal]
    approved_amount: Mapped[Decimal | None]
    opened_at: Mapped[datetime]


class OutboxEventModel(Base):
    """A domain event saved in the same transaction as the aggregate, waiting to be published."""

    __tablename__ = "outbox"
    __table_args__ = (
        Index(
            "ix_outbox_unpublished",
            "occurred_at",
            postgresql_where=text("published_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    dispute_id: Mapped[UUID] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime]
    published_at: Mapped[datetime | None]


class MerchantOrderModel(Base):
    """An order as the merchant knows it: was the product delivered?

    Linked to the bank transaction by id only: the merchant is another bounded context.
    """

    __tablename__ = "orders"
    __table_args__ = {"schema": MERCHANTS_SCHEMA}  # noqa: RUF012

    id: Mapped[UUID] = mapped_column(primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(unique=True)
    merchant: Mapped[str]
    delivery_status: Mapped[str] = mapped_column(String(16))
    tracking_code: Mapped[str | None] = mapped_column(String(32))
    delivered_at: Mapped[datetime | None]
