"""Merchant orders: proof of delivery for not-delivered disputes, in their own schema.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MERCHANTS = "merchants"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {MERCHANTS}")
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("merchant", sa.String(), nullable=False),
        sa.Column("delivery_status", sa.String(length=16), nullable=False),
        sa.Column("tracking_code", sa.String(length=32), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("transaction_id", name=op.f("uq_orders_transaction_id")),
        schema=MERCHANTS,
    )


def downgrade() -> None:
    op.drop_table("orders", schema=MERCHANTS)
    op.execute(f"DROP SCHEMA IF EXISTS {MERCHANTS}")
