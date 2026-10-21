import cv2
import numpy as np
import pytest

from face_access.adapters.image_decoder import InvalidImageError, OpenCVImageDecoder
from face_access.adapters.quality import OpenCVFaceQualityEvaluator
from face_access.domain.models import BoundingBox, DetectedFace, Frame


def test_decoder_decodes_an_image_in_memory() -> None:
    image = np.full((20, 30, 3), 127, dtype=np.uint8)
    success, encoded = cv2.imencode(".png", image)
    assert success
    decoder = OpenCVImageDecoder(max_bytes=10_000, max_pixels=1_000)

    frame = decoder.decode(encoded.tobytes(), source_id="test")

    assert frame.width == 30
    assert frame.height == 20
    assert frame.source_id == "test"


@pytest.mark.parametrize("content", [b"", b"not-an-image"])
def test_decoder_rejects_invalid_content(content: bytes) -> None:
    decoder = OpenCVImageDecoder(max_bytes=10_000, max_pixels=1_000)

    with pytest.raises(InvalidImageError):
        decoder.decode(content, source_id="test")


def test_quality_rejects_small_dark_blurry_face() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    frame = Frame(image, width=100, height=100)
    face = DetectedFace(BoundingBox(10, 10, 30, 30), (), 0.99)
    evaluator = OpenCVFaceQualityEvaluator(
        min_face_size_px=80,
        min_blur_score=80,
        min_brightness=45,
        max_brightness=210,
    )

    result = evaluator.evaluate(frame, face)

    assert result.accepted is False
    assert set(result.reasons) == {"face_too_small", "image_too_blurry", "image_too_dark"}
