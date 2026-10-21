from face_access.domain.models import AccessDecisionEvent


class InMemoryDecisionPublisher:
    def __init__(self) -> None:
        self.events: list[AccessDecisionEvent] = []

    def publish(self, event: AccessDecisionEvent) -> None:
        self.events.append(event)
