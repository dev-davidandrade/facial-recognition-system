from enum import StrEnum


class PersonStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class BiometricDecision(StrEnum):
    IDENTIFIED = "identified"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    NO_FACE = "no_face"
    MULTIPLE_FACES = "multiple_faces"
    LOW_QUALITY = "low_quality"
    SPOOF_SUSPECTED = "spoof_suspected"
    PROCESSING_ERROR = "processing_error"


class AuthorizationDecision(StrEnum):
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    MANUAL_REVIEW = "manual_review"


class LicenseStatus(StrEnum):
    RESEARCH_ONLY = "research_only"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
