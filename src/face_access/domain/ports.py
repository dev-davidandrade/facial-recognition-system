from collections.abc import Iterable, Sequence
from typing import Protocol
from uuid import UUID

from face_access.domain.enums import BiometricDecision
from face_access.domain.models import (
    AccessDecisionEvent,
    AlignedFace,
    AuthorizationResult,
    DetectedFace,
    FaceEmbedding,
    FaceTemplateCandidate,
    FaceTemplateMatch,
    Frame,
    ModelDescriptor,
    Person,
    QualityAssessment,
)


class ImageDecoder(Protocol):
    def decode(self, encoded_image: bytes, *, source_id: str) -> Frame: ...


class FaceDetector(Protocol):
    @property
    def version(self) -> str: ...

    def detect(self, frame: Frame) -> Sequence[DetectedFace]: ...


class FaceAligner(Protocol):
    def align(self, frame: Frame, face: DetectedFace) -> AlignedFace: ...


class FaceEmbedder(Protocol):
    @property
    def model_version(self) -> str: ...

    def embed(self, face: AlignedFace) -> FaceEmbedding: ...


class FaceMatcher(Protocol):
    def similarity(self, first: FaceEmbedding, second: FaceEmbedding) -> float: ...


class FaceQualityEvaluator(Protocol):
    def evaluate(self, frame: Frame, face: DetectedFace) -> QualityAssessment: ...


class LivenessDetector(Protocol):
    def is_live(self, frame: Frame, face: DetectedFace) -> bool: ...


class PersonRepository(Protocol):
    def get(self, person_id: UUID) -> Person | None: ...

    def add(self, person: Person) -> None: ...

    def revoke(self, person_id: UUID) -> bool: ...


class FaceTemplateRepository(Protocol):
    def add_many(
        self,
        person_id: UUID,
        model_version_id: UUID,
        templates: Sequence[FaceTemplateCandidate],
    ) -> None: ...

    def deactivate_for_person(self, person_id: UUID) -> None: ...

    def find_nearest_people(
        self,
        embedding: FaceEmbedding,
        model_version_id: UUID,
        *,
        limit: int,
    ) -> Sequence[FaceTemplateMatch]: ...


class ModelVersionRepository(Protocol):
    def get_or_create(self, descriptor: ModelDescriptor) -> UUID: ...

    def find(self, descriptor: ModelDescriptor) -> UUID | None: ...


class RecognitionEventRepository(Protocol):
    def add(self, event: AccessDecisionEvent) -> None: ...


class AuthorizationPolicy(Protocol):
    def decide(
        self,
        person: Person | None,
        biometric_decision: BiometricDecision,
    ) -> AuthorizationResult: ...


class FrameSource(Protocol):
    def frames(self) -> Iterable[Frame]: ...


class DecisionPublisher(Protocol):
    def publish(self, event: AccessDecisionEvent) -> None: ...


class UnitOfWork(Protocol):
    def commit(self) -> None: ...

    def rollback(self) -> None: ...
