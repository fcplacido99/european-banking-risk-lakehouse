"""Tests for EBA reporting-period conversion."""

from datetime import date

import pytest

from eba_lakehouse.contracts import ContractError, ErrorCode
from eba_lakehouse.periods import parse_period_end


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        ("202406", date(2024, 6, 30)),
        ("202412", date(2024, 12, 31)),
        ("202402", date(2024, 2, 29)),
    ],
)
def test_parse_period_end_returns_calendar_month_end(
    period: str,
    expected: date,
) -> None:
    assert parse_period_end(period) == expected


@pytest.mark.parametrize(
    "period",
    ["202413", "202400", "2024-06", "20241", "ABCDEF", "000001"],
)
def test_parse_period_end_rejects_invalid_periods(period: str) -> None:
    with pytest.raises(ContractError) as captured:
        parse_period_end(period)

    assert captured.value.code is ErrorCode.INVALID_PERIOD