"""Exercise real Tk windows and the unpacked Windows EXE, never the user's settings."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import win32gui
from PIL import Image, ImageGrab
from tkinterdnd2 import TkinterDnD

from heictojpg.app_gui import ConverterWindow
from heictojpg.config import AppConfig, save_config
from heictojpg.version import __version__


def wait_for(predicate, timeout: float = 45) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise TimeoutError("Release smoke test timed out")
        time.sleep(0.1)


def run_tk(window: ConverterWindow, action) -> None:
    errors: list[str] = []
    deadline = time.monotonic() + 45

    def report_error(kind, value, _traceback) -> None:
        errors.append(f"{kind.__name__}: {value}")
        window.root.quit()

    def poll() -> None:
        if not window._busy:
            window.root.quit()
        elif time.monotonic() >= deadline:
            errors.append("GUI conversion timed out")
            window.root.quit()
        else:
            window.root.after(20, poll)

    window.root.report_callback_exception = report_error
    window.root.after(20, action)
    window.root.after(40, poll)
    window.root.mainloop()
    assert not errors, errors
    assert not window._busy
    assert not window.widgets["convert"].instate(["disabled"])


def capture_tk(root, path: Path) -> None:
    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    ImageGrab.grab((x, y, x + root.winfo_width(), y + root.winfo_height())).save(path)


def make_inputs(folder: Path) -> list[Path]:
    folder.mkdir(parents=True)
    exif = Image.Exif()
    exif[315] = "Release privacy fixture"
    heic = folder / "photo.heic"
    Image.new("RGB", (40, 20), (80, 120, 200)).save(heic, format="HEIF", exif=exif)
    png = folder / "transparent image.png"
    Image.new("RGB", (20, 40), (0, 255, 0)).save(
        png, transparency=(0, 255, 0), exif=exif, icc_profile=b"fixture-profile"
    )
    return [heic, png]


def check_images(folder: Path, output_format: str) -> None:
    extension = {"jpeg": "jpg", "png": "png", "webp": "webp"}[output_format]
    for stem, size in [("photo", (16, 8)), ("transparent image", (8, 16))]:
        with Image.open(folder / f"{stem}.{extension}") as image:
            image.load()
            assert image.format == output_format.upper(), image.format
            assert image.size == size, (image.size, size)
            assert not image.getexif(), "Stripped EXIF reappeared in packaged output"
            assert not image.info.get("icc_profile"), "Stripped ICC reappeared"
            if stem == "transparent image":
                if output_format == "jpeg":
                    assert min(image.convert("RGB").getpixel((0, 0))) >= 240
                else:
                    assert image.convert("RGBA").getpixel((0, 0))[3] == 0
    assert not list(folder.glob(".heictojpg-*"))


def verify_case(exe: Path, work: Path, reports: Path, language: str, fmt: str) -> dict:
    from pywinauto import Desktop, mouse

    case = work / f"{language}-{fmt}"
    inputs = make_inputs(case / "入力 images")
    source_out, exe_out = case / "source-output", case / "exe-output"
    source_out.mkdir()
    exe_out.mkdir()
    config = AppConfig(
        output_mode="fixed_folder",
        output_dir=source_out,
        output_format=fmt,
        keep_exif=False,
        keep_icc_profile=False,
        max_dimension=16,
        language=language,
    )
    save_config(config)
    root = TkinterDnD.Tk()
    try:
        window = ConverterWindow(root, initial_paths=inputs)
        root.geometry("900x680+0+0")
        root.update()
        button = window.widgets["convert"]
        point = (
            button.winfo_rootx() - root.winfo_rootx() + button.winfo_width() // 2,
            button.winfo_rooty() - root.winfo_rooty() + button.winfo_height() // 2,
        )
        client_size = root.winfo_width(), root.winfo_height()
        run_tk(window, button.invoke)
        check_images(source_out, fmt)
        capture_tk(root, reports / f"source-{language}-{fmt}.png")
    finally:
        root.destroy()

    save_config(config.with_changes(output_dir=exe_out))
    process = subprocess.Popen([str(exe), *(str(path) for path in inputs)], cwd=case)
    wrapper = None
    try:
        spec = Desktop(backend="win32").window(title=f"HEIC Converter v{__version__}")
        spec.wait("visible", timeout=60)
        wrapper = spec.wrapper_object()
        hwnd = wrapper.handle
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        _, _, width, height = win32gui.GetClientRect(hwnd)
        wrapper.move_window(
            x=0,
            y=0,
            width=client_size[0] + right - left - width,
            height=client_size[1] + bottom - top - height,
        )
        wrapper.set_focus()
        time.sleep(0.3)
        click_point = win32gui.ClientToScreen(hwnd, point)
        print(f"Clicking Convert at {click_point}; client size {client_size}", flush=True)
        wrapper.capture_as_image().save(reports / f"exe-ready-{language}-{fmt}.png")
        hit = win32gui.WindowFromPoint(click_point)
        while hit and hit != hwnd:
            hit = win32gui.GetParent(hit)
        assert hit == hwnd, "Convert button is obscured or outside the test desktop"
        mouse.click(coords=click_point)
        extension = {"jpeg": "jpg", "png": "png", "webp": "webp"}[fmt]
        wait_for(lambda: len(list(exe_out.glob(f"*.{extension}"))) == len(inputs))
        check_images(exe_out, fmt)
        time.sleep(0.2)
        wrapper.capture_as_image().save(reports / f"exe-{language}-{fmt}.png")
        wrapper.close()
        process.wait(timeout=20)
        assert process.returncode == 0, process.returncode
    finally:
        if process.poll() is None:
            if wrapper is not None:
                wrapper.capture_as_image().save(reports / f"failure-{language}-{fmt}.png")
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False, timeout=15
            )
            process.wait(timeout=15)
    return {"language": language, "format": fmt, "source_gui": "passed", "exe_gui": "passed"}


def verify_cancel(work: Path, reports: Path) -> dict:
    folder = work / "cancel"
    folder.mkdir()
    output = folder / "output"
    output.mkdir()
    inputs = []
    for index in range(24):
        path = folder / f"batch-{index}.png"
        Image.new("RGB", (80, 40), (80, 120, 200)).save(path)
        inputs.append(path)
    save_config(AppConfig(output_mode="fixed_folder", output_dir=output))
    root = TkinterDnD.Tk()
    try:
        window = ConverterWindow(root, initial_paths=inputs)
        root.geometry("900x680+0+0")

        def start_and_cancel() -> None:
            window.widgets["convert"].invoke()
            window.widgets["cancel"].invoke()

        run_tk(window, start_and_cancel)
        count = len(list(output.glob("*.jpg")))
        assert count < len(inputs)
        assert window.cancel_event.is_set()
        capture_tk(root, reports / "source-cancelled.png")
        window.overwrite_policy = "skip"
        run_tk(window, window.widgets["convert"].invoke)
        assert len(list(output.glob("*.jpg"))) == len(inputs)
        assert not window.cancel_event.is_set()
        assert not list(output.glob(".heictojpg-*"))
        capture_tk(root, reports / "source-restarted.png")
    finally:
        root.destroy()
    return {"cancel": "passed", "restart": "passed", "completed_before_cancel": count}


def run_isolated_case(args, reports: Path, case: str) -> dict:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--exe",
        str(args.exe.resolve(strict=True)),
        "--report-dir",
        str(reports),
        "--case",
        case,
    ]
    if args.workspace_base is not None:
        command.extend(["--workspace-base", str(args.workspace_base.resolve())])
    with subprocess.Popen(command) as process:
        try:
            returncode = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False, timeout=15
            )
            process.wait(timeout=15)
            raise
        if returncode:
            raise subprocess.CalledProcessError(returncode, command)
    return json.loads((reports / f"case-{case}.json").read_text(encoding="utf-8"))


def main() -> None:
    # TkDnD uses OLE on the GUI thread. Select STA before importing pywinauto.
    sys.coinit_flags = 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--workspace-base", type=Path)
    parser.add_argument("--case", choices=["en-jpeg", "ja-png", "ja-webp", "cancel"])
    args = parser.parse_args()
    exe = args.exe.resolve(strict=True)
    reports = args.report_dir.resolve()
    reports.mkdir(parents=True, exist_ok=True)
    if args.case is None:
        # A real application owns one Tk interpreter per process. Isolate test
        # cases likewise: a later decoder thread must not garbage-collect an
        # earlier case's destroyed Tk variables/interpreter.
        cases = [
            run_isolated_case(args, reports, case) for case in ["en-jpeg", "ja-png", "ja-webp"]
        ]
        cancellation = run_isolated_case(args, reports, "cancel")
        result = {
            "version": __version__,
            "exe_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
            "workspaces": [record["workspace"] for record in [*cases, cancellation]],
            "cases": [record["result"] for record in cases],
            "cancellation": cancellation["result"],
            "physical_usb_tested": False,
        }
        (reports / "gui-verification.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2), flush=True)
        return

    old_appdata = os.environ.get("APPDATA")
    try:
        with tempfile.TemporaryDirectory(dir=args.workspace_base, prefix="heic-release-") as name:
            work = Path(name)
            os.environ["APPDATA"] = str(work / "appdata")
            if args.case == "cancel":
                case_result = verify_cancel(work, reports)
            else:
                language, fmt = args.case.split("-", 1)
                case_result = verify_case(exe, work, reports, language, fmt)
            # Finalize unreachable GUI cycles on the interpreter-owning thread.
            gc.collect()
            record = {"workspace": str(work), "result": case_result}
            (reports / f"case-{args.case}.json").write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8"
            )
    finally:
        if old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = old_appdata


if __name__ == "__main__":
    main()
