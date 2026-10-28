from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dispute_analyst.bootstrap.disputes.analyze_dispute import get_dispute_analyzer
from dispute_analyst.domain.enums.proposal_outcome import ProposalOutcome
from dispute_analyst.domain.value_objects.decision_proposal import DecisionProposal
from dispute_analyst.features.disputes.analyze_dispute.gateway import DisputeCaseDto
from dispute_analyst.infrastructure.agents.unavailable_analyzer import UnavailableAnalyzer
from dispute_analyst.infrastructure.core_banking.seed import (
    CUSTOMER_ANA,
    TX_ANA_STREAMING,
    TX_ANA_STREAMING_AGAIN,
)

CITATION = f"transaction:{TX_ANA_STREAMING}"


class ApprovingAnalyzer:
    """Approves the whole disputed amount, citing the twin charge."""

    async def analyze(self, case: DisputeCaseDto) -> DecisionProposal:
        return DecisionProposal(
            outcome=ProposalOutcome.APPROVE,
            justification="Same card, merchant and amount one minute apart.",
            citations=(CITATION,),
            amount=case.disputed_amount,
        )


@pytest.fixture
def approving(app: FastAPI, client: TestClient) -> TestClient:
    """The client, with an analyzer that approves: no real model in unit tests."""
    app.dependency_overrides[get_dispute_analyzer] = ApprovingAnalyzer
    return client


@pytest.fixture
def unavailable(app: FastAPI, client: TestClient) -> TestClient:
    """The client, with an analyzer that cannot answer, like a model that is down."""
    app.dependency_overrides[get_dispute_analyzer] = lambda: UnavailableAnalyzer("model is down")
    return client


def open_dispute(client: TestClient) -> str:
    response = client.post(
        "/disputes",
        json={
            "customer_id": str(CUSTOMER_ANA),
            "transaction_id": str(TX_ANA_STREAMING_AGAIN),
            "reason": "duplicate_charge",
            "description": "Fui cobrado duas vezes pela mesma assinatura.",
        },
    )
    assert response.status_code == 201
    dispute_id: str = response.json()["id"]
    return dispute_id


def test_the_agent_proposes_and_the_domain_approves(approving: TestClient) -> None:
    dispute_id = open_dispute(approving)

    response = approving.post(f"/disputes/{dispute_id}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["proposal"] == {
        "outcome": "approve",
        "justification": "Same card, merchant and amount one minute apart.",
        "citations": [CITATION],
        "amount": "129.90",  # text, never a float
        "currency": "BRL",
    }
    assert body["failure"] is None
    assert approving.get(f"/disputes/{dispute_id}").json()["approved_amount"] == "129.90"


def test_a_failed_analysis_is_an_answer_not_an_error(unavailable: TestClient) -> None:
    dispute_id = open_dispute(unavailable)

    response = unavailable.post(f"/disputes/{dispute_id}/analysis")

    assert response.status_code == 200
    assert response.json() == {
        "id": dispute_id,
        "status": "manual_review",
        "proposal": None,
        "failure": "model is down",
    }


def test_unknown_dispute_is_404(approving: TestClient) -> None:
    assert approving.post(f"/disputes/{uuid4()}/analysis").status_code == 404


def test_a_dispute_that_is_not_open_is_409(approving: TestClient) -> None:
    dispute_id = open_dispute(approving)
    approving.post(f"/disputes/{dispute_id}/analysis")

    response = approving.post(f"/disputes/{dispute_id}/analysis")

    assert response.status_code == 409
