"""Entry point for Free-hand."""

from __future__ import annotations

import os
import sys


def _has_display() -> bool:
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def main() -> None:
    if not _has_display():
        print("Free-hand requires a display. Exiting gracefully (no DISPLAY).")
        print("Install deps with: pip install -r requirements.txt")
        print("Run with: python -m freehand.main")
        raise SystemExit(0)

    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("Free-hand needs Tkinter (e.g. sudo apt install python3-tk).")
        raise SystemExit(1)

    from freehand.ui.app import run_app

    run_app()


if __name__ == "__main__":
    main()
