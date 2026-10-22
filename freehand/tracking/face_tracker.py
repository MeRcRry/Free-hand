"""MediaPipe Face Mesh landmark extraction (nose tip or mid-eyes)."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

# MediaPipe Face Mesh landmark indices
NOSE_TIP = 1
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 362
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263


class FaceTracker:
    """
    Extract a stable head-control point from Face Mesh.

    Uses nose tip or the midpoint between the inner eye corners —
    head pose, not pupil gaze.
    """

    def __init__(self, landmark_mode: str = "nose") -> None:
        self.landmark_mode = landmark_mode
        self._mp = None
        self._face_mesh = None
        self._available = False
        self._init_mediapipe()

    def _init_mediapipe(self) -> None:
        try:
            import mediapipe as mp

            self._mp = mp
            self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._available = True
        except Exception:  # noqa: BLE001
            self._available = False
            self._face_mesh = None

    @property
    def available(self) -> bool:
        return self._available

    def process(self, frame_bgr: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        Return normalized (x, y) in [0, 1] image space, or None if no face.
        Coordinates are in the original (unmirrored) camera frame.
        """
        if not self._available or self._face_mesh is None or frame_bgr is None:
            return None

        try:
            import cv2

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            result = self._face_mesh.process(rgb)
        except Exception:  # noqa: BLE001
            return None

        if not result.multi_face_landmarks:
            return None

        lm = result.multi_face_landmarks[0].landmark
        mode = (self.landmark_mode or "nose").lower()
        if mode == "mid_eyes":
            a = lm[LEFT_EYE_INNER]
            b = lm[RIGHT_EYE_INNER]
            return (a.x + b.x) * 0.5, (a.y + b.y) * 0.5

        tip = lm[NOSE_TIP]
        return tip.x, tip.y

    def close(self) -> None:
        if self._face_mesh is not None:
            try:
                self._face_mesh.close()
            except Exception:  # noqa: BLE001
                pass
        self._face_mesh = None
