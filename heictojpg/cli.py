from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from heictojpg.config import (
    APP_NAME,
    FORMAT_JPEG,
    FORMAT_PNG,
    FORMAT_WEBP,
    OUTPUT_MODE_FIXED_FOLDER,
    OVERWRITE_POLICIES,
    OVERWRITE_OVERWRITE,
    AppConfig,
    ConfigError,
    load_config,
    validate_config,
)
from heictojpg.app_gui import run_converter_app
from heictojpg.converter import ConversionError, convert_files, convert_folder
from heictojpg.gui import run_settings_app
from heictojpg.version import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "convert":
            return _run_convert(args)
        if args.command == "convert-folder":
            return _run_convert_folder(args)
        if args.command == "context-convert":
            return _run_context_convert(args)
        if args.command == "app":
            run_converter_app([Path(value) for value in args.files])
            return 0
        if args.command == "settings":
            run_settings_app()
            return 0
    except (ConfigError, ConversionError) as exc:
        _write_error(str(exc))
        _show_error_dialog(APP_NAME, str(exc), enabled=not args.no_dialog)
        return 1

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="heictojpg")
    parser.add_argument(
        "--no-dialog",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"heictojpg {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    convert = subparsers.add_parser("convert", help="Convert image files.")
    convert.add_argument("files", nargs="+", help="Image files to convert.")
    _add_conversion_options(convert)

    context_convert = subparsers.add_parser(
        "context-convert",
        help="Start File Explorer right-click conversion and return immediately.",
    )
    context_convert.add_argument("files", nargs="+", help="Image files to convert.")

    app = subparsers.add_parser("app", help="Open the drag-and-drop conversion app.")
    app.add_argument("files", nargs="*", help="Image files or folders to pre-load.")

    convert_folder_parser = subparsers.add_parser(
        "convert-folder",
        help="Convert image files in a folder.",
    )
    convert_folder_parser.add_argument("folder", type=Path, help="Folder containing image files.")
    convert_folder_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Convert files in child folders too.",
    )
    _add_conversion_options(convert_folder_parser)

    subparsers.add_parser("settings", help="Open conversion settings.")
    return parser


def _add_conversion_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        type=Path,
        help="Fixed output folder. If omitted, saved settings are used.",
    )
    parser.add_argument(
        "--format",
        choices=(FORMAT_JPEG, FORMAT_PNG, FORMAT_WEBP),
        dest="output_format",
        help="Output format.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        help="JPEG/WebP quality from 1 to 100.",
    )
    parser.add_argument(
        "--jpeg-optimize",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable JPEG optimize.",
    )
    parser.add_argument(
        "--jpeg-progressive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable progressive JPEG.",
    )
    parser.add_argument(
        "--webp-lossless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable WebP lossless output.",
    )
    parser.add_argument(
        "--png-compress-level",
        type=int,
        help="PNG compression level from 0 to 9.",
    )
    parser.add_argument(
        "--overwrite-policy",
        choices=OVERWRITE_POLICIES,
        help="What to do when the target file already exists.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Shortcut for --overwrite-policy overwrite.",
    )
    parser.add_argument(
        "--keep-exif",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Keep or remove EXIF metadata.",
    )
    parser.add_argument(
        "--keep-icc-profile",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Keep or remove ICC color profiles.",
    )
    parser.add_argument(
        "--remove-gps",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Remove GPS metadata from EXIF when EXIF is kept.",
    )
    parser.add_argument(
        "--open-output-folder",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Open output folders after conversion.",
    )


def _run_convert(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    results = convert_files(args.files, settings=config)
    _print_results(results)
    if config.open_output_folder:
        _open_result_folders(results)
    return _exit_code_for_results(results)


def _run_convert_folder(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    results = convert_folder(args.folder, recursive=args.recursive, settings=config)
    _print_results(results)
    if config.open_output_folder:
        _open_result_folders(results)
    return _exit_code_for_results(results)


def _run_context_convert(args: argparse.Namespace) -> int:
    command = _context_worker_command(args.files)
    try:
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=_detached_creationflags(),
        )
    except OSError as exc:
        raise ConfigError(f"Failed to start right-click conversion: {exc}") from exc
    return 0


def _context_worker_command(files: Sequence[str]) -> list[str]:
    return [
        sys.executable,
        "-m",
        "heictojpg",
        "convert",
        "--no-open-output-folder",
        *files,
    ]


def _detached_creationflags() -> int:
    if sys.platform != "win32":
        return 0
    return (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.CREATE_NO_WINDOW
    )


def _config_from_args(args: argparse.Namespace) -> AppConfig:
    config = load_config()
    changes: dict[str, object] = {}

    if args.output is not None:
        changes["output_mode"] = OUTPUT_MODE_FIXED_FOLDER
        changes["output_dir"] = args.output.resolve()
    if args.output_format is not None:
        changes["output_format"] = args.output_format
    if args.quality is not None:
        if args.output_format == FORMAT_WEBP or (
            args.output_format is None and config.output_format == FORMAT_WEBP
        ):
            changes["webp_quality"] = args.quality
        elif args.output_format == FORMAT_PNG or (
            args.output_format is None and config.output_format == FORMAT_PNG
        ):
            raise ConfigError("--quality applies only to JPEG and WebP output.")
        else:
            changes["jpeg_quality"] = args.quality
    if args.jpeg_optimize is not None:
        changes["jpeg_optimize"] = args.jpeg_optimize
    if args.jpeg_progressive is not None:
        changes["jpeg_progressive"] = args.jpeg_progressive
    if args.webp_lossless is not None:
        changes["webp_lossless"] = args.webp_lossless
    if args.png_compress_level is not None:
        changes["png_compress_level"] = args.png_compress_level
    if args.overwrite_policy is not None:
        changes["overwrite_policy"] = args.overwrite_policy
    if args.overwrite:
        changes["overwrite_policy"] = OVERWRITE_OVERWRITE
    if args.keep_exif is not None:
        changes["keep_exif"] = args.keep_exif
    if args.keep_icc_profile is not None:
        changes["keep_icc_profile"] = args.keep_icc_profile
    if args.remove_gps is not None:
        changes["remove_gps"] = args.remove_gps
    if args.open_output_folder is not None:
        changes["open_output_folder"] = args.open_output_folder

    if changes:
        config = config.with_changes(**changes)
    return validate_config(config)


def _print_results(results: list[object]) -> None:
    if not results:
        _write_line("No supported image files found.")
        return
    for result in results:
        status = getattr(result, "status", "converted")
        source = getattr(result, "source")
        target = getattr(result, "target")
        if status == "skipped":
            _write_line(f"Skipped: {source} -> {target}")
        elif status == "failed":
            error = getattr(result, "error", None) or "Unknown conversion error."
            _write_line(f"Failed: {source}: {error}")
        else:
            _write_line(f"{source} -> {target}")
    converted, skipped, failed = _result_counts(results)
    _write_line(f"Summary: converted {converted}; skipped {skipped}; failed {failed}.")


def _exit_code_for_results(results: list[object]) -> int:
    _converted, _skipped, failed = _result_counts(results)
    return 1 if failed else 0


def _result_counts(results: list[object]) -> tuple[int, int, int]:
    converted = sum(1 for result in results if getattr(result, "status", "converted") == "converted")
    skipped = sum(1 for result in results if getattr(result, "status", "converted") == "skipped")
    failed = sum(1 for result in results if getattr(result, "status", "converted") == "failed")
    return converted, skipped, failed


def _open_result_folders(results: list[object]) -> None:
    folders = sorted(
        {
            str(getattr(result, "target").parent)
            for result in results
            if getattr(result, "status", "converted") != "failed"
        }
    )
    for folder in folders:
        _open_folder(folder)


def _open_folder(folder: str) -> None:
    if sys.platform == "win32":
        os.startfile(folder)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


def _write_line(message: str) -> None:
    if sys.stdout is not None:
        print(message)


def _write_error(message: str) -> None:
    if sys.stderr is not None:
        print(f"Error: {message}", file=sys.stderr)


def _show_error_dialog(title: str, message: str, *, enabled: bool) -> None:
    if not enabled or os.environ.get("HEICTOJPG_DISABLE_DIALOG") == "1":
        return
    if not _should_show_dialog():
        return

    try:
        from tkinter import messagebox

        messagebox.showerror(title, message)
    except Exception:
        return


def _should_show_dialog() -> bool:
    if sys.platform != "win32":
        return False

    executable = Path(sys.executable).name.lower()
    if executable == "pythonw.exe":
        return True

    stream = sys.stderr
    return stream is None or not stream.isatty()
