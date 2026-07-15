from pathlib import Path

import pytest
from PIL import Image

import heictojpg.converter as converter_module
from heictojpg.config import (
    FORMAT_PNG,
    FORMAT_WEBP,
    OUTPUT_MODE_CONVERTED_SUBFOLDER,
    OUTPUT_MODE_FIXED_FOLDER,
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


def test_resize_applies_orientation_and_updates_exif_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "oriented.jpeg"
    exif = Image.Exif()
    exif[274] = 6
    exif[256] = 40
    exif[257] = 20
    exif[34665] = {40962: 40, 40963: 20}
    Image.new("RGB", (40, 20), (80, 120, 200)).save(source, format="JPEG", exif=exif)

    result = convert_file(source, settings=AppConfig(max_dimension=30))

    with Image.open(result.target) as image:
        output_exif = image.getexif()
        output_exif_ifd = output_exif.get_ifd(34665)
        assert image.size == (15, 30)
        assert 274 not in output_exif
        assert output_exif[256] == 15
        assert output_exif[257] == 30
        assert output_exif_ifd[40962] == 15
        assert output_exif_ifd[40963] == 30


def test_resize_uses_lanczos_resampling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "sample.png"
    Image.new("RGB", (13, 7), (80, 120, 200)).save(source, format="PNG")
    resize_filters: list[object] = []
    original_resize = Image.Image.resize

    def tracked_resize(
        image: Image.Image,
        size: tuple[int, int],
        resample: int | None = None,
        box: tuple[float, float, float, float] | None = None,
        reducing_gap: float | None = None,
    ) -> Image.Image:
        resize_filters.append(resample)
        return original_resize(image, size, resample, box, reducing_gap)

    monkeypatch.setattr(Image.Image, "resize", tracked_resize)

    result = convert_file(
        source,
        settings=AppConfig(output_format=FORMAT_PNG, max_dimension=5),
    )

    with Image.open(result.target) as image:
        assert image.size == (5, 3)
    assert Image.Resampling.LANCZOS in resize_filters


def test_resize_does_not_upscale_smaller_images(tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    Image.new("RGB", (20, 10), (80, 120, 200)).save(source, format="PNG")

    result = convert_file(
        source,
        settings=AppConfig(output_format=FORMAT_PNG, max_dimension=100),
    )

    with Image.open(result.target) as image:
        assert image.size == (20, 10)


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


def test_convert_folder_recursive_excludes_converted_output_tree(tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    converted_dir = tmp_path / "converted"
    converted_dir.mkdir()
    previous_output = converted_dir / "previous.png"
    _write_sample_png(source)
    _write_sample_png(previous_output)

    results = convert_folder(
        tmp_path,
        recursive=True,
        settings=AppConfig(output_mode=OUTPUT_MODE_CONVERTED_SUBFOLDER),
    )

    assert [result.source for result in results] == [source]
    assert results[0].target == converted_dir / "sample.jpg"
    assert not (converted_dir / "converted").exists()


def test_convert_folder_recursive_excludes_fixed_output_tree(tmp_path: Path) -> None:
    source = tmp_path / "sample.png"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    previous_output = output_dir / "previous.png"
    _write_sample_png(source)
    _write_sample_png(previous_output)

    results = convert_folder(
        tmp_path,
        recursive=True,
        settings=AppConfig(
            output_mode=OUTPUT_MODE_FIXED_FOLDER,
            output_dir=output_dir,
        ),
    )

    assert [result.source for result in results] == [source]
    assert results[0].target == output_dir / "sample.jpg"
    assert not (output_dir / "previous.jpg").exists()


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


def test_convert_files_keeps_processing_after_decompression_bomb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = tmp_path / "oversized.png"
    good = tmp_path / "good.png"
    Image.new("RGB", (3, 3), (80, 120, 200)).save(oversized, format="PNG")
    Image.new("RGB", (1, 1), (80, 120, 200)).save(good, format="PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 4)

    results = convert_files([oversized, good])

    assert [result.status for result in results] == ["failed", "converted"]
    assert results[0].source == oversized
    assert results[0].error is not None
    assert results[1].target == tmp_path / "good.jpg"
    assert results[1].target.exists()


def test_encode_error_reports_output_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "sample.png"
    _write_sample_png(source)

    monkeypatch.setattr(
        "heictojpg.converter._save_image_atomically",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("encoder rejected image")),
    )

    with pytest.raises(ConversionError, match="Failed to encode or save image"):
        convert_file(source)


def test_convert_files_keeps_processing_after_unexpected_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad = Path("bad.png")
    good = Path("good.png")
    calls: list[Path] = []

    def fake_convert(source: Path, _settings: AppConfig) -> converter_module.ConversionResult:
        calls.append(source)
        if source == bad:
            raise RuntimeError("unexpected decoder failure")
        return converter_module.ConversionResult(source=source, target=Path("good.jpg"))

    monkeypatch.setattr(converter_module, "_convert_file_with_settings", fake_convert)

    results = convert_files([bad, good])

    assert calls == [bad, good]
    assert [result.status for result in results] == ["failed", "converted"]
    assert results[0].error == "unexpected decoder failure"


@pytest.mark.parametrize("exception_type", [MemoryError, SystemExit])
def test_convert_files_does_not_swallow_fatal_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[BaseException],
) -> None:
    def fail_conversion(_source: Path, _settings: AppConfig) -> converter_module.ConversionResult:
        raise exception_type("stop")

    monkeypatch.setattr(converter_module, "_convert_file_with_settings", fail_conversion)

    with pytest.raises(exception_type):
        convert_files([Path("sample.png")])


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
