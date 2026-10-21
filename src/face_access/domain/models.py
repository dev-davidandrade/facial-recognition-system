from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from face_access.domain.enums import (
    AuthorizationDecision,
    BiometricDecision,
    LicenseStatus,
    PersonStatus,
)

type Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    @property
    def shortest_side(self) -> float:
        return min(self.width, self.height)


@dataclass(frozen=True, slots=True)
class Frame:
    """Quadro desacoplado da representação concreta (por exemplo, ndarray)."""

    data: object
    width: int
    height: int
    source_id: str = "api-upload"


@dataclass(frozen=True, slots=True)
class DetectedFace:
    bounding_box: BoundingBox
    landmarks: tuple[Point, ...]
    confidence: float
    detector_payload: object | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class AlignedFace:
    data: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class FaceEmbedding:
    values: tuple[float, ...] = field(repr=False)
    model_name: str
    model_version: str

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("An embedding cannot be empty")


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    accepted: bool
    score: float
    face_size_px: float
    blur_score: float
    brightness: float
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Person:
    id: UUID
    status: PersonStatus
    consent_at: datetime
    consent_version: str
    external_id: str | None = None
    display_name: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    detector_name: str
    detector_version: str
    embedder_name: str
    embedder_version: str
    embedding_dimension: int
    model_checksum: str
    license_status: LicenseStatus


@dataclass(frozen=True, slots=True)
class FaceTemplateCandidate:
    embedding: FaceEmbedding
    quality: QualityAssessment


@dataclass(frozen=True, slots=True)
class FaceTemplateMatch:
    person_id: UUID
    similarity: float


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    decision: AuthorizationDecision
    reason_code: str


@dataclass(frozen=True, slots=True)
class AccessDecisionEvent:
    correlation_id: UUID
    decision: AuthorizationDecision
    person_id: UUID | None
    reason: str
    confidence: float | None
    model_version: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_type: str = "access_decision"


@dataclass(frozen=True, slots=True)
class VerificationResult:
    biometric_decision: BiometricDecision
    is_match: bool | None
    similarity: float | None
    threshold: float
    reason_code: str
    detector_version: str
    embedding_model_version: str
    processing_time_ms: float
    first_quality: QualityAssessment | None = None
    second_quality: QualityAssessment | None = None
    transaction_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class IdentificationResult:
    biometric_decision: BiometricDecision
    person: Person | None
    best_similarity: float | None
    second_best_similarity: float | None
    score_margin: float | None
    threshold: float
    minimum_margin: float
    reason_code: str
    detector_version: str
    embedding_model_version: str
    processing_time_ms: float
    quality: QualityAssessment | None = None
    transaction_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
