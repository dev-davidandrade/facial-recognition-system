import cv2
import numpy as np

from face_access.domain.models import Frame


class InvalidImageError(ValueError):
    pass


class OpenCVImageDecoder:
    def __init__(self, *, max_bytes: int, max_pixels: int) -> None:
        self._max_bytes = max_bytes
        self._max_pixels = max_pixels

    def decode(self, encoded_image: bytes, *, source_id: str) -> Frame:
        if not encoded_image:
            raise InvalidImageError("The image is empty")
        if len(encoded_image) > self._max_bytes:
            raise InvalidImageError("The image exceeds the configured size limit")

        buffer = np.frombuffer(encoded_image, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidImageError("The uploaded content is not a decodable image")
        height, width = image.shape[:2]
        if width * height > self._max_pixels:
            raise InvalidImageError("The decoded image exceeds the configured resolution limit")
        return Frame(data=image, width=int(width), height=int(height), source_id=source_id)
