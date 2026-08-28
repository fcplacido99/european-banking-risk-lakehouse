"""Stream official source responses to temporary local files."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Iterable, Protocol
from requests import exceptions as requests_exceptions

import requests
import csv

from eba_lakehouse.contracts import (
    ContractError,
    DownloadedArtifact,
    ErrorCode,
    SourceArtifactContract,
    SourceFileType,
)


CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 120
DOWNLOAD_CHUNK_BYTES = 1024 * 1024

CREDIT_CSV_HEADER = (
    "LEI_Code",
    "NSA",
    "Period",
    "Item",
    "Label",
    "Portfolio",
    "Country",
    "Country_rank",
    "Exposure",
    "Status",
    "Perf_Status",
    "NACE_codes",
    "Amount",
    "Footnote",
    "Row",
    "Column",
    "Sheet",
)

OTHER_CSV_HEADER = (
    "LEI_Code",
    "NSA",
    "Period",
    "Item",
    "Label",
    "ASSETS_FV",
    "ASSETS_Stages",
    "Exposure",
    "Financial_instruments",
    "Amount",
    "Fin_end_year",
    "n_quarters",
    "Footnote",
    "Row",
    "Column",
    "Sheet",
)

_EXPECTED_CSV_HEADERS = {
    "tr_cre.csv": CREDIT_CSV_HEADER,
    "tr_oth.csv": OTHER_CSV_HEADER,
}

PDF_SIGNATURE = b"%PDF-"
XLSX_SIGNATURE = b"PK\x03\x04"


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


def _validate_csv_header(
    staged_path: Path,
    contract: SourceArtifactContract,
) -> None:
    """Validate the complete header of a locked CSV artifact."""

    expected_header = _EXPECTED_CSV_HEADERS.get(
        contract.source_file
    )

    if expected_header is None:
        raise _download_error(
            ErrorCode.INVALID_FILE_SIGNATURE,
            contract,
            "no CSV header contract is defined",
        )

    try:
        with staged_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as staged_file:
            observed_header = tuple(
                next(csv.reader(staged_file))
            )

    except (
        UnicodeDecodeError,
        csv.Error,
        StopIteration,
    ) as error:
        raise _download_error(
            ErrorCode.INVALID_FILE_SIGNATURE,
            contract,
            "file is not a readable UTF-8 CSV",
        ) from error

    if observed_header != expected_header:
        raise _download_error(
            ErrorCode.INVALID_FILE_SIGNATURE,
            contract,
            (
                "CSV header does not match the locked "
                f"{contract.source_file} contract"
            ),
        )


def _validate_binary_signature(
    staged_path: Path,
    contract: SourceArtifactContract,
    expected_signature: bytes,
) -> None:
    """Validate a binary file's leading signature bytes."""

    with staged_path.open("rb") as staged_file:
        observed_signature = staged_file.read(
            len(expected_signature)
        )

    if observed_signature != expected_signature:
        raise _download_error(
            ErrorCode.INVALID_FILE_SIGNATURE,
            contract,
            (
                "file signature does not match "
                f"{contract.file_type.value}"
            ),
        )


def _validate_staged_download(
    staged: _StagedDownload,
    contract: SourceArtifactContract,
) -> None:
    """Validate size, physical signature and configured hash."""

    if staged.content_length == 0:
        raise _download_error(
            ErrorCode.EMPTY_FILE,
            contract,
            "downloaded artifact is empty",
        )

    if contract.file_type is SourceFileType.CSV:
        _validate_csv_header(
            staged.path,
            contract,
        )

    elif contract.file_type is SourceFileType.XLSX:
        _validate_binary_signature(
            staged.path,
            contract,
            XLSX_SIGNATURE,
        )

    elif contract.file_type is SourceFileType.PDF:
        _validate_binary_signature(
            staged.path,
            contract,
            PDF_SIGNATURE,
        )

    else:
        raise _download_error(
            ErrorCode.INVALID_FILE_SIGNATURE,
            contract,
            f"unsupported file type {contract.file_type!r}",
        )

    if (
        staged.sha256.lower()
        != contract.expected_sha256.lower()
    ):
        raise _download_error(
            ErrorCode.HASH_MISMATCH,
            contract,
            (
                "downloaded SHA-256 does not match "
                "the configured source contract"
            ),
        )


def _validate_source_filename(
    contract: SourceArtifactContract,
) -> None:
    """Reject directory components in a destination filename."""

    if (
        contract.source_file != Path(contract.source_file).name
        or "/" in contract.source_file
        or "\\" in contract.source_file
    ):
        raise ContractError(
            ErrorCode.INVALID_SOURCE_CONFIG,
            (
                "source_file must contain only a filename: "
                f"{contract.source_file!r}"
            ),
        )


def download_artifact(
    contract: SourceArtifactContract,
    output_dir: Path,
    *,
    session: _HttpSession | None = None,
) -> DownloadedArtifact:
    """Download, validate and atomically publish one artifact."""

    _validate_source_filename(contract)

    final_path = output_dir / contract.source_file

    # Week 4 will replace this with same-hash idempotency.
    if final_path.exists():
        raise FileExistsError(
            f"Destination already exists: {final_path}"
        )

    staged: _StagedDownload | None = None

    try:
        staged = _stage_download(
            contract,
            output_dir,
            session=session,
        )

        _validate_staged_download(
            staged,
            contract,
        )

        # Check again immediately before publication.
        if final_path.exists():
            raise FileExistsError(
                f"Destination already exists: {final_path}"
            )

        os.replace(
            staged.path,
            final_path,
        )

        return DownloadedArtifact(
            source_file=contract.source_file,
            local_path=final_path,
            content_length=staged.content_length,
            sha256=staged.sha256,
        )

    finally:
        if staged is not None:
            _remove_if_present(staged.path)