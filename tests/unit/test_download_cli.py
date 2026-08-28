"""Tests for the local acquisition command-line interface."""

from pathlib import Path

import pytest

from eba_lakehouse.contracts import (
    AcquisitionResult,
    ContractError,
    DownloadedArtifact,
    ErrorCode,
    ManifestStatus,
)
from eba_lakehouse import download


def make_result(output_dir: Path, status: ManifestStatus) -> AcquisitionResult:
    return AcquisitionResult(
        artifact=DownloadedArtifact(
            source_file="tr_cre.csv",
            local_path=output_dir / "tr_cre.csv",
            content_length=10,
            sha256="a" * 64,
        ),
        status=status,
    )


def test_help_describes_public_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        download.main(["--help"])

    assert caught.value.code == 0
    output = capsys.readouterr().out
    assert "--release-year" in output
    assert "--output-dir" in output
    assert "--force-redownload" in output


@pytest.mark.parametrize("value", ["yes", "1", "invalid"])
def test_invalid_boolean_is_rejected(
    value: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as caught:
        download.main(
            [
                "--release-year",
                "2024",
                "--output-dir",
                "outside",
                "--force-redownload",
                value,
            ]
        )
    assert caught.value.code == 2
    assert "expected 'true' or 'false'" in capsys.readouterr().err


@pytest.mark.parametrize("relative_path", [".", "src", "tests/unit", ".venv"])
def test_repository_destinations_are_rejected(
    relative_path: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    unsafe_path = download._repository_root() / relative_path
    exit_code = download.main(
        ["--release-year", "2024", "--output-dir", str(unsafe_path)]
    )
    assert exit_code == 2
    assert "unsafe acquisition output directory" in capsys.readouterr().err


def test_regular_file_destination_is_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "not-a-directory"
    path.write_text("content", encoding="utf-8")
    assert download.main(["--release-year", "2024", "--output-dir", str(path)]) == 2
    assert "is not a directory" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("force_value", "expected_force"),
    [("false", False), ("FALSE", False), ("true", True), ("TRUE", True)],
)
def test_cli_passes_arguments_and_prints_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    force_value: str,
    expected_force: bool,
) -> None:
    output_dir = tmp_path / "new-output"
    observed: dict[str, object] = {}

    def fake_acquire(
        config_path: Path,
        release_year: int,
        received_output_dir: Path,
        *,
        force_redownload: bool,
    ) -> tuple[AcquisitionResult, ...]:
        observed.update(
            config_path=config_path,
            release_year=release_year,
            output_dir=received_output_dir,
            force_redownload=force_redownload,
        )
        received_output_dir.mkdir(parents=True)
        return (make_result(received_output_dir, ManifestStatus.UNCHANGED),)

    monkeypatch.setattr(download, "acquire_release", fake_acquire)
    exit_code = download.main(
        [
            "--release-year",
            "2024",
            "--output-dir",
            str(output_dir),
            "--force-redownload",
            force_value,
        ]
    )

    assert exit_code == 0
    assert observed["release_year"] == 2024
    assert observed["force_redownload"] is expected_force
    assert observed["config_path"] == download._repository_root() / "config" / "sources.yml"
    assert output_dir.exists()
    output = capsys.readouterr().out
    assert "tr_cre.csv: unchanged" in output
    assert f"Manifest: {output_dir / 'manifest.json'}" in output


def test_controlled_failure_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_acquire(*args, **kwargs):
        raise ContractError(ErrorCode.INVALID_SOURCE_CONFIG, "release is unavailable")

    monkeypatch.setattr(download, "acquire_release", fail_acquire)
    exit_code = download.main(
        ["--release-year", "2025", "--output-dir", str(tmp_path / "output")]
    )
    assert exit_code == 2
    error = capsys.readouterr().err
    assert "INVALID_SOURCE_CONFIG" in error
    assert "release is unavailable" in error
