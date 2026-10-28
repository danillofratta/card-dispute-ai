from uuid import uuid4

import pytest

from dispute_analyst.domain.enums.dispute_reason import DisputeReason
from dispute_analyst.domain.value_objects.money import Money
from dispute_analyst.features.disputes.analyze_dispute.exceptions import (
    AnalyzeDisputeUnavailableError,
)
from dispute_analyst.features.disputes.analyze_dispute.gateway import (
    DisputeCaseDto,
)
from dispute_analyst.infrastructure.agents.unavailable_analyzer import UnavailableAnalyzer


async def test_never_proposes_and_says_why() -> None:
    case = DisputeCaseDto(
        dispute_id=uuid4(),
        transaction_id=uuid4(),
        reason=DisputeReason.NOT_DELIVERED,
        description="O produto nunca chegou.",
        disputed_amount=Money.of("99.90"),
    )

    with pytest.raises(AnalyzeDisputeUnavailableError, match="no LLM configured"):
        await UnavailableAnalyzer("no LLM configured").analyze(case)
