import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from heictojpg import cli
from heictojpg.cli import main


def test_cli_convert_png(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_config(tmp_path, monkeypatch)
    source = tmp_path / "sample.heic"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    _write_sample_heic(source)

    exit_code = main(
        [
            "--no-dialog",
            "convert",
            str(source),
            "--output",
            str(output_dir),
            "--format",
            "png",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "sample.png").exists()


def test_cli_context_convert_starts_detached_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "sample.heic"
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_popen(command: list[str], **kwargs: object) -> object:
        calls.append((command, kwargs))
        return object()

    monkeypatch.setattr(sys, "executable", "pythonw.exe")
    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(cli, "_detached_creationflags", lambda: 123)

    exit_code = main(["--no-dialog", "context-convert", str(source)])

    assert exit_code == 0
    assert calls == [
        (
            [
                "pythonw.exe",
                "-m",
                "heictojpg",
                "convert",
                "--no-open-output-folder",
                str(source),
            ],
            {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "close_fds": True,
                "creationflags": 123,
            },
        )
    ]


def test_cli_app_opens_converter_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "sample.png"
    calls: list[list[Path]] = []

    monkeypatch.setattr(cli, "run_converter_app", lambda paths: calls.append(paths))

    exit_code = main(["--no-dialog", "app", str(source)])

    assert exit_code == 0
    assert calls == [[source]]


def test_cli_convert_folder_recursive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _isolate_config(tmp_path, monkeypatch)
    source = tmp_path / "sample.heic"
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_sample_heic(source)
    _write_sample_heic(nested / "nested.heic")

    exit_code = main(["--no-dialog", "convert-folder", str(tmp_path), "--recursive"])

    assert exit_code == 0
    assert (tmp_path / "sample.jpg").exists()
    assert (nested / "nested.jpg").exists()


def test_cli_convert_reports_failures_and_returns_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _isolate_config(tmp_path, monkeypatch)
    good = tmp_path / "good.png"
    bad = tmp_path / "bad.png"
    _write_sample_png(good)
    bad.write_text("not an image", encoding="utf-8")

    exit_code = main(["--no-dialog", "convert", str(bad), str(good)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Failed:" in output
    assert "Summary: converted 1; skipped 0; failed 1." in output
    assert (tmp_path / "good.jpg").exists()


def test_cli_convert_can_remove_icc_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_config(tmp_path, monkeypatch)
    source = tmp_path / "sample.png"
    _write_sample_png(source, icc_profile=b"test-icc-profile")

    exit_code = main(
        [
            "--no-dialog",
            "convert",
            str(source),
            "--format",
            "png",
            "--no-keep-icc-profile",
        ]
    )

    assert exit_code == 0
    with Image.open(tmp_path / "sample_1.png") as image:
        assert "icc_profile" not in image.info


def _isolate_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    appdata = tmp_path / "appdata"
    home = tmp_path / "home"
    appdata.mkdir()
    home.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("HOME", str(home))


def _write_sample_heic(path: Path) -> None:
    image = Image.new("RGB", (8, 6), (80, 120, 200))
    try:
        image.save(path, format="HEIF")
    except Exception as exc:
        pytest.skip(f"HEIF encoding is unavailable in this environment: {exc}")


def _write_sample_png(path: Path, *, icc_profile: bytes | None = None) -> None:
    save_kwargs = {}
    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile
    Image.new("RGBA", (8, 6), (80, 120, 200, 160)).save(
        path,
        format="PNG",
        **save_kwargs,
    )
