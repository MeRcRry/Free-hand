"""Screen 2 — Calibration: mirrored feed, corner mapping, dwell practice."""

from __future__ import annotations

import math
import threading
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

import customtkinter as ctk
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageTk

from freehand.core.config import AppConfig, RuntimeState
from freehand.core.thread_loop import TrackingLoop
from freehand.tracking.camera import CameraSource
from freehand.ui.theme import COLORS, SPACING, make_font

if TYPE_CHECKING:
    from freehand.ui.app import FreeHandApp

Point = Tuple[float, float]

STEPS = [
    ("center", "Look at the center of the screen"),
    ("tl", "Look toward the top-left corner"),
    ("tr", "Look toward the top-right corner"),
    ("br", "Look toward the bottom-right corner"),
    ("bl", "Look toward the bottom-left corner"),
    ("practice", "Dwell on the glowing target to practice clicking"),
]


class CalibrationScreen(ctk.CTkFrame):
    """Live preview + guided calibration with dwell practice."""

    def __init__(
        self,
        master: "FreeHandApp",
        *,
        config: AppConfig,
        state: RuntimeState,
        camera: CameraSource,
        on_complete: Callable[[], None],
        on_back: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master, fg_color=COLORS["bg"])
        self.app = master
        self.app_config = config
        self.runtime = state
        self.camera = camera
        self.on_complete = on_complete
        self.on_back = on_back

        self._step_idx = 0
        self._samples: List[Point] = []
        self._preview_photo = None
        self._preview_size = (560, 420)
        self._practice_hits = 0
        self._practice_needed = 1
        self._hold_progress = 0.0
        self._hold_anchor: Optional[Point] = None
        self._pulse = 0.0
        self._latest_frame = None
        self._latest_landmark: Optional[Point] = None
        self._frame_lock = threading.Lock()
        self._loop: Optional[TrackingLoop] = None
        self._finished = False

        self._build()
        self._start_preview_loop()
        self.after(33, self._ui_tick)
        self.after(16, self._pulse_tick)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=SPACING["xl"], pady=(SPACING["lg"], SPACING["sm"]))

        ctk.CTkLabel(
            header,
            text="Calibration",
            font=make_font(36, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(anchor="w")

        self.instruction = ctk.CTkLabel(
            header,
            text=STEPS[0][1],
            font=make_font(18),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.instruction.pack(anchor="w", pady=(SPACING["xs"], 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=SPACING["xl"], pady=SPACING["md"])

        # Preview card — soft elevated panel, not a busy dashboard
        preview_wrap = ctk.CTkFrame(
            body,
            fg_color=COLORS["bg_elevated"],
            corner_radius=28,
            border_width=1,
            border_color=COLORS["border"],
        )
        preview_wrap.pack(side="left", fill="both", expand=True, padx=(0, SPACING["md"]))

        self.preview_label = ctk.CTkLabel(preview_wrap, text="", fg_color=COLORS["bg_soft"])
        self.preview_label.pack(fill="both", expand=True, padx=18, pady=18)

        side = ctk.CTkFrame(body, fg_color="transparent", width=280)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)

        self.step_pills = []
        for i, (key, _) in enumerate(STEPS):
            label = "Practice" if key == "practice" else key.upper() if len(key) <= 2 else key.title()
            pill = ctk.CTkLabel(
                side,
                text=f"  {i + 1}.  {label}",
                font=make_font(15, "medium"),
                text_color=COLORS["text_dim"],
                anchor="w",
                height=36,
            )
            pill.pack(fill="x", pady=4)
            self.step_pills.append(pill)

        self.status = ctk.CTkLabel(
            side,
            text="Hold still to capture…",
            font=make_font(14),
            text_color=COLORS["accent"],
            anchor="w",
            wraplength=260,
        )
        self.status.pack(anchor="w", pady=(SPACING["lg"], 0))

        self.capture_bar = ctk.CTkProgressBar(
            side,
            height=8,
            progress_color=COLORS["accent"],
            fg_color=COLORS["surface"],
        )
        self.capture_bar.pack(fill="x", pady=(SPACING["sm"], 0))
        self.capture_bar.set(0)

        self.btn_skip = ctk.CTkButton(
            side,
            text="Use defaults",
            height=48,
            font=make_font(15, "semibold"),
            fg_color=COLORS["surface"],
            hover_color=COLORS["surface_hover"],
            border_width=1,
            border_color=COLORS["border"],
            command=self._skip_to_practice_or_finish,
        )
        self.btn_skip.pack(side="bottom", fill="x", pady=(SPACING["md"], 0))

        self._refresh_step_pills()

    def _refresh_step_pills(self) -> None:
        for i, pill in enumerate(self.step_pills):
            if i < self._step_idx:
                pill.configure(text_color=COLORS["accent_dim"])
            elif i == self._step_idx:
                pill.configure(text_color=COLORS["accent"])
            else:
                pill.configure(text_color=COLORS["text_dim"])

    def _start_preview_loop(self) -> None:
        # During calibration we do NOT move the OS cursor — only sample landmarks
        self._loop = TrackingLoop(
            self.app_config,
            self.runtime,
            self.camera,
            move_cursor=False,
            on_frame=self._on_frame,
            on_click=None,
        )
        self._loop.start()

    def _on_frame(self, frame, landmark: Optional[Point]) -> None:
        with self._frame_lock:
            self._latest_frame = frame
            self._latest_landmark = landmark

    def _ui_tick(self) -> None:
        if self._finished:
            return
        frame = None
        landmark = None
        with self._frame_lock:
            frame = self._latest_frame
            landmark = self._latest_landmark

        if frame is not None:
            self._render_preview(frame, landmark)

        key = STEPS[self._step_idx][0]
        if key == "practice":
            self._tick_practice(landmark)
        else:
            self._tick_capture(landmark)

        self.after(33, self._ui_tick)

    def _tick_capture(self, landmark: Optional[Point]) -> None:
        if landmark is None:
            self._hold_progress = 0.0
            self._hold_anchor = None
            self.capture_bar.set(0)
            self.status.configure(text="Face not detected — center your head")
            return

        # landmark is already display-mirrored from TrackingLoop (1-nx, ny)
        # For mapping we need unmirrored camera space: invert x back
        cam_pt = (1.0 - landmark[0], landmark[1])

        if self._hold_anchor is None:
            self._hold_anchor = cam_pt
            self._hold_progress = 0.0
        else:
            dx = cam_pt[0] - self._hold_anchor[0]
            dy = cam_pt[1] - self._hold_anchor[1]
            if math.hypot(dx, dy) > 0.025:
                self._hold_anchor = cam_pt
                self._hold_progress = 0.0
            else:
                self._hold_progress = min(1.0, self._hold_progress + 0.045)

        self.capture_bar.set(self._hold_progress)
        self.status.configure(text="Hold still to capture…")

        if self._hold_progress >= 1.0 and self._hold_anchor is not None:
            self._samples.append(self._hold_anchor)
            self._hold_progress = 0.0
            self._hold_anchor = None
            self._advance_step()

    def _tick_practice(self, landmark: Optional[Point]) -> None:
        """Show on-preview target; complete when dwell progress hits 1 via TrackingLoop."""
        self.capture_bar.set(self.runtime.dwell_progress)
        if landmark is None:
            self.status.configure(text="Face not detected")
            return

        # Map practice using current (possibly default) bounds — cursor in screen space
        # For practice we check if the *display* landmark is near the on-preview target.
        # Target sits at ~center-right of the mirrored preview.
        target = (0.62, 0.48)
        dist = math.hypot(landmark[0] - target[0], landmark[1] - target[1])
        if dist < 0.07:
            self._hold_progress = min(1.0, self._hold_progress + 0.035)
        else:
            self._hold_progress = max(0.0, self._hold_progress - 0.05)
        self.capture_bar.set(self._hold_progress)
        self.status.configure(text="Dwell on the target…")
        if self._hold_progress >= 1.0:
            self._practice_hits += 1
            self._hold_progress = 0.0
            self.status.configure(text="Nice — entering Active Mode")
            self.after(500, self._finish)

    def _advance_step(self) -> None:
        self._step_idx += 1
        if self._step_idx >= len(STEPS):
            self._finish()
            return
        if STEPS[self._step_idx][0] == "practice":
            if self._samples:
                self.app_config.set_face_bounds_from_samples(self._samples)
            self.btn_skip.configure(text="Skip practice → Active")
        self.instruction.configure(text=STEPS[self._step_idx][1])
        self._refresh_step_pills()
        self.capture_bar.set(0)

    def _skip_to_practice_or_finish(self) -> None:
        if STEPS[self._step_idx][0] == "practice":
            self._finish()
            return
        # Jump to practice with whatever samples we have (or defaults)
        if self._samples:
            self.app_config.set_face_bounds_from_samples(self._samples)
        self._step_idx = len(STEPS) - 1
        self.instruction.configure(text=STEPS[self._step_idx][1])
        self._refresh_step_pills()
        self.btn_skip.configure(text="Skip practice → Active")

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        if self._samples:
            self.app_config.set_face_bounds_from_samples(self._samples)
        self.runtime.calibration_samples = list(self._samples)
        self._stop_loop()
        self.on_complete()

    def _stop_loop(self) -> None:
        if self._loop is not None:
            self._loop.stop()
            self._loop = None

    def _pulse_tick(self) -> None:
        if self._finished:
            return
        self._pulse = (self._pulse + 0.07) % (math.pi * 2)
        self.after(16, self._pulse_tick)

    def _render_preview(self, frame_bgr: np.ndarray, landmark: Optional[Point]) -> None:
        try:
            import cv2
        except ImportError:
            return

        h, w = frame_bgr.shape[:2]
        tw, th = self._preview_size
        scale = min(tw / w, th / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        resized = cv2.resize(frame_bgr, (nw, nh))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        # Soft blur vignette mask for rounded ambient look
        mask = Image.new("L", (nw, nh), 0)
        draw = ImageDraw.Draw(mask)
        inset = 8
        draw.rounded_rectangle((inset, inset, nw - inset, nh - inset), radius=36, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(6))

        soft = img.filter(ImageFilter.GaussianBlur(10))
        img = Image.composite(img, soft, mask)

        # Dark rounded plate behind
        plate = Image.new("RGBA", (tw, th), (18, 24, 32, 255))
        ox, oy = (tw - nw) // 2, (th - nh) // 2
        rgba = img.convert("RGBA")
        plate.paste(rgba, (ox, oy), mask)

        canvas = ImageDraw.Draw(plate, "RGBA")
        # Soft outer glow ring
        glow = int(40 + 20 * math.sin(self._pulse))
        canvas.rounded_rectangle(
            (4, 4, tw - 4, th - 4),
            radius=40,
            outline=(61, 220, 151, glow),
            width=2,
        )

        if landmark is not None:
            lx = ox + landmark[0] * nw
            ly = oy + landmark[1] * nh
            r = 6
            canvas.ellipse((lx - r, ly - r, lx + r, ly + r), fill=(61, 220, 151, 220))

        if STEPS[self._step_idx][0] == "practice":
            tx = ox + 0.62 * nw
            ty = oy + 0.48 * nh
            pr = 28 + 4 * math.sin(self._pulse)
            # Outer dwell ring
            canvas.ellipse(
                (tx - pr - 8, ty - pr - 8, tx + pr + 8, ty + pr + 8),
                outline=(61, 220, 151, 180),
                width=3,
            )
            fill_a = int(80 + 100 * self._hold_progress)
            canvas.ellipse(
                (tx - pr, ty - pr, tx + pr, ty + pr),
                fill=(61, 220, 151, fill_a),
                outline=(242, 245, 248, 220),
                width=2,
            )

        self._preview_photo = ImageTk.PhotoImage(plate)
        self.preview_label.configure(image=self._preview_photo)

    def destroy(self) -> None:
        self._finished = True
        self._stop_loop()
        super().destroy()
