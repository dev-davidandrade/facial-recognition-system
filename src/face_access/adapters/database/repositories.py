from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from face_access.adapters.database.models import (
    FaceTemplateRecord,
    ModelVersionRecord,
    PersonRecord,
)
from face_access.application.persons import DataConflictError
from face_access.domain.enums import PersonStatus
from face_access.domain.models import (
    FaceEmbedding,
    FaceTemplateCandidate,
    FaceTemplateMatch,
    ModelDescriptor,
    Person,
)


class SQLAlchemyPersonRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, person_id: UUID) -> Person | None:
        record = self._session.get(PersonRecord, person_id)
        return _person_from_record(record) if record is not None else None

    def add(self, person: Person) -> None:
        self._session.add(
            PersonRecord(
                id=person.id,
                external_id=person.external_id,
                display_name=person.display_name,
                status=person.status.value,
                consent_at=person.consent_at,
                consent_version=person.consent_version,
                revoked_at=person.revoked_at,
                created_at=person.created_at,
                updated_at=person.updated_at,
            )
        )

    def revoke(self, person_id: UUID) -> bool:
        record = self._session.get(PersonRecord, person_id)
        if record is None:
            return False
        now = datetime.now(UTC)
        record.status = PersonStatus.REVOKED.value
        record.revoked_at = now
        record.updated_at = now
        return True


class SQLAlchemyFaceTemplateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_many(
        self,
        person_id: UUID,
        model_version_id: UUID,
        templates: Sequence[FaceTemplateCandidate],
    ) -> None:
        now = datetime.now(UTC)
        self._session.add_all(
            [
                FaceTemplateRecord(
                    person_id=person_id,
                    model_version_id=model_version_id,
                    embedding=list(template.embedding.values),
                    quality_score=template.quality.score,
                    active=True,
                    created_at=now,
                    revoked_at=None,
                )
                for template in templates
            ]
        )

    def deactivate_for_person(self, person_id: UUID) -> None:
        now = datetime.now(UTC)
        self._session.execute(
            update(FaceTemplateRecord)
            .where(FaceTemplateRecord.person_id == person_id)
            .where(FaceTemplateRecord.active.is_(True))
            .values(active=False, revoked_at=now)
        )

    def find_nearest_people(
        self,
        embedding: FaceEmbedding,
        model_version_id: UUID,
        *,
        limit: int,
    ) -> Sequence[FaceTemplateMatch]:
        cosine_similarity = 1 - FaceTemplateRecord.embedding.cosine_distance(list(embedding.values))
        best_similarity = func.max(cosine_similarity).label("best_similarity")
        rows = self._session.execute(
            select(FaceTemplateRecord.person_id, best_similarity)
            .join(PersonRecord, PersonRecord.id == FaceTemplateRecord.person_id)
            .where(
                FaceTemplateRecord.model_version_id == model_version_id,
                FaceTemplateRecord.active.is_(True),
                FaceTemplateRecord.revoked_at.is_(None),
                PersonRecord.status == PersonStatus.ACTIVE.value,
                PersonRecord.revoked_at.is_(None),
            )
            .group_by(FaceTemplateRecord.person_id)
            .order_by(best_similarity.desc())
            .limit(limit)
        ).all()
        return tuple(
            FaceTemplateMatch(person_id=person_id, similarity=float(similarity))
            for person_id, similarity in rows
        )


class SQLAlchemyModelVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create(self, descriptor: ModelDescriptor) -> UUID:
        existing_id = self.find(descriptor)
        if existing_id is not None:
            return existing_id

        record = ModelVersionRecord(
            detector_name=descriptor.detector_name,
            detector_version=descriptor.detector_version,
            embedder_name=descriptor.embedder_name,
            embedder_version=descriptor.embedder_version,
            embedding_dimension=descriptor.embedding_dimension,
            model_checksum=descriptor.model_checksum,
            license_status=descriptor.license_status.value,
            created_at=datetime.now(UTC),
            active=True,
        )
        self._session.add(record)
        self._session.flush()
        return record.id

    def find(self, descriptor: ModelDescriptor) -> UUID | None:
        return self._session.scalar(
            select(ModelVersionRecord.id).where(
                ModelVersionRecord.detector_name == descriptor.detector_name,
                ModelVersionRecord.detector_version == descriptor.detector_version,
                ModelVersionRecord.embedder_name == descriptor.embedder_name,
                ModelVersionRecord.embedder_version == descriptor.embedder_version,
                ModelVersionRecord.embedding_dimension == descriptor.embedding_dimension,
                ModelVersionRecord.model_checksum == descriptor.model_checksum,
            )
        )


class SQLAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise DataConflictError("A unique person identifier is already registered") from exc

    def rollback(self) -> None:
        self._session.rollback()


def _person_from_record(record: PersonRecord) -> Person:
    return Person(
        id=record.id,
        status=PersonStatus(record.status),
        consent_at=record.consent_at,
        consent_version=record.consent_version,
        external_id=record.external_id,
        display_name=record.display_name,
        revoked_at=record.revoked_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
