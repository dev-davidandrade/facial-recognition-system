from math import sqrt

from face_access.domain.enums import AuthorizationDecision, BiometricDecision, PersonStatus
from face_access.domain.models import AuthorizationResult, FaceEmbedding, Person


class CosineFaceMatcher:
    def similarity(self, first: FaceEmbedding, second: FaceEmbedding) -> float:
        if (first.model_name, first.model_version) != (
            second.model_name,
            second.model_version,
        ):
            raise ValueError("Embeddings from different model versions cannot be compared")
        if len(first.values) != len(second.values):
            raise ValueError("Embedding dimensions do not match")

        dot_product = sum(
            left * right for left, right in zip(first.values, second.values, strict=True)
        )
        first_norm = sqrt(sum(value * value for value in first.values))
        second_norm = sqrt(sum(value * value for value in second.values))
        if first_norm == 0.0 or second_norm == 0.0:
            raise ValueError("A zero-norm embedding cannot be compared")
        return max(-1.0, min(1.0, dot_product / (first_norm * second_norm)))


class ConsentAuthorizationPolicy:
    def decide(
        self,
        person: Person | None,
        biometric_decision: BiometricDecision,
    ) -> AuthorizationResult:
        if biometric_decision in {
            BiometricDecision.AMBIGUOUS,
            BiometricDecision.SPOOF_SUSPECTED,
            BiometricDecision.PROCESSING_ERROR,
        }:
            return AuthorizationResult(
                AuthorizationDecision.MANUAL_REVIEW,
                "biometric_result_requires_review",
            )
        if biometric_decision is not BiometricDecision.IDENTIFIED or person is None:
            return AuthorizationResult(
                AuthorizationDecision.ACCESS_DENIED, "identity_not_confirmed"
            )
        if person.status is not PersonStatus.ACTIVE:
            return AuthorizationResult(AuthorizationDecision.ACCESS_DENIED, "person_not_active")
        return AuthorizationResult(AuthorizationDecision.ACCESS_GRANTED, "authorized_identity")
