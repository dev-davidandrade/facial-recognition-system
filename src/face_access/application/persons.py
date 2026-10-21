from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from face_access.domain.enums import BiometricDecision, PersonStatus
from face_access.domain.models import (
    FaceTemplateCandidate,
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
    UnitOfWork,
)


class PersonServiceError(Exception):
    pass


class ConsentRequiredError(PersonServiceError):
    pass


class PersonNotFoundError(PersonServiceError):
    pass


class PersonNotActiveError(PersonServiceError):
    pass


class DataConflictError(PersonServiceError):
    pass


class InvalidEnrollmentCountError(PersonServiceError):
    def __init__(self, minimum: int, maximum: int) -> None:
        super().__init__(f"Enrollment requires between {minimum} and {maximum} images")
        self.minimum = minimum
        self.maximum = maximum


class EnrollmentRejectedError(PersonServiceError):
    def __init__(
        self,
        *,
        image_index: int,
        decision: BiometricDecision,
        reason_code: str,
        quality: QualityAssessment | None = None,
    ) -> None:
        super().__init__(f"Enrollment image {image_index} rejected: {reason_code}")
        self.image_index = image_index
        self.decision = decision
        self.reason_code = reason_code
        self.quality = quality


@dataclass(frozen=True, slots=True)
class CreatePersonCommand:
    consent_confirmed: bool
    consent_version: str
    external_id: str | None = None
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class EnrollmentResult:
    person_id: UUID
    templates_created: int
    model_version_id: UUID
    embedding_model_version: str
    qualities: tuple[QualityAssessment, ...]


class PersonManagementHandler(Protocol):
    def create(self, command: CreatePersonCommand) -> Person: ...

    def get(self, person_id: UUID) -> Person: ...

    def enroll(
        self,
        person_id: UUID,
        images: tuple[bytes, ...],
        *,
        source_id: str,
    ) -> EnrollmentResult: ...

    def revoke(self, person_id: UUID) -> None: ...


class PersonManagementService:
    def __init__(
        self,
        *,
        persons: PersonRepository,
        templates: FaceTemplateRepository,
        model_versions: ModelVersionRepository,
        unit_of_work: UnitOfWork,
        decoder: ImageDecoder,
        detector: FaceDetector,
        aligner: FaceAligner,
        embedder: FaceEmbedder,
        quality_evaluator: FaceQualityEvaluator,
        model_descriptor: ModelDescriptor,
        minimum_enrollment_images: int,
        maximum_enrollment_images: int,
    ) -> None:
        self._persons = persons
        self._templates = templates
        self._model_versions = model_versions
        self._unit_of_work = unit_of_work
        self._decoder = decoder
        self._detector = detector
        self._aligner = aligner
        self._embedder = embedder
        self._quality_evaluator = quality_evaluator
        self._model_descriptor = model_descriptor
        self._minimum_enrollment_images = minimum_enrollment_images
        self._maximum_enrollment_images = maximum_enrollment_images

    def create(self, command: CreatePersonCommand) -> Person:
        if not command.consent_confirmed:
            raise ConsentRequiredError("Explicit consent is required")
        now = datetime.now(UTC)
        person = Person(
            id=uuid4(),
            status=PersonStatus.ACTIVE,
            consent_at=now,
            consent_version=command.consent_version,
            external_id=command.external_id,
            display_name=command.display_name,
            created_at=now,
            updated_at=now,
        )
        try:
            self._persons.add(person)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise
        return person

    def get(self, person_id: UUID) -> Person:
        person = self._persons.get(person_id)
        if person is None:
            raise PersonNotFoundError(f"Person not found: {person_id}")
        return person

    def enroll(
        self,
        person_id: UUID,
        images: tuple[bytes, ...],
        *,
        source_id: str,
    ) -> EnrollmentResult:
        if not self._minimum_enrollment_images <= len(images) <= self._maximum_enrollment_images:
            raise InvalidEnrollmentCountError(
                self._minimum_enrollment_images,
                self._maximum_enrollment_images,
            )
        person = self.get(person_id)
        if person.status is not PersonStatus.ACTIVE:
            raise PersonNotActiveError(f"Person is not active: {person_id}")

        candidates: list[FaceTemplateCandidate] = []
        try:
            for index, image in enumerate(images):
                frame = self._decoder.decode(image, source_id=source_id)
                faces = self._detector.detect(frame)
                if not faces:
                    raise EnrollmentRejectedError(
                        image_index=index,
                        decision=BiometricDecision.NO_FACE,
                        reason_code="no_face_detected",
                    )
                if len(faces) > 1:
                    raise EnrollmentRejectedError(
                        image_index=index,
                        decision=BiometricDecision.MULTIPLE_FACES,
                        reason_code="multiple_faces_detected",
                    )
                face = faces[0]
                quality = self._quality_evaluator.evaluate(frame, face)
                if not quality.accepted:
                    raise EnrollmentRejectedError(
                        image_index=index,
                        decision=BiometricDecision.LOW_QUALITY,
                        reason_code="quality_rejected",
                        quality=quality,
                    )
                embedding = self._embedder.embed(self._aligner.align(frame, face))
                if len(embedding.values) != self._model_descriptor.embedding_dimension:
                    raise RuntimeError("Embedding dimension does not match the active model")
                candidates.append(FaceTemplateCandidate(embedding, quality))

            model_version_id = self._model_versions.get_or_create(self._model_descriptor)
            self._templates.add_many(person_id, model_version_id, candidates)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise

        return EnrollmentResult(
            person_id=person_id,
            templates_created=len(candidates),
            model_version_id=model_version_id,
            embedding_model_version=self._embedder.model_version,
            qualities=tuple(candidate.quality for candidate in candidates),
        )

    def revoke(self, person_id: UUID) -> None:
        self.get(person_id)
        try:
            self._persons.revoke(person_id)
            self._templates.deactivate_for_person(person_id)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise
