from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from face_access.application.persons import EnrollmentResult
from face_access.domain.enums import BiometricDecision, PersonStatus
from face_access.domain.models import (
    IdentificationResult,
    Person,
    QualityAssessment,
    VerificationResult,
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


class TemporalPolicyResponse(BaseModel):
    confirmations_required: int
    window_size: int
    max_gap_ms: int
    review_after_ms: int
    frame_interval_ms: int


class CreatePersonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_confirmed: bool
    consent_version: str = Field(min_length=1, max_length=64)
    external_id: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)


class PersonResponse(BaseModel):
    id: UUID
    external_id: str | None
    display_name: str | None
    status: PersonStatus
    consent_at: datetime
    consent_version: str
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, person: Person) -> "PersonResponse":
        return cls(
            id=person.id,
            external_id=person.external_id,
            display_name=person.display_name,
            status=person.status,
            consent_at=person.consent_at,
            consent_version=person.consent_version,
            revoked_at=person.revoked_at,
            created_at=person.created_at,
            updated_at=person.updated_at,
        )


class QualityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    accepted: bool
    score: float
    face_size_px: float
    blur_score: float
    brightness: float
    reasons: tuple[str, ...]

    @classmethod
    def from_domain(cls, quality: QualityAssessment | None) -> "QualityResponse | None":
        if quality is None:
            return None
        return cls(
            accepted=quality.accepted,
            score=quality.score,
            face_size_px=quality.face_size_px,
            blur_score=quality.blur_score,
            brightness=quality.brightness,
            reasons=quality.reasons,
        )


class VerificationResponse(BaseModel):
    transaction_id: UUID
    biometric_decision: BiometricDecision
    is_match: bool | None
    similarity: float | None
    threshold: float
    reason_code: str
    first_quality: QualityResponse | None
    second_quality: QualityResponse | None
    detector_version: str
    embedding_model_version: str
    processing_time_ms: float
    timestamp: datetime

    @classmethod
    def from_domain(cls, result: VerificationResult) -> "VerificationResponse":
        return cls(
            transaction_id=result.transaction_id,
            biometric_decision=result.biometric_decision,
            is_match=result.is_match,
            similarity=result.similarity,
            threshold=result.threshold,
            reason_code=result.reason_code,
            first_quality=QualityResponse.from_domain(result.first_quality),
            second_quality=QualityResponse.from_domain(result.second_quality),
            detector_version=result.detector_version,
            embedding_model_version=result.embedding_model_version,
            processing_time_ms=result.processing_time_ms,
            timestamp=result.timestamp,
        )


class IdentificationResponse(BaseModel):
    transaction_id: UUID
    biometric_decision: BiometricDecision
    person_id: UUID | None
    external_id: str | None
    display_name: str | None
    best_similarity: float | None
    second_best_similarity: float | None
    score_margin: float | None
    threshold: float
    minimum_margin: float
    reason_code: str
    quality: QualityResponse | None
    detector_version: str
    embedding_model_version: str
    processing_time_ms: float
    timestamp: datetime

    @classmethod
    def from_domain(cls, result: IdentificationResult) -> "IdentificationResponse":
        return cls(
            transaction_id=result.transaction_id,
            biometric_decision=result.biometric_decision,
            person_id=result.person.id if result.person is not None else None,
            external_id=result.person.external_id if result.person is not None else None,
            display_name=result.person.display_name if result.person is not None else None,
            best_similarity=result.best_similarity,
            second_best_similarity=result.second_best_similarity,
            score_margin=result.score_margin,
            threshold=result.threshold,
            minimum_margin=result.minimum_margin,
            reason_code=result.reason_code,
            quality=QualityResponse.from_domain(result.quality),
            detector_version=result.detector_version,
            embedding_model_version=result.embedding_model_version,
            processing_time_ms=result.processing_time_ms,
            timestamp=result.timestamp,
        )


class EnrollmentRejectionResponse(BaseModel):
    image_index: int
    biometric_decision: BiometricDecision
    reason_code: str
    quality: QualityResponse | None


class EnrollmentResponse(BaseModel):
    person_id: UUID
    templates_created: int
    images_received: int
    images_rejected: int
    model_version_id: UUID
    embedding_model_version: str
    qualities: tuple[QualityResponse, ...]
    rejections: tuple[EnrollmentRejectionResponse, ...]

    @classmethod
    def from_domain(cls, result: EnrollmentResult) -> "EnrollmentResponse":
        return cls(
            person_id=result.person_id,
            templates_created=result.templates_created,
            images_received=result.images_received,
            images_rejected=len(result.rejections),
            model_version_id=result.model_version_id,
            embedding_model_version=result.embedding_model_version,
            qualities=tuple(
                quality_response
                for quality in result.qualities
                if (quality_response := QualityResponse.from_domain(quality)) is not None
            ),
            rejections=tuple(
                EnrollmentRejectionResponse(
                    image_index=rejection.image_index,
                    biometric_decision=rejection.decision,
                    reason_code=rejection.reason_code,
                    quality=QualityResponse.from_domain(rejection.quality),
                )
                for rejection in result.rejections
            ),
        )
