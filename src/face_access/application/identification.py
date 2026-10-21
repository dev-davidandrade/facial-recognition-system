from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from face_access.domain.enums import BiometricDecision, PersonStatus
from face_access.domain.models import (
    IdentificationResult,
    ModelDescriptor,
    Person,
    QualityAssessment,
)
from face_access.domain.ports import (
    FaceAligner,
    FaceDetector,
    FaceEmbedder,
    FaceQualityEvaluator,
    FaceTemplateRepository,
    ImageDecoder,
    ModelVersionRepository,
    PersonRepository,
)


@dataclass(frozen=True, slots=True)
class IdentificationThresholds:
    similarity: float
    minimum_margin: float


class IdentificationHandler(Protocol):
    def execute(self, image: bytes, *, source_id: str) -> IdentificationResult: ...


class IdentifyFaceService:
    def __init__(
        self,
        *,
        persons: PersonRepository,
        templates: FaceTemplateRepository,
        model_versions: ModelVersionRepository,
        decoder: ImageDecoder,
        detector: FaceDetector,
        aligner: FaceAligner,
        embedder: FaceEmbedder,
        quality_evaluator: FaceQualityEvaluator,
        model_descriptor: ModelDescriptor,
        thresholds: IdentificationThresholds,
    ) -> None:
        self._persons = persons
        self._templates = templates
        self._model_versions = model_versions
        self._decoder = decoder
        self._detector = detector
        self._aligner = aligner
        self._embedder = embedder
        self._quality_evaluator = quality_evaluator
        self._model_descriptor = model_descriptor
        self._thresholds = thresholds

    def execute(self, image: bytes, *, source_id: str) -> IdentificationResult:
        started_at = perf_counter()
        quality: QualityAssessment | None = None
        try:
            frame = self._decoder.decode(image, source_id=source_id)
            faces = self._detector.detect(frame)
            if not faces:
                return self._result(
                    BiometricDecision.NO_FACE,
                    "no_face_detected",
                    started_at,
                )
            if len(faces) > 1:
                return self._result(
                    BiometricDecision.MULTIPLE_FACES,
                    "multiple_faces_detected",
                    started_at,
                )

            face = faces[0]
            quality = self._quality_evaluator.evaluate(frame, face)
            if not quality.accepted:
                return self._result(
                    BiometricDecision.LOW_QUALITY,
                    "quality_rejected",
                    started_at,
                    quality=quality,
                )

            embedding = self._embedder.embed(self._aligner.align(frame, face))
            if len(embedding.values) != self._model_descriptor.embedding_dimension:
                raise RuntimeError("Embedding dimension does not match the active model")

            model_version_id = self._model_versions.find(self._model_descriptor)
            if model_version_id is None:
                return self._result(
                    BiometricDecision.UNKNOWN,
                    "no_compatible_templates",
                    started_at,
                    quality=quality,
                )

            candidates = self._templates.find_nearest_people(
                embedding,
                model_version_id,
                limit=2,
            )
            if not candidates:
                return self._result(
                    BiometricDecision.UNKNOWN,
                    "no_active_templates",
                    started_at,
                    quality=quality,
                )

            best = candidates[0]
            second_similarity = candidates[1].similarity if len(candidates) > 1 else None
            margin = best.similarity - second_similarity if second_similarity is not None else None
            if best.similarity < self._thresholds.similarity:
                return self._result(
                    BiometricDecision.UNKNOWN,
                    "similarity_below_threshold",
                    started_at,
                    quality=quality,
                    best_similarity=best.similarity,
                    second_best_similarity=second_similarity,
                    score_margin=margin,
                )
            if margin is not None and margin < self._thresholds.minimum_margin:
                return self._result(
                    BiometricDecision.AMBIGUOUS,
                    "candidate_margin_too_small",
                    started_at,
                    quality=quality,
                    best_similarity=best.similarity,
                    second_best_similarity=second_similarity,
                    score_margin=margin,
                )

            person = self._persons.get(best.person_id)
            if person is None or person.status is not PersonStatus.ACTIVE:
                return self._result(
                    BiometricDecision.UNKNOWN,
                    "candidate_not_active",
                    started_at,
                    quality=quality,
                    best_similarity=best.similarity,
                    second_best_similarity=second_similarity,
                    score_margin=margin,
                )
            return self._result(
                BiometricDecision.IDENTIFIED,
                "identification_match",
                started_at,
                quality=quality,
                person=person,
                best_similarity=best.similarity,
                second_best_similarity=second_similarity,
                score_margin=margin,
            )
        except Exception:
            return self._result(
                BiometricDecision.PROCESSING_ERROR,
                "face_processing_failed",
                started_at,
                quality=quality,
            )

    def _result(
        self,
        decision: BiometricDecision,
        reason_code: str,
        started_at: float,
        *,
        quality: QualityAssessment | None = None,
        person: Person | None = None,
        best_similarity: float | None = None,
        second_best_similarity: float | None = None,
        score_margin: float | None = None,
    ) -> IdentificationResult:
        return IdentificationResult(
            biometric_decision=decision,
            person=person,
            best_similarity=best_similarity,
            second_best_similarity=second_best_similarity,
            score_margin=score_margin,
            threshold=self._thresholds.similarity,
            minimum_margin=self._thresholds.minimum_margin,
            reason_code=reason_code,
            detector_version=self._detector.version,
            embedding_model_version=self._embedder.model_version,
            processing_time_ms=(perf_counter() - started_at) * 1000,
            quality=quality,
        )
