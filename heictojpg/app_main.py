from __future__ import annotations

import sys
from pathlib import Path

from heictojpg.app_gui import run_converter_app


def main() -> int:
    run_converter_app([Path(value) for value in sys.argv[1:]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
