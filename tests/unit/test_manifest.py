"""Tests for deterministic acquisition manifests."""

from datetime import UTC, datetime, timedelta, timezone
import json
import os
from pathlib import Path

import pytest

from eba_lakehouse.contracts import (
    ContractError,
    ErrorCode,
    ManifestRecord,
    ManifestStatus,
)
from eba_lakehouse.manifest import read_manifest, write_manifest


def make_record(
    source_file: str = "tr_cre.csv",
    *,
    release_year: int = 2024,
    sha256: str = "A" * 64,
    retrieved_at: datetime | None = None,
) -> ManifestRecord:
    return ManifestRecord(
        release_year=release_year,
        source_url=f"https://www.eba.europa.eu/example/{source_file}",
        source_file=source_file,
        content_length=10,
        sha256=sha256,
        retrieved_at_utc=retrieved_at or datetime(2026, 9, 2, 18, 30, tzinfo=UTC),
        status=ManifestStatus.DOWNLOADED,
    )


def assert_invalid_manifest(callable_) -> None:
    with pytest.raises(ContractError) as caught:
        callable_()
    assert caught.value.code is ErrorCode.INVALID_MANIFEST


def test_manifest_round_trip_is_sorted_and_canonical(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    records = [make_record("z.pdf"), make_record("a.csv")]

    assert write_manifest(path, 2024, records)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.read_bytes().endswith(b"\n")
    assert [item["source_file"] for item in payload["artifacts"]] == [
        "a.csv",
        "z.pdf",
    ]
    assert payload["artifacts"][0]["sha256"] == "a" * 64
    assert payload["artifacts"][0]["retrieved_at_utc"].endswith("Z")
    assert payload["artifacts"][0]["error_code"] is None
    parsed = read_manifest(path, 2024)
    assert [record.source_file for record in parsed] == ["a.csv", "z.pdf"]
    assert all(record.sha256 == "a" * 64 for record in parsed)


def test_manifest_normalizes_non_utc_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    offset = timezone(timedelta(hours=1))
    write_manifest(path, 2024, [make_record(retrieved_at=datetime(2026, 9, 2, 19, 30, tzinfo=offset))])

    record = read_manifest(path, 2024)[0]
    assert record.retrieved_at_utc == datetime(2026, 9, 2, 18, 30, tzinfo=UTC)


def test_identical_manifest_is_not_rewritten(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    records = [make_record()]
    assert write_manifest(path, 2024, records)
    before = path.stat().st_mtime_ns
    assert not write_manifest(path, 2024, records)
    assert path.stat().st_mtime_ns == before


def test_manifest_rejects_duplicate_names(tmp_path: Path) -> None:
    assert_invalid_manifest(
        lambda: write_manifest(tmp_path / "manifest.json", 2024, [make_record(), make_record()])
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda payload: payload.update(manifest_version=2),
        lambda payload: payload.update(release_year=2025),
        lambda payload: payload.update(extra=True),
        lambda payload: payload["artifacts"][0].update(extra=True),
        lambda payload: payload["artifacts"][0].pop("status"),
        lambda payload: payload["artifacts"][0].update(sha256="bad"),
        lambda payload: payload["artifacts"][0].update(retrieved_at_utc="not-a-date"),
        lambda payload: payload["artifacts"][0].update(retrieved_at_utc="2026-09-02T18:30:00"),
        lambda payload: payload["artifacts"][0].update(status="unknown"),
        lambda payload: payload["artifacts"][0].update(error_code="UNKNOWN"),
        lambda payload: payload["artifacts"][0].update(content_length=0),
        lambda payload: payload["artifacts"].append(dict(payload["artifacts"][0])),
    ],
)
def test_read_manifest_rejects_invalid_payload(tmp_path: Path, change) -> None:
    path = tmp_path / "manifest.json"
    write_manifest(path, 2024, [make_record()])
    payload = json.loads(path.read_text(encoding="utf-8"))
    change(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert_invalid_manifest(lambda: read_manifest(path, 2024))


def test_read_manifest_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("{", encoding="utf-8")
    assert_invalid_manifest(lambda: read_manifest(path, 2024))


def test_write_manifest_rejects_naive_timestamp(tmp_path: Path) -> None:
    assert_invalid_manifest(
        lambda: write_manifest(
            tmp_path / "manifest.json",
            2024,
            [make_record(retrieved_at=datetime(2026, 9, 2, 18, 30))],
        )
    )


def test_atomic_failure_cleans_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "manifest.json"

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated publication failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated publication failure"):
        write_manifest(path, 2024, [make_record()])

    assert not path.exists()
    assert not list(tmp_path.glob("*.part"))
