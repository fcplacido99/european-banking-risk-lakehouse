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
    SourceArtifactContract,
    SourceFileType,
)
from eba_lakehouse.download import (
    CONNECT_TIMEOUT_SECONDS,
    DOWNLOAD_CHUNK_BYTES,
    READ_TIMEOUT_SECONDS,
    _stage_download,
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
) -> SourceArtifactContract:
    return SourceArtifactContract(
        release_year=2024,
        source_url=(
            "https://www.eba.europa.eu/"
            "assets/example/tr_cre.csv"
        ),
        source_file="tr_cre.csv",
        expected_sha256=expected_sha256,
        file_type=SourceFileType.CSV,
    )


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