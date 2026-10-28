"""Where the merchant says an online order is."""

from enum import StrEnum


class DeliveryStatus(StrEnum):
    DELIVERED = "delivered"
    NOT_DELIVERED = "not_delivered"
