from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import WithJsonSchema
from starlette.concurrency import run_in_threadpool

from face_access.adapters.database.readiness import ReadinessProbe
from face_access.api.dependencies import (
    get_identification_handler,
    get_person_service,
    get_readiness_probe,
    get_settings,
    get_verification_handler,
)
from face_access.api.schemas import (
    CreatePersonRequest,
    EnrollmentResponse,
    HealthResponse,
    IdentificationResponse,
    PersonResponse,
    ReadinessResponse,
    TemporalPolicyResponse,
    VerificationResponse,
)
from face_access.application.identification import IdentificationHandler
from face_access.application.persons import (
    ConsentRequiredError,
    CreatePersonCommand,
    DataConflictError,
    EnrollmentRejectedError,
    InvalidEnrollmentCountError,
    PersonManagementHandler,
    PersonNotActiveError,
    PersonNotFoundError,
)
from face_access.application.verification import VerificationHandler
from face_access.config.settings import Settings

health_router = APIRouter(tags=["service"])
verification_router = APIRouter(prefix="/v1/verifications", tags=["verifications"])
identification_router = APIRouter(prefix="/v1/identifications", tags=["identifications"])
person_router = APIRouter(prefix="/v1/persons", tags=["persons"])

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png"}
BinaryUpload = Annotated[
    UploadFile,
    WithJsonSchema({"type": "string", "format": "binary"}),
]


@health_router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version=settings.app_version)


@health_router.get("/ready", response_model=ReadinessResponse)
def ready(
    response: Response,
    probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
) -> ReadinessResponse:
    report = probe.check()
    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="ready" if report.ready else "not_ready", checks=report.checks)


@verification_router.post("/verify", response_model=VerificationResponse)
async def verify_faces(
    first_image: Annotated[BinaryUpload, File(description="Primeira imagem JPEG ou PNG")],
    second_image: Annotated[BinaryUpload, File(description="Segunda imagem JPEG ou PNG")],
    handler: Annotated[VerificationHandler, Depends(get_verification_handler)],
    settings: Annotated[Settings, Depends(get_settings)],
    source_id: Annotated[str, Form(min_length=1, max_length=100)] = "api-upload",
) -> VerificationResponse:
    first_bytes = await _read_validated(first_image, settings.max_upload_bytes)
    second_bytes = await _read_validated(second_image, settings.max_upload_bytes)
    result = await run_in_threadpool(
        handler.execute,
        first_bytes,
        second_bytes,
        source_id=source_id,
    )
    return VerificationResponse.from_domain(result)


async def _read_validated(upload: UploadFile, max_bytes: int) -> bytes:
    if upload.content_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG and PNG images are accepted",
        )
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Image exceeds the configured upload limit",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Image cannot be empty",
        )
    return content


@identification_router.post("/identify", response_model=IdentificationResponse)
async def identify_face(
    image: Annotated[BinaryUpload, File(description="Imagem de consulta JPEG ou PNG")],
    handler: Annotated[IdentificationHandler, Depends(get_identification_handler)],
    settings: Annotated[Settings, Depends(get_settings)],
    source_id: Annotated[str, Form(min_length=1, max_length=100)] = "api-identification",
) -> IdentificationResponse:
    image_bytes = await _read_validated(image, settings.max_upload_bytes)
    result = await run_in_threadpool(handler.execute, image_bytes, source_id=source_id)
    return IdentificationResponse.from_domain(result)


@identification_router.get("/temporal-policy", response_model=TemporalPolicyResponse)
def temporal_policy(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TemporalPolicyResponse:
    return TemporalPolicyResponse(
        confirmations_required=settings.temporal_confirmations,
        window_size=settings.temporal_window_size,
        max_gap_ms=settings.temporal_max_gap_ms,
        review_after_ms=settings.temporal_review_after_ms,
        frame_interval_ms=settings.temporal_frame_interval_ms,
    )


@person_router.post("", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
    payload: Annotated[CreatePersonRequest, Body()],
    service: Annotated[PersonManagementHandler, Depends(get_person_service)],
) -> PersonResponse:
    try:
        person = await run_in_threadpool(
            service.create,
            CreatePersonCommand(
                consent_confirmed=payload.consent_confirmed,
                consent_version=payload.consent_version,
                external_id=payload.external_id,
                display_name=payload.display_name,
            ),
        )
    except ConsentRequiredError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except DataConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return PersonResponse.from_domain(person)


@person_router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: UUID,
    service: Annotated[PersonManagementHandler, Depends(get_person_service)],
) -> PersonResponse:
    try:
        person = await run_in_threadpool(service.get, person_id)
    except PersonNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Person not found") from exc
    return PersonResponse.from_domain(person)


@person_router.post("/{person_id}/enroll", response_model=EnrollmentResponse)
async def enroll_person(
    person_id: UUID,
    images: Annotated[list[BinaryUpload], File(description="De 2 a 10 imagens JPEG ou PNG")],
    service: Annotated[PersonManagementHandler, Depends(get_person_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    source_id: Annotated[str, Form(min_length=1, max_length=100)] = "api-enrollment",
) -> EnrollmentResponse:
    if not settings.minimum_enrollment_images <= len(images) <= settings.maximum_enrollment_images:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Enrollment requires between {settings.minimum_enrollment_images} and "
                f"{settings.maximum_enrollment_images} images"
            ),
        )
    encoded_images = tuple(
        [await _read_validated(image, settings.max_upload_bytes) for image in images]
    )
    try:
        result = await run_in_threadpool(
            service.enroll,
            person_id,
            encoded_images,
            source_id=source_id,
        )
    except PersonNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Person not found") from exc
    except PersonNotActiveError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Person is not active") from exc
    except InvalidEnrollmentCountError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except EnrollmentRejectedError as exc:
        rejections = [
            {
                "image_index": rejection.image_index,
                "biometric_decision": rejection.decision.value,
                "reason_code": rejection.reason_code,
                "quality": (
                    {
                        "score": rejection.quality.score,
                        "face_size_px": rejection.quality.face_size_px,
                        "blur_score": rejection.quality.blur_score,
                        "brightness": rejection.quality.brightness,
                        "reasons": rejection.quality.reasons,
                    }
                    if rejection.quality is not None
                    else None
                ),
            }
            for rejection in exc.rejections
        ]
        detail: dict[str, object] = {
            "message": "Not enough enrollment images met the quality requirements",
            "image_index": exc.image_index,
            "biometric_decision": exc.decision.value,
            "reason_code": exc.reason_code,
            "accepted_images": exc.accepted_images,
            "required_images": exc.required_images,
            "rejected_images": len(exc.rejections),
            "rejections": rejections,
        }
        if exc.quality is not None:
            detail["quality"] = {
                "score": exc.quality.score,
                "face_size_px": exc.quality.face_size_px,
                "blur_score": exc.quality.blur_score,
                "brightness": exc.quality.brightness,
                "reasons": exc.quality.reasons,
            }
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail) from exc
    return EnrollmentResponse.from_domain(result)


@person_router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_person(
    person_id: UUID,
    service: Annotated[PersonManagementHandler, Depends(get_person_service)],
) -> Response:
    try:
        await run_in_threadpool(service.revoke, person_id)
    except PersonNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Person not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router = APIRouter()
router.include_router(health_router)
router.include_router(person_router)
router.include_router(verification_router)
router.include_router(identification_router)
