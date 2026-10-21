from collections.abc import Sequence

import pytest

from face_access.application.verification import CompareFacesUseCase, VerificationThresholds
from face_access.domain.enums import BiometricDecision
from face_access.domain.models import (
    AlignedFace,
    BoundingBox,
    DetectedFace,
    FaceEmbedding,
    Frame,
    QualityAssessment,
)
from face_access.domain.services import CosineFaceMatcher

GOOD_FACE = DetectedFace(BoundingBox(0, 0, 120, 120), (), 0.99)
GOOD_QUALITY = QualityAssessment(True, 0.9, 120, 150, 120)
BAD_QUALITY = QualityAssessment(False, 0.2, 30, 10, 20, ("face_too_small",))


class FakeDetector:
    version = "fake-detector-v1"

    def __init__(self, detections: dict[str, Sequence[DetectedFace]]) -> None:
        self._detections = detections

    def detect(self, frame: Frame) -> Sequence[DetectedFace]:
        return self._detections[frame.source_id]


class FakeAligner:
    def align(self, frame: Frame, face: DetectedFace) -> AlignedFace:
        return AlignedFace(frame.data)


class FakeEmbedder:
    model_version = "fake-embedder-v1"

    def embed(self, face: AlignedFace) -> FaceEmbedding:
        assert isinstance(face.data, tuple)
        return FaceEmbedding(face.data, "fake", self.model_version)


class FakeQualityEvaluator:
    def __init__(self, assessments: dict[str, QualityAssessment] | None = None) -> None:
        self._assessments = assessments or {}

    def evaluate(self, frame: Frame, face: DetectedFace) -> QualityAssessment:
        return self._assessments.get(frame.source_id, GOOD_QUALITY)


def make_use_case(
    detections: dict[str, Sequence[DetectedFace]],
    assessments: dict[str, QualityAssessment] | None = None,
) -> CompareFacesUseCase:
    return CompareFacesUseCase(
        detector=FakeDetector(detections),
        aligner=FakeAligner(),
        embedder=FakeEmbedder(),
        matcher=CosineFaceMatcher(),
        quality_evaluator=FakeQualityEvaluator(assessments),
        thresholds=VerificationThresholds(similarity=0.8),
    )


def frame(source_id: str, values: tuple[float, ...]) -> Frame:
    return Frame(data=values, width=200, height=200, source_id=source_id)


def test_verification_accepts_matching_embeddings() -> None:
    use_case = make_use_case({"first": (GOOD_FACE,), "second": (GOOD_FACE,)})

    result = use_case.execute(frame("first", (1.0, 0.0)), frame("second", (0.9, 0.1)))

    assert result.biometric_decision is BiometricDecision.IDENTIFIED
    assert result.is_match is True
    assert result.similarity == pytest.approx(0.993883, abs=1e-6)


def test_verification_rejects_unknown() -> None:
    use_case = make_use_case({"first": (GOOD_FACE,), "second": (GOOD_FACE,)})

    result = use_case.execute(frame("first", (1.0, 0.0)), frame("second", (0.0, 1.0)))

    assert result.biometric_decision is BiometricDecision.UNKNOWN
    assert result.is_match is False


@pytest.mark.parametrize(
    ("faces", "decision"),
    [
        ((), BiometricDecision.NO_FACE),
        ((GOOD_FACE, GOOD_FACE), BiometricDecision.MULTIPLE_FACES),
    ],
)
def test_verification_rejects_invalid_face_count(
    faces: Sequence[DetectedFace],
    decision: BiometricDecision,
) -> None:
    use_case = make_use_case({"first": faces, "second": (GOOD_FACE,)})

    result = use_case.execute(frame("first", (1.0, 0.0)), frame("second", (1.0, 0.0)))

    assert result.biometric_decision is decision
    assert result.is_match is None


def test_verification_rejects_low_quality_face() -> None:
    use_case = make_use_case(
        {"first": (GOOD_FACE,), "second": (GOOD_FACE,)},
        {"first": BAD_QUALITY},
    )

    result = use_case.execute(frame("first", (1.0, 0.0)), frame("second", (1.0, 0.0)))

    assert result.biometric_decision is BiometricDecision.LOW_QUALITY
    assert result.reason_code == "first_image_quality_rejected"
