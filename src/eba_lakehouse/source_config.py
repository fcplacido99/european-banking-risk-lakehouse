"""Load and validate release-specific source artifact contracts."""

from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import yaml

from eba_lakehouse.contracts import (
    ContractError,
    ErrorCode,
    SourceArtifactContract,
    SourceFileType,
)


_ARTIFACT_FIELDS = {
    "source_url",
    "source_file",
    "expected_sha256",
    "file_type",
}
_EXTENSIONS = {
    SourceFileType.CSV: ".csv",
    SourceFileType.XLSX: ".xlsx",
    SourceFileType.PDF: ".pdf",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _invalid(message: str) -> ContractError:
    return ContractError(ErrorCode.INVALID_SOURCE_CONFIG, message)


def _load_yaml(config_path: Path) -> dict[str, Any]:
    try:
        with config_path.open(encoding="utf-8") as config_file:
            payload = yaml.safe_load(config_file)
    except (OSError, yaml.YAMLError) as error:
        raise _invalid(f"Could not read {config_path}: {error}") from error

    if not isinstance(payload, dict) or set(payload) != {"releases"}:
        raise _invalid("Configuration must contain only the 'releases' mapping.")
    if not isinstance(payload["releases"], dict):
        raise _invalid("'releases' must be a mapping.")
    return payload


def _validate_filename(source_file: object) -> str:
    if not isinstance(source_file, str) or not source_file.strip():
        raise _invalid("source_file must be a non-empty string.")
    if source_file != Path(source_file).name or "/" in source_file or "\\" in source_file:
        raise _invalid(f"source_file must be a filename only: {source_file!r}.")
    return source_file


def _validate_url(source_url: object, source_file: str) -> str:
    if not isinstance(source_url, str):
        raise _invalid(f"source_url for {source_file} must be a string.")
    parsed = urlparse(source_url)
    hostname = parsed.hostname or ""
    if parsed.scheme != "https" or not (
        hostname == "eba.europa.eu" or hostname.endswith(".eba.europa.eu")
    ):
        raise _invalid(f"source_url for {source_file} must be an HTTPS EBA URL.")
    return source_url


def _parse_artifact(release_year: int, raw: object) -> SourceArtifactContract:
    if not isinstance(raw, dict) or set(raw) != _ARTIFACT_FIELDS:
        raise _invalid(
            f"Each artifact must contain exactly: {sorted(_ARTIFACT_FIELDS)}."
        )

    source_file = _validate_filename(raw["source_file"])
    source_url = _validate_url(raw["source_url"], source_file)

    expected_sha256 = raw["expected_sha256"]
    if not isinstance(expected_sha256, str) or not _SHA256_PATTERN.fullmatch(
        expected_sha256
    ):
        raise _invalid(f"expected_sha256 for {source_file} must be 64 hexadecimal characters.")

    try:
        file_type = SourceFileType(raw["file_type"])
    except (TypeError, ValueError) as error:
        raise _invalid(f"Unsupported file_type for {source_file}: {raw['file_type']!r}.") from error

    if Path(source_file).suffix.lower() != _EXTENSIONS[file_type]:
        raise _invalid(f"Filename extension and file_type disagree for {source_file}.")

    return SourceArtifactContract(
        release_year=release_year,
        source_url=source_url,
        source_file=source_file,
        expected_sha256=expected_sha256.lower(),
        file_type=file_type,
    )


def load_source_contracts(
    config_path: Path,
    release_year: int,
) -> tuple[SourceArtifactContract, ...]:
    """Return validated source contracts for one configured release."""

    payload = _load_yaml(config_path)
    release = payload["releases"].get(str(release_year))
    if release is None:
        raise _invalid(f"Release year {release_year} is not configured.")
    if not isinstance(release, dict) or set(release) != {"artifacts"}:
        raise _invalid(f"Release {release_year} must contain only 'artifacts'.")
    if not isinstance(release["artifacts"], list) or not release["artifacts"]:
        raise _invalid(f"Release {release_year} must contain a non-empty artifact list.")

    contracts = tuple(
        _parse_artifact(release_year, artifact) for artifact in release["artifacts"]
    )
    filenames = [contract.source_file for contract in contracts]
    if len(filenames) != len(set(filenames)):
        raise _invalid(f"Release {release_year} contains duplicate source filenames.")
    return contracts
