from __future__ import annotations


__version__ = "1.0.0"


def format_app_title(app_name: str) -> str:
    return f"{app_name} v{__version__}"
