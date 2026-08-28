"""Stable data contracts and controlled error codes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class SourceFileType(StrEnum):
    """Supported physical formats for official source artifacts."""

    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class ManifestStatus(StrEnum):
    """Possible outcomes recorded for a source artifact."""

    DOWNLOADED = "downloaded"
    UNCHANGED = "unchanged"
    FAILED = "failed"


class ValidationSeverity(StrEnum):
    """Severity levels used by pipeline validation results."""

    FATAL = "fatal"
    QUARANTINE_FATAL = "quarantine_fatal"
    EXPECTED_NULLABLE = "expected_nullable"
    WARNING = "warning"


class ErrorCode(StrEnum):
    """Stable machine-readable codes for controlled failures."""

    INVALID_HEADER = "INVALID_HEADER"
    INVALID_PERIOD = "INVALID_PERIOD"
    SOURCE_CONTENT_CHANGED = "SOURCE_CONTENT_CHANGED"
    EMPTY_FILE = "EMPTY_FILE"
    INVALID_FILE_SIGNATURE = "INVALID_FILE_SIGNATURE"
    HASH_MISMATCH = "HASH_MISMATCH"
    DUPLICATE_NATURAL_KEY = "DUPLICATE_NATURAL_KEY"
    NONNUMERIC_AMOUNT = "NONNUMERIC_AMOUNT"
    INVALID_SOURCE_CONFIG = "INVALID_SOURCE_CONFIG"
    DOWNLOAD_TIMEOUT = "DOWNLOAD_TIMEOUT"
    HTTP_ERROR = "HTTP_ERROR"
    DOWNLOAD_INTERRUPTED = "DOWNLOAD_INTERRUPTED"
    INVALID_MANIFEST = "INVALID_MANIFEST"


class ContractError(ValueError):
    """Controlled contract failure carrying a stable error code."""

    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code.value}: {message}")


@dataclass(frozen=True, slots=True)
class SourceArtifactContract:
    """Expected identity and format of one official source artifact."""

    release_year: int
    source_url: str
    source_file: str
    expected_sha256: str
    file_type: SourceFileType


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    """Observed source-artifact metadata recorded during acquisition."""

    release_year: int
    source_url: str
    source_file: str
    content_length: int
    sha256: str
    retrieved_at_utc: datetime
    status: ManifestStatus
    error_code: ErrorCode | None = None


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    """Observed outcome for one artifact in a release acquisition."""

    artifact: DownloadedArtifact
    status: ManifestStatus


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of one named validation check."""

    check_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    error_code: ErrorCode | None = None


@dataclass(frozen=True, slots=True)
class DownloadedArtifact:
    """Validated local artifact produced by the acquisition boundary."""

    source_file: str
    local_path: Path
    content_length: int
    sha256: str
