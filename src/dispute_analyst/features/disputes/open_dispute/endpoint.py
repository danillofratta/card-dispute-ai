"""HTTP adapter of open_dispute: POST /disputes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from dispute_analyst.bootstrap.dependencies import CoreBankingDependency, UnitOfWorkDependency
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.features.disputes.open_dispute.command import OpenDisputeCommand
from dispute_analyst.features.disputes.open_dispute.exceptions import TransactionNotFoundError
from dispute_analyst.features.disputes.open_dispute.handler import OpenDisputeHandler
from dispute_analyst.features.disputes.open_dispute.models import (
    OpenDisputeRequest,
    OpenDisputeResponse,
)

router = APIRouter(prefix="/disputes", tags=["Disputes"])


def get_handler(
    unit_of_work: UnitOfWorkDependency, core_banking: CoreBankingDependency
) -> OpenDisputeHandler:
    """Build the handler from the ports the composition root provides."""
    return OpenDisputeHandler(unit_of_work, core_banking)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Transaction not found for this customer"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid dispute"},
    },
)
async def open_dispute(
    request: OpenDisputeRequest,
    handler: Annotated[OpenDisputeHandler, Depends(get_handler)],
) -> OpenDisputeResponse:
    """Open a dispute for one card transaction."""
    amount = None if request.disputed_amount is None else Money.of(request.disputed_amount)
    command = OpenDisputeCommand(
        customer_id=request.customer_id,
        transaction_id=request.transaction_id,
        reason=request.reason,
        description=request.description,
        disputed_amount=amount,
    )
    try:
        result = await handler.handle(command)
    except TransactionNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        # The domain rejected the input, for example an amount above the transaction.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    return OpenDisputeResponse(id=result.dispute_id, status=result.status)
