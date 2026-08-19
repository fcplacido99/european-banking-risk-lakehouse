"""Conversion helpers for EBA reporting periods."""

from calendar import monthrange
from datetime import date

from eba_lakehouse.contracts import ContractError, ErrorCode


def parse_period_end(period: str) -> date:
    """Convert an EBA YYYYMM period to its actual month-end date."""

    valid_shape = (
        isinstance(period, str)
        and len(period) == 6
        and all(character in "0123456789" for character in period)
    )

    if not valid_shape:
        raise ContractError(
            ErrorCode.INVALID_PERIOD,
            f"Period must use valid YYYYMM format: {period!r}.",
        )

    year = int(period[:4])
    month = int(period[4:])

    try:
        final_day = monthrange(year, month)[1]
        return date(year, month, final_day)
    except ValueError as error:
        raise ContractError(
            ErrorCode.INVALID_PERIOD,
            f"Period must use valid YYYYMM format: {period!r}.",
        ) from error