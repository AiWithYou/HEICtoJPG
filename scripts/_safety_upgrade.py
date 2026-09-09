"""One-off maintenance helper; not included in the final main-branch commit."""
from pathlib import Path
import hashlib

p = Path('heictojpg/converter.py')
s = p.read_text(encoding='utf-8')
raw = s.encode('utf-8')
assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == '861de2267eb1be5a7a711766d43b21ab0fe6df38', 'Unexpected converter base'
s = s.replace('''    target_path = _target_path_for_policy(
        target_dir / f"{source_path.stem}{extension}",
        settings.overwrite_policy,
    )''', '''    target_candidate = target_dir / f"{source_path.stem}{extension}"
    target_path = _target_path_for_policy(target_candidate, settings.overwrite_policy)''')
s = s.replace('''            if not settings.keep_icc_profile:
                output_image = _remove_icc_profile(output_image)
''', '')
s = s.replace('''            if exif:
                save_kwargs["exif"] = exif
''', '''            # PNG falls back to image.info["exif"] when the keyword is omitted.
            # An explicit empty value also prevents GPS-only EXIF from returning
            # after the last tag has been removed.
            save_kwargs["exif"] = exif or b""
''')
s = s.replace('''            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile
''', '''            # Override inherited ICC data without copying the entire pixel buffer.
            save_kwargs["icc_profile"] = icc_profile or b""
''')
s = s.replace('''        _save_image_atomically(output_image, target_path, save_kwargs)''', '''        published_path = _save_image_atomically(
            output_image,
            target_path,
            save_kwargs,
            overwrite_policy=settings.overwrite_policy,
            rename_base=target_candidate,
        )''')
s = s.replace('''    return ConversionResult(source=source_path, target=target_path)
''', '''    if published_path is None:
        return ConversionResult(source=source_path, target=target_candidate, status="skipped")
    return ConversionResult(source=source_path, target=published_path)
''')
s = s.replace('''    if not target_path.exists():
        return target_path''', '''    if not os.path.lexists(target_path):
        return target_path''')
s = s.replace('''        if not candidate.exists():
            return candidate''', '''        if not os.path.lexists(candidate):
            return candidate''')
s = s.replace('''    if output_format == FORMAT_WEBP:
        if image.mode in {"RGB", "RGBA"}:''', '''    if output_format == FORMAT_WEBP:
        # PNG may encode transparency as a color key rather than an alpha band.
        if _has_alpha(image) and image.mode != "RGBA":
            return image.convert("RGBA")
        if image.mode in {"RGB", "RGBA"}:''')
start = s.index('def _remove_icc_profile(')
end = s.index('def _save_kwargs(', start)
s = s[:start] + s[end:]
start = s.index('def _save_image_atomically(')
end = s.index('def _set_hidden_attribute(', start)
s = s[:start] + '''def _save_image_atomically(
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
        return _publish_output(
            temp_path, target_path, overwrite_policy, rename_base or target_path
        )
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
    descriptor, name = tempfile.mkstemp(
        prefix=".heictojpg-", suffix=".tmp", dir=target_path.parent
    )
    return Path(name), descriptor


''' + s[end:]
s = s.replace('except Exception as exc:', 'except Exception as exc:  # noqa: BLE001 - isolate third-party decoder failures per file.')
p.write_text(s, encoding='utf-8', newline='\n')

p = Path('heictojpg/cli.py')
s = p.read_text(encoding='utf-8')
s = s.replace('    except Exception:\n        return\n', '    except Exception:  # noqa: BLE001 - a best-effort dialog must not hide the original error.\n        return\n')
p.write_text(s, encoding='utf-8', newline='\n')
for name in ('tests/test_cli.py', 'tests/test_converter.py'):
    p = Path(name)
    s = p.read_text(encoding='utf-8')
    s = s.replace('    except Exception as exc:', '    except (OSError, ValueError, RuntimeError) as exc:')
    p.write_text(s, encoding='utf-8', newline='\n')
for name in ('pyproject.toml', 'heictojpg/version.py'):
    p = Path(name)
    s = p.read_text(encoding='utf-8')
    assert '"1.1.0"' in s
    s = s.replace('"1.1.0"', '"1.1.1"')
    if name == 'pyproject.toml':
        s += '\n[tool.ruff.lint]\n# Keep the quality policy explicit instead of inheriting changing tool defaults.\nselect = ["E4", "E7", "E9", "F", "I", "UP", "B", "BLE"]\n'
    p.write_text(s, encoding='utf-8', newline='\n')
print('Applied safety fixes and version 1.1.1; ready for lint, format and real codec tests.')
