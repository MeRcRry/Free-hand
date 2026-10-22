"""Visual dwell-progress ring drawn near the system cursor (overlay window)."""

from __future__ import annotations

import math
import tkinter as tk
from typing import Optional, Tuple

from freehand.ui.theme import COLORS


class DwellRingOverlay(tk.Toplevel):
    """
    Tiny always-on-top transparent window that draws a progress arc.

    Used during Active Mode so the user sees dwell progress around the cursor.
    """

    SIZE = 72

    def __init__(self, master) -> None:
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-transparentcolor", "#010101")
        except tk.TclError:
            pass
        self.configure(bg="#010101")
        self.geometry(f"{self.SIZE}x{self.SIZE}+0+0")

        self._canvas = tk.Canvas(
            self,
            width=self.SIZE,
            height=self.SIZE,
            bg="#010101",
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(fill="both", expand=True)
        self._progress = 0.0
        self._visible = False
        self.withdraw()

    def set_progress(self, progress: float, screen_xy: Optional[Tuple[float, float]] = None) -> None:
        self._progress = max(0.0, min(1.0, progress))
        if screen_xy is not None:
            x, y = screen_xy
            half = self.SIZE // 2
            self.geometry(f"{self.SIZE}x{self.SIZE}+{int(x - half)}+{int(y - half)}")

        if self._progress <= 0.02:
            if self._visible:
                self.withdraw()
                self._visible = False
            return

        if not self._visible:
            self.deiconify()
            self._visible = True

        self._draw()

    def hide(self) -> None:
        self._progress = 0.0
        if self._visible:
            self.withdraw()
            self._visible = False

    def _draw(self) -> None:
        self._canvas.delete("all")
        pad = 8
        x0, y0, x1, y1 = pad, pad, self.SIZE - pad, self.SIZE - pad
        # Track
        self._canvas.create_oval(x0, y0, x1, y1, outline=COLORS["track_off"], width=4)
        extent = -360.0 * self._progress  # clockwise-ish from top
        # Tk arcs start at 3 o'clock; rotate so progress starts at 12 o'clock
        self._canvas.create_arc(
            x0,
            y0,
            x1,
            y1,
            start=90,
            extent=extent,
            style=tk.ARC,
            outline=COLORS["accent"],
            width=5,
        )
        # Soft center dot
        cx = self.SIZE / 2
        cy = self.SIZE / 2
        r = 3 + 2 * math.sin(self._progress * math.pi)
        self._canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=COLORS["accent"], outline="")
