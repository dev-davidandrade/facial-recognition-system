import cv2
import numpy as np

from face_access.domain.models import DetectedFace, Frame, QualityAssessment


class OpenCVFaceQualityEvaluator:
    def __init__(
        self,
        *,
        min_face_size_px: int,
        min_blur_score: float,
        min_brightness: float,
        max_brightness: float,
    ) -> None:
        self._min_face_size_px = min_face_size_px
        self._min_blur_score = min_blur_score
        self._min_brightness = min_brightness
        self._max_brightness = max_brightness

    def evaluate(self, frame: Frame, face: DetectedFace) -> QualityAssessment:
        image = _require_image(frame.data)
        box = face.bounding_box
        x1 = max(0, int(box.x))
        y1 = max(0, int(box.y))
        x2 = min(frame.width, int(box.x + box.width))
        y2 = min(frame.height, int(box.y + box.height))
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return QualityAssessment(False, 0.0, box.shortest_side, 0.0, 0.0, ("empty_crop",))

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(gray.mean())
        reasons: list[str] = []
        if box.shortest_side < self._min_face_size_px:
            reasons.append("face_too_small")
        if blur_score < self._min_blur_score:
            reasons.append("image_too_blurry")
        if brightness < self._min_brightness:
            reasons.append("image_too_dark")
        if brightness > self._max_brightness:
            reasons.append("image_too_bright")

        size_component = min(1.0, box.shortest_side / self._min_face_size_px)
        blur_component = min(1.0, blur_score / self._min_blur_score)
        light_midpoint = (self._min_brightness + self._max_brightness) / 2
        light_half_range = (self._max_brightness - self._min_brightness) / 2
        light_component = max(0.0, 1.0 - abs(brightness - light_midpoint) / light_half_range)
        score = (size_component + blur_component + light_component) / 3
        return QualityAssessment(
            accepted=not reasons,
            score=score,
            face_size_px=box.shortest_side,
            blur_score=blur_score,
            brightness=brightness,
            reasons=tuple(reasons),
        )


def _require_image(value: object) -> np.ndarray:
    if not isinstance(value, np.ndarray):
        raise TypeError("The frame data must be a NumPy array")
    return value
