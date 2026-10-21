"""Initial biometric access schema.

Revision ID: 20261020_0001
Revises:
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20261020_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "persons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_version", sa.String(length=64), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive', 'revoked')", name="ck_persons_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_persons_status", "persons", ["status"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("detector_name", sa.String(length=128), nullable=False),
        sa.Column("detector_version", sa.String(length=128), nullable=False),
        sa.Column("embedder_name", sa.String(length=128), nullable=False),
        sa.Column("embedder_version", sa.String(length=128), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("model_checksum", sa.String(length=128), nullable=False),
        sa.Column("license_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("embedding_dimension > 0", name="ck_model_embedding_dimension"),
        sa.CheckConstraint(
            "license_status IN ('research_only', 'under_review', 'approved')",
            name="ck_model_license_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "face_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", Vector(128), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_face_templates_model_version_id", "face_templates", ["model_version_id"])
    op.create_index("ix_face_templates_person_id", "face_templates", ["person_id"])

    op.create_table(
        "recognition_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=True),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("biometric_decision", sa.String(length=32), nullable=False),
        sa.Column("authorization_decision", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("best_similarity", sa.Float(), nullable=True),
        sa.Column("second_best_similarity", sa.Float(), nullable=True),
        sa.Column("score_margin", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("quality_metadata", sa.JSON(), nullable=False),
        sa.Column("processing_time_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recognition_events_authorization_decision",
        "recognition_events",
        ["authorization_decision"],
    )
    op.create_index(
        "ix_recognition_events_biometric_decision", "recognition_events", ["biometric_decision"]
    )
    op.create_index(
        "ix_recognition_events_correlation_id", "recognition_events", ["correlation_id"]
    )
    op.create_index("ix_recognition_events_created_at", "recognition_events", ["created_at"])
    op.create_index("ix_recognition_events_person_id", "recognition_events", ["person_id"])

    op.create_table(
        "threshold_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False),
        sa.Column("similarity_threshold", sa.Float(), nullable=False),
        sa.Column("minimum_margin", sa.Float(), nullable=False),
        sa.Column("quality_config", sa.JSON(), nullable=False),
        sa.Column("temporal_config", sa.JSON(), nullable=False),
        sa.Column("validation_metrics", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_threshold_configs_model_version_id", "threshold_configs", ["model_version_id"]
    )
    op.create_index(
        "ix_threshold_configs_one_active_per_environment",
        "threshold_configs",
        ["model_version_id", "environment"],
        unique=True,
        postgresql_where=sa.text("active IS true"),
    )


def downgrade() -> None:
    op.drop_table("threshold_configs")
    op.drop_table("recognition_events")
    op.drop_table("face_templates")
    op.drop_table("model_versions")
    op.drop_table("persons")
    op.execute("DROP EXTENSION IF EXISTS vector")
