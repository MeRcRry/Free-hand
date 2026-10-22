"""Anti-jitter cursor smoothing: EMA with optional 1D Kalman filter."""

from __future__ import annotations

from typing import Optional, Tuple


class EMAFilter:
    """Exponential moving average for a single axis."""

    def __init__(self, alpha: float = 0.28) -> None:
        self.alpha = alpha
        self._value: Optional[float] = None

    def reset(self) -> None:
        self._value = None

    def update(self, sample: float) -> float:
        if self._value is None:
            self._value = sample
        else:
            a = max(0.01, min(1.0, self.alpha))
            self._value = a * sample + (1.0 - a) * self._value
        return self._value


class SimpleKalman1D:
    """Lightweight constant-position Kalman for one axis."""

    def __init__(self, process_var: float = 1.2, measure_var: float = 18.0) -> None:
        self.q = process_var
        self.r = measure_var
        self.x: Optional[float] = None
        self.p = 1.0

    def reset(self) -> None:
        self.x = None
        self.p = 1.0

    def update(self, measurement: float) -> float:
        if self.x is None:
            self.x = measurement
            self.p = 1.0
            return self.x
        # Predict
        self.p = self.p + self.q
        # Update
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (measurement - self.x)
        self.p = (1.0 - k) * self.p
        return self.x


class CursorSmoother:
    """Smooth (x, y) before sending to the OS cursor."""

    def __init__(self, alpha: float = 0.28, use_kalman: bool = False) -> None:
        self.alpha = alpha
        self.use_kalman = use_kalman
        self._ema_x = EMAFilter(alpha)
        self._ema_y = EMAFilter(alpha)
        self._k_x = SimpleKalman1D()
        self._k_y = SimpleKalman1D()

    def reset(self) -> None:
        self._ema_x.reset()
        self._ema_y.reset()
        self._k_x.reset()
        self._k_y.reset()

    def update(self, x: float, y: float) -> Tuple[float, float]:
        self._ema_x.alpha = self.alpha
        self._ema_y.alpha = self.alpha
        sx = self._ema_x.update(x)
        sy = self._ema_y.update(y)
        if self.use_kalman:
            sx = self._k_x.update(sx)
            sy = self._k_y.update(sy)
        return sx, sy
