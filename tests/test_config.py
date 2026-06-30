from pathlib import Path

import pytest

from heictojpg.config import (
    FORMAT_PNG,
    LANGUAGE_JA,
    OUTPUT_MODE_FIXED_FOLDER,
    OUTPUT_MODE_SAME_FOLDER,
    OVERWRITE_SKIP,
    AppConfig,
    ConfigError,
    load_config,
    save_config,
)


def test_missing_config_uses_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "config.json")

    assert config.output_mode == OUTPUT_MODE_SAME_FOLDER
    assert config.output_dir is None
    assert config.output_format == "jpeg"


def test_save_and_load_full_config(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    config_path = tmp_path / "config.json"
    config = AppConfig(
        output_mode=OUTPUT_MODE_FIXED_FOLDER,
        output_dir=output_dir,
        output_format=FORMAT_PNG,
        png_compress_level=3,
        overwrite_policy=OVERWRITE_SKIP,
        keep_exif=False,
        keep_icc_profile=False,
        open_output_folder=True,
        language=LANGUAGE_JA,
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.output_mode == OUTPUT_MODE_FIXED_FOLDER
    assert loaded.output_dir == output_dir
    assert loaded.output_format == FORMAT_PNG
    assert loaded.png_compress_level == 3
    assert loaded.overwrite_policy == OVERWRITE_SKIP
    assert loaded.keep_exif is False
    assert loaded.keep_icc_profile is False
    assert loaded.open_output_folder is True
    assert loaded.language == LANGUAGE_JA


def test_existing_output_dir_only_config_remains_compatible(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(f'{{"output_dir": "{output_dir.as_posix()}"}}', encoding="utf-8")

    loaded = load_config(config_path)

    assert loaded.output_mode == OUTPUT_MODE_FIXED_FOLDER
    assert loaded.output_dir == output_dir
    assert loaded.output_format == "jpeg"


def test_existing_null_output_dir_config_remains_compatible(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"output_dir": null}', encoding="utf-8")

    loaded = load_config(config_path)

    assert loaded.output_mode == OUTPUT_MODE_SAME_FOLDER
    assert loaded.output_dir is None


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"output_dir": null, "future_key": "ignored"}', encoding="utf-8")

    loaded = load_config(config_path)

    assert loaded.output_mode == OUTPUT_MODE_SAME_FOLDER


def test_missing_language_defaults_to_english(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"output_dir": null}', encoding="utf-8")

    loaded = load_config(config_path)

    assert loaded.language == "en"


def test_config_rejects_unknown_language() -> None:
    with pytest.raises(ConfigError, match="Unsupported UI language"):
        save_config(AppConfig(language="fr"), Path("unused.json"))


def test_config_rejects_missing_fixed_output_dir(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"output_mode": "fixed_folder", "output_dir": "C:/path/that/does/not/exist"}',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="does not exist"):
        load_config(config_path)
