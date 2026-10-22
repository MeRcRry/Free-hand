"""Webcam and IP-camera video sources."""

from __future__ import annotations

from typing import Optional, Tuple, Union

import numpy as np

Frame = Optional[np.ndarray]


class CameraSource:
    """Thin wrapper around cv2.VideoCapture with probe helpers."""

    def __init__(
        self,
        source: Union[int, str] = 0,
        *,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
    ) -> None:
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self._cap = None
        self._cv2 = None

    @staticmethod
    def probe_webcam(index: int = 0, timeout_frames: int = 8) -> bool:
        """Return True if a local webcam at *index* can deliver a frame."""
        try:
            import cv2
        except ImportError:
            return False

        cap = None
        try:
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                return False
            # Give the device a moment; some drivers need a few grabs.
            for _ in range(timeout_frames):
                ok, frame = cap.read()
                if ok and frame is not None:
                    return True
            return False
        except Exception:  # noqa: BLE001
            return False
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:  # noqa: BLE001
                    pass

    def open(self) -> bool:
        try:
            import cv2

            self._cv2 = cv2
        except ImportError:
            return False

        try:
            self._cap = self._cv2.VideoCapture(self.source)
            if not self._cap.isOpened():
                self.close()
                return False
            self._cap.set(self._cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(self._cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cap.set(self._cv2.CAP_PROP_FPS, self.fps)
            return True
        except Exception:  # noqa: BLE001
            self.close()
            return False

    def read(self) -> Tuple[bool, Frame]:
        if self._cap is None:
            return False, None
        try:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                return False, None
            return True, frame
        except Exception:  # noqa: BLE001
            return False, None

    def close(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:  # noqa: BLE001
                pass
        self._cap = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()
