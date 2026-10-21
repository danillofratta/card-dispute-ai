"""Cpf value object: a Brazilian taxpayer number, validated and never shown in full by default."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

_ELEVEN_DIGITS = re.compile(r"[0-9]{11}")
_CPF_TEXT = re.compile(r"([0-9]{3})\.?([0-9]{3})\.?([0-9]{3})-?([0-9]{2})")


def _check_digit(digits: str) -> int:
    """Mod-11 check digit: weights go down from len + 1 to 2; a result of 10 becomes 0."""
    weights = range(len(digits) + 1, 1, -1)
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights, strict=True))
    return total * 10 % 11 % 10


@dataclass(frozen=True, slots=True, repr=False)
class Cpf:
    """Eleven digits with valid check digits, stored without punctuation."""

    digits: str

    def __post_init__(self) -> None:
        if not isinstance(self.digits, str):
            raise TypeError(f"digits must be a str, got {type(self.digits).__name__}")
        # The messages never echo the number itself: a CPF must not leak into logs.
        if not _ELEVEN_DIGITS.fullmatch(self.digits):
            raise ValueError("CPF must have exactly 11 digits")
        if len(set(self.digits)) == 1:
            raise ValueError("CPF cannot have all digits equal")
        first = _check_digit(self.digits[:9])
        second = _check_digit(self.digits[:9] + str(first))
        if self.digits[9:] != f"{first}{second}":
            raise ValueError("CPF check digits are invalid")

    @classmethod
    def parse(cls, text: str) -> Self:
        """Accept "123.456.789-09" or "12345678909", with surrounding spaces."""
        match = _CPF_TEXT.fullmatch(text.strip())
        if match is None:
            raise ValueError("CPF must look like 123.456.789-09 or 12345678909")
        return cls("".join(match.groups()))

    def formatted(self) -> str:
        """The full number, for authorized output only."""
        d = self.digits
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"

    def masked(self) -> str:
        """Safe to log and display: ***.456.789-**."""
        d = self.digits
        return f"***.{d[3:6]}.{d[6:9]}-**"

    def __repr__(self) -> str:
        return f"Cpf({self.masked()!r})"