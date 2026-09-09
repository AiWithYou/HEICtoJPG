"""Regression tests for metadata privacy and non-destructive output publishing."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from PIL import Image

import heictojpg.converter as converter
from heictojpg.config import (
    FORMAT_JPEG,
    FORMAT_PNG,
    FORMAT_WEBP,
    OVERWRITE_ERROR,
    OVERWRITE_OVERWRITE,
    OVERWRITE_RENAME,
    OVERWRITE_SKIP,
    AppConfig,
)


FORMATS = [FORMAT_JPEG, FORMAT_PNG, FORMAT_WEBP]
SENTINEL = b"An existing file must not be overwritten accidentally."


def settings_for(output_format: str, **changes: object) -> AppConfig:
    if output_format == FORMAT_WEBP and not converter.is_webp_supported():
        pytest.skip("WebP output is unavailable in this Pillow build.")
    return AppConfig(output_format=output_format).with_changes(**changes)


def write_source(path: Path, *, mode: str = "RGB", exif: Image.Exif | None = None) -> None:
    with Image.new(mode, (8, 6)) as image:
        kwargs = {"exif": exif} if exif is not None else {}
        image.save(path, format="PNG", **kwargs)


@pytest.mark.parametrize("output_format", FORMATS)
@pytest.mark.parametrize("mode", ["RGB", "RGBA"])
def test_strip_exif_does_not_inherit_source_metadata(
    tmp_path: Path, output_format: str, mode: str
) -> None:
    source = tmp_path / "private.png"
    exif = Image.Exif()
    exif[315] = "Private author"
    exif[274] = 6
    write_source(source, mode=mode, exif=exif)
    original = source.read_bytes()

    result = converter.convert_file(source, settings=settings_for(output_format, keep_exif=False))

    with Image.open(result.target) as image:
        assert image.size == (6, 8)
        assert not image.getexif()
    assert source.read_bytes() == original


@pytest.mark.parametrize("output_format", FORMATS)
def test_gps_only_exif_is_not_reintroduced_when_removal_empties_it(
    tmp_path: Path, output_format: str
) -> None:
    source = tmp_path / "gps.png"
    exif = Image.Exif()
    exif[34853] = {1: "N", 2: (35.0, 0.0, 0.0)}
    write_source(source, exif=exif)

    result = converter.convert_file(source, settings=settings_for(output_format, remove_gps=True))

    with Image.open(result.target) as image:
        assert 34853 not in image.getexif()
    with Image.open(source) as image:
        assert 34853 in image.getexif()


@pytest.mark.parametrize("output_format", FORMATS)
@pytest.mark.parametrize("keep_icc", [False, True])
def test_metadata_controls_preserve_only_requested_metadata(
    tmp_path: Path, output_format: str, keep_icc: bool
) -> None:
    source = tmp_path / "metadata.png"
    exif = Image.Exif()
    exif[315] = "Keep this author"
    exif[34853] = {1: "N", 2: (35.0, 0.0, 0.0)}
    profile = b"test-icc-profile"
    with Image.new("RGB", (8, 6)) as image:
        image.save(source, exif=exif, icc_profile=profile)

    result = converter.convert_file(
        source,
        settings=settings_for(output_format, remove_gps=True, keep_icc_profile=keep_icc),
    )

    with Image.open(result.target) as image:
        assert image.getexif()[315] == "Keep this author"
        assert 34853 not in image.getexif()
        assert image.info.get("icc_profile") == (profile if keep_icc else None)


@pytest.mark.parametrize("mode,transparent,opaque", [("RGB", (0, 0, 0), (255, 0, 0)), ("L", 0, 255)])
def test_webp_preserves_png_color_key_transparency(
    tmp_path: Path, mode: str, transparent: object, opaque: object
) -> None:
    source = tmp_path / "transparent.png"
    with Image.new(mode, (2, 1)) as image:
        image.putdata([transparent, opaque])
        image.save(source, transparency=transparent)

    result = converter.convert_file(
        source, settings=settings_for(FORMAT_WEBP, webp_lossless=True)
    )

    with Image.open(result.target) as image:
        rgba = image.convert("RGBA")
        assert rgba.getpixel((0, 0))[3] == 0
        assert rgba.getpixel((1, 0))[3] == 255


@pytest.mark.parametrize("policy", [OVERWRITE_RENAME, OVERWRITE_SKIP, OVERWRITE_ERROR])
def test_late_collision_respects_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: str
) -> None:
    source = tmp_path / "photo.png"
    target = tmp_path / "photo.jpg"
    write_source(source)
    original_save = Image.Image.save
    calls = []

    def save_and_collide(image, fp, **kwargs):
        calls.append(fp)
        original_save(image, fp, **kwargs)
        target.write_bytes(SENTINEL)

    monkeypatch.setattr(Image.Image, "save", save_and_collide)
    if policy == OVERWRITE_ERROR:
        with pytest.raises(converter.ConversionError, match="already exists"):
            converter.convert_file(source, overwrite_policy=policy)
    else:
        result = converter.convert_file(source, overwrite_policy=policy)
        assert result.status == ("skipped" if policy == OVERWRITE_SKIP else "converted")
        assert result.target == (target if policy == OVERWRITE_SKIP else tmp_path / "photo_1.jpg")
    assert target.read_bytes() == SENTINEL
    assert len(calls) == 1  # A collision must not cause a second JPEG encode.
    assert list(tmp_path.glob(".heictojpg-*")) == []


def test_numbered_collision_keeps_flat_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "photo.png"
    write_source(source)
    (tmp_path / "photo.jpg").write_bytes(SENTINEL)
    original_save = Image.Image.save

    def save_and_collide(image, fp, **kwargs):
        original_save(image, fp, **kwargs)
        (tmp_path / "photo_1.jpg").write_bytes(SENTINEL)

    monkeypatch.setattr(Image.Image, "save", save_and_collide)
    result = converter.convert_file(source)

    assert result.target == tmp_path / "photo_2.jpg"
    assert (tmp_path / "photo.jpg").read_bytes() == SENTINEL
    assert (tmp_path / "photo_1.jpg").read_bytes() == SENTINEL


@pytest.mark.parametrize("policy", [OVERWRITE_RENAME, OVERWRITE_SKIP, OVERWRITE_ERROR])
def test_concurrent_converters_do_not_clobber_each_other(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: str
) -> None:
    source = tmp_path / "parallel.png"
    write_source(source)
    count = 4
    barrier = Barrier(count)
    original_save = Image.Image.save

    def synchronized_save(image, fp, **kwargs):
        original_save(image, fp, **kwargs)
        barrier.wait(timeout=20)

    monkeypatch.setattr(Image.Image, "save", synchronized_save)

    def convert_once(_index):
        return converter.convert_files([source], overwrite_policy=policy)[0]

    with ThreadPoolExecutor(max_workers=count) as executor:
        results = list(executor.map(convert_once, range(count)))

    converted = [result for result in results if result.status == "converted"]
    assert len(converted) == (count if policy == OVERWRITE_RENAME else 1)
    assert len({result.target for result in converted}) == len(converted)
    if policy != OVERWRITE_RENAME:
        expected_status = "skipped" if policy == OVERWRITE_SKIP else "failed"
        assert sum(result.status == expected_status for result in results) == count - 1
    for result in converted:
        with Image.open(result.target) as image:
            image.verify()
    assert list(tmp_path.glob(".heictojpg-*")) == []


@pytest.mark.parametrize("policy", [OVERWRITE_RENAME, OVERWRITE_SKIP, OVERWRITE_ERROR])
def test_dangling_symlink_counts_as_existing_target(tmp_path: Path, policy: str) -> None:
    source = tmp_path / "photo.png"
    target = tmp_path / "photo.jpg"
    write_source(source)
    try:
        target.symlink_to(tmp_path / "missing.jpg")
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks is not permitted in this environment.")

    if policy == OVERWRITE_ERROR:
        with pytest.raises(converter.ConversionError, match="already exists"):
            converter.convert_file(source, overwrite_policy=policy)
    else:
        result = converter.convert_file(source, overwrite_policy=policy)
        assert result.status == ("skipped" if policy == OVERWRITE_SKIP else "converted")
    assert target.is_symlink()
    assert not (tmp_path / "missing.jpg").exists()


def test_long_valid_source_name_does_not_overflow_temporary_name(tmp_path: Path) -> None:
    source = tmp_path / ("s" * 240 + ".png")
    try:
        write_source(source)
    except OSError:
        pytest.skip("The filesystem cannot create this long source path.")

    result = converter.convert_file(source)

    assert result.target == source.with_suffix(".jpg")
    with Image.open(result.target) as image:
        image.verify()
    assert list(tmp_path.glob(".heictojpg-*")) == []


@pytest.mark.parametrize("failure_point", ["encode", "fsync", "attributes"])
def test_failure_before_publish_preserves_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_point: str
) -> None:
    source = tmp_path / "photo.png"
    target = tmp_path / "photo.jpg"
    write_source(source)
    target.write_bytes(SENTINEL)

    def fail(*args, **kwargs):
        raise OSError("injected failure")

    if failure_point == "encode":
        monkeypatch.setattr(Image.Image, "save", fail)
    elif failure_point == "fsync":
        monkeypatch.setattr(os, "fsync", fail)
    else:
        monkeypatch.setattr(converter, "_clear_hidden_attribute", fail)

    with pytest.raises(converter.ConversionError, match="injected failure"):
        converter.convert_file(source, overwrite_policy=OVERWRITE_OVERWRITE)

    assert target.read_bytes() == SENTINEL
    assert list(tmp_path.glob(".heictojpg-*")) == []
