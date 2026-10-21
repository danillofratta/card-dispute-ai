import pytest

from dispute_analyst.domain.enums.dispute_reason import DisputeReason


def test_builds_from_its_stored_value() -> None:
    assert DisputeReason("duplicate_charge") is DisputeReason.DUPLICATE_CHARGE


def test_rejects_an_unknown_value() -> None:
    with pytest.raises(ValueError):
        DisputeReason("chargeback")


def test_is_a_string() -> None:
    assert isinstance(DisputeReason.NOT_DELIVERED, str)
    assert str(DisputeReason.NOT_DELIVERED) == "not_delivered"
