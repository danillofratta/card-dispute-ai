"""Errors of the open_dispute use case."""

from uuid import UUID


class TransactionNotFoundError(Exception):
    """The transaction does not exist, or it is not on one of the customer's cards.

    Both cases look the same on purpose: a customer must not learn that someone else's
    transaction exists.
    """

    def __init__(self, transaction_id: UUID) -> None:
        """Keep the id for the message; it is the caller's own input."""
        super().__init__(f"transaction {transaction_id} not found for this customer")
        self.transaction_id = transaction_id
