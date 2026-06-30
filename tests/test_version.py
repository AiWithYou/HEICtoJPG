from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from heictojpg import __version__ as package_version
from heictojpg.cli import main
from heictojpg.version import __version__, format_app_title


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_version_matches_package_version() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == __version__
    assert package_version == __version__


def test_cli_version_outputs_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out == f"heictojpg {__version__}\n"


def test_app_title_includes_version() -> None:
    assert format_app_title("HEIC Converter") == f"HEIC Converter v{__version__}"
