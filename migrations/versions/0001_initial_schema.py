"""Initial schema: disputes and outbox, plus the simulated core bank in its own schema.

Revision ID: 0001
Revises:
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_BANKING = "core_banking"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {CORE_BANKING}")

    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customers")),
        sa.UniqueConstraint("cpf", name=op.f("uq_customers_cpf")),
        schema=CORE_BANKING,
    )
    op.create_table(
        "cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("last_four", sa.String(length=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            [f"{CORE_BANKING}.customers.id"],
            name=op.f("fk_cards_customer_id_customers"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cards")),
        schema=CORE_BANKING,
    )
    op.create_index(
        op.f("ix_core_banking_cards_customer_id"),
        "cards",
        ["customer_id"],
        schema=CORE_BANKING,
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("merchant", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("ck_transactions_positive_amount")),
        sa.ForeignKeyConstraint(
            ["card_id"],
            [f"{CORE_BANKING}.cards.id"],
            name=op.f("fk_transactions_card_id_cards"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
        schema=CORE_BANKING,
    )
    op.create_index(
        op.f("ix_core_banking_transactions_card_id"),
        "transactions",
        ["card_id"],
        schema=CORE_BANKING,
    )

    op.create_table(
        "disputes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("disputed_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_disputes")),
    )
    op.create_index(op.f("ix_disputes_customer_id"), "disputes", ["customer_id"])
    op.create_index(op.f("ix_disputes_transaction_id"), "disputes", ["transaction_id"])
    op.create_index("ix_disputes_queue", "disputes", ["status", "opened_at", "id"])

    op.create_table(
        "outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dispute_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox")),
    )
    op.create_index(op.f("ix_outbox_dispute_id"), "outbox", ["dispute_id"])
    op.create_index(
        "ix_outbox_unpublished",
        "outbox",
        ["occurred_at"],
        postgresql_where=sa.text("published_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("outbox")
    op.drop_table("disputes")
    op.drop_table("transactions", schema=CORE_BANKING)
    op.drop_table("cards", schema=CORE_BANKING)
    op.drop_table("customers", schema=CORE_BANKING)
    op.execute(f"DROP SCHEMA IF EXISTS {CORE_BANKING}")
