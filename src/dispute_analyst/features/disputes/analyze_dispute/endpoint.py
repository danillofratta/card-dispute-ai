"""HTTP adapter of analyze_dispute: POST /disputes/{dispute_id}/analysis."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dispute_analyst.bootstrap.dependencies import UnitOfWorkDependency
from dispute_analyst.bootstrap.disputes.analyze_dispute import (
    ApprovalLimitDependency,
    DisputeAnalyzerDependency,
)
from dispute_analyst.domain.exceptions import InvalidTransitionError
from dispute_analyst.features.disputes.analyze_dispute.command import AnalyzeDisputeCommand
from dispute_analyst.features.disputes.analyze_dispute.exceptions import AnalyzeDisputeNotFoundError
from dispute_analyst.features.disputes.analyze_dispute.handler import AnalyzeDisputeHandler
from dispute_analyst.features.disputes.analyze_dispute.models import AnalyzeDisputeResponse

router = APIRouter(prefix="/disputes", tags=["Disputes"])


def get_handler(
    unit_of_work: UnitOfWorkDependency,
    analyzer: DisputeAnalyzerDependency,
    limit: ApprovalLimitDependency,
) -> AnalyzeDisputeHandler:
    """Build the handler from the shared providers and the slice's own ones."""
    return AnalyzeDisputeHandler(unit_of_work, analyzer, limit)


@router.post(
    "/{dispute_id}/analysis",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Dispute not found"},
        status.HTTP_409_CONFLICT: {"description": "The dispute is not open"},
    },
)
async def analyze_dispute(
    dispute_id: UUID,
    handler: Annotated[AnalyzeDisputeHandler, Depends(get_handler)],
) -> AnalyzeDisputeResponse:
    """Let the agent analyze an open dispute; the domain decides.

    A failed analysis is not an error: the dispute goes to manual review.
    """
    try:
        result = await handler.handle(AnalyzeDisputeCommand(dispute_id=dispute_id))
    except AnalyzeDisputeNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InvalidTransitionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error

    return AnalyzeDisputeResponse.from_result(result)
