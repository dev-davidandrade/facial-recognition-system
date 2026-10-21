from datetime import UTC, datetime
from uuid import uuid4

from face_access.adapters.events.memory import InMemoryDecisionPublisher
from face_access.domain.enums import AuthorizationDecision
from face_access.domain.models import AccessDecisionEvent


def test_access_decision_event_contract_has_no_embedding_or_image() -> None:
    event = AccessDecisionEvent(
        correlation_id=uuid4(),
        decision=AuthorizationDecision.ACCESS_GRANTED,
        person_id=uuid4(),
        reason="authorized_identity",
        confidence=0.91,
        model_version="model-v1",
        occurred_at=datetime.now(UTC),
    )
    publisher = InMemoryDecisionPublisher()

    publisher.publish(event)

    published = publisher.events[0]
    assert published.event_type == "access_decision"
    assert not hasattr(published, "embedding")
    assert not hasattr(published, "image")
