# Tests for stable source and validation contracts.

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eba_lakehouse.contracts import (
    ContractError,
    DownloadedArtifact,
    ErrorCode,
    ManifestRecord,
    ManifestStatus,
    SourceArtifactContract,
    SourceFileType,
    ValidationResult,
    ValidationSeverity,
)


def test_enum_values_are_stable() -> None:
    assert {member.value for member in SourceFileType} == {
        "csv",
        "xlsx",
        "pdf",
    }
    assert {member.value for member in ManifestStatus} == {
        "downloaded",
        "unchanged",
        "failed",
    }
    assert {member.value for member in ValidationSeverity} == {
        "fatal",
        "quarantine_fatal",
        "expected_nullable",
        "warning",
    }
    assert {member.value for member in ErrorCode} == {
        "INVALID_HEADER",
        "INVALID_PERIOD",
        "SOURCE_CONTENT_CHANGED",
        "EMPTY_FILE",
        "INVALID_FILE_SIGNATURE",
        "HASH_MISMATCH",
        "DUPLICATE_NATURAL_KEY",
        "NONNUMERIC_AMOUNT",
        "INVALID_SOURCE_CONFIG",
        "DOWNLOAD_TIMEOUT",
        "HTTP_ERROR",
        "DOWNLOAD_INTERRUPTED",
    }


def test_source_artifact_contract_is_immutable() -> None:
    artifact = SourceArtifactContract(
        release_year=2024,
        source_url="https://example.test/tr_cre.csv",
        source_file="tr_cre.csv",
        expected_sha256="a" * 64,
        file_type=SourceFileType.CSV,
    )

    with pytest.raises(FrozenInstanceError):
        artifact.release_year = 2025  # type: ignore[misc]


def test_manifest_record_preserves_acquisition_metadata() -> None:
    retrieved_at = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)

    record = ManifestRecord(
        release_year=2024,
        source_url="https://example.test/tr_cre.csv",
        source_file="tr_cre.csv",
        content_length=119_032_803,
        sha256="a" * 64,
        retrieved_at_utc=retrieved_at,
        status=ManifestStatus.DOWNLOADED,
    )

    assert record.retrieved_at_utc is retrieved_at
    assert record.content_length == 119_032_803


def test_validation_result_allows_optional_error_code() -> None:
    passed = ValidationResult(
        check_name="required_columns",
        passed=True,
        severity=ValidationSeverity.FATAL,
        message="All required columns are present.",
    )
    failed = ValidationResult(
        check_name="amount_numeric",
        passed=False,
        severity=ValidationSeverity.FATAL,
        message="Amount could not be parsed.",
        error_code=ErrorCode.NONNUMERIC_AMOUNT,
    )

    assert passed.error_code is None
    assert failed.error_code is ErrorCode.NONNUMERIC_AMOUNT


def test_contract_error_exposes_code_and_message() -> None:
    error = ContractError(
        ErrorCode.INVALID_PERIOD,
        "Period must use YYYYMM.",
    )

    assert error.code is ErrorCode.INVALID_PERIOD
    assert error.message == "Period must use YYYYMM."
    assert str(error) == "INVALID_PERIOD: Period must use YYYYMM."


def test_public_contract_types_have_docstrings() -> None:
    public_types = (
        SourceFileType,
        ManifestStatus,
        ValidationSeverity,
        ErrorCode,
        ContractError,
        SourceArtifactContract,
        ManifestRecord,
        ValidationResult,
        DownloadedArtifact,
    )

    assert all(
        public_type.__doc__ is not None and public_type.__doc__.strip()
        for public_type in public_types
    )


def test_downloaded_artifact_is_immutable() -> None:
    artifact = DownloadedArtifact(
        source_file="tr_cre.csv",
        local_path=Path("tr_cre.csv"),
        content_length=10,
        sha256="a" * 64,
    )

    with pytest.raises(FrozenInstanceError):
        artifact.content_length = 11  # type: ignore[misc]
