"""Dark-theme design tokens, fonts, and spacing for Free-hand."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Tuple

# ---------------------------------------------------------------------------
# Color tokens — deep charcoal + mint accent (high contrast)
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#0B0E11",
    "bg_elevated": "#12161C",
    "bg_soft": "#181E27",
    "surface": "#1C2430",
    "surface_hover": "#243040",
    "border": "#2A3544",
    "text": "#F2F5F8",
    "text_muted": "#9AA8B8",
    "text_dim": "#6B7A8D",
    "accent": "#3DDC97",
    "accent_dim": "#2A9B6A",
    "accent_soft": "#1A3D2E",
    "danger": "#FF6B6B",
    "danger_dim": "#C44A4A",
    "warning": "#F0C14A",
    "success": "#3DDC97",
    "track_off": "#4A5564",
    "overlay": "#0B0E11EE",
}

SPACING = {
    "xs": 6,
    "sm": 12,
    "md": 20,
    "lg": 32,
    "xl": 48,
    "xxl": 72,
}

RADIUS = {
    "sm": 10,
    "md": 16,
    "lg": 24,
    "xl": 32,
}

_FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_FAMILY = "Outfit"
_FONTS_LOADED = False


def load_fonts() -> str:
    """Load bundled Outfit faces via CustomTkinter FontManager; return family."""
    global _FONTS_LOADED, _FAMILY
    if _FONTS_LOADED:
        return _FAMILY

    loaded = False
    try:
        from customtkinter.windows.widgets.font.font_manager import FontManager

        for name in (
            "Outfit-Regular.ttf",
            "Outfit-Medium.ttf",
            "Outfit-SemiBold.ttf",
            "Outfit-Bold.ttf",
        ):
            path = _FONT_DIR / name
            if path.is_file():
                FontManager.load_font(str(path))
                loaded = True
    except Exception:  # noqa: BLE001
        loaded = False

    if loaded:
        _FAMILY = "Outfit"
    else:
        # Expressive system fallbacks — avoid Inter / generic UI stacks when possible
        _FAMILY = "Noto Sans Display"
        try:
            from tkinter import font as tkfont

            families = set(tkfont.families())
            for candidate in ("Noto Sans Display", "Source Sans 3", "Cantarell", "DejaVu Sans"):
                if candidate in families:
                    _FAMILY = candidate
                    break
        except Exception:  # noqa: BLE001
            pass

    _FONTS_LOADED = True
    return _FAMILY


def font_family() -> str:
    return load_fonts()


def ctk_font(size: int, weight: str = "normal") -> Tuple[str, int, str]:
    """Return a CTk-compatible font tuple."""
    w = "bold" if weight in ("bold", "semibold", "medium") else "normal"
    return (font_family(), size, w)


def make_font(size: int, weight: str = "normal") -> Any:
    """Build a CTkFont with the project family."""
    import customtkinter as ctk

    load_fonts()
    w = "bold" if weight in ("bold", "semibold") else "normal"
    return ctk.CTkFont(family=font_family(), size=size, weight=w)


def apply_appearance() -> None:
    """Configure CustomTkinter global appearance for dark mode."""
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    load_fonts()
