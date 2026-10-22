"""Background tracking loop so the CustomTkinter UI never blocks."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from freehand.core.config import AppConfig, RuntimeState
from freehand.tracking.camera import CameraSource
from freehand.tracking.dwell_click import DwellClicker
from freehand.tracking.face_tracker import FaceTracker
from freehand.tracking.smoothing import CursorSmoother


class TrackingLoop:
    """Runs camera → face → smooth → dwell → cursor on a daemon thread."""

    def __init__(
        self,
        config: AppConfig,
        state: RuntimeState,
        camera: CameraSource,
        *,
        move_cursor: bool = True,
        on_frame: Optional[Callable] = None,
        on_click: Optional[Callable[[float, float], None]] = None,
    ) -> None:
        self.config = config
        self.runtime = state
        self.camera = camera
        self.move_cursor = move_cursor
        self.on_frame = on_frame
        self.on_click = on_click

        self._tracker = FaceTracker(landmark_mode=config.landmark_mode)
        self._smoother = CursorSmoother(
            alpha=config.ema_alpha,
            use_kalman=config.use_kalman,
        )
        self._dwell = DwellClicker(
            radius_px=config.dwell_radius_px,
            dwell_time_s=config.dwell_time_s,
            cooldown_s=config.dwell_cooldown_s,
        )

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._pyautogui = None
        self._failsafe_disabled = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="freehand-track", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None
        self._tracker.close()

    def reset_smoothing(self) -> None:
        self._smoother.reset()
        self._dwell.reset()

    def update_config(self) -> None:
        """Pull latest tunables from AppConfig into helpers."""
        self._smoother.alpha = self.config.ema_alpha
        self._smoother.use_kalman = self.config.use_kalman
        self._dwell.radius_px = self.config.dwell_radius_px
        self._dwell.dwell_time_s = self.config.dwell_time_s
        self._dwell.cooldown_s = self.config.dwell_cooldown_s
        self._tracker.landmark_mode = self.config.landmark_mode

    def _ensure_pyautogui(self) -> None:
        if self._pyautogui is not None:
            return
        try:
            import pyautogui

            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0
            self._pyautogui = pyautogui
            self._failsafe_disabled = True
        except Exception as exc:  # noqa: BLE001
            self.runtime.last_error = f"PyAutoGUI unavailable: {exc}"
            self._pyautogui = None

    def _run(self) -> None:
        self.runtime.tracking_active = True
        self.runtime.last_error = None
        self._ensure_pyautogui()

        target_dt = 1.0 / max(self.config.camera_fps, 1)
        while not self._stop.is_set():
            t0 = time.perf_counter()
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001
                self.runtime.last_error = str(exc)
                self.runtime.face_detected = False
            elapsed = time.perf_counter() - t0
            sleep_for = target_dt - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

        self.runtime.tracking_active = False
        self.runtime.face_detected = False
        self.runtime.dwell_progress = 0.0

    def _tick(self) -> None:
        ok, frame = self.camera.read()
        if not ok or frame is None:
            self.runtime.face_detected = False
            self.runtime.dwell_progress = 0.0
            if self.on_frame is not None:
                self.on_frame(None, None)
            return

        landmark = self._tracker.process(frame)
        mirrored = None
        try:
            import cv2

            mirrored = cv2.flip(frame, 1)
        except Exception:  # noqa: BLE001
            mirrored = frame

        if landmark is None:
            self.runtime.face_detected = False
            self.runtime.dwell_progress = 0.0
            self._dwell.reset()
            if self.on_frame is not None:
                self.on_frame(mirrored, None)
            return

        self.runtime.face_detected = True
        nx, ny = landmark
        # Mirrored preview: flip x for display consistency with invert_x mapping
        display_pt = (1.0 - nx, ny)

        sx, sy = self.config.map_face_to_screen(nx, ny)
        smooth_x, smooth_y = self._smoother.update(sx, sy)
        self.runtime.cursor_xy = (smooth_x, smooth_y)

        if self.runtime.paused:
            self.runtime.dwell_progress = 0.0
            self._dwell.reset()
        else:
            clicked, progress = self._dwell.update(smooth_x, smooth_y)
            self.runtime.dwell_progress = progress
            if self.move_cursor and self._pyautogui is not None:
                try:
                    self._pyautogui.moveTo(int(smooth_x), int(smooth_y), _pause=False)
                except Exception as exc:  # noqa: BLE001
                    self.runtime.last_error = f"Cursor move failed: {exc}"
            if clicked:
                if self.move_cursor and self._pyautogui is not None:
                    try:
                        self._pyautogui.click(button="left")
                    except Exception as exc:  # noqa: BLE001
                        self.runtime.last_error = f"Click failed: {exc}"
                if self.on_click is not None:
                    self.on_click(smooth_x, smooth_y)

        if self.on_frame is not None:
            self.on_frame(mirrored, display_pt)
