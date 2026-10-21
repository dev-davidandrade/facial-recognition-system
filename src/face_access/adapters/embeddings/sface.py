from pathlib import Path
from threading import Lock

import cv2
import numpy as np

from face_access.domain.models import AlignedFace, DetectedFace, FaceEmbedding, Frame


class SFaceModel:
    """Compartilha uma instância OpenCV entre alinhador e extrator."""

    def __init__(
        self,
        model_path: Path,
        *,
        model_version: str = "opencv-zoo-sface",
    ) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"SFace model not found: {model_path}")
        self._recognizer = cv2.FaceRecognizerSF.create(str(model_path), "")
        self._model_version = model_version
        self._lock = Lock()

    @property
    def model_version(self) -> str:
        return self._model_version

    def align(self, frame: Frame, face: DetectedFace) -> AlignedFace:
        image = _require_array(frame.data, "frame")
        detector_payload = _require_array(face.detector_payload, "detector payload")
        with self._lock:
            aligned = self._recognizer.alignCrop(image, detector_payload)
        return AlignedFace(data=aligned)

    def embed(self, face: AlignedFace) -> FaceEmbedding:
        aligned = _require_array(face.data, "aligned face")
        with self._lock:
            feature = self._recognizer.feature(aligned).reshape(-1).astype(np.float32)
        norm = float(np.linalg.norm(feature))
        if norm == 0.0:
            raise ValueError("SFace produced a zero-norm embedding")
        normalized = feature / norm
        return FaceEmbedding(
            values=tuple(float(value) for value in normalized),
            model_name="sface",
            model_version=self._model_version,
        )


def _require_array(value: object, label: str) -> np.ndarray:
    if not isinstance(value, np.ndarray):
        raise TypeError(f"The {label} must be a NumPy array")
    return value
