"""Dwell-to-click: hold still within a pixel radius for N seconds → left click."""

from __future__ import annotations

import math
import time
from typing import Tuple


class DwellClicker:
    """Tracks dwell progress and fires when the cursor stays put long enough."""

    def __init__(
        self,
        radius_px: float = 28.0,
        dwell_time_s: float = 1.35,
        cooldown_s: float = 0.85,
    ) -> None:
        self.radius_px = radius_px
        self.dwell_time_s = dwell_time_s
        self.cooldown_s = cooldown_s

        self._anchor_x: float = 0.0
        self._anchor_y: float = 0.0
        self._dwell_start: float = 0.0
        self._active = False
        self._last_click_at: float = 0.0

    def reset(self) -> None:
        self._active = False
        self._dwell_start = 0.0

    def update(self, x: float, y: float) -> Tuple[bool, float]:
        """
        Feed a smoothed cursor position.

        Returns (clicked, progress) where progress is in [0, 1].
        """
        now = time.perf_counter()
        if now - self._last_click_at < self.cooldown_s:
            self._active = False
            return False, 0.0

        if not self._active:
            self._anchor_x = x
            self._anchor_y = y
            self._dwell_start = now
            self._active = True
            return False, 0.0

        dist = math.hypot(x - self._anchor_x, y - self._anchor_y)
        if dist > self.radius_px:
            self._anchor_x = x
            self._anchor_y = y
            self._dwell_start = now
            return False, 0.0

        elapsed = now - self._dwell_start
        progress = min(1.0, elapsed / max(self.dwell_time_s, 1e-3))
        if progress >= 1.0:
            self._last_click_at = now
            self._active = False
            return True, 1.0
        return False, progress
