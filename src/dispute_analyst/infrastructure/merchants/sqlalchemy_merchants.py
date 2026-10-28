"""Merchants over the merchants schema in Postgres.

The anti-corruption layer for the merchants: it reads their orders table and translates each
row into our MerchantOrder.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dispute_analyst.domain.entities.merchant_order import MerchantOrder
from dispute_analyst.domain.enums.delivery_status import DeliveryStatus
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import MerchantOrderModel


class SqlAlchemyMerchants:
    """Each call uses its own short session, like SqlAlchemyCoreBanking."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_order_by_transaction(self, transaction_id: UUID) -> MerchantOrder | None:
        """Return the order this transaction paid for, or None if there is none."""
        statement = select(MerchantOrderModel).where(
            MerchantOrderModel.transaction_id == transaction_id
        )
        async with self._session_factory() as session:
            row = await session.scalar(statement)
        if row is None:
            return None
        return MerchantOrder(
            id=row.id,
            transaction_id=row.transaction_id,
            merchant=row.merchant,
            delivery_status=DeliveryStatus(row.delivery_status),
            tracking_code=row.tracking_code,
            delivered_at=row.delivered_at,
        )
