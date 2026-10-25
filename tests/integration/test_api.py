from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from face_access.adapters.database.readiness import ReadinessReport
from face_access.api.dependencies import (
    get_identification_handler,
    get_person_service,
    get_readiness_probe,
    get_settings,
    get_verification_handler,
)
from face_access.application.persons import CreatePersonCommand, EnrollmentResult
from face_access.config.settings import Settings
from face_access.domain.enums import BiometricDecision, PersonStatus
from face_access.domain.models import (
    IdentificationResult,
    Person,
    QualityAssessment,
    VerificationResult,
)
from face_access.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeVerificationHandler:
    def execute(
        self,
        first_image: bytes,
        second_image: bytes,
        *,
        source_id: str,
    ) -> VerificationResult:
        assert first_image == b"first"
        assert second_image == b"second"
        assert source_id == "test-source"
        quality = QualityAssessment(True, 0.9, 100, 120, 128)
        return VerificationResult(
            biometric_decision=BiometricDecision.IDENTIFIED,
            is_match=True,
            similarity=0.92,
            threshold=0.8,
            reason_code="verification_match",
            detector_version="fake-detector-v1",
            embedding_model_version="fake-embedder-v1",
            processing_time_ms=2.5,
            first_quality=quality,
            second_quality=quality,
        )


class FakeIdentificationHandler:
    def execute(self, image: bytes, *, source_id: str) -> IdentificationResult:
        assert image == b"query"
        assert source_id == "test-source"
        now = datetime.now(UTC)
        person = Person(
            id=uuid4(),
            status=PersonStatus.ACTIVE,
            consent_at=now,
            consent_version="v1",
            external_id="person-001",
            display_name="Test Person",
            created_at=now,
            updated_at=now,
        )
        return IdentificationResult(
            biometric_decision=BiometricDecision.IDENTIFIED,
            person=person,
            best_similarity=0.88,
            second_best_similarity=0.62,
            score_margin=0.26,
            threshold=0.5,
            minimum_margin=0.05,
            reason_code="identification_match",
            detector_version="fake-detector-v1",
            embedding_model_version="fake-embedder-v1",
            processing_time_ms=3.0,
            quality=QualityAssessment(True, 0.9, 100, 120, 128),
        )


class FakeReadinessProbe:
    def __init__(self, ready: bool) -> None:
        self._ready = ready

    def check(self) -> ReadinessReport:
        return ReadinessReport(self._ready, {"database": "ready" if self._ready else "unavailable"})


class FakePersonService:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.person = Person(
            id=uuid4(),
            status=PersonStatus.ACTIVE,
            consent_at=now,
            consent_version="v1",
            external_id="person-001",
            display_name="Test Person",
            created_at=now,
            updated_at=now,
        )

    def create(self, command: CreatePersonCommand) -> Person:
        return self.person

    def get(self, person_id: UUID) -> Person:
        return self.person

    def enroll(
        self,
        person_id: UUID,
        images: tuple[bytes, ...],
        *,
        source_id: str,
    ) -> EnrollmentResult:
        assert images == (b"first", b"second")
        quality = QualityAssessment(True, 0.9, 100, 120, 128)
        return EnrollmentResult(
            person_id=person_id,
            templates_created=2,
            images_received=2,
            model_version_id=uuid4(),
            embedding_model_version="fake-embedder-v1",
            qualities=(quality, quality),
            rejections=(),
        )

    def revoke(self, person_id: UUID) -> None:
        return None


def make_app(*, ready: bool = True, max_upload_bytes: int = 1024) -> FastAPI:
    settings = Settings(database_healthcheck_enabled=False, max_upload_bytes=max_upload_bytes)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_readiness_probe] = lambda: FakeReadinessProbe(ready)
    app.dependency_overrides[get_verification_handler] = FakeVerificationHandler
    app.dependency_overrides[get_identification_handler] = FakeIdentificationHandler
    app.dependency_overrides[get_person_service] = FakePersonService
    return app


def _multipart_schema(app: FastAPI, path: str) -> dict[str, Any]:
    request_schema = app.openapi()["paths"][path]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]["schema"]
    component_name = request_schema["$ref"].rsplit("/", maxsplit=1)[-1]
    return app.openapi()["components"]["schemas"][component_name]


def test_openapi_describes_uploads_as_binary_files_for_swagger_ui() -> None:
    app = make_app()

    verification = _multipart_schema(app, "/v1/verifications/verify")
    enrollment = _multipart_schema(app, "/v1/persons/{person_id}/enroll")
    identification = _multipart_schema(app, "/v1/identifications/identify")

    assert verification["properties"]["first_image"]["format"] == "binary"
    assert verification["properties"]["second_image"]["format"] == "binary"
    assert enrollment["properties"]["images"]["items"]["format"] == "binary"
    assert identification["properties"]["image"]["format"] == "binary"


@pytest.mark.anyio
async def test_health_endpoint() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.anyio
async def test_demo_console_and_assets_are_served_locally() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()), base_url="http://test"
    ) as client:
        page = await client.get("/demo")
        stylesheet = await client.get("/demo/assets/app.css")
        script = await client.get("/demo/assets/app.js")

    assert page.status_code == 200
    assert "Face Access Lab" in page.text
    assert "Cadastro consentido" in page.text
    assert "Usar webcam" in page.text
    assert stylesheet.status_code == 200
    assert "--accent" in stylesheet.text
    assert script.status_code == 200
    assert "/v1/identifications/identify" in script.text
    assert "demo-ui-webcam-enrollment" in script.text


@pytest.mark.anyio
async def test_ready_returns_503_when_a_dependency_is_unavailable() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app(ready=False)), base_url="http://test"
    ) as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": {"database": "unavailable"}}


@pytest.mark.anyio
async def test_verify_endpoint_does_not_expose_embeddings() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/verifications/verify",
            files={
                "first_image": ("first.jpg", b"first", "image/jpeg"),
                "second_image": ("second.png", b"second", "image/png"),
            },
            data={"source_id": "test-source"},
        )

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["biometric_decision"] == "identified"
    assert body["similarity"] == 0.92
    assert "embedding" not in body


@pytest.mark.anyio
async def test_identify_endpoint_returns_the_matched_person_without_embedding() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/identifications/identify",
            files={"image": ("query.jpg", b"query", "image/jpeg")},
            data={"source_id": "test-source"},
        )

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["biometric_decision"] == "identified"
    assert body["external_id"] == "person-001"
    assert body["best_similarity"] == 0.88
    assert body["score_margin"] == 0.26
    assert "embedding" not in body


@pytest.mark.anyio
async def test_temporal_policy_exposes_only_public_confirmation_settings() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()), base_url="http://test"
    ) as client:
        response = await client.get("/v1/identifications/temporal-policy")

    assert response.status_code == 200
    assert response.json() == {
        "confirmations_required": 3,
        "window_size": 5,
        "max_gap_ms": 1000,
        "review_after_ms": 5000,
        "frame_interval_ms": 350,
    }


@pytest.mark.anyio
async def test_verify_rejects_unsupported_media_type() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/verifications/verify",
            files={
                "first_image": ("first.gif", b"first", "image/gif"),
                "second_image": ("second.png", b"second", "image/png"),
            },
        )

    assert response.status_code == 415


@pytest.mark.anyio
async def test_verify_rejects_oversized_upload() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app(max_upload_bytes=1024)), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/verifications/verify",
            files={
                "first_image": ("first.jpg", b"x" * 1025, "image/jpeg"),
                "second_image": ("second.png", b"second", "image/png"),
            },
        )

    assert response.status_code == 413


@pytest.mark.anyio
async def test_create_and_get_person() -> None:
    app = make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/v1/persons",
            json={
                "consent_confirmed": True,
                "consent_version": "v1",
                "external_id": "person-001",
                "display_name": "Test Person",
            },
        )
        person_id = created.json()["id"]
        fetched = await client.get(f"/v1/persons/{person_id}")

    assert created.status_code == 201
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "active"


@pytest.mark.anyio
async def test_enroll_person_with_multiple_images() -> None:
    app = make_app()
    person_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/persons/{person_id}/enroll",
            files=[
                ("images", ("first.jpg", b"first", "image/jpeg")),
                ("images", ("second.jpg", b"second", "image/jpeg")),
            ],
            data={"source_id": "test"},
        )

    assert response.status_code == 200
    assert response.json()["templates_created"] == 2
    assert response.json()["images_received"] == 2
    assert response.json()["images_rejected"] == 0


@pytest.mark.anyio
async def test_revoke_person() -> None:
    app = make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/v1/persons/{uuid4()}")

    assert response.status_code == 204
    assert response.content == b""
