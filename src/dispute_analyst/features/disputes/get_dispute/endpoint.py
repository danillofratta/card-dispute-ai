"""HTTP adapter of get_dispute: GET /disputes/{dispute_id}."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dispute_analyst.bootstrap.dependencies import (
    CoreBankingDependency,
    DisputeRepositoryDependency,
)
from dispute_analyst.features.disputes.get_dispute.handler import GetDisputeHandler
from dispute_analyst.features.disputes.get_dispute.models import GetDisputeResponse
from dispute_analyst.features.disputes.get_dispute.query import GetDisputeQuery

router = APIRouter(prefix="/disputes", tags=["Disputes"])


def get_handler(
    disputes: DisputeRepositoryDependency, core_banking: CoreBankingDependency
) -> GetDisputeHandler:
    """Build the handler from the ports the composition root provides."""
    return GetDisputeHandler(disputes, core_banking)


@router.get(
    "/{dispute_id}",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Dispute not found"}},
)
async def get_dispute(
    dispute_id: UUID,
    handler: Annotated[GetDisputeHandler, Depends(get_handler)],
) -> GetDisputeResponse:
    """Show one dispute, with the merchant and the card it was charged on."""
    result = await handler.handle(GetDisputeQuery(dispute_id=dispute_id))
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="dispute not found")
    return GetDisputeResponse.from_result(result)
