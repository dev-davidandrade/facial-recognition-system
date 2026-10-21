from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from face_access.domain.enums import BiometricDecision
from face_access.domain.models import FaceEmbedding, Frame, QualityAssessment, VerificationResult
from face_access.domain.ports import (
    FaceAligner,
    FaceDetector,
    FaceEmbedder,
    FaceMatcher,
    FaceQualityEvaluator,
    ImageDecoder,
)


@dataclass(frozen=True, slots=True)
class VerificationThresholds:
    similarity: float


@dataclass(frozen=True, slots=True)
class _PreparedFace:
    embedding: FaceEmbedding | None
    quality: QualityAssessment | None
    rejection: BiometricDecision | None
    reason: str | None


class VerificationHandler(Protocol):
    def execute(
        self,
        first_image: bytes,
        second_image: bytes,
        *,
        source_id: str,
    ) -> VerificationResult: ...


class CompareFacesUseCase:
    def __init__(
        self,
        detector: FaceDetector,
        aligner: FaceAligner,
        embedder: FaceEmbedder,
        matcher: FaceMatcher,
        quality_evaluator: FaceQualityEvaluator,
        thresholds: VerificationThresholds,
    ) -> None:
        self._detector = detector
        self._aligner = aligner
        self._embedder = embedder
        self._matcher = matcher
        self._quality_evaluator = quality_evaluator
        self._thresholds = thresholds

    def execute(self, first: Frame, second: Frame) -> VerificationResult:
        started_at = perf_counter()
        try:
            first_face = self._prepare(first)
            if first_face.rejection is not None:
                return self._rejected(first_face, None, started_at, "first_image")

            second_face = self._prepare(second)
            if second_face.rejection is not None:
                return self._rejected(first_face, second_face, started_at, "second_image")

            if first_face.embedding is None or second_face.embedding is None:
                raise RuntimeError("Face preparation completed without an embedding")
            similarity = self._matcher.similarity(first_face.embedding, second_face.embedding)
            is_match = similarity >= self._thresholds.similarity
            return VerificationResult(
                biometric_decision=(
                    BiometricDecision.IDENTIFIED if is_match else BiometricDecision.UNKNOWN
                ),
                is_match=is_match,
                similarity=similarity,
                threshold=self._thresholds.similarity,
                reason_code=("verification_match" if is_match else "similarity_below_threshold"),
                detector_version=self._detector.version,
                embedding_model_version=self._embedder.model_version,
                processing_time_ms=(perf_counter() - started_at) * 1000,
                first_quality=first_face.quality,
                second_quality=second_face.quality,
            )
        except Exception:
            return VerificationResult(
                biometric_decision=BiometricDecision.PROCESSING_ERROR,
                is_match=None,
                similarity=None,
                threshold=self._thresholds.similarity,
                reason_code="face_processing_failed",
                detector_version=self._detector.version,
                embedding_model_version=self._embedder.model_version,
                processing_time_ms=(perf_counter() - started_at) * 1000,
            )

    def _prepare(self, frame: Frame) -> _PreparedFace:
        faces = self._detector.detect(frame)
        if not faces:
            return _PreparedFace(None, None, BiometricDecision.NO_FACE, "no_face_detected")
        if len(faces) > 1:
            return _PreparedFace(
                None,
                None,
                BiometricDecision.MULTIPLE_FACES,
                "multiple_faces_detected",
            )

        face = faces[0]
        quality = self._quality_evaluator.evaluate(frame, face)
        if not quality.accepted:
            return _PreparedFace(None, quality, BiometricDecision.LOW_QUALITY, "quality_rejected")
        aligned = self._aligner.align(frame, face)
        return _PreparedFace(self._embedder.embed(aligned), quality, None, None)

    def _rejected(
        self,
        first: _PreparedFace,
        second: _PreparedFace | None,
        started_at: float,
        image_label: str,
    ) -> VerificationResult:
        rejected = first if image_label == "first_image" else second
        if rejected is None or rejected.rejection is None or rejected.reason is None:
            raise RuntimeError("Invalid rejection state")
        return VerificationResult(
            biometric_decision=rejected.rejection,
            is_match=None,
            similarity=None,
            threshold=self._thresholds.similarity,
            reason_code=f"{image_label}_{rejected.reason}",
            detector_version=self._detector.version,
            embedding_model_version=self._embedder.model_version,
            processing_time_ms=(perf_counter() - started_at) * 1000,
            first_quality=first.quality,
            second_quality=second.quality if second is not None else None,
        )


class EncodedImageVerificationService:
    def __init__(self, decoder: ImageDecoder, comparison: CompareFacesUseCase) -> None:
        self._decoder = decoder
        self._comparison = comparison

    def execute(
        self,
        first_image: bytes,
        second_image: bytes,
        *,
        source_id: str,
    ) -> VerificationResult:
        first = self._decoder.decode(first_image, source_id=source_id)
        second = self._decoder.decode(second_image, source_id=source_id)
        return self._comparison.execute(first, second)
