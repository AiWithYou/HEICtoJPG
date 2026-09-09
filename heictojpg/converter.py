from __future__ import annotations

import ctypes
import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError, features
from pillow_heif import register_heif_opener

from heictojpg.config import (
    FORMAT_EXTENSIONS,
    FORMAT_JPEG,
    FORMAT_PNG,
    FORMAT_WEBP,
    OUTPUT_MODE_CONVERTED_SUBFOLDER,
    OUTPUT_MODE_FIXED_FOLDER,
    OUTPUT_MODE_SAME_FOLDER,
    OVERWRITE_ERROR,
    OVERWRITE_OVERWRITE,
    OVERWRITE_RENAME,
    OVERWRITE_SKIP,
    AppConfig,
    validate_config,
)

SUPPORTED_SOURCE_SUFFIXES = {
    ".apng",
    ".avif",
    ".bmp",
    ".dib",
    ".gif",
    ".heic",
    ".heif",
    ".hif",
    ".jfif",
    ".jpe",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
PIL_FORMATS = {
    FORMAT_JPEG: "JPEG",
    FORMAT_PNG: "PNG",
    FORMAT_WEBP: "WEBP",
}
GPS_INFO_TAG = 34853
EXIF_IFD_TAG = int(ExifTags.IFD.Exif)
IMAGE_WIDTH_TAG = int(ExifTags.Base.ImageWidth)
IMAGE_HEIGHT_TAG = int(ExifTags.Base.ImageLength)
EXIF_IMAGE_WIDTH_TAG = int(ExifTags.Base.ExifImageWidth)
EXIF_IMAGE_HEIGHT_TAG = int(ExifTags.Base.ExifImageHeight)
WINDOWS_FILE_ATTRIBUTE_HIDDEN = 0x02
WINDOWS_INVALID_FILE_ATTRIBUTES = -1


class ConversionError(RuntimeError):
    """Raised when an image file cannot be converted."""


@dataclass(frozen=True)
class ConversionResult:
    source: Path
    target: Path
    status: str = "converted"
    error: str | None = None


register_heif_opener()


def is_webp_supported() -> bool:
    return bool(features.check("webp"))


def convert_file(
    source: Path | str,
    output_dir: Path | str | None = None,
    *,
    settings: AppConfig | None = None,
    quality: int | None = None,
    overwrite: bool = False,
    output_format: str | None = None,
    overwrite_policy: str | None = None,
) -> ConversionResult:
    active_settings = _settings_with_legacy_overrides(
        settings or AppConfig(),
        output_dir=output_dir,
        quality=quality,
        overwrite=overwrite,
        output_format=output_format,
        overwrite_policy=overwrite_policy,
    )
    return _convert_file_with_settings(Path(source), active_settings)


def convert_files(
    sources: Iterable[Path | str],
    output_dir: Path | str | None = None,
    *,
    settings: AppConfig | None = None,
    quality: int | None = None,
    overwrite: bool = False,
    output_format: str | None = None,
    overwrite_policy: str | None = None,
) -> list[ConversionResult]:
    source_list = list(sources)
    if not source_list:
        raise ConversionError("At least one source file is required.")

    active_settings = _settings_with_legacy_overrides(
        settings or AppConfig(),
        output_dir=output_dir,
        quality=quality,
        overwrite=overwrite,
        output_format=output_format,
        overwrite_policy=overwrite_policy,
    )
    results: list[ConversionResult] = []
    for source in source_list:
        source_path = Path(source)
        try:
            results.append(_convert_file_with_settings(source_path, active_settings))
        except (ConversionError, OSError) as exc:
            results.append(_failed_result(source_path, active_settings, str(exc)))
        except (MemoryError, RecursionError):
            raise
        except Exception as exc:  # noqa: BLE001 - isolate third-party decoder failures per file.
            error = str(exc) or type(exc).__name__
            results.append(_failed_result(source_path, active_settings, error))
    return results


def convert_folder(
    folder: Path | str,
    *,
    recursive: bool = False,
    settings: AppConfig | None = None,
) -> list[ConversionResult]:
    active_settings = validate_config(settings or AppConfig())
    folder_path = Path(folder)
    excluded_directory_names: tuple[str, ...] = ()
    excluded_directories: tuple[Path, ...] = ()
    if active_settings.output_mode == OUTPUT_MODE_CONVERTED_SUBFOLDER:
        excluded_directory_names = ("converted",)
    elif (
        active_settings.output_mode == OUTPUT_MODE_FIXED_FOLDER
        and active_settings.output_dir is not None
        and _is_strictly_within(active_settings.output_dir, folder_path)
    ):
        excluded_directories = (active_settings.output_dir,)

    sources = list_source_images(
        folder_path,
        recursive=recursive,
        excluded_directory_names=excluded_directory_names,
        excluded_directories=excluded_directories,
    )
    if not sources:
        return []
    return convert_files(sources, settings=active_settings)


def list_source_images(
    folder: Path | str,
    *,
    recursive: bool = False,
    excluded_directory_names: Iterable[str] = (),
    excluded_directories: Iterable[Path | str] = (),
) -> list[Path]:
    folder_path = Path(folder)
    if not folder_path.exists():
        raise ConversionError(f"Source folder does not exist: {folder_path}")
    if not folder_path.is_dir():
        raise ConversionError(f"Source path is not a folder: {folder_path}")

    excluded_names = {name.casefold() for name in excluded_directory_names}
    excluded_roots = tuple(Path(path).resolve() for path in excluded_directories)
    iterator = (
        _walk_files(folder_path, excluded_names=excluded_names, excluded_roots=excluded_roots)
        if recursive
        else folder_path.glob("*")
    )
    return sorted(
        path
        for path in iterator
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES
        and not _is_in_excluded_directory(
            path,
            folder_path=folder_path,
            excluded_names=excluded_names,
            excluded_roots=excluded_roots,
        )
    )


def _settings_with_legacy_overrides(
    settings: AppConfig,
    *,
    output_dir: Path | str | None,
    quality: int | None,
    overwrite: bool,
    output_format: str | None,
    overwrite_policy: str | None,
) -> AppConfig:
    changes: dict[str, object] = {}
    if output_dir is not None:
        changes["output_mode"] = OUTPUT_MODE_FIXED_FOLDER
        changes["output_dir"] = Path(output_dir)
    if output_format is not None:
        changes["output_format"] = output_format
    effective_format = str(changes.get("output_format", settings.output_format))
    if quality is not None:
        if effective_format == FORMAT_WEBP:
            changes["webp_quality"] = quality
        else:
            changes["jpeg_quality"] = quality
    if overwrite_policy is not None:
        changes["overwrite_policy"] = overwrite_policy
    if overwrite:
        changes["overwrite_policy"] = OVERWRITE_OVERWRITE

    return validate_config(settings.with_changes(**changes) if changes else settings)


def _convert_file_with_settings(source_path: Path, settings: AppConfig) -> ConversionResult:
    settings = validate_config(settings)
    _validate_source(source_path)
    if settings.output_format == FORMAT_WEBP and not is_webp_supported():
        raise ConversionError("WebP output is not available in this Pillow build.")

    target_dir = _target_dir_for_source(source_path, settings)
    extension = FORMAT_EXTENSIONS[settings.output_format]
    target_candidate = target_dir / f"{source_path.stem}{extension}"
    target_path = _target_path_for_policy(target_candidate, settings.overwrite_policy)
    if target_path is None:
        return ConversionResult(
            source=source_path,
            target=target_dir / f"{source_path.stem}{extension}",
            status="skipped",
        )

    try:
        with Image.open(source_path) as image:
            image.load()
            normalized = ImageOps.exif_transpose(image)
            resized = _resize_image(normalized, settings.max_dimension)
            output_image = _image_for_format(resized, settings.output_format)
            save_kwargs = _save_kwargs(output_image, settings)
            exif = _exif_bytes(
                resized,
                keep_exif=settings.keep_exif,
                remove_gps=settings.remove_gps,
                output_size=output_image.size,
            )
            # PNG falls back to image.info["exif"] when the keyword is omitted.
            # An explicit empty value also prevents GPS-only EXIF from returning
            # after the last tag has been removed.
            save_kwargs["exif"] = exif or b""
            icc_profile = _icc_profile_bytes(
                image,
                normalized,
                keep_icc_profile=settings.keep_icc_profile,
            )
            # Override inherited ICC data without copying the entire pixel buffer.
            save_kwargs["icc_profile"] = icc_profile or b""
    except UnidentifiedImageError as exc:
        raise ConversionError(f"Source file is not a readable image: {source_path}") from exc
    except (Image.DecompressionBombError, SyntaxError, ValueError) as exc:
        raise ConversionError(
            f"Source image could not be processed '{source_path}': {exc}"
        ) from exc
    except OSError as exc:
        raise ConversionError(f"Failed to read or transform image '{source_path}': {exc}") from exc

    try:
        published_path = _save_image_atomically(
            output_image,
            target_path,
            save_kwargs,
            overwrite_policy=settings.overwrite_policy,
            rename_base=target_candidate,
        )
    except (OSError, SyntaxError, ValueError) as exc:
        raise ConversionError(
            f"Failed to encode or save image '{source_path}' to '{target_path}': {exc}"
        ) from exc

    if published_path is None:
        return ConversionResult(source=source_path, target=target_candidate, status="skipped")
    return ConversionResult(source=source_path, target=published_path)


def _failed_result(source_path: Path, settings: AppConfig, error: str) -> ConversionResult:
    return ConversionResult(
        source=source_path,
        target=_target_candidate_for_failure(source_path, settings),
        status="failed",
        error=error,
    )


def _target_candidate_for_failure(source_path: Path, settings: AppConfig) -> Path:
    extension = FORMAT_EXTENSIONS[settings.output_format]
    if settings.output_mode == OUTPUT_MODE_FIXED_FOLDER and settings.output_dir is not None:
        target_dir = settings.output_dir
    elif settings.output_mode == OUTPUT_MODE_CONVERTED_SUBFOLDER:
        target_dir = source_path.parent / "converted"
    else:
        target_dir = source_path.parent
    return target_dir / f"{source_path.stem}{extension}"


def _validate_source(source_path: Path) -> None:
    if not source_path.exists():
        raise ConversionError(f"Source file does not exist: {source_path}")
    if not source_path.is_file():
        raise ConversionError(f"Source path is not a file: {source_path}")
    if source_path.suffix.lower() not in SUPPORTED_SOURCE_SUFFIXES:
        allowed = ", ".join(sorted(SUPPORTED_SOURCE_SUFFIXES))
        raise ConversionError(
            f"Unsupported file extension '{source_path.suffix}'. Expected {allowed}."
        )


def _target_dir_for_source(source_path: Path, settings: AppConfig) -> Path:
    if settings.output_mode == OUTPUT_MODE_SAME_FOLDER:
        return source_path.parent
    if settings.output_mode == OUTPUT_MODE_CONVERTED_SUBFOLDER:
        target_dir = source_path.parent / "converted"
        target_dir.mkdir(exist_ok=True)
        return target_dir
    if settings.output_mode == OUTPUT_MODE_FIXED_FOLDER and settings.output_dir is not None:
        return settings.output_dir
    raise ConversionError("Output folder is not configured.")


def _target_path_for_policy(target_path: Path, overwrite_policy: str) -> Path | None:
    if not os.path.lexists(target_path):
        return target_path
    if overwrite_policy == OVERWRITE_ERROR:
        raise ConversionError(f"Target file already exists: {target_path}")
    if overwrite_policy == OVERWRITE_SKIP:
        return None
    if overwrite_policy == OVERWRITE_OVERWRITE:
        return target_path
    if overwrite_policy == OVERWRITE_RENAME:
        return _renamed_path(target_path)
    raise ConversionError(f"Unsupported overwrite policy: {overwrite_policy}")


def _renamed_path(target_path: Path) -> Path:
    counter = 1
    while True:
        candidate = target_path.with_name(f"{target_path.stem}_{counter}{target_path.suffix}")
        if not os.path.lexists(candidate):
            return candidate
        counter += 1


def _image_for_format(image: Image.Image, output_format: str) -> Image.Image:
    if output_format == FORMAT_JPEG:
        return _to_rgb_on_white(image)
    if output_format == FORMAT_PNG:
        if image.mode in {"RGB", "RGBA", "L", "LA", "P"}:
            return image
        return image.convert("RGBA")
    if output_format == FORMAT_WEBP:
        # PNG may encode transparency as a color key rather than an alpha band.
        if _has_alpha(image) and image.mode != "RGBA":
            return image.convert("RGBA")
        if image.mode in {"RGB", "RGBA"}:
            return image
        return image.convert("RGBA" if _has_alpha(image) else "RGB")
    raise ConversionError(f"Unsupported output format: {output_format}")


def _resize_image(image: Image.Image, max_dimension: int | None) -> Image.Image:
    if max_dimension is None or max(image.size) <= max_dimension:
        return image

    resize_source = image
    if image.mode in {"1", "P"}:
        resize_source = image.convert("RGBA" if _has_alpha(image) else "RGB")
    resized = resize_source.copy()
    resized.thumbnail(
        (max_dimension, max_dimension),
        Image.Resampling.LANCZOS,
        reducing_gap=3.0,
    )
    return resized


def _to_rgb_on_white(image: Image.Image) -> Image.Image:
    if _has_alpha(image):
        background = Image.new("RGB", image.size, (255, 255, 255))
        alpha_source = image.convert("RGBA")
        background.paste(alpha_source, mask=alpha_source.getchannel("A"))
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _has_alpha(image: Image.Image) -> bool:
    return "A" in image.getbands() or "transparency" in image.info


def _save_kwargs(image: Image.Image, settings: AppConfig) -> dict[str, object]:
    kwargs: dict[str, object] = {"format": PIL_FORMATS[settings.output_format]}
    if settings.output_format == FORMAT_JPEG:
        kwargs.update(
            quality=settings.jpeg_quality,
            optimize=settings.jpeg_optimize,
            progressive=settings.jpeg_progressive,
        )
    elif settings.output_format == FORMAT_PNG:
        kwargs["compress_level"] = settings.png_compress_level
    elif settings.output_format == FORMAT_WEBP:
        kwargs.update(
            quality=settings.webp_quality,
            lossless=settings.webp_lossless,
        )
    return kwargs


def _save_image_atomically(
    image: Image.Image,
    target_path: Path,
    save_kwargs: dict[str, object],
    *,
    overwrite_policy: str = OVERWRITE_OVERWRITE,
    rename_base: Path | None = None,
) -> Path | None:
    """Encode once, then publish without violating the selected collision policy."""
    temp_path, descriptor = _temporary_output_file(target_path)
    try:
        with os.fdopen(descriptor, "w+b") as temp_file:
            _set_hidden_attribute(temp_path)
            image.save(temp_file, **save_kwargs)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        # Finish attribute changes before publishing. Failure must leave any
        # existing target untouched, not replace it and then report failure.
        _clear_hidden_attribute(temp_path)
        return _publish_output(temp_path, target_path, overwrite_policy, rename_base or target_path)
    finally:
        temp_path.unlink(missing_ok=True)


def _publish_output(
    temp_path: Path,
    target_path: Path,
    overwrite_policy: str,
    rename_base: Path,
) -> Path | None:
    if overwrite_policy == OVERWRITE_OVERWRITE:
        temp_path.replace(target_path)
        return target_path
    if overwrite_policy not in {OVERWRITE_RENAME, OVERWRITE_SKIP, OVERWRITE_ERROR}:
        raise ConversionError(f"Unsupported overwrite policy: {overwrite_policy}")

    while True:
        try:
            if os.name == "nt":
                # Windows rename refuses an existing destination, including on
                # FAT/exFAT where hard links are unavailable.
                os.rename(temp_path, target_path)
            else:
                # POSIX rename replaces files, so link the completed temp file
                # instead. Both names are on the same filesystem. Fail safely
                # if the filesystem cannot link; never fall back to overwrite.
                os.link(temp_path, target_path)
            return target_path
        except FileExistsError as exc:
            if overwrite_policy == OVERWRITE_SKIP:
                return None
            if overwrite_policy == OVERWRITE_ERROR:
                raise ConversionError(f"Target file already exists: {target_path}") from exc
            target_path = _renamed_path(rename_base)


def _temporary_output_file(target_path: Path) -> tuple[Path, int]:
    # Do not embed the source name: a valid long filename can exceed NAME_MAX
    # once the temporary prefix, random suffix and extension are appended.
    descriptor, name = tempfile.mkstemp(prefix=".heictojpg-", suffix=".tmp", dir=target_path.parent)
    return Path(name), descriptor


def _set_hidden_attribute(path: Path) -> None:
    if os.name != "nt":
        return
    attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    if attributes == WINDOWS_INVALID_FILE_ATTRIBUTES:
        raise OSError(f"Failed to read temporary output file attributes: {path}")
    if (
        ctypes.windll.kernel32.SetFileAttributesW(
            str(path),
            attributes | WINDOWS_FILE_ATTRIBUTE_HIDDEN,
        )
        == 0
    ):
        raise OSError(f"Failed to hide temporary output file: {path}")


def _clear_hidden_attribute(path: Path) -> None:
    if os.name != "nt":
        return
    attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    if attributes == WINDOWS_INVALID_FILE_ATTRIBUTES:
        raise OSError(f"Failed to read output file attributes: {path}")
    if (
        ctypes.windll.kernel32.SetFileAttributesW(
            str(path),
            attributes & ~WINDOWS_FILE_ATTRIBUTE_HIDDEN,
        )
        == 0
    ):
        raise OSError(f"Failed to unhide output file: {path}")


def _exif_bytes(
    image: Image.Image,
    *,
    keep_exif: bool,
    remove_gps: bool,
    output_size: tuple[int, int],
) -> bytes | None:
    if not keep_exif:
        return None
    exif = image.getexif()
    if not exif:
        return None
    if remove_gps and GPS_INFO_TAG in exif:
        del exif[GPS_INFO_TAG]
    _update_exif_dimensions(exif, output_size)
    if not exif:
        return None
    return exif.tobytes()


def _update_exif_dimensions(exif: Image.Exif, output_size: tuple[int, int]) -> None:
    width, height = output_size
    for tag, value in ((IMAGE_WIDTH_TAG, width), (IMAGE_HEIGHT_TAG, height)):
        if tag in exif:
            exif[tag] = value

    if EXIF_IFD_TAG not in exif:
        return
    exif_ifd = exif.get_ifd(EXIF_IFD_TAG)
    for tag, value in (
        (EXIF_IMAGE_WIDTH_TAG, width),
        (EXIF_IMAGE_HEIGHT_TAG, height),
    ):
        if tag in exif_ifd:
            exif_ifd[tag] = value


def _icc_profile_bytes(
    source_image: Image.Image,
    normalized_image: Image.Image,
    *,
    keep_icc_profile: bool,
) -> bytes | None:
    if not keep_icc_profile:
        return None
    for image in (normalized_image, source_image):
        icc_profile = image.info.get("icc_profile")
        if isinstance(icc_profile, bytes) and icc_profile:
            return icc_profile
        if isinstance(icc_profile, bytearray) and icc_profile:
            return bytes(icc_profile)
    return None


def _is_strictly_within(path: Path, parent: Path) -> bool:
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    return resolved_path != resolved_parent and resolved_path.is_relative_to(resolved_parent)


def _is_in_excluded_directory(
    path: Path,
    *,
    folder_path: Path,
    excluded_names: set[str],
    excluded_roots: tuple[Path, ...],
) -> bool:
    if excluded_names:
        relative_parent_parts = path.relative_to(folder_path).parts[:-1]
        if any(part.casefold() in excluded_names for part in relative_parent_parts):
            return True

    resolved_path = path.resolve()
    return any(resolved_path.is_relative_to(root) for root in excluded_roots)


def _walk_files(
    folder_path: Path,
    *,
    excluded_names: set[str],
    excluded_roots: tuple[Path, ...],
) -> Iterable[Path]:
    def raise_walk_error(error: OSError) -> None:
        raise error

    for current_root, directory_names, file_names in os.walk(
        folder_path,
        onerror=raise_walk_error,
    ):
        current_path = Path(current_root)
        kept_directories: list[str] = []
        for directory_name in directory_names:
            directory_path = current_path / directory_name
            resolved_directory = directory_path.resolve()
            if directory_name.casefold() in excluded_names:
                continue
            if any(
                resolved_directory == root or resolved_directory.is_relative_to(root)
                for root in excluded_roots
            ):
                continue
            kept_directories.append(directory_name)
        directory_names[:] = sorted(kept_directories, key=str.casefold)
        for file_name in sorted(file_names, key=str.casefold):
            yield current_path / file_name
