"""Tests for safe streamed source acquisition."""

import hashlib
from pathlib import Path
from typing import Iterable

import pytest
import requests

from requests import exceptions as requests_exceptions

from eba_lakehouse.contracts import (
    ContractError,
    ErrorCode,
    ManifestStatus,
    SourceArtifactContract,
    SourceFileType,
)
from eba_lakehouse.download import (
    CONNECT_TIMEOUT_SECONDS,
    DOWNLOAD_CHUNK_BYTES,
    READ_TIMEOUT_SECONDS,
    _stage_download,
    acquire_release,
    calculate_file_identity,
    download_artifact,
)

FIXTURE_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "csv"
)


class FakeResponse:
    """Controllable streamed HTTP response used by unit tests."""

    def __init__(
        self,
        chunks: list[bytes | Exception],
        status_code: int = 200,
    ):
        self.chunks = chunks
        self.status_code = status_code
        self.closed = False
        self.requested_chunk_size: int | None = None

    @property
    def content(self) -> bytes:
        raise AssertionError(
            "Streaming code must not access response.content."
        )

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error_response = requests.Response()
            error_response.status_code = self.status_code

            raise requests_exceptions.HTTPError(
                response=error_response,
            )

    def iter_content(
        self,
        chunk_size: int,
    ) -> Iterable[bytes]:
        self.requested_chunk_size = chunk_size

        for chunk in self.chunks:
            if isinstance(chunk, Exception):
                raise chunk

            yield chunk

    def close(self) -> None:
        self.closed = True


class FakeSession:
    """Controllable HTTP session that never accesses the internet."""

    def __init__(
        self,
        response: FakeResponse | None = None,
        request_error: Exception | None = None,
    ):
        self.response = response
        self.request_error = request_error
        self.calls: list[
            tuple[str, bool, tuple[int, int]]
        ] = []
        self.closed = False

    def get(
        self,
        url: str,
        *,
        stream: bool,
        timeout: tuple[int, int],
    ) -> FakeResponse:
        self.calls.append((url, stream, timeout))

        if self.request_error is not None:
            raise self.request_error

        assert self.response is not None
        return self.response

    def close(self) -> None:
        self.closed = True


def make_contract(
    expected_sha256: str = "a" * 64,
    *,
    source_file: str = "tr_cre.csv",
    file_type: SourceFileType = SourceFileType.CSV,
) -> SourceArtifactContract:
    return SourceArtifactContract(
        release_year=2024,
        source_url=(
            "https://www.eba.europa.eu/"
            f"assets/example/{source_file}"
        ),
        source_file=source_file,
        expected_sha256=expected_sha256,
        file_type=file_type,
    )


def write_single_source_config(
    path: Path,
    payload: bytes,
) -> Path:
    config_path = path / "sources.yml"
    config_path.write_text(
        "\n".join(
            [
                "releases:",
                '  "2024":',
                "    artifacts:",
                "      - source_url: https://www.eba.europa.eu/example/tr_cre.csv",
                "        source_file: tr_cre.csv",
                f"        expected_sha256: {hashlib.sha256(payload).hexdigest()}",
                "        file_type: csv",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def test_stage_download_streams_multiple_chunks(
    tmp_path: Path,
) -> None:
    chunks = [
        b"first",
        b"",
        b"-second",
        b"-third",
    ]
    expected_bytes = b"first-second-third"

    response = FakeResponse(chunks)
    session = FakeSession(response=response)

    staged = _stage_download(
        make_contract(),
        tmp_path,
        session=session,
    )

    assert staged.path.read_bytes() == expected_bytes
    assert staged.content_length == len(expected_bytes)
    assert staged.sha256 == hashlib.sha256(
        expected_bytes
    ).hexdigest()

    assert staged.path.suffix == ".part"
    assert not (tmp_path / "tr_cre.csv").exists()

    assert (
        response.requested_chunk_size
        == DOWNLOAD_CHUNK_BYTES
    )
    assert response.closed

    # An injected session belongs to its caller.
    assert not session.closed

    assert session.calls == [
        (
            (
                "https://www.eba.europa.eu/"
                "assets/example/tr_cre.csv"
            ),
            True,
            (
                CONNECT_TIMEOUT_SECONDS,
                READ_TIMEOUT_SECONDS,
            ),
        )
    ]

    staged.path.unlink()


def test_stage_download_cleans_interrupted_transfer(
    tmp_path: Path,
) -> None:
    response = FakeResponse(
        [
            b"partial",
            requests_exceptions.ChunkedEncodingError("transfer stopped"),
        ]
    )
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        _stage_download(
            make_contract(),
            tmp_path,
            session=session,
        )

    assert (
        caught.value.code
        is ErrorCode.DOWNLOAD_INTERRUPTED
    )
    assert "tr_cre.csv" in caught.value.message

    assert not list(tmp_path.glob("*.part"))
    assert not (tmp_path / "tr_cre.csv").exists()
    assert response.closed


def test_stage_download_maps_request_timeout(
    tmp_path: Path,
) -> None:
    session = FakeSession(
        request_error=requests_exceptions.ConnectTimeout(
            "connection timed out"
        )
    )

    with pytest.raises(ContractError) as caught:
        _stage_download(
            make_contract(),
            tmp_path,
            session=session,
        )

    assert caught.value.code is ErrorCode.DOWNLOAD_TIMEOUT
    assert "tr_cre.csv" in caught.value.message

    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    (
        "source_file",
        "file_type",
        "payload",
    ),
    [
        (
            "tr_cre.csv",
            SourceFileType.CSV,
            (
                FIXTURE_DIRECTORY
                / "tr_cre_valid.csv"
            ).read_bytes(),
        ),
        (
            "TR_Metadata.xlsx",
            SourceFileType.XLSX,
            b"PK\x03\x04synthetic-xlsx-content",
        ),
        (
            "CSV_and_Tools_guide_Transparency_2024.pdf",
            SourceFileType.PDF,
            b"%PDF-1.7\nsynthetic-pdf-content\n%%EOF",
        ),
    ],
)
def test_download_artifact_validates_and_publishes(
    tmp_path: Path,
    source_file: str,
    file_type: SourceFileType,
    payload: bytes,
) -> None:
    expected_sha256 = hashlib.sha256(
        payload
    ).hexdigest()

    response = FakeResponse(
        [
            payload[:5],
            payload[5:],
        ]
    )
    session = FakeSession(response=response)

    result = download_artifact(
        make_contract(
            expected_sha256,
            source_file=source_file,
            file_type=file_type,
        ),
        tmp_path,
        session=session,
    )

    expected_path = tmp_path / source_file

    assert result.source_file == source_file
    assert result.local_path == expected_path
    assert result.content_length == len(payload)
    assert result.sha256 == expected_sha256

    assert expected_path.read_bytes() == payload
    assert not list(tmp_path.glob("*.part"))


def test_download_artifact_rejects_empty_file(
    tmp_path: Path,
) -> None:
    payload = b""
    response = FakeResponse([payload])
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract(
                hashlib.sha256(payload).hexdigest()
            ),
            tmp_path,
            session=session,
        )

    assert caught.value.code is ErrorCode.EMPTY_FILE
    assert "tr_cre.csv" in caught.value.message
    assert not (tmp_path / "tr_cre.csv").exists()
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.parametrize(
    (
        "source_file",
        "file_type",
        "payload",
    ),
    [
        (
            "TR_Metadata.xlsx",
            SourceFileType.XLSX,
            b"PK",
        ),
        (
            "CSV_and_Tools_guide_Transparency_2024.pdf",
            SourceFileType.PDF,
            b"%PD",
        ),
    ],
)
def test_download_artifact_rejects_truncated_signature(
    tmp_path: Path,
    source_file: str,
    file_type: SourceFileType,
    payload: bytes,
) -> None:
    response = FakeResponse([payload])
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract(
                hashlib.sha256(payload).hexdigest(),
                source_file=source_file,
                file_type=file_type,
            ),
            tmp_path,
            session=session,
        )

    assert (
        caught.value.code
        is ErrorCode.INVALID_FILE_SIGNATURE
    )
    assert source_file in caught.value.message
    assert not (tmp_path / source_file).exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_artifact_rejects_wrong_csv_header(
    tmp_path: Path,
) -> None:
    payload = b"wrong,header\n1,2\n"
    response = FakeResponse([payload])
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract(
                hashlib.sha256(payload).hexdigest()
            ),
            tmp_path,
            session=session,
        )

    assert (
        caught.value.code
        is ErrorCode.INVALID_FILE_SIGNATURE
    )
    assert not (tmp_path / "tr_cre.csv").exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_artifact_rejects_invalid_utf8_csv(
    tmp_path: Path,
) -> None:
    payload = b"\xff\xfe\xfa"
    response = FakeResponse([payload])
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract(
                hashlib.sha256(payload).hexdigest()
            ),
            tmp_path,
            session=session,
        )

    assert (
        caught.value.code
        is ErrorCode.INVALID_FILE_SIGNATURE
    )
    assert not (tmp_path / "tr_cre.csv").exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_artifact_rejects_hash_mismatch(
    tmp_path: Path,
) -> None:
    payload = (
        FIXTURE_DIRECTORY
        / "tr_cre_valid.csv"
    ).read_bytes()

    response = FakeResponse([payload])
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract("0" * 64),
            tmp_path,
            session=session,
        )

    assert caught.value.code is ErrorCode.HASH_MISMATCH
    assert not (tmp_path / "tr_cre.csv").exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_artifact_does_not_overwrite_existing_file(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "tr_cre.csv"
    destination.write_bytes(b"existing-content")

    session = FakeSession()

    with pytest.raises(FileExistsError):
        download_artifact(
            make_contract(),
            tmp_path,
            session=session,
        )

    assert destination.read_bytes() == b"existing-content"
    assert session.calls == []
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.parametrize(
    "status_code",
    [404, 500],
)
def test_download_artifact_maps_http_status_errors(
    tmp_path: Path,
    status_code: int,
) -> None:
    response = FakeResponse(
        chunks=[],
        status_code=status_code,
    )
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract(),
            tmp_path,
            session=session,
        )

    assert caught.value.code is ErrorCode.HTTP_ERROR
    assert "tr_cre.csv" in caught.value.message
    assert f"HTTP status {status_code}" in caught.value.message

    assert response.closed
    assert len(session.calls) == 1
    assert not (tmp_path / "tr_cre.csv").exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_artifact_maps_stream_read_timeout(
    tmp_path: Path,
) -> None:
    response = FakeResponse(
        [
            b"partial-content",
            requests_exceptions.ReadTimeout(
                "response stopped"
            ),
        ]
    )
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract(),
            tmp_path,
            session=session,
        )

    assert caught.value.code is ErrorCode.DOWNLOAD_TIMEOUT
    assert "tr_cre.csv" in caught.value.message
    assert "streaming" in caught.value.message

    assert response.closed
    assert not (tmp_path / "tr_cre.csv").exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_artifact_cleans_interruption_before_first_chunk(
    tmp_path: Path,
) -> None:
    response = FakeResponse(
        [
            requests_exceptions.ChunkedEncodingError(
                "response ended before first chunk"
            )
        ]
    )
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract(),
            tmp_path,
            session=session,
        )

    assert (
        caught.value.code
        is ErrorCode.DOWNLOAD_INTERRUPTED
    )
    assert "tr_cre.csv" in caught.value.message

    assert response.closed
    assert not (tmp_path / "tr_cre.csv").exists()
    assert not list(tmp_path.glob("*.part"))


def test_validation_failure_preserves_unrelated_file(
    tmp_path: Path,
) -> None:
    unrelated_file = tmp_path / "existing-notes.txt"
    unrelated_file.write_bytes(b"do-not-change")

    payload = b"wrong,header\n1,2\n"
    response = FakeResponse([payload])
    session = FakeSession(response=response)

    with pytest.raises(ContractError) as caught:
        download_artifact(
            make_contract(
                hashlib.sha256(payload).hexdigest()
            ),
            tmp_path,
            session=session,
        )

    assert (
        caught.value.code
        is ErrorCode.INVALID_FILE_SIGNATURE
    )

    assert (
        unrelated_file.read_bytes()
        == b"do-not-change"
    )
    assert not (tmp_path / "tr_cre.csv").exists()
    assert not list(tmp_path.glob("*.part"))


def test_calculate_file_identity_streams_local_file(tmp_path: Path) -> None:
    path = tmp_path / "artifact.bin"
    payload = b"content" * 100
    path.write_bytes(payload)

    assert calculate_file_identity(path) == (
        len(payload),
        hashlib.sha256(payload).hexdigest(),
    )


def test_acquire_release_reuses_matching_file_without_http(tmp_path: Path) -> None:
    payload = (FIXTURE_DIRECTORY / "tr_cre_valid.csv").read_bytes()
    config_path = write_single_source_config(tmp_path, payload)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "tr_cre.csv").write_bytes(payload)
    session = FakeSession()

    results = acquire_release(config_path, 2024, output_dir, session=session)

    assert len(results) == 1
    assert results[0].status is ManifestStatus.UNCHANGED
    assert session.calls == []
    assert (output_dir / "manifest.json").exists()


def test_acquire_release_rejects_changed_local_content(tmp_path: Path) -> None:
    payload = (FIXTURE_DIRECTORY / "tr_cre_valid.csv").read_bytes()
    config_path = write_single_source_config(tmp_path, payload)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "tr_cre.csv"
    destination.write_bytes(b"changed")
    session = FakeSession()

    with pytest.raises(ContractError) as caught:
        acquire_release(config_path, 2024, output_dir, session=session)

    assert caught.value.code is ErrorCode.SOURCE_CONTENT_CHANGED
    assert destination.read_bytes() == b"changed"
    assert session.calls == []
    assert not (output_dir / "manifest.json").exists()


def test_force_redownload_replaces_only_after_validation(tmp_path: Path) -> None:
    payload = (FIXTURE_DIRECTORY / "tr_cre_valid.csv").read_bytes()
    config_path = write_single_source_config(tmp_path, payload)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "tr_cre.csv"
    destination.write_bytes(b"corrupt")

    results = acquire_release(
        config_path,
        2024,
        output_dir,
        force_redownload=True,
        session=FakeSession(FakeResponse([payload])),
    )

    assert results[0].status is ManifestStatus.DOWNLOADED
    assert destination.read_bytes() == payload
    assert not list(output_dir.glob("*.part"))


def test_failed_force_redownload_preserves_file_and_manifest(tmp_path: Path) -> None:
    payload = (FIXTURE_DIRECTORY / "tr_cre_valid.csv").read_bytes()
    config_path = write_single_source_config(tmp_path, payload)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "tr_cre.csv"
    destination.write_bytes(payload)
    acquire_release(config_path, 2024, output_dir, session=FakeSession())
    manifest_before = (output_dir / "manifest.json").read_bytes()

    with pytest.raises(ContractError) as caught:
        acquire_release(
            config_path,
            2024,
            output_dir,
            force_redownload=True,
            session=FakeSession(FakeResponse([b"wrong,header\n"])),
        )

    assert caught.value.code is ErrorCode.INVALID_FILE_SIGNATURE
    assert destination.read_bytes() == payload
    assert (output_dir / "manifest.json").read_bytes() == manifest_before
    assert not list(output_dir.glob("*.part"))
