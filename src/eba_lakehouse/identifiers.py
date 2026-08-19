"""Normalization helpers for source headers and identifiers."""

import re

from eba_lakehouse.contracts import ContractError, ErrorCode


_NON_ALPHANUMERIC = re.compile(r"[^0-9A-Za-z]+")


def snake_case_header(header: str) -> str:
    """Convert a source header to a stable snake-case identifier."""

    normalized = _NON_ALPHANUMERIC.sub("_", header.strip())
    normalized = normalized.strip("_").lower()

    if not normalized:
        raise ContractError(
            ErrorCode.INVALID_HEADER,
            "Header must contain at least one letter or number.",
        )

    return normalized


def normalize_lei(source_lei: str | None) -> str | None:
    """Return a trimmed uppercase LEI without altering its source value."""

    if source_lei is None:
        return None

    normalized = source_lei.strip().upper()
    return normalized or None


def is_aggregate(nsa: str | None) -> bool:
    """Return whether NSA explicitly identifies the aggregate entity."""

    if nsa is None:
        return False

    return nsa.strip().upper() == "OT"