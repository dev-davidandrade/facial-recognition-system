from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from face_access.adapters.database.readiness import ReadinessProbe
from face_access.adapters.database.repositories import (
    SQLAlchemyFaceTemplateRepository,
    SQLAlchemyModelVersionRepository,
    SQLAlchemyPersonRepository,
    SQLAlchemyUnitOfWork,
)
from face_access.adapters.database.session import get_session
from face_access.adapters.factory import (
    VisionComponents,
    build_verification_handler,
    build_vision_components,
)
from face_access.application.identification import (
    IdentificationHandler,
    IdentificationThresholds,
    IdentifyFaceService,
)
from face_access.application.persons import PersonManagementHandler, PersonManagementService
from face_access.application.verification import VerificationHandler
from face_access.config.settings import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def _get_cached_vision_components() -> VisionComponents:
    return build_vision_components(get_settings())


def get_vision_components() -> VisionComponents:
    try:
        return _get_cached_vision_components()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Face models are not configured on this instance",
        ) from exc


@lru_cache
def _get_cached_verification_handler() -> VerificationHandler:
    return build_verification_handler(get_settings(), _get_cached_vision_components())


def get_verification_handler() -> VerificationHandler:
    try:
        return _get_cached_verification_handler()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Face models are not configured on this instance",
        ) from exc


def get_person_service(
    session: Annotated[Session, Depends(get_session)],
    vision: Annotated[VisionComponents, Depends(get_vision_components)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PersonManagementHandler:
    return PersonManagementService(
        persons=SQLAlchemyPersonRepository(session),
        templates=SQLAlchemyFaceTemplateRepository(session),
        model_versions=SQLAlchemyModelVersionRepository(session),
        unit_of_work=SQLAlchemyUnitOfWork(session),
        decoder=vision.decoder,
        detector=vision.detector,
        aligner=vision.aligner,
        embedder=vision.embedder,
        quality_evaluator=vision.quality_evaluator,
        model_descriptor=vision.model_descriptor,
        minimum_enrollment_images=settings.minimum_enrollment_images,
        maximum_enrollment_images=settings.maximum_enrollment_images,
    )


def get_identification_handler(
    session: Annotated[Session, Depends(get_session)],
    vision: Annotated[VisionComponents, Depends(get_vision_components)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IdentificationHandler:
    return IdentifyFaceService(
        persons=SQLAlchemyPersonRepository(session),
        templates=SQLAlchemyFaceTemplateRepository(session),
        model_versions=SQLAlchemyModelVersionRepository(session),
        decoder=vision.decoder,
        detector=vision.detector,
        aligner=vision.aligner,
        embedder=vision.embedder,
        quality_evaluator=vision.quality_evaluator,
        model_descriptor=vision.model_descriptor,
        thresholds=IdentificationThresholds(
            similarity=settings.identification_similarity_threshold,
            minimum_margin=settings.identification_minimum_margin,
        ),
    )


@lru_cache
def get_readiness_probe() -> ReadinessProbe:
    return ReadinessProbe(get_settings())
