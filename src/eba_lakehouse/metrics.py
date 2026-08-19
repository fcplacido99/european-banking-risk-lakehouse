"""Small dependency-free helpers for metric calculations."""

from decimal import Decimal


def safe_divide(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:
    """Divide when both values exist and the denominator is positive."""

    if numerator is None or denominator is None:
        return None

    if denominator <= 0:
        return None

    return numerator / denominator