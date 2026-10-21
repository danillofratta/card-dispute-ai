"""Domain errors: raised for programming mistakes, never for a bad LLM proposal."""


class DomainError(Exception):
    """Base class for every error the domain raises on its own."""


class InvalidTransitionError(DomainError):
    """A dispute was asked to move to a status its state machine does not allow."""
