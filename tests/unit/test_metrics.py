"""Tests for dependency-free metric helpers."""

from decimal import Decimal

import pytest

from eba_lakehouse.metrics import safe_divide


def test_safe_divide_returns_decimal_ratio() -> None:
    assert safe_divide(
        Decimal("5"),
        Decimal("10"),
    ) == Decimal("0.5")


def test_safe_divide_allows_negative_numerator() -> None:
    assert safe_divide(
        Decimal("-5"),
        Decimal("10"),
    ) == Decimal("-0.5")


@pytest.mark.parametrize(
    "denominator",
    [Decimal("0"), Decimal("-1")],
)
def test_safe_divide_rejects_nonpositive_denominator(
    denominator: Decimal,
) -> None:
    assert safe_divide(Decimal("5"), denominator) is None


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    [
        (None, Decimal("10")),
        (Decimal("5"), None),
        (None, None),
    ],
)
def test_safe_divide_preserves_missingness(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> None:
    assert safe_divide(numerator, denominator) is None