"""Read and atomically publish deterministic acquisition manifests."""

from collections.abc import Iterable
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from eba_lakehouse.contracts import (
    ContractError,
    ErrorCode,
    ManifestRecord,
    ManifestStatus,
)


MANIFEST_VERSION = 1
_ROOT_FIELDS = {"manifest_version", "release_year", "artifacts"}
_ARTIFACT_FIELDS = {
    "release_year",
    "source_url",
    "source_file",
    "content_length",
    "sha256",
    "retrieved_at_utc",
    "status",
    "error_code",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _invalid(message: str) -> ContractError:
    return ContractError(ErrorCode.INVALID_MANIFEST, message)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise _invalid("retrieved_at_utc must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _record_payload(record: ManifestRecord, release_year: int) -> dict[str, Any]:
    if record.release_year != release_year:
        raise _invalid(
            f"Artifact {record.source_file!r} has release year "
            f"{record.release_year}, expected {release_year}"
        )
    if record.content_length <= 0:
        raise _invalid(f"Artifact {record.source_file!r} must have a positive size")
    if not _SHA256_PATTERN.fullmatch(record.sha256):
        raise _invalid(f"Artifact {record.source_file!r} has an invalid SHA-256")

    return {
        "release_year": record.release_year,
        "source_url": record.source_url,
        "source_file": record.source_file,
        "content_length": record.content_length,
        "sha256": record.sha256.lower(),
        "retrieved_at_utc": _format_utc(record.retrieved_at_utc),
        "status": record.status.value,
        "error_code": record.error_code.value if record.error_code else None,
    }


def _manifest_bytes(
    release_year: int,
    records: Iterable[ManifestRecord],
) -> bytes:
    records_by_name: dict[str, ManifestRecord] = {}
    for record in records:
        if record.source_file in records_by_name:
            raise _invalid(f"Duplicate artifact filename: {record.source_file!r}")
        records_by_name[record.source_file] = record

    payload = {
        "manifest_version": MANIFEST_VERSION,
        "release_year": release_year,
        "artifacts": [
            _record_payload(records_by_name[name], release_year)
            for name in sorted(records_by_name)
        ],
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_manifest(
    manifest_path: Path,
    release_year: int,
    records: Iterable[ManifestRecord],
) -> bool:
    """Atomically publish a canonical manifest, returning whether it changed."""

    content = _manifest_bytes(release_year, records)
    if manifest_path.exists() and manifest_path.read_bytes() == content:
        return False

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    staged_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=manifest_path.parent,
            prefix=f".{manifest_path.name}.",
            suffix=".part",
            delete=False,
        ) as staged_file:
            staged_path = Path(staged_file.name)
            staged_file.write(content)
            staged_file.flush()
            os.fsync(staged_file.fileno())
        os.replace(staged_path, manifest_path)
        return True
    finally:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)


def _parse_timestamp(value: object, source_file: str) -> datetime:
    if not isinstance(value, str):
        raise _invalid(f"Artifact {source_file!r} has an invalid retrieval timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise _invalid(
            f"Artifact {source_file!r} has an invalid retrieval timestamp"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _invalid(f"Artifact {source_file!r} timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _parse_record(raw: object, expected_release_year: int) -> ManifestRecord:
    if not isinstance(raw, dict) or set(raw) != _ARTIFACT_FIELDS:
        raise _invalid(f"Each artifact must contain exactly: {sorted(_ARTIFACT_FIELDS)}")

    source_file = raw["source_file"]
    if not isinstance(source_file, str) or not source_file:
        raise _invalid("Artifact source_file must be a non-empty string")
    if raw["release_year"] != expected_release_year:
        raise _invalid(f"Artifact {source_file!r} has the wrong release year")
    if not isinstance(raw["source_url"], str) or not raw["source_url"]:
        raise _invalid(f"Artifact {source_file!r} has an invalid source URL")
    if not isinstance(raw["content_length"], int) or isinstance(
        raw["content_length"], bool
    ) or raw["content_length"] <= 0:
        raise _invalid(f"Artifact {source_file!r} must have a positive size")
    if not isinstance(raw["sha256"], str) or not _SHA256_PATTERN.fullmatch(
        raw["sha256"]
    ):
        raise _invalid(f"Artifact {source_file!r} has an invalid SHA-256")

    try:
        status = ManifestStatus(raw["status"])
    except (TypeError, ValueError) as error:
        raise _invalid(f"Artifact {source_file!r} has an invalid status") from error

    error_code_value = raw["error_code"]
    try:
        error_code = None if error_code_value is None else ErrorCode(error_code_value)
    except (TypeError, ValueError) as error:
        raise _invalid(f"Artifact {source_file!r} has an invalid error code") from error

    return ManifestRecord(
        release_year=expected_release_year,
        source_url=raw["source_url"],
        source_file=source_file,
        content_length=raw["content_length"],
        sha256=raw["sha256"].lower(),
        retrieved_at_utc=_parse_timestamp(raw["retrieved_at_utc"], source_file),
        status=status,
        error_code=error_code,
    )


def read_manifest(
    manifest_path: Path,
    expected_release_year: int,
) -> tuple[ManifestRecord, ...]:
    """Read and strictly validate one acquisition manifest."""

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _invalid(f"Could not read {manifest_path}: {error}") from error

    if not isinstance(payload, dict) or set(payload) != _ROOT_FIELDS:
        raise _invalid(f"Manifest must contain exactly: {sorted(_ROOT_FIELDS)}")
    if payload["manifest_version"] != MANIFEST_VERSION:
        raise _invalid(f"Unsupported manifest version: {payload['manifest_version']!r}")
    if payload["release_year"] != expected_release_year:
        raise _invalid(
            f"Manifest release year {payload['release_year']!r} does not match "
            f"{expected_release_year}"
        )
    if not isinstance(payload["artifacts"], list):
        raise _invalid("Manifest artifacts must be a list")

    records = tuple(
        _parse_record(raw, expected_release_year) for raw in payload["artifacts"]
    )
    names = [record.source_file for record in records]
    if len(names) != len(set(names)):
        raise _invalid("Manifest contains duplicate artifact filenames")
    return records
