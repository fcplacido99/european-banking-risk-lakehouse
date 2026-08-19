"""Tests for release-specific source configuration."""

from pathlib import Path

import pytest
import yaml

from eba_lakehouse.contracts import ContractError, ErrorCode, SourceFileType
from eba_lakehouse.source_config import load_source_contracts


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CONFIG = PROJECT_ROOT / "config" / "sources.yml"


def _artifact(**overrides: object) -> dict[str, object]:
    artifact: dict[str, object] = {
        "source_url": "https://www.eba.europa.eu/assets/example/tr_cre.csv",
        "source_file": "tr_cre.csv",
        "expected_sha256": "a" * 64,
        "file_type": "csv",
    }
    artifact.update(overrides)
    return artifact


def _write_config(tmp_path: Path, artifacts: list[dict[str, object]]) -> Path:
    config_path = tmp_path / "sources.yml"
    config_path.write_text(
        yaml.safe_dump({"releases": {"2024": {"artifacts": artifacts}}}),
        encoding="utf-8",
    )
    return config_path


def test_official_2024_config_contains_the_five_locked_artifacts() -> None:
    contracts = load_source_contracts(SOURCE_CONFIG, 2024)
    expected_hashes = {
        "tr_cre.csv": "4175521fbbe352e7e8973c37f419f16a8fe3b6fc5974ea7955baf67aadf2060e",
        "tr_oth.csv": "e2c6d0b9ddb887f96ff0af7a51bbbd7d8e7b467a9e9e1110514660aecbcaa584",
        "TR_Metadata.xlsx": "ecd488dffa578dabb89594ccc00409303b14446e7b0eaebab2bdaa7a65e7bc21",
        "SDD.xlsx": "9f350211b2d54ae7a273526a0402ab43965822ff527dc2e587149c98bd13d6a9",
        "CSV_and_Tools_guide_Transparency_2024.pdf": (
            "95302ef9e86db6354cefc44b027977a894fadc2c4a17f71ef47d40232fe1f5f2"
        ),
    }

    assert len(contracts) == 5
    assert {contract.source_file for contract in contracts} == {
        "tr_cre.csv",
        "tr_oth.csv",
        "TR_Metadata.xlsx",
        "SDD.xlsx",
        "CSV_and_Tools_guide_Transparency_2024.pdf",
    }
    assert {contract.file_type for contract in contracts} == {
        SourceFileType.CSV,
        SourceFileType.XLSX,
        SourceFileType.PDF,
    }
    assert all(contract.release_year == 2024 for contract in contracts)
    assert {
        contract.source_file: contract.expected_sha256 for contract in contracts
    } == expected_hashes


def test_missing_release_is_rejected(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, [_artifact()])

    with pytest.raises(ContractError) as caught:
        load_source_contracts(config_path, 2025)

    assert caught.value.code is ErrorCode.INVALID_SOURCE_CONFIG


@pytest.mark.parametrize(
    "overrides",
    [
        {"expected_sha256": "not-a-hash"},
        {"source_url": "http://www.eba.europa.eu/tr_cre.csv"},
        {"source_url": "https://example.test/tr_cre.csv"},
        {"source_file": "../tr_cre.csv"},
        {"source_file": "tr_cre.pdf"},
    ],
)
def test_invalid_artifact_contract_is_rejected(
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    config_path = _write_config(tmp_path, [_artifact(**overrides)])

    with pytest.raises(ContractError) as caught:
        load_source_contracts(config_path, 2024)

    assert caught.value.code is ErrorCode.INVALID_SOURCE_CONFIG


def test_duplicate_filenames_are_rejected(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, [_artifact(), _artifact()])

    with pytest.raises(ContractError) as caught:
        load_source_contracts(config_path, 2024)

    assert caught.value.code is ErrorCode.INVALID_SOURCE_CONFIG
