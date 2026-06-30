from pathlib import Path

from PIL import Image

from heictojpg.app_gui import ConverterWindow, collect_image_files, parse_drop_data
from heictojpg.config import FORMAT_JPEG, OUTPUT_MODE_SAME_FOLDER, OVERWRITE_RENAME, AppConfig


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


def test_converter_window_config_includes_quality_controls() -> None:
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
    window.keep_exif = _Value(False)
    window.keep_icc_profile = _Value(False)
    window.remove_gps = _Value(True)
    window.open_output_folder = _Value(True)

    config = ConverterWindow._config_from_ui(window)

    assert config.jpeg_quality == 82
    assert config.jpeg_optimize is False
    assert config.jpeg_progressive is True
    assert config.webp_quality == 74
    assert config.webp_lossless is True
    assert config.png_compress_level == 3
    assert config.keep_icc_profile is False


def _write_sample_jpeg(path: Path) -> None:
    Image.new("RGB", (8, 6), (80, 120, 200)).save(path, format="JPEG")


def _write_sample_png(path: Path) -> None:
    Image.new("RGBA", (8, 6), (80, 120, 200, 160)).save(path, format="PNG")


class _Value:
    def __init__(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value
