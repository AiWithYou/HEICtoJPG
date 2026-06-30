from pathlib import Path

import pytest
from PIL import Image

from heictojpg.config import (
    FORMAT_PNG,
    FORMAT_WEBP,
    OUTPUT_MODE_CONVERTED_SUBFOLDER,
    OVERWRITE_OVERWRITE,
    OVERWRITE_RENAME,
    OVERWRITE_SKIP,
    AppConfig,
    ConfigError,
    validate_config,
)
from heictojpg.converter import (
    ConversionError,
    convert_file,
    convert_files,
    convert_folder,
    is_webp_supported,
    list_source_images,
)


def test_convert_heic_to_default_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "sample.heic"
    _write_sample_heic(source)

    result = convert_file(source)

    assert result.target == tmp_path / "sample.jpg"
    assert result.target.exists()
    assert list(tmp_path.glob(".heictojpg-*")) == []
    with Image.open(result.target) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_convert_heic_to_png(tmp_path: Path) -> None:
    source = tmp_path / "sample.heic"
    _write_sample_heic(source)

    result = convert_file(source, settings=AppConfig(output_format=FORMAT_PNG))

    assert result.target == tmp_path / "sample.png"
    with Image.open(result.target) as image:
        assert image.format == "PNG"


def test_convert_png_source_to_default_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    _write_sample_png(source)

    result = convert_file(source)

    assert result.target == tmp_path / "sample.jpg"
    with Image.open(result.target) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_convert_heic_to_webp(tmp_path: Path) -> None:
    if not is_webp_supported():
        pytest.skip("WebP output is unavailable in this Pillow build.")

    source = tmp_path / "sample.heic"
    _write_sample_heic(source)

    result = convert_file(source, settings=AppConfig(output_format=FORMAT_WEBP))

    assert result.target == tmp_path / "sample.webp"
    with Image.open(result.target) as image:
        assert image.format == "WEBP"


def test_rename_policy_uses_numbered_target(tmp_path: Path) -> None:
    source = tmp_path / "sample.heic"
    _write_sample_heic(source)
    (tmp_path / "sample.jpg").write_bytes(b"already here")

    result = convert_file(source, settings=AppConfig(overwrite_policy=OVERWRITE_RENAME))

    assert result.target == tmp_path / "sample_1.jpg"
    assert result.target.exists()


def test_skip_policy_keeps_existing_target(tmp_path: Path) -> None:
    source = tmp_path / "sample.heic"
    target = tmp_path / "sample.jpg"
    _write_sample_heic(source)
    target.write_bytes(b"already here")

    result = convert_file(source, settings=AppConfig(overwrite_policy=OVERWRITE_SKIP))

    assert result.status == "skipped"
    assert result.target == target
    assert target.read_bytes() == b"already here"


def test_overwrite_policy_replaces_existing_target(tmp_path: Path) -> None:
    source = tmp_path / "sample.heic"
    target = tmp_path / "sample.jpg"
    _write_sample_heic(source)
    target.write_bytes(b"already here")

    result = convert_file(source, settings=AppConfig(overwrite_policy=OVERWRITE_OVERWRITE))

    assert result.target == target
    with Image.open(target) as image:
        assert image.format == "JPEG"


def test_converted_subfolder_output_mode(tmp_path: Path) -> None:
    source = tmp_path / "sample.heic"
    _write_sample_heic(source)

    result = convert_file(source, settings=AppConfig(output_mode=OUTPUT_MODE_CONVERTED_SUBFOLDER))

    assert result.target == tmp_path / "converted" / "sample.jpg"
    assert result.target.exists()


def test_convert_folder_non_recursive(tmp_path: Path) -> None:
    source = tmp_path / "sample.heic"
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_sample_heic(source)
    _write_sample_heic(nested / "nested.heic")

    results = convert_folder(tmp_path)

    assert [result.target for result in results] == [tmp_path / "sample.jpg"]


def test_convert_folder_includes_supported_image_sources(tmp_path: Path) -> None:
    _write_sample_png(tmp_path / "sample.png")
    _write_sample_jpeg(tmp_path / "photo.jpeg")
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    sources = list_source_images(tmp_path)
    results = convert_folder(tmp_path, settings=AppConfig(output_format=FORMAT_PNG))

    assert sources == [tmp_path / "photo.jpeg", tmp_path / "sample.png"]
    assert [result.target for result in results] == [
        tmp_path / "photo.png",
        tmp_path / "sample_1.png",
    ]


def test_convert_files_keeps_processing_after_failed_file(tmp_path: Path) -> None:
    good = tmp_path / "good.png"
    bad = tmp_path / "bad.png"
    _write_sample_png(good)
    bad.write_text("not an image", encoding="utf-8")

    results = convert_files([bad, good])

    assert [result.status for result in results] == ["failed", "converted"]
    assert results[0].source == bad
    assert results[0].error is not None
    assert "readable image" in results[0].error
    assert results[1].target == tmp_path / "good.jpg"
    assert results[1].target.exists()


def test_keeps_icc_profile_by_default(tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    icc_profile = b"test-icc-profile"
    _write_sample_png(source, icc_profile=icc_profile)

    result = convert_file(source, settings=AppConfig(output_format=FORMAT_PNG))

    with Image.open(result.target) as image:
        assert image.info.get("icc_profile") == icc_profile


def test_can_remove_icc_profile(tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    _write_sample_png(source, icc_profile=b"test-icc-profile")

    result = convert_file(
        source,
        settings=AppConfig(output_format=FORMAT_PNG, keep_icc_profile=False),
    )

    with Image.open(result.target) as image:
        assert "icc_profile" not in image.info


def test_rejects_unsupported_source_extension(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("not an image", encoding="utf-8")

    with pytest.raises(ConversionError, match="Unsupported file extension '.txt'"):
        convert_file(source)


def test_png_compress_level_range_check() -> None:
    with pytest.raises(ConfigError, match="PNG compress_level"):
        validate_config(AppConfig(png_compress_level=10))


def test_jpeg_quality_range_check() -> None:
    with pytest.raises(ConfigError, match="JPEG quality"):
        validate_config(AppConfig(jpeg_quality=0))


def test_webp_quality_range_check() -> None:
    with pytest.raises(ConfigError, match="WebP quality"):
        validate_config(AppConfig(webp_quality=101))


def _write_sample_heic(path: Path) -> None:
    image = Image.new("RGB", (8, 6), (80, 120, 200))
    try:
        image.save(path, format="HEIF")
    except Exception as exc:
        pytest.skip(f"HEIF encoding is unavailable in this environment: {exc}")


def _write_sample_jpeg(path: Path) -> None:
    Image.new("RGB", (8, 6), (80, 120, 200)).save(path, format="JPEG")


def _write_sample_png(path: Path, *, icc_profile: bytes | None = None) -> None:
    save_kwargs = {}
    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile
    Image.new("RGBA", (8, 6), (80, 120, 200, 160)).save(
        path,
        format="PNG",
        **save_kwargs,
    )
