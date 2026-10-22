"""Screen 3 — Always-on-top floating control widget for Active Mode."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

import customtkinter as ctk

from freehand.core.config import AppConfig, RuntimeState
from freehand.ui.theme import COLORS, SPACING, make_font

if TYPE_CHECKING:
    from freehand.ui.app import FreeHandApp


class FloatingWidget(ctk.CTkToplevel):
    """Compact Always-on-Top panel: status · Pause · Settings."""

    def __init__(
        self,
        master: "FreeHandApp",
        *,
        config: AppConfig,
        state: RuntimeState,
        on_pause_toggle: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.app_config = config
        self.runtime = state
        self.on_pause_toggle = on_pause_toggle
        self.on_open_settings = on_open_settings
        self.on_exit = on_exit

        self.title("Free-hand")
        self.geometry("300x148+24+24")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color=COLORS["bg_elevated"])
        try:
            self.overrideredirect(False)
        except Exception:  # noqa: BLE001
            pass

        self._drag_x = 0
        self._drag_y = 0
        self._build()
        self.after(100, self._poll_status)

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _build(self) -> None:
        root = ctk.CTkFrame(self, fg_color=COLORS["bg_elevated"], corner_radius=0)
        root.pack(fill="both", expand=True)

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", padx=SPACING["md"], pady=(SPACING["md"], SPACING["sm"]))

        self.status_dot = ctk.CTkLabel(
            header,
            text="●",
            font=make_font(18),
            text_color=COLORS["danger"],
            width=24,
        )
        self.status_dot.pack(side="left")

        self.status_label = ctk.CTkLabel(
            header,
            text="Searching…",
            font=make_font(16, "semibold"),
            text_color=COLORS["text"],
            anchor="w",
        )
        self.status_label.pack(side="left", padx=(4, 0))

        # Drag affordance
        grab = ctk.CTkLabel(
            header,
            text="Free-hand",
            font=make_font(13),
            text_color=COLORS["text_dim"],
        )
        grab.pack(side="right")
        for widget in (header, grab, self.status_label):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)

        row = ctk.CTkFrame(root, fg_color="transparent")
        row.pack(fill="x", padx=SPACING["md"], pady=(0, SPACING["md"]))

        self.pause_btn = ctk.CTkButton(
            row,
            text="Pause",
            height=56,
            font=make_font(16, "semibold"),
            fg_color=COLORS["surface"],
            hover_color=COLORS["surface_hover"],
            border_width=1,
            border_color=COLORS["border"],
            command=self._toggle_pause,
        )
        self.pause_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.settings_btn = ctk.CTkButton(
            row,
            text="⚙",
            width=56,
            height=56,
            font=make_font(22),
            fg_color=COLORS["surface"],
            hover_color=COLORS["surface_hover"],
            border_width=1,
            border_color=COLORS["border"],
            command=self.on_open_settings,
        )
        self.settings_btn.pack(side="left")

    def _toggle_pause(self) -> None:
        self.on_pause_toggle()
        self._refresh_pause_label()

    def _refresh_pause_label(self) -> None:
        if self.runtime.paused:
            self.pause_btn.configure(text="Resume", fg_color=COLORS["accent_soft"], border_color=COLORS["accent"])
        else:
            self.pause_btn.configure(text="Pause", fg_color=COLORS["surface"], border_color=COLORS["border"])

    def _poll_status(self) -> None:
        if not self.winfo_exists():
            return
        if self.runtime.paused:
            self.status_dot.configure(text_color=COLORS["warning"])
            self.status_label.configure(text="Paused")
        elif self.runtime.face_detected and self.runtime.tracking_active:
            self.status_dot.configure(text_color=COLORS["success"])
            self.status_label.configure(text="Tracking")
        else:
            self.status_dot.configure(text_color=COLORS["danger"])
            self.status_label.configure(text="No face")
        self._refresh_pause_label()
        self.after(120, self._poll_status)

    def _start_drag(self, event) -> None:
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _on_drag(self, event) -> None:
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")


class SettingsPanel(ctk.CTkToplevel):
    """Lightweight settings for dwell + smoothing."""

    def __init__(
        self,
        master,
        config: AppConfig,
        on_apply: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master)
        self.app_config = config
        self.on_apply = on_apply
        self.title("Settings")
        self.geometry("420x460")
        self.configure(fg_color=COLORS["bg_elevated"])
        self.attributes("-topmost", True)

        ctk.CTkLabel(
            self,
            text="Settings",
            font=make_font(24, "bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"]))

        self._dwell_time = self._slider("Dwell time (s)", 0.6, 2.5, config.dwell_time_s, 0.05)
        self._dwell_radius = self._slider("Dwell radius (px)", 12, 60, config.dwell_radius_px, 1)
        self._ema = self._slider("Smoothing (EMA α)", 0.08, 0.7, config.ema_alpha, 0.01)

        self.landmark = ctk.CTkSegmentedButton(
            self,
            values=["nose", "mid_eyes"],
            font=make_font(14),
            fg_color=COLORS["surface"],
            selected_color=COLORS["accent_dim"],
            selected_hover_color=COLORS["accent"],
            unselected_color=COLORS["surface"],
            unselected_hover_color=COLORS["surface_hover"],
            command=self._noop,
        )
        self.landmark.set(config.landmark_mode)
        ctk.CTkLabel(
            self,
            text="Control point",
            font=make_font(13),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", padx=SPACING["lg"], pady=(SPACING["md"], 4))
        self.landmark.pack(fill="x", padx=SPACING["lg"])

        ctk.CTkButton(
            self,
            text="Apply",
            height=52,
            font=make_font(16, "semibold"),
            fg_color=COLORS["accent_dim"],
            hover_color=COLORS["accent"],
            text_color=COLORS["bg"],
            command=self._apply,
        ).pack(fill="x", padx=SPACING["lg"], pady=SPACING["lg"])

    def _noop(self, _value=None) -> None:
        return

    def _slider(self, label: str, lo: float, hi: float, value: float, step: float):
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["sm"], 0))
        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=label, font=make_font(13), text_color=COLORS["text_muted"]).pack(side="left")
        val_lbl = ctk.CTkLabel(top, text=f"{value:.2f}", font=make_font(13), text_color=COLORS["text"])
        val_lbl.pack(side="right")

        slider = ctk.CTkSlider(
            wrap,
            from_=lo,
            to=hi,
            number_of_steps=max(1, int((hi - lo) / step)),
            progress_color=COLORS["accent"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["text"],
            fg_color=COLORS["surface"],
            command=lambda v, lbl=val_lbl: lbl.configure(text=f"{float(v):.2f}"),
        )
        slider.set(value)
        slider.pack(fill="x", pady=(4, 0))
        return slider

    def _apply(self) -> None:
        self.app_config.dwell_time_s = float(self._dwell_time.get())
        self.app_config.dwell_radius_px = float(self._dwell_radius.get())
        self.app_config.ema_alpha = float(self._ema.get())
        self.app_config.landmark_mode = self.landmark.get()
        if self.on_apply:
            self.on_apply()
        self.destroy()
