"""Alembic environment: runs migrations with the async engine and the app's settings."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from dispute_analyst.bootstrap.settings import get_settings
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# Our schemas: the default one plus every schema a table model declares.
SCHEMAS = {None, "public"} | {table.schema for table in target_metadata.tables.values()}


def include_name(name: str | None, type_: str, parent_names: object) -> bool:
    """Compare only our schemas, so autogenerate and `alembic check` ignore anything else."""
    return name in SCHEMAS if type_ == "schema" else True


def database_url() -> str:
    url = get_settings().database_url
    if url is None:
        raise RuntimeError("Set DATABASE_URL to run migrations, see .env.example")
    return url


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (`alembic upgrade head --sql`)."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
