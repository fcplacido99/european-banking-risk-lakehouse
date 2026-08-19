"""Tests for source-header and entity-identifier helpers."""

import pytest

from eba_lakehouse.contracts import ContractError, ErrorCode
from eba_lakehouse.identifiers import (
    is_aggregate,
    normalize_lei,
    snake_case_header,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("LEI_Code", "lei_code"),
        ("ASSETS_Stages", "assets_stages"),
        ("Financial instruments", "financial_instruments"),
        (" Country-rank ", "country_rank"),
        ("A__B", "a_b"),
    ],
)
def test_snake_case_header(
    source: str,
    expected: str,
) -> None:
    assert snake_case_header(source) == expected


@pytest.mark.parametrize("source", ["", "   ", "---", "___"])
def test_snake_case_header_rejects_empty_results(source: str) -> None:
    with pytest.raises(ContractError) as captured:
        snake_case_header(source)

    assert captured.value.code is ErrorCode.INVALID_HEADER


def test_normalize_lei_returns_derived_uppercase_value() -> None:
    source_lei = "  0w2pzjm8xoy22m4gg883  "

    normalized = normalize_lei(source_lei)

    assert normalized == "0W2PZJM8XOY22M4GG883"
    assert source_lei == "  0w2pzjm8xoy22m4gg883  "


@pytest.mark.parametrize("source", [None, "", "   "])
def test_normalize_lei_preserves_missing_values(
    source: str | None,
) -> None:
    assert normalize_lei(source) is None


@pytest.mark.parametrize("source", ["OT", "ot", " Ot "])
def test_is_aggregate_uses_explicit_nsa_code(source: str) -> None:
    assert is_aggregate(source) is True


@pytest.mark.parametrize(
    "source",
    [None, "", "DE", "XXXXXXXXXXXXXXXXXXXX"],
)
def test_is_aggregate_does_not_infer_from_other_values(
    source: str | None,
) -> None:
    assert is_aggregate(source) is False