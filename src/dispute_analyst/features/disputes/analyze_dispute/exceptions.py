"""Errors of the analyze_dispute use case."""

from uuid import UUID


class AnalyzeDisputeUnavailableError(Exception):
    """The analyzer could not propose anything: the model is down, timed out or answered badly.

    Implementations translate every failure of the outside world into this error, and the
    handler turns it into manual review: the dispute never ends in an unknown state.
    """


class AnalyzeDisputeNotFoundError(Exception):
    """There is no dispute with this id."""

    def __init__(self, dispute_id: UUID) -> None:
        """Keep the id for the message; it is the caller's own input."""
        super().__init__(f"dispute {dispute_id} not found")
        self.dispute_id = dispute_id
