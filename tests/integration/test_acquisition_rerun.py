"""Offline integration proof for release-level acquisition idempotency."""

import hashlib
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import pytest

from eba_lakehouse.contracts import ContractError, ErrorCode, ManifestStatus
from eba_lakehouse.download import acquire_release, calculate_file_identity
from eba_lakehouse.manifest import read_manifest


FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1] / "fixtures" / "csv"


class FixtureResponse:
    """Small streamed response backed by deterministic fixture bytes."""

    status_code = 200

    def __init__(self, payload: bytes):
        self.payload = payload
        self.closed = False

    @property
    def content(self) -> bytes:
        raise AssertionError("Acquisition must stream fixture responses.")

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int) -> Iterable[bytes]:
        midpoint = max(1, len(self.payload) // 2)
        yield self.payload[:midpoint]
        yield self.payload[midpoint:]

    def close(self) -> None:
        self.closed = True


class FixtureSession:
    """Route official-looking URLs to local fixture responses."""

    def __init__(self, payloads: dict[str, bytes], *, forbid_calls: bool = False):
        self.payloads = payloads
        self.forbid_calls = forbid_calls
        self.calls: list[str] = []

    def get(self, url: str, *, stream: bool, timeout: tuple[int, int]) -> FixtureResponse:
        if self.forbid_calls:
            raise AssertionError(f"Second acquisition made an HTTP request: {url}")
        self.calls.append(url)
        return FixtureResponse(self.payloads[Path(urlparse(url).path).name])

    def close(self) -> None:
        return None


def fixture_payloads() -> dict[str, bytes]:
    return {
        "tr_cre.csv": (FIXTURE_DIRECTORY / "tr_cre_valid.csv").read_bytes(),
        "tr_oth.csv": (FIXTURE_DIRECTORY / "tr_oth_valid.csv").read_bytes(),
        "TR_Metadata.xlsx": b"PK\x03\x04synthetic-metadata-workbook",
        "SDD.xlsx": b"PK\x03\x04synthetic-sdd-workbook",
        "CSV_and_Tools_guide_Transparency_2024.pdf": (
            b"%PDF-1.7\nsynthetic-tools-guide\n%%EOF"
        ),
    }


def write_fixture_config(path: Path, payloads: dict[str, bytes]) -> Path:
    types = {
        "tr_cre.csv": "csv",
        "tr_oth.csv": "csv",
        "TR_Metadata.xlsx": "xlsx",
        "SDD.xlsx": "xlsx",
        "CSV_and_Tools_guide_Transparency_2024.pdf": "pdf",
    }
    lines = ["releases:", '  "2024":', "    artifacts:"]
    for filename, payload in payloads.items():
        lines.extend(
            [
                f"      - source_url: https://www.eba.europa.eu/test/{filename}",
                f"        source_file: {filename}",
                f"        expected_sha256: {hashlib.sha256(payload).hexdigest()}",
                f"        file_type: {types[filename]}",
            ]
        )
    config_path = path / "sources.yml"
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


def test_five_artifact_rerun_is_byte_stable_and_offline(tmp_path: Path) -> None:
    payloads = fixture_payloads()
    config_path = write_fixture_config(tmp_path, payloads)
    output_dir = tmp_path / "release_year=2024"
    first_session = FixtureSession(payloads)

    first_results = acquire_release(
        config_path,
        2024,
        output_dir,
        session=first_session,
    )

    assert len(first_results) == 5
    assert all(result.status is ManifestStatus.DOWNLOADED for result in first_results)
    assert len(first_session.calls) == 5
    assert len(list(output_dir.iterdir())) == 6
    assert not list(output_dir.glob("*.part"))

    manifest_path = output_dir / "manifest.json"
    manifest_before = manifest_path.read_bytes()
    records = read_manifest(manifest_path, 2024)
    assert len(records) == 5
    assert len({record.source_file for record in records}) == 5
    identities_before = {
        filename: calculate_file_identity(output_dir / filename)
        for filename in payloads
    }

    second_session = FixtureSession(payloads, forbid_calls=True)
    second_results = acquire_release(
        config_path,
        2024,
        output_dir,
        session=second_session,
    )

    assert all(result.status is ManifestStatus.UNCHANGED for result in second_results)
    assert second_session.calls == []
    assert manifest_path.read_bytes() == manifest_before
    assert len(list(output_dir.iterdir())) == 6
    assert identities_before == {
        filename: calculate_file_identity(output_dir / filename)
        for filename in payloads
    }
    assert not list(output_dir.glob("*.part"))

    corrupted_path = output_dir / "tr_cre.csv"
    corrupted_path.write_bytes(b"corrupted-local-content")
    unrelated_before = {
        filename: (output_dir / filename).read_bytes()
        for filename in payloads
        if filename != "tr_cre.csv"
    }

    with pytest.raises(ContractError) as caught:
        acquire_release(
            config_path,
            2024,
            output_dir,
            session=FixtureSession(payloads, forbid_calls=True),
        )

    assert caught.value.code is ErrorCode.SOURCE_CONTENT_CHANGED
    assert corrupted_path.read_bytes() == b"corrupted-local-content"
    assert manifest_path.read_bytes() == manifest_before
    assert unrelated_before == {
        filename: (output_dir / filename).read_bytes()
        for filename in payloads
        if filename != "tr_cre.csv"
    }
    assert not list(output_dir.glob("*.part"))
