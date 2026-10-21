from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from face_access.adapters.database.base import Base


class PersonRecord(Base):
    __tablename__ = "persons"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(64))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    templates: Mapped[list["FaceTemplateRecord"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )


class ModelVersionRecord(Base):
    __tablename__ = "model_versions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    detector_name: Mapped[str] = mapped_column(String(128))
    detector_version: Mapped[str] = mapped_column(String(128))
    embedder_name: Mapped[str] = mapped_column(String(128))
    embedder_version: Mapped[str] = mapped_column(String(128))
    embedding_dimension: Mapped[int] = mapped_column(Integer)
    model_checksum: Mapped[str] = mapped_column(String(128))
    license_status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=False)

    templates: Mapped[list["FaceTemplateRecord"]] = relationship(back_populates="model_version")


class FaceTemplateRecord(Base):
    __tablename__ = "face_templates"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        index=True,
    )
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
        index=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(128))
    quality_score: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    person: Mapped[PersonRecord] = relationship(back_populates="templates")
    model_version: Mapped[ModelVersionRecord] = relationship(back_populates="templates")


class RecognitionEventRecord(Base):
    __tablename__ = "recognition_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    correlation_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"),
        index=True,
    )
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT")
    )
    source_id: Mapped[str] = mapped_column(String(255))
    biometric_decision: Mapped[str] = mapped_column(String(32), index=True)
    authorization_decision: Mapped[str] = mapped_column(String(32), index=True)
    reason_code: Mapped[str] = mapped_column(String(128))
    best_similarity: Mapped[float | None] = mapped_column(Float)
    second_best_similarity: Mapped[float | None] = mapped_column(Float)
    score_margin: Mapped[float | None] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    quality_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)
    processing_time_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ThresholdConfigRecord(Base):
    __tablename__ = "threshold_configs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        index=True,
    )
    environment: Mapped[str] = mapped_column(String(64))
    similarity_threshold: Mapped[float] = mapped_column(Float)
    minimum_margin: Mapped[float] = mapped_column(Float)
    quality_config: Mapped[dict[str, Any]] = mapped_column(JSON)
    temporal_config: Mapped[dict[str, Any]] = mapped_column(JSON)
    validation_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=False)


Index(
    "ix_threshold_configs_one_active_per_environment",
    ThresholdConfigRecord.model_version_id,
    ThresholdConfigRecord.environment,
    unique=True,
    postgresql_where=ThresholdConfigRecord.active.is_(True),
)
