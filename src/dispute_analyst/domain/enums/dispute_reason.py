"""Why the customer is disputes a card transaction"""

from enum import StrEnum


class DisputeReason(StrEnum):
    UNRECOGNIZED_CHARGE = "unrecognized_charge"
    DUPLICATE_CHARGE = "duplicate_charge"
    NOT_DELIVERED = "not_delivered"
