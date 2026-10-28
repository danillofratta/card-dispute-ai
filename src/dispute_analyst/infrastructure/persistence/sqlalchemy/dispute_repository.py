"""DisputeRepository over Postgres, bound to one SQLAlchemy session."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dispute_analyst.domain.aggregates.dispute import Dispute
from dispute_analyst.domain.enums.dispute_status import DisputeStatus
from dispute_analyst.infrastructure.persistence.sqlalchemy.mappers import dispute_from_model
from dispute_analyst.infrastructure.persistence.sqlalchemy.models import DisputeModel


class SqlAlchemyDisputeRepository:
    """Tracks every dispute loaded or added, so the unit of work can save them on commit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tracked: dict[UUID, Dispute] = {}

    async def get_by_id(self, dispute_id: UUID) -> Dispute | None:
        """Retrieve a dispute by its ID, or return None if not found."""
        if dispute_id in self._tracked:
            return self._tracked[dispute_id]
        model = await self._session.get(DisputeModel, dispute_id)
        return None if model is None else self._load(model)

    async def add(self, dispute: Dispute) -> None:
        """Stage a new dispute; it is inserted when the unit of work commits."""
        if dispute.id in self._tracked:
            raise ValueError(f"Dispute with ID {dispute.id} already exists.")
        self._tracked[dispute.id] = dispute

    async def list_by_status(
        self, status: DisputeStatus | None, *, limit: int, offset: int
    ) -> list[Dispute]:
        """Oldest first; the id breaks ties so the order never changes between calls."""
        query = select(DisputeModel).order_by(DisputeModel.opened_at, DisputeModel.id)
        if status is not None:
            query = query.where(DisputeModel.status == status.value)
        models = await self._session.scalars(query.limit(limit).offset(offset))
        return [self._load(model) for model in models]

    async def count_by_status(self, status: DisputeStatus | None) -> int:
        """Count disputes in this status, or all of them when status is None."""
        query = select(func.count()).select_from(DisputeModel)
        if status is not None:
            query = query.where(DisputeModel.status == status.value)
        return await self._session.scalar(query) or 0

    def tracked(self) -> list[Dispute]:
        """Return a list of all tracked disputes."""
        return list(self._tracked.values())

    def _load(self, model: DisputeModel) -> Dispute:
        """Return this repository's aggregate for a row, the same one on every load."""
        if model.id not in self._tracked:
            self._tracked[model.id] = dispute_from_model(model)
        return self._tracked[model.id]
