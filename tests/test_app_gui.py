from pathlib import Path

import pytest
from PIL import Image

import heictojpg.app_gui as app_gui_module
from heictojpg.app_gui import (
    ConverterWindow,
    collect_image_files,
    is_output_source,
    parse_drop_data,
)
from heictojpg.config import (
    FORMAT_JPEG,
    LANGUAGE_EN,
    OUTPUT_MODE_CONVERTED_SUBFOLDER,
    OUTPUT_MODE_FIXED_FOLDER,
    OUTPUT_MODE_SAME_FOLDER,
    OVERWRITE_RENAME,
    AppConfig,
    ConfigError,
)
from heictojpg.converter import ConversionError, ConversionResult
from heictojpg.gui import SettingsWindow


def test_parse_drop_data_handles_paths_with_spaces() -> None:
    paths = parse_drop_data("{C:/Photos/A One.png} C:/Photos/B.jpg")

    assert paths == [Path("C:/Photos/A One.png"), Path("C:/Photos/B.jpg")]


def test_collect_image_files_includes_folder_images(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_image = nested / "nested.jpg"
    _write_sample_png(image_path)
    _write_sample_jpeg(nested_image)
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    files, errors = collect_image_files([tmp_path], recursive=True)

    assert files == [nested_image, image_path]
    assert errors == []


def test_collect_image_files_reports_unsupported_paths(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("not an image", encoding="utf-8")

    files, errors = collect_image_files([notes], recursive=False)

    assert files == []
    assert errors == [f"{notes}: unsupported source type"]


def test_collect_image_files_reports_scan_error_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreadable = tmp_path / "unreadable"
    unreadable.mkdir()
    valid = tmp_path / "valid.png"
    _write_sample_png(valid)
    original_list_source_images = app_gui_module.list_source_images

    def list_source_images(path: Path, **kwargs: object) -> list[Path]:
        if path == unreadable:
            raise ConversionError("simulated folder read failure")
        return original_list_source_images(path, **kwargs)

    monkeypatch.setattr(app_gui_module, "list_source_images", list_source_images)

    files, errors = collect_image_files([unreadable, valid], recursive=False)

    assert files == [valid]
    assert errors == [f"{unreadable}: simulated folder read failure"]


def test_output_source_filter_uses_final_settings_and_folder_origin(tmp_path: Path) -> None:
    source_root = tmp_path / "photos"
    converted = source_root / "converted"
    fixed_output = source_root / "export"
    converted.mkdir(parents=True)
    fixed_output.mkdir()
    converted_file = converted / "previous.jpg"
    fixed_file = fixed_output / "previous.jpg"
    explicit_file = converted / "explicit.jpg"

    converted_config = AppConfig(output_mode=OUTPUT_MODE_CONVERTED_SUBFOLDER)
    fixed_config = AppConfig(
        output_mode=OUTPUT_MODE_FIXED_FOLDER,
        output_dir=fixed_output,
    )
    ancestor_config = AppConfig(
        output_mode=OUTPUT_MODE_FIXED_FOLDER,
        output_dir=tmp_path,
    )

    assert is_output_source(converted_file, source_root, converted_config) is True
    assert is_output_source(fixed_file, source_root, fixed_config) is True
    assert is_output_source(explicit_file, None, converted_config) is False
    assert is_output_source(converted_file, source_root, ancestor_config) is False


def test_converter_window_config_includes_quality_controls() -> None:
    window = _converter_window()

    config = ConverterWindow._config_from_ui(window)

    assert config.jpeg_quality == 82
    assert config.jpeg_optimize is False
    assert config.jpeg_progressive is True
    assert config.webp_quality == 74
    assert config.webp_lossless is True
    assert config.png_compress_level == 3
    assert config.max_dimension == 1600
    assert config.keep_icc_profile is False

    window.resize_enabled = _Value(False)
    assert ConverterWindow._config_from_ui(window).max_dimension is None


@pytest.mark.parametrize(
    ("field", "value"),
    [("jpeg_quality", ""), ("max_dimension", "not-an-integer")],
)
def test_converter_window_config_rejects_invalid_numeric_input(
    field: str,
    value: str,
) -> None:
    window = _converter_window()
    setattr(window, field, _Value(value))

    with pytest.raises(ConfigError, match="must be an integer"):
        ConverterWindow._config_from_ui(window)


def test_settings_window_config_includes_max_dimension() -> None:
    window = object.__new__(SettingsWindow)
    window.output_mode = _Value(OUTPUT_MODE_SAME_FOLDER)
    window.fixed_output_dir = None
    window.output_format = _Value(FORMAT_JPEG)
    window.jpeg_quality = _Value(82)
    window.jpeg_optimize = _Value(False)
    window.jpeg_progressive = _Value(True)
    window.webp_quality = _Value(74)
    window.webp_lossless = _Value(True)
    window.png_compress_level = _Value(3)
    window.resize_enabled = _Value(True)
    window.max_dimension = _Value("2048")
    window.overwrite_policy = OVERWRITE_RENAME
    window.keep_exif = _Value(False)
    window.keep_icc_profile = _Value(False)
    window.remove_gps = _Value(True)
    window.open_output_folder = _Value(True)
    window.language = LANGUAGE_EN

    config = SettingsWindow._config_from_ui(window)

    assert config.max_dimension == 2048


def test_converter_window_reports_output_folder_open_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = object.__new__(ConverterWindow)
    window.language = LANGUAGE_EN
    window.root = object()
    warnings: list[tuple[str, str, object]] = []

    def fail_startfile(_folder: str) -> None:
        raise OSError("simulated shell failure")

    def capture_warning(title: str, message: str, *, parent: object) -> None:
        warnings.append((title, message, parent))

    monkeypatch.setattr(app_gui_module.os, "startfile", fail_startfile)
    monkeypatch.setattr(app_gui_module.messagebox, "showwarning", capture_warning)
    result = ConversionResult(source=tmp_path / "source.png", target=tmp_path / "output.jpg")

    ConverterWindow._open_result_folders(window, [result])

    assert len(warnings) == 1
    assert warnings[0][0] == "Could not open output folder"
    assert "simulated shell failure" in warnings[0][1]
    assert warnings[0][2] is window.root


def _write_sample_jpeg(path: Path) -> None:
    Image.new("RGB", (8, 6), (80, 120, 200)).save(path, format="JPEG")


def _write_sample_png(path: Path) -> None:
    Image.new("RGBA", (8, 6), (80, 120, 200, 160)).save(path, format="PNG")


def _converter_window() -> ConverterWindow:
    window = object.__new__(ConverterWindow)
    window.config = AppConfig()
    window.output_mode = _Value(OUTPUT_MODE_SAME_FOLDER)
    window.fixed_output_dir = None
    window.output_format = _Value(FORMAT_JPEG)
    window.overwrite_policy = OVERWRITE_RENAME
    window.jpeg_quality = _Value(82)
    window.jpeg_optimize = _Value(False)
    window.jpeg_progressive = _Value(True)
    window.webp_quality = _Value(74)
    window.webp_lossless = _Value(True)
    window.png_compress_level = _Value(3)
    window.resize_enabled = _Value(True)
    window.max_dimension = _Value("1600")
    window.keep_exif = _Value(False)
    window.keep_icc_profile = _Value(False)
    window.remove_gps = _Value(True)
    window.open_output_folder = _Value(True)
    return window


class _Value:
    def __init__(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value
