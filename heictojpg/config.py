from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


APP_NAME = "HEIC Converter"
APP_DIR_NAME = "HEICtoJPG"
CONFIG_FILENAME = "config.json"

OUTPUT_MODE_SAME_FOLDER = "same_folder"
OUTPUT_MODE_FIXED_FOLDER = "fixed_folder"
OUTPUT_MODE_CONVERTED_SUBFOLDER = "converted_subfolder"
OUTPUT_MODES = (
    OUTPUT_MODE_SAME_FOLDER,
    OUTPUT_MODE_FIXED_FOLDER,
    OUTPUT_MODE_CONVERTED_SUBFOLDER,
)

FORMAT_JPEG = "jpeg"
FORMAT_PNG = "png"
FORMAT_WEBP = "webp"
OUTPUT_FORMATS = (FORMAT_JPEG, FORMAT_PNG, FORMAT_WEBP)
FORMAT_EXTENSIONS = {
    FORMAT_JPEG: ".jpg",
    FORMAT_PNG: ".png",
    FORMAT_WEBP: ".webp",
}

OVERWRITE_RENAME = "rename"
OVERWRITE_SKIP = "skip"
OVERWRITE_OVERWRITE = "overwrite"
OVERWRITE_ERROR = "error"
OVERWRITE_POLICIES = (
    OVERWRITE_RENAME,
    OVERWRITE_SKIP,
    OVERWRITE_OVERWRITE,
    OVERWRITE_ERROR,
)

LANGUAGE_EN = "en"
LANGUAGE_JA = "ja"
LANGUAGES = (LANGUAGE_EN, LANGUAGE_JA)


class ConfigError(RuntimeError):
    """Raised when the saved application configuration cannot be used."""


@dataclass(frozen=True)
class AppConfig:
    output_mode: str = OUTPUT_MODE_SAME_FOLDER
    output_dir: Path | None = None
    output_format: str = FORMAT_JPEG
    jpeg_quality: int = 95
    jpeg_optimize: bool = True
    jpeg_progressive: bool = False
    webp_quality: int = 95
    webp_lossless: bool = False
    png_compress_level: int = 6
    overwrite_policy: str = OVERWRITE_RENAME
    keep_exif: bool = True
    keep_icc_profile: bool = True
    remove_gps: bool = False
    open_output_folder: bool = False
    language: str = LANGUAGE_EN

    def with_changes(self, **changes: object) -> AppConfig:
        return validate_config(replace(self, **changes))

    def output_label(self) -> str:
        if self.output_mode == OUTPUT_MODE_SAME_FOLDER:
            return "Same folder as the source image"
        if self.output_mode == OUTPUT_MODE_CONVERTED_SUBFOLDER:
            return "converted subfolder next to the source image"
        if self.output_dir is None:
            return "Fixed folder is not set"
        return str(self.output_dir)

    def label(self) -> str:
        return self.output_label()


def default_config_path() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise ConfigError("APPDATA is not set; cannot locate the Windows app data folder.")
        return Path(appdata) / APP_DIR_NAME / CONFIG_FILENAME

    return Path.home() / ".config" / APP_DIR_NAME / CONFIG_FILENAME


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or default_config_path()
    if not config_path.exists():
        return AppConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file: {config_path}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Config file must contain a JSON object: {config_path}")

    return _config_from_mapping(data, config_path)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    config = validate_config(config)
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(_config_to_mapping(config), indent=2) + "\n", encoding="utf-8")
    return config_path


def validate_config(config: AppConfig) -> AppConfig:
    if config.output_mode not in OUTPUT_MODES:
        raise ConfigError(f"Unsupported output mode: {config.output_mode}")
    if config.output_format not in OUTPUT_FORMATS:
        raise ConfigError(f"Unsupported output format: {config.output_format}")
    if config.overwrite_policy not in OVERWRITE_POLICIES:
        raise ConfigError(f"Unsupported overwrite policy: {config.overwrite_policy}")
    if config.language not in LANGUAGES:
        raise ConfigError(f"Unsupported UI language: {config.language}")

    if config.output_mode == OUTPUT_MODE_FIXED_FOLDER:
        if config.output_dir is None:
            raise ConfigError("Fixed output folder mode requires an output folder.")
        _validate_output_dir(config.output_dir)
    elif config.output_dir is not None:
        config = replace(config, output_dir=None)

    _validate_range("JPEG quality", config.jpeg_quality, 1, 100)
    _validate_range("WebP quality", config.webp_quality, 1, 100)
    _validate_range("PNG compress_level", config.png_compress_level, 0, 9)
    return config


def _config_from_mapping(data: dict[str, Any], config_path: Path) -> AppConfig:
    output_dir = _read_optional_path(data, "output_dir", config_path)
    output_mode = _read_string(data, "output_mode", config_path)
    if output_mode is None:
        output_mode = OUTPUT_MODE_FIXED_FOLDER if output_dir is not None else OUTPUT_MODE_SAME_FOLDER

    config = AppConfig(
        output_mode=output_mode,
        output_dir=output_dir,
        output_format=_read_string(data, "output_format", config_path) or FORMAT_JPEG,
        jpeg_quality=_read_int(data, "jpeg_quality", config_path, 95),
        jpeg_optimize=_read_bool(data, "jpeg_optimize", config_path, True),
        jpeg_progressive=_read_bool(data, "jpeg_progressive", config_path, False),
        webp_quality=_read_int(data, "webp_quality", config_path, 95),
        webp_lossless=_read_bool(data, "webp_lossless", config_path, False),
        png_compress_level=_read_int(data, "png_compress_level", config_path, 6),
        overwrite_policy=_read_string(data, "overwrite_policy", config_path) or OVERWRITE_RENAME,
        keep_exif=_read_bool(data, "keep_exif", config_path, True),
        keep_icc_profile=_read_bool(data, "keep_icc_profile", config_path, True),
        remove_gps=_read_bool(data, "remove_gps", config_path, False),
        open_output_folder=_read_bool(data, "open_output_folder", config_path, False),
        language=_read_string(data, "language", config_path) or LANGUAGE_EN,
    )
    return validate_config(config)


def _config_to_mapping(config: AppConfig) -> dict[str, object]:
    return {
        "output_mode": config.output_mode,
        "output_dir": str(config.output_dir) if config.output_dir is not None else None,
        "output_format": config.output_format,
        "jpeg_quality": config.jpeg_quality,
        "jpeg_optimize": config.jpeg_optimize,
        "jpeg_progressive": config.jpeg_progressive,
        "webp_quality": config.webp_quality,
        "webp_lossless": config.webp_lossless,
        "png_compress_level": config.png_compress_level,
        "overwrite_policy": config.overwrite_policy,
        "keep_exif": config.keep_exif,
        "keep_icc_profile": config.keep_icc_profile,
        "remove_gps": config.remove_gps,
        "open_output_folder": config.open_output_folder,
        "language": config.language,
    }


def _read_string(data: dict[str, Any], key: str, config_path: Path) -> str | None:
    if key not in data or data[key] is None:
        return None
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{key}' must be a non-empty string in config file: {config_path}")
    return value


def _read_bool(data: dict[str, Any], key: str, config_path: Path, default: bool) -> bool:
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, bool):
        raise ConfigError(f"'{key}' must be a boolean in config file: {config_path}")
    return value


def _read_int(data: dict[str, Any], key: str, config_path: Path, default: int) -> int:
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"'{key}' must be an integer in config file: {config_path}")
    return value


def _read_optional_path(data: dict[str, Any], key: str, config_path: Path) -> Path | None:
    if key not in data or data[key] is None:
        return None
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{key}' must be null or a non-empty string in config file: {config_path}")
    return Path(value)


def _validate_output_dir(output_dir: Path) -> None:
    if not output_dir.is_absolute():
        raise ConfigError(f"Output folder must be an absolute path: {output_dir}")
    if not output_dir.exists():
        raise ConfigError(f"Configured output folder does not exist: {output_dir}")
    if not output_dir.is_dir():
        raise ConfigError(f"Configured output path is not a folder: {output_dir}")


def _validate_range(label: str, value: int, minimum: int, maximum: int) -> None:
    if not minimum <= value <= maximum:
        raise ConfigError(f"{label} must be between {minimum} and {maximum}.")
