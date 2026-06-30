from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from tkinter import Tk

from PIL import ImageGrab
from tkinterdnd2 import TkinterDnD

from heictojpg.app_gui import ConverterWindow
from heictojpg.config import LANGUAGE_EN, LANGUAGE_JA
from heictojpg.gui import SettingsWindow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = PROJECT_ROOT / "docs" / "images"


def main() -> int:
    _enable_dpi_awareness()
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="heic-converter-screenshots-") as appdata:
        os.environ["APPDATA"] = appdata
        _capture_converter(LANGUAGE_JA, IMAGE_DIR / "converter-ja.png")
        _capture_converter(LANGUAGE_EN, IMAGE_DIR / "converter-en.png")
        _capture_settings(LANGUAGE_JA, IMAGE_DIR / "settings-ja.png")
        _capture_settings(LANGUAGE_EN, IMAGE_DIR / "settings-en.png")
    return 0


def _enable_dpi_awareness() -> None:
    if os.name != "nt":
        return

    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except OSError:
        ctypes.windll.user32.SetProcessDPIAware()


def _capture_converter(language: str, output_path: Path) -> None:
    root = TkinterDnD.Tk()
    try:
        window = ConverterWindow(root)
        window.language = language
        window._apply_language()
        _capture_root(root, output_path, geometry="1280x900+80+80")
    finally:
        root.destroy()


def _capture_settings(language: str, output_path: Path) -> None:
    root = Tk()
    try:
        window = SettingsWindow(root)
        window.language = language
        window._apply_language()
        _capture_root(root, output_path, geometry="680x900+80+80")
    finally:
        root.destroy()


def _capture_root(root: Tk, output_path: Path, *, geometry: str) -> None:
    root.update_idletasks()
    root.overrideredirect(True)
    root.geometry(geometry)
    root.attributes("-topmost", True)
    root.deiconify()
    root.lift()
    root.focus_force()
    root.update()
    time.sleep(0.3)
    root.update()

    left = root.winfo_rootx()
    top = root.winfo_rooty()
    right = left + root.winfo_width()
    bottom = top + root.winfo_height()
    image = ImageGrab.grab(bbox=(left, top, right, bottom))
    image.save(output_path)


if __name__ == "__main__":
    raise SystemExit(main())
