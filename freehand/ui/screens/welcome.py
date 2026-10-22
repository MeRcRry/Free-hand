"""Screen 1 — Welcome: camera source selection with auto-select timer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

import customtkinter as ctk

from freehand.ui.theme import COLORS, SPACING, make_font
from freehand.ui.widgets.large_button import LargeChoiceButton

if TYPE_CHECKING:
    from freehand.ui.app import FreeHandApp


class WelcomeScreen(ctk.CTkFrame):
    """Dark minimalist welcome with Webcam | Mobile Phone choices."""

    def __init__(
        self,
        master: "FreeHandApp",
        *,
        webcam_available: bool,
        on_select: Callable[[str], None],
        auto_seconds: float = 10.0,
    ) -> None:
        super().__init__(master, fg_color=COLORS["bg"])
        self._on_select = on_select
        self._webcam_available = webcam_available
        self._auto_seconds = auto_seconds
        self._remaining = auto_seconds
        self._timer_id: Optional[str] = None
        self._selected: Optional[str] = None
        self._fade = 0.0

        self._build()
        self.after(80, self._tick_countdown)
        self.after(16, self._animate_in)

    def _build(self) -> None:
        # Atmospheric gradient simulation via stacked bands
        self._hero = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self._hero.pack(fill="both", expand=True)

        top = ctk.CTkFrame(self._hero, fg_color="transparent")
        top.pack(fill="x", padx=SPACING["xl"], pady=(SPACING["xxl"], SPACING["sm"]))

        brand = ctk.CTkLabel(
            top,
            text="Free-hand",
            font=make_font(56, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        )
        brand.pack(anchor="w")

        tagline = ctk.CTkLabel(
            top,
            text="Move the cursor with your head. Click by dwelling.",
            font=make_font(18, "normal"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        tagline.pack(anchor="w", pady=(SPACING["sm"], 0))

        # Soft accent rule
        rule = ctk.CTkFrame(self._hero, fg_color=COLORS["accent"], height=3, width=96, corner_radius=2)
        rule.pack(anchor="w", padx=SPACING["xl"], pady=(SPACING["md"], SPACING["xl"]))

        choices = ctk.CTkFrame(self._hero, fg_color="transparent")
        choices.pack(fill="x", padx=SPACING["xl"])

        webcam_sub = "Ready" if self._webcam_available else "No camera detected"
        self.btn_webcam = LargeChoiceButton(
            choices,
            text="Webcam",
            subtitle=webcam_sub,
            height=120,
            enabled=self._webcam_available,
            command=lambda: self._choose("webcam"),
        )
        self.btn_webcam.pack(fill="x", pady=(0, SPACING["md"]))

        self.btn_ip = LargeChoiceButton(
            choices,
            text="Mobile Phone",
            subtitle="IP camera stream",
            height=120,
            enabled=True,
            command=lambda: self._choose("ip"),
        )
        self.btn_ip.pack(fill="x")

        footer = ctk.CTkFrame(self._hero, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=SPACING["xl"], pady=SPACING["xl"])

        self.countdown_label = ctk.CTkLabel(
            footer,
            text=self._countdown_text(),
            font=make_font(16, "normal"),
            text_color=COLORS["text_dim"],
            anchor="w",
        )
        self.countdown_label.pack(anchor="w")

        # Progress bar for auto-select
        self.progress = ctk.CTkProgressBar(
            footer,
            height=6,
            progress_color=COLORS["accent"],
            fg_color=COLORS["surface"],
            corner_radius=3,
        )
        self.progress.pack(fill="x", pady=(SPACING["sm"], 0))
        self.progress.set(0.0)

        hint = ctk.CTkLabel(
            footer,
            text="Large targets · 10s auto-select · high-contrast dark UI",
            font=make_font(13, "normal"),
            text_color=COLORS["text_dim"],
            anchor="w",
        )
        hint.pack(anchor="w", pady=(SPACING["md"], 0))

    def _countdown_text(self) -> str:
        secs = max(0, int(self._remaining + 0.999))
        default = "Webcam" if self._webcam_available else "Mobile Phone"
        return f"Auto-selecting {default} in {secs}s…"

    def _tick_countdown(self) -> None:
        if self._selected is not None:
            return
        self._remaining -= 0.1
        elapsed = self._auto_seconds - max(0.0, self._remaining)
        self.progress.set(min(1.0, elapsed / self._auto_seconds))
        self.countdown_label.configure(text=self._countdown_text())
        if self._remaining <= 0:
            self._auto_choose()
            return
        self._timer_id = self.after(100, self._tick_countdown)

    def _auto_choose(self) -> None:
        if self._webcam_available:
            self._choose("webcam")
        else:
            self._choose("ip")

    def _choose(self, source: str) -> None:
        if self._selected is not None:
            return
        if source == "webcam" and not self._webcam_available:
            return
        self._selected = source
        if self._timer_id is not None:
            try:
                self.after_cancel(self._timer_id)
            except Exception:  # noqa: BLE001
                pass
        self.btn_webcam.set_selected(source == "webcam")
        self.btn_ip.set_selected(source == "ip")
        self.countdown_label.configure(text="Opening…")
        self.after(220, lambda: self._on_select(source))

    def _animate_in(self) -> None:
        """Subtle fade-style opacity ramp on the hero content via padding drift."""
        self._fade = min(1.0, self._fade + 0.08)
        # Soft vertical settle: reduce top padding as we "arrive"
        pad = int(SPACING["xxl"] * (1.2 - 0.2 * self._fade))
        try:
            self._hero.pack_configure()
        except Exception:  # noqa: BLE001
            pass
        if self._fade < 1.0:
            self.after(16, self._animate_in)

    def destroy(self) -> None:
        if self._timer_id is not None:
            try:
                self.after_cancel(self._timer_id)
            except Exception:  # noqa: BLE001
                pass
        super().destroy()


class IPCameraDialog(ctk.CTkToplevel):
    """Collect an IP camera URL with large controls."""

    def __init__(self, master, on_submit: Callable[[str], None], initial: str = "") -> None:
        super().__init__(master)
        self.title("IP Camera")
        self.configure(fg_color=COLORS["bg_elevated"])
        self.geometry("520x320")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._on_submit = on_submit

        ctk.CTkLabel(
            self,
            text="Phone camera URL",
            font=make_font(24, "bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"]))

        ctk.CTkLabel(
            self,
            text="Paste an MJPEG / RTSP / HTTP stream URL from your phone app.",
            font=make_font(14),
            text_color=COLORS["text_muted"],
            wraplength=460,
            justify="left",
        ).pack(anchor="w", padx=SPACING["lg"])

        self.entry = ctk.CTkEntry(
            self,
            height=56,
            font=make_font(16),
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            placeholder_text="http://192.168.1.20:8080/video",
        )
        self.entry.pack(fill="x", padx=SPACING["lg"], pady=SPACING["md"])
        if initial:
            self.entry.insert(0, initial)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=SPACING["lg"], pady=SPACING["md"])

        ctk.CTkButton(
            row,
            text="Cancel",
            height=52,
            font=make_font(16, "semibold"),
            fg_color=COLORS["surface"],
            hover_color=COLORS["surface_hover"],
            command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        ctk.CTkButton(
            row,
            text="Connect",
            height=52,
            font=make_font(16, "semibold"),
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["accent"],
            text_color=COLORS["bg"],
            command=self._submit,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        self.bind("<Return>", lambda _e: self._submit())
        self.after(100, self.entry.focus_set)

    def _submit(self) -> None:
        url = self.entry.get().strip()
        if not url:
            return
        self._on_submit(url)
        self.destroy()
