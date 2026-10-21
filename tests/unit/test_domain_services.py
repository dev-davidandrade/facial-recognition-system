from datetime import UTC, datetime
from uuid import uuid4

import pytest

from face_access.domain.enums import AuthorizationDecision, BiometricDecision, PersonStatus
from face_access.domain.models import FaceEmbedding, Person
from face_access.domain.services import ConsentAuthorizationPolicy, CosineFaceMatcher


def embedding(values: tuple[float, ...], version: str = "v1") -> FaceEmbedding:
    return FaceEmbedding(values=values, model_name="fake", model_version=version)


def test_cosine_matcher_returns_one_for_same_direction() -> None:
    matcher = CosineFaceMatcher()

    similarity = matcher.similarity(embedding((1.0, 2.0)), embedding((2.0, 4.0)))

    assert similarity == pytest.approx(1.0)


def test_cosine_matcher_rejects_different_model_versions() -> None:
    matcher = CosineFaceMatcher()

    with pytest.raises(ValueError, match="different model versions"):
        matcher.similarity(embedding((1.0, 0.0), "v1"), embedding((1.0, 0.0), "v2"))


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (PersonStatus.ACTIVE, AuthorizationDecision.ACCESS_GRANTED),
        (PersonStatus.INACTIVE, AuthorizationDecision.ACCESS_DENIED),
        (PersonStatus.REVOKED, AuthorizationDecision.ACCESS_DENIED),
    ],
)
def test_authorization_is_separate_from_identification(
    status: PersonStatus,
    expected: AuthorizationDecision,
) -> None:
    person = Person(
        id=uuid4(),
        status=status,
        consent_at=datetime.now(UTC),
        consent_version="v1",
    )

    result = ConsentAuthorizationPolicy().decide(person, BiometricDecision.IDENTIFIED)

    assert result.decision is expected


def test_ambiguous_identity_requires_manual_review() -> None:
    result = ConsentAuthorizationPolicy().decide(None, BiometricDecision.AMBIGUOUS)

    assert result.decision is AuthorizationDecision.MANUAL_REVIEW
