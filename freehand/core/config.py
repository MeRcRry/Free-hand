"""Runtime configuration for tracking, dwell click, and screen mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple


Point = Tuple[float, float]
Rect = Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y


@dataclass
class AppConfig:
    """Tunable parameters shared across tracking and UI."""

    # Dwell click
    dwell_radius_px: float = 28.0
    dwell_time_s: float = 1.35
    dwell_cooldown_s: float = 0.85

    # Smoothing (EMA)
    ema_alpha: float = 0.28
    use_kalman: bool = False

    # Face → screen mapping (normalized face space → screen pixels)
    # Updated during calibration.
    face_bounds: Rect = (0.35, 0.30, 0.65, 0.70)
    screen_width: int = 1920
    screen_height: int = 1080
    invert_x: bool = True  # mirrored webcam feel
    invert_y: bool = False

    # Camera
    webcam_index: int = 0
    ip_camera_url: str = ""
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 30

    # Tracking landmark: "nose" or "mid_eyes"
    landmark_mode: str = "nose"

    # Accessibility UI
    auto_select_seconds: float = 10.0
    large_button_height: int = 96
    large_button_font_size: int = 28

    # Practice target on calibration
    practice_target_radius: int = 48

    def map_face_to_screen(self, nx: float, ny: float) -> Point:
        """Map normalized face landmark to screen coordinates."""
        min_x, min_y, max_x, max_y = self.face_bounds
        span_x = max(max_x - min_x, 1e-4)
        span_y = max(max_y - min_y, 1e-4)

        u = (nx - min_x) / span_x
        v = (ny - min_y) / span_y
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))

        if self.invert_x:
            u = 1.0 - u
        if self.invert_y:
            v = 1.0 - v

        return u * (self.screen_width - 1), v * (self.screen_height - 1)

    def set_face_bounds_from_samples(self, samples: list[Point], pad: float = 0.04) -> None:
        """Fit face_bounds from calibration samples (center + corners)."""
        if not samples:
            return
        xs = [p[0] for p in samples]
        ys = [p[1] for p in samples]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        # Expand slightly so corners remain reachable
        dx = max(max_x - min_x, 0.08)
        dy = max(max_y - min_y, 0.08)
        self.face_bounds = (
            max(0.0, min_x - pad * dx),
            max(0.0, min_y - pad * dy),
            min(1.0, max_x + pad * dx),
            min(1.0, max_y + pad * dy),
        )


@dataclass
class RuntimeState:
    """Mutable flags shared between UI and tracking thread."""

    paused: bool = False
    tracking_active: bool = False
    face_detected: bool = False
    dwell_progress: float = 0.0  # 0..1
    cursor_xy: Point = (0.0, 0.0)
    last_error: Optional[str] = None
    camera_source_label: str = ""
    calibration_samples: list[Point] = field(default_factory=list)
