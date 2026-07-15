from pathlib import Path

import pytest

import heictojpg.config as config_module
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
    assert config.max_dimension is None


def test_save_and_load_full_config(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    config_path = tmp_path / "config.json"
    config = AppConfig(
        output_mode=OUTPUT_MODE_FIXED_FOLDER,
        output_dir=output_dir,
        output_format=FORMAT_PNG,
        max_dimension=1600,
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
    assert loaded.max_dimension == 1600
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


@pytest.mark.parametrize("max_dimension", [0, -1])
def test_config_rejects_non_positive_max_dimension(max_dimension: int) -> None:
    with pytest.raises(ConfigError):
        save_config(AppConfig(max_dimension=max_dimension), Path("unused.json"))


@pytest.mark.parametrize("json_value", ["true", '"100"', "1.5"])
def test_config_rejects_non_integer_max_dimension(tmp_path: Path, json_value: str) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(f'{{"max_dimension": {json_value}}}', encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_non_utf8_config_is_reported_as_config_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_bytes(b"\xff")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_config_read_os_error_is_reported_as_config_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.mkdir()

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_save_config_write_failure_preserves_existing_file_and_removes_temp_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    original_contents = b'{"language": "ja"}\n'
    config_path.write_bytes(original_contents)

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("simulated disk failure")

    monkeypatch.setattr(config_module.os, "fsync", fail_fsync)

    with pytest.raises(ConfigError, match="Could not save config file"):
        save_config(AppConfig(), config_path)

    assert config_path.read_bytes() == original_contents
    assert list(tmp_path.glob(".config.json-*.tmp")) == []
