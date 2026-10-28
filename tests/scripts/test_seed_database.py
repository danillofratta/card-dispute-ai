import pytest
from sqlalchemy import func, select

from dispute_analyst.infrastructure.persistence.sqlalchemy.database import Database
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import (
    CustomerModel,
    DisputeModel,
    MerchantOrderModel,
    OutboxEventModel,
    TransactionModel,
)
from scripts.seed import generate, load

pytestmark = pytest.mark.integration

MODELS = (CustomerModel, TransactionModel, MerchantOrderModel, DisputeModel, OutboxEventModel)


async def counts(database: Database) -> list[int]:
    async with database.session_factory() as session:
        return [
            await session.scalar(select(func.count()).select_from(model)) or 0 for model in MODELS
        ]


async def test_loads_everything_once(empty_database: Database) -> None:
    data = generate()

    assert await load(empty_database, data) is True
    loaded = await counts(empty_database)
    assert loaded == [
        len(data.customers),
        len(data.transactions),
        len(data.orders),
        len(data.cases),
        len(data.cases),  # one DisputeOpened event per dispute
    ]

    assert await load(empty_database, data) is False
    assert await counts(empty_database) == loaded
