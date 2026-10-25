from collections.abc import Sequence
from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from face_access.application.persons import (
    ConsentRequiredError,
    CreatePersonCommand,
    EnrollmentRejectedError,
    PersonManagementService,
)
from face_access.domain.enums import LicenseStatus, PersonStatus
from face_access.domain.models import (
    AlignedFace,
    BoundingBox,
    DetectedFace,
    FaceEmbedding,
    FaceTemplateCandidate,
    FaceTemplateMatch,
    Frame,
    ModelDescriptor,
    Person,
    QualityAssessment,
)

GOOD_FACE = DetectedFace(BoundingBox(0, 0, 120, 120), (), 0.99)
GOOD_QUALITY = QualityAssessment(True, 0.9, 120, 150, 120)
BAD_QUALITY = QualityAssessment(False, 0.2, 120, 20, 120, ("image_too_blurry",))


class MemoryPersonRepository:
    def __init__(self) -> None:
        self.people: dict[UUID, Person] = {}

    def get(self, person_id: UUID) -> Person | None:
        return self.people.get(person_id)

    def add(self, person: Person) -> None:
        self.people[person.id] = person

    def revoke(self, person_id: UUID) -> bool:
        person = self.people.get(person_id)
        if person is None:
            return False
        self.people[person_id] = replace(person, status=PersonStatus.REVOKED)
        return True


class MemoryTemplateRepository:
    def __init__(self) -> None:
        self.templates: list[FaceTemplateCandidate] = []
        self.deactivated_people: list[UUID] = []

    def add_many(
        self,
        person_id: UUID,
        model_version_id: UUID,
        templates: Sequence[FaceTemplateCandidate],
    ) -> None:
        self.templates.extend(templates)

    def deactivate_for_person(self, person_id: UUID) -> None:
        self.deactivated_people.append(person_id)

    def find_nearest_people(
        self,
        embedding: FaceEmbedding,
        model_version_id: UUID,
        *,
        limit: int,
    ) -> Sequence[FaceTemplateMatch]:
        return ()


class MemoryModelVersionRepository:
    def __init__(self) -> None:
        self.id = uuid4()

    def get_or_create(self, descriptor: ModelDescriptor) -> UUID:
        return self.id

    def find(self, descriptor: ModelDescriptor) -> UUID | None:
        return self.id


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeDecoder:
    def decode(self, encoded_image: bytes, *, source_id: str) -> Frame:
        return Frame(encoded_image, 200, 200, source_id)


class FakeDetector:
    version = "detector-v1"

    def detect(self, frame: Frame) -> Sequence[DetectedFace]:
        if frame.data == b"no-face":
            return ()
        if frame.data == b"multiple":
            return (GOOD_FACE, GOOD_FACE)
        return (GOOD_FACE,)


class FakeAligner:
    def align(self, frame: Frame, face: DetectedFace) -> AlignedFace:
        return AlignedFace(frame.data)


class FakeEmbedder:
    model_version = "embedder-v1"

    def embed(self, face: AlignedFace) -> FaceEmbedding:
        return FaceEmbedding((1.0,) * 128, "fake", self.model_version)


class FakeQualityEvaluator:
    def evaluate(self, frame: Frame, face: DetectedFace) -> QualityAssessment:
        return BAD_QUALITY if frame.data == b"bad-quality" else GOOD_QUALITY


def make_service() -> tuple[
    PersonManagementService,
    MemoryPersonRepository,
    MemoryTemplateRepository,
    FakeUnitOfWork,
]:
    people = MemoryPersonRepository()
    templates = MemoryTemplateRepository()
    unit_of_work = FakeUnitOfWork()
    descriptor = ModelDescriptor(
        detector_name="fake",
        detector_version="detector-v1",
        embedder_name="fake",
        embedder_version="embedder-v1",
        embedding_dimension=128,
        model_checksum="a" * 64,
        license_status=LicenseStatus.RESEARCH_ONLY,
    )
    service = PersonManagementService(
        persons=people,
        templates=templates,
        model_versions=MemoryModelVersionRepository(),
        unit_of_work=unit_of_work,
        decoder=FakeDecoder(),
        detector=FakeDetector(),
        aligner=FakeAligner(),
        embedder=FakeEmbedder(),
        quality_evaluator=FakeQualityEvaluator(),
        model_descriptor=descriptor,
        minimum_enrollment_images=2,
        maximum_enrollment_images=10,
    )
    return service, people, templates, unit_of_work


def test_create_requires_explicit_consent() -> None:
    service, _, _, _ = make_service()

    with pytest.raises(ConsentRequiredError):
        service.create(CreatePersonCommand(False, "v1"))


def test_create_and_enroll_multiple_templates_atomically() -> None:
    service, _, templates, unit_of_work = make_service()
    person = service.create(CreatePersonCommand(True, "v1", external_id="person-001"))

    result = service.enroll(person.id, (b"image-1", b"image-2"), source_id="test")

    assert result.templates_created == 2
    assert len(templates.templates) == 2
    assert unit_of_work.commits == 2


def test_enrollment_rejects_entire_batch_when_one_image_has_low_quality() -> None:
    service, _, templates, unit_of_work = make_service()
    person = service.create(CreatePersonCommand(True, "v1"))

    with pytest.raises(EnrollmentRejectedError) as error:
        service.enroll(person.id, (b"image-1", b"bad-quality"), source_id="test")

    assert error.value.image_index == 1
    assert templates.templates == []
    assert unit_of_work.rollbacks == 1


def test_enrollment_discards_bad_frame_when_enough_good_images_remain() -> None:
    service, _, templates, unit_of_work = make_service()
    person = service.create(CreatePersonCommand(True, "v1"))

    result = service.enroll(
        person.id,
        (b"image-1", b"bad-quality", b"image-3", b"image-4", b"image-5"),
        source_id="test",
    )

    assert result.templates_created == 4
    assert result.images_received == 5
    assert len(result.rejections) == 1
    assert result.rejections[0].image_index == 1
    assert len(templates.templates) == 4
    assert unit_of_work.commits == 2


def test_revoke_deactivates_all_templates() -> None:
    service, people, templates, _ = make_service()
    person = service.create(CreatePersonCommand(True, "v1"))
    service.enroll(person.id, (b"image-1", b"image-2"), source_id="test")

    service.revoke(person.id)

    revoked_person = people.get(person.id)
    assert revoked_person is not None
    assert revoked_person.status is PersonStatus.REVOKED
    assert templates.deactivated_people == [person.id]
