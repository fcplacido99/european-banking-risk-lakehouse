"""Stream official source responses to temporary local files."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Iterable, Protocol
from requests import exceptions as requests_exceptions

import requests

from eba_lakehouse.contracts import (
    ContractError,
    ErrorCode,
    SourceArtifactContract,
)


CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 120
DOWNLOAD_CHUNK_BYTES = 1024 * 1024


class _StreamingResponse(Protocol):
    """Minimum HTTP response interface required by the downloader."""

    status_code: int

    def raise_for_status(self) -> None:
        """Raise when the HTTP response is unsuccessful."""

    def iter_content(self, chunk_size: int) -> Iterable[bytes]:
        """Yield response-body chunks."""

    def close(self) -> None:
        """Close the response."""


class _HttpSession(Protocol):
    """Minimum HTTP session interface required by the downloader."""

    def get(
        self,
        url: str,
        *,
        stream: bool,
        timeout: tuple[int, int],
    ) -> _StreamingResponse:
        """Perform one streamed HTTP request."""

    def close(self) -> None:
        """Close the session."""


@dataclass(frozen=True, slots=True)
class _StagedDownload:
    """Temporary artifact awaiting content validation."""

    path: Path
    content_length: int
    sha256: str


def _download_error(
    code: ErrorCode,
    contract: SourceArtifactContract,
    detail: str,
) -> ContractError:
    return ContractError(
        code,
        f"{contract.source_file}: {detail}",
    )


def _remove_if_present(path: Path | None) -> None:
    if path is not None:
        path.unlink(missing_ok=True)


def _stream_to_temporary_file(
    response: _StreamingResponse,
    contract: SourceArtifactContract,
    output_dir: Path,
) -> _StagedDownload:
    """Stream a response to a unique temporary file."""

    staged_path: Path | None = None
    digest = hashlib.sha256()
    content_length = 0

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output_dir,
            prefix=f".{contract.source_file}.",
            suffix=".part",
            delete=False,
        ) as staged_file:
            staged_path = Path(staged_file.name)

            for chunk in response.iter_content(
                chunk_size=DOWNLOAD_CHUNK_BYTES
            ):
                # Requests may emit empty keep-alive chunks.
                if not chunk:
                    continue

                staged_file.write(chunk)
                digest.update(chunk)
                content_length += len(chunk)

            staged_file.flush()
            os.fsync(staged_file.fileno())

        return _StagedDownload(
            path=staged_path,
            content_length=content_length,
            sha256=digest.hexdigest(),
        )

    except requests_exceptions.Timeout as error:
        _remove_if_present(staged_path)

        raise _download_error(
            ErrorCode.DOWNLOAD_TIMEOUT,
            contract,
            "download timed out while streaming the response",
        ) from error

    except requests_exceptions.RequestException as error:
        _remove_if_present(staged_path)

        raise _download_error(
            ErrorCode.DOWNLOAD_INTERRUPTED,
            contract,
            "download was interrupted while streaming the response",
        ) from error

    except Exception:
        _remove_if_present(staged_path)
        raise


def _stage_download(
    contract: SourceArtifactContract,
    output_dir: Path,
    *,
    session: _HttpSession | None = None,
) -> _StagedDownload:
    """Request and stage one artifact without publishing its final name."""

    output_dir.mkdir(parents=True, exist_ok=True)

    owns_session = session is None
    http_session: _HttpSession = session or requests.Session()
    response: _StreamingResponse | None = None

    try:
        try:
            response = http_session.get(
                contract.source_url,
                stream=True,
                timeout=(
                    CONNECT_TIMEOUT_SECONDS,
                    READ_TIMEOUT_SECONDS,
                ),
            )
            response.raise_for_status()

        except requests_exceptions.Timeout as error:
            raise _download_error(
                ErrorCode.DOWNLOAD_TIMEOUT,
                contract,
                "HTTP request timed out",
            ) from error

        except requests_exceptions.HTTPError as error:
            status_code = getattr(
                error.response,
                "status_code",
                None,
            )
            detail = (
                f"HTTP status {status_code}"
                if status_code is not None
                else "HTTP request failed"
            )

            raise _download_error(
                ErrorCode.HTTP_ERROR,
                contract,
                detail,
            ) from error

        except requests_exceptions.RequestException as error:
            raise _download_error(
                ErrorCode.DOWNLOAD_INTERRUPTED,
                contract,
                "HTTP request was interrupted",
            ) from error

        return _stream_to_temporary_file(
            response,
            contract,
            output_dir,
        )

    finally:
        if response is not None:
            response.close()

        if owns_session:
            http_session.close()