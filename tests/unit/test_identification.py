from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from face_access.application.identification import (
    IdentificationThresholds,
    IdentifyFaceService,
)
from face_access.domain.enums import BiometricDecision, LicenseStatus, PersonStatus
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
    def __init__(self, people: Sequence[Person]) -> None:
        self.people = {person.id: person for person in people}

    def get(self, person_id: UUID) -> Person | None:
        return self.people.get(person_id)

    def add(self, person: Person) -> None:
        self.people[person.id] = person

    def revoke(self, person_id: UUID) -> bool:
        return False


class MemoryTemplateRepository:
    def __init__(self, matches: Sequence[FaceTemplateMatch]) -> None:
        self.matches = tuple(matches)

    def add_many(
        self,
        person_id: UUID,
        model_version_id: UUID,
        templates: Sequence[FaceTemplateCandidate],
    ) -> None:
        raise AssertionError("Not used by identification")

    def deactivate_for_person(self, person_id: UUID) -> None:
        raise AssertionError("Not used by identification")

    def find_nearest_people(
        self,
        embedding: FaceEmbedding,
        model_version_id: UUID,
        *,
        limit: int,
    ) -> Sequence[FaceTemplateMatch]:
        assert len(embedding.values) == 128
        assert limit == 2
        return self.matches[:limit]


class MemoryModelVersionRepository:
    def __init__(self, model_version_id: UUID | None = None) -> None:
        self.model_version_id = model_version_id

    def get_or_create(self, descriptor: ModelDescriptor) -> UUID:
        raise AssertionError("Not used by identification")

    def find(self, descriptor: ModelDescriptor) -> UUID | None:
        return self.model_version_id


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


def person() -> Person:
    now = datetime.now(UTC)
    return Person(
        id=uuid4(),
        status=PersonStatus.ACTIVE,
        consent_at=now,
        consent_version="v1",
        external_id="person-001",
        created_at=now,
        updated_at=now,
    )


def make_service(
    people: Sequence[Person],
    matches: Sequence[FaceTemplateMatch],
    *,
    has_model_version: bool = True,
) -> IdentifyFaceService:
    descriptor = ModelDescriptor(
        detector_name="fake",
        detector_version="detector-v1",
        embedder_name="fake",
        embedder_version="embedder-v1",
        embedding_dimension=128,
        model_checksum="a" * 64,
        license_status=LicenseStatus.RESEARCH_ONLY,
    )
    return IdentifyFaceService(
        persons=MemoryPersonRepository(people),
        templates=MemoryTemplateRepository(matches),
        model_versions=MemoryModelVersionRepository(uuid4() if has_model_version else None),
        decoder=FakeDecoder(),
        detector=FakeDetector(),
        aligner=FakeAligner(),
        embedder=FakeEmbedder(),
        quality_evaluator=FakeQualityEvaluator(),
        model_descriptor=descriptor,
        thresholds=IdentificationThresholds(similarity=0.5, minimum_margin=0.05),
    )


def test_identifies_best_person_above_threshold_with_sufficient_margin() -> None:
    best = person()
    second = person()
    service = make_service(
        [best, second],
        [FaceTemplateMatch(best.id, 0.82), FaceTemplateMatch(second.id, 0.65)],
    )

    result = service.execute(b"query", source_id="test")

    assert result.biometric_decision is BiometricDecision.IDENTIFIED
    assert result.person == best
    assert result.best_similarity == pytest.approx(0.82)
    assert result.score_margin == pytest.approx(0.17)


def test_rejects_unknown_when_best_candidate_is_below_threshold() -> None:
    candidate = person()
    service = make_service([candidate], [FaceTemplateMatch(candidate.id, 0.49)])

    result = service.execute(b"query", source_id="test")

    assert result.biometric_decision is BiometricDecision.UNKNOWN
    assert result.person is None
    assert result.reason_code == "similarity_below_threshold"


def test_marks_close_candidates_as_ambiguous() -> None:
    best = person()
    second = person()
    service = make_service(
        [best, second],
        [FaceTemplateMatch(best.id, 0.81), FaceTemplateMatch(second.id, 0.78)],
    )

    result = service.execute(b"query", source_id="test")

    assert result.biometric_decision is BiometricDecision.AMBIGUOUS
    assert result.person is None
    assert result.reason_code == "candidate_margin_too_small"


@pytest.mark.parametrize(
    ("image", "expected"),
    [
        (b"no-face", BiometricDecision.NO_FACE),
        (b"multiple", BiometricDecision.MULTIPLE_FACES),
        (b"bad-quality", BiometricDecision.LOW_QUALITY),
    ],
)
def test_rejects_invalid_query_images(image: bytes, expected: BiometricDecision) -> None:
    service = make_service([], [])

    result = service.execute(image, source_id="test")

    assert result.biometric_decision is expected


def test_returns_unknown_when_there_is_no_compatible_model_version() -> None:
    service = make_service([], [], has_model_version=False)

    result = service.execute(b"query", source_id="test")

    assert result.biometric_decision is BiometricDecision.UNKNOWN
    assert result.reason_code == "no_compatible_templates"
