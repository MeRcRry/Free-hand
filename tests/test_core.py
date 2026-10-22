"""Unit tests that run without a camera or display."""

from __future__ import annotations

from freehand.core.config import AppConfig
from freehand.tracking.dwell_click import DwellClicker
from freehand.tracking.smoothing import CursorSmoother


def test_ema_converges_toward_target():
    s = CursorSmoother(alpha=0.5, use_kalman=False)
    x, y = 0.0, 0.0
    for _ in range(20):
        x, y = s.update(100.0, 200.0)
    assert abs(x - 100.0) < 1.0
    assert abs(y - 200.0) < 1.0


def test_dwell_requires_stillness(monkeypatch):
    clicker = DwellClicker(radius_px=10, dwell_time_s=0.2, cooldown_s=0.0)
    # Patch time so we can advance deterministically
    t = {"now": 1000.0}

    def fake_perf():
        return t["now"]

    monkeypatch.setattr("freehand.tracking.dwell_click.time.perf_counter", fake_perf)

    clicked, progress = clicker.update(0, 0)
    assert not clicked and progress == 0.0

    t["now"] += 0.05
    clicked, progress = clicker.update(1, 1)
    assert not clicked
    assert 0.0 < progress < 1.0

    t["now"] += 0.2
    clicked, progress = clicker.update(1, 1)
    assert clicked
    assert progress == 1.0


def test_map_face_to_screen_invert_x():
    cfg = AppConfig(screen_width=1000, screen_height=1000, face_bounds=(0.0, 0.0, 1.0, 1.0), invert_x=True)
    x, y = cfg.map_face_to_screen(0.0, 0.0)
    assert x == 999.0
    assert y == 0.0


def test_face_bounds_from_samples():
    cfg = AppConfig()
    cfg.set_face_bounds_from_samples([(0.4, 0.4), (0.6, 0.4), (0.6, 0.6), (0.4, 0.6), (0.5, 0.5)])
    min_x, min_y, max_x, max_y = cfg.face_bounds
    assert min_x < 0.4
    assert max_x > 0.6
    assert min_y < 0.4
    assert max_y > 0.6
