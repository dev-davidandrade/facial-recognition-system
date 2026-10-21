from pathlib import Path
from threading import Lock

import cv2
import numpy as np

from face_access.domain.models import BoundingBox, DetectedFace, Frame


class YuNetFaceDetector:
    def __init__(
        self,
        model_path: Path,
        *,
        score_threshold: float,
        model_version: str = "opencv-zoo-yunet",
    ) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"YuNet model not found: {model_path}")
        self._model_version = model_version
        self._lock = Lock()
        self._detector = cv2.FaceDetectorYN.create(
            str(model_path),
            "",
            (320, 320),
            score_threshold,
            0.3,
            5000,
        )

    @property
    def version(self) -> str:
        return self._model_version

    def detect(self, frame: Frame) -> tuple[DetectedFace, ...]:
        image = _require_image(frame.data)
        with self._lock:
            self._detector.setInputSize((frame.width, frame.height))
            _, raw_faces = self._detector.detect(image)
        if raw_faces is None:
            return ()

        detected: list[DetectedFace] = []
        for raw_face in raw_faces:
            values = raw_face.astype(np.float32, copy=True)
            landmarks = tuple(
                (float(values[index]), float(values[index + 1])) for index in range(4, 14, 2)
            )
            detected.append(
                DetectedFace(
                    bounding_box=BoundingBox(
                        x=float(values[0]),
                        y=float(values[1]),
                        width=float(values[2]),
                        height=float(values[3]),
                    ),
                    landmarks=landmarks,
                    confidence=float(values[14]),
                    detector_payload=values,
                )
            )
        return tuple(detected)


def _require_image(value: object) -> np.ndarray:
    if not isinstance(value, np.ndarray):
        raise TypeError("The frame data must be a NumPy array")
    return value
