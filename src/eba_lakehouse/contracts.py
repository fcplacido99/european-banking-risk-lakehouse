# Stable data coontracts and controlled error codes

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

# Supported physical formats for official source artifacts
class SourceFileType(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


# possible outcomes recorded for source artifact
class ManifestStatus(StrEnum):
    DOWNLOADED = "downloaded"
    UNCHANGED = "unchanged"
    FAILED = "failed"


# severity levels used by pipeline validation results
class ValidationSeverity(StrEnum):
    FATAL = "fatal"
    QUARANTINE_FATAL = "quarantine_fatal"
    EXPECTED_NULLABLE = "expected_nullable"
    WARNING = "warning"


# Stable machine-readable codes for controlled failures.
class ErrorCode(StrEnum):
    INVALID_HEADER = "INVALID_HEADER"
    INVALID_PERIOD = "INVALID_PERIOD"
    SOURCE_CONTENT_CHANGED = "SOURCE_CONTENT_CHANGED"
    EMPTY_FILE = "EMPTY_FILE"
    INVALID_FILE_SIGNATURE = "INVALID_FILE_SIGNATURE"
    HASH_MISMATCH = "HASH_MISMATCH"
    DUPLICATE_NATURAL_KEY = "DUPLICATE_NATURAL_KEY"
    NONNUMERIC_AMOUNT = "NONNUMERIC_AMOUNT"


# a controlled contract failure carrying a stable error code
class ContractError(ValueError):
    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code.value}: {message}")


# Expected identity and format of one official source artifact
@dataclass(frozen=True, slots=True)
class SourceArtifactContract:
    release_year: int
    source_url: str
    source_file: str
    expected_sha256: str
    file_type: SourceFileType


# Observed source-artifact metadata recorded during acquisition.
@dataclass(frozen=True, slots=True)
class ManifestRecord:
    release_year: int
    source_url: str
    source_file: str
    content_length: int
    sha256: str
    retrieved_at_utc: datetime
    status: ManifestStatus


# Outcome of one named validation check
@dataclass(frozen=True, slots=True)
class ValidationResult:
    check_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    error_code: ErrorCode | None = None