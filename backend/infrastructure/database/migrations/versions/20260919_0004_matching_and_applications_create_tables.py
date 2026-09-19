"""create matching and application tables

Revision ID: 0004_matching_and_applications
Revises: 0003_jobs_and_sources
Create Date: 2026-09-19 14:20:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_matching_and_applications"
down_revision: str | None = "0003_jobs_and_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create matching, requirement, and application tracking tables."""
    # 1. job_requirements
    op.create_table(
        "job_requirements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("normalized_skill", sa.String(length=150), nullable=True),
        sa.Column(
            "required_level",
            sa.String(length=50),
            server_default=sa.text("'REQUIRED'"),
            nullable=False,
        ),
        sa.Column(
            "importance",
            sa.String(length=50),
            server_default=sa.text("'MEDIUM'"),
            nullable=False,
        ),
        sa.Column(
            "criticality",
            sa.String(length=50),
            server_default=sa.text("'NORMAL'"),
            nullable=False,
        ),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_requirements_job_id"),
        "job_requirements",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_requirements_normalized_skill"),
        "job_requirements",
        ["normalized_skill"],
        unique=False,
    )

    # 2. match_results
    op.create_table(
        "match_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "base_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "search_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "deterministic_score",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "ai_score",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column(
            "ai_adjustment",
            sa.Numeric(precision=4, scale=2),
            server_default=sa.text("0.0"),
            nullable=True,
        ),
        sa.Column(
            "final_score",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["base_profile_id"],
            ["base_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["search_profile_id"],
            ["search_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "base_profile_id",
            "search_profile_id",
            name="uq_match_results_job_base_search",
        ),
    )
    op.create_index(
        op.f("ix_match_results_base_profile_id"),
        "match_results",
        ["base_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_results_job_id"),
        "match_results",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_results_search_profile_id"),
        "match_results",
        ["search_profile_id"],
        unique=False,
    )

    # 3. requirement_matches
    op.create_table(
        "requirement_matches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "match_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "requirement_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("match_status", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "is_blocker",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["match_result_id"],
            ["match_results.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["job_requirements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_requirement_matches_match_result_id"),
        "requirement_matches",
        ["match_result_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_requirement_matches_requirement_id"),
        "requirement_matches",
        ["requirement_id"],
        unique=False,
    )

    # 4. ai_analyses
    op.create_table(
        "ai_analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "match_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("ai_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("assessment", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["match_result_id"],
            ["match_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_result_id",
            name="uq_ai_analyses_match_result_id",
        ),
    )

    # 5. ai_evidence
    op.create_table(
        "ai_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "ai_analysis_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ai_analysis_id"],
            ["ai_analyses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_evidence_ai_analysis_id"),
        "ai_evidence",
        ["ai_analysis_id"],
        unique=False,
    )

    # 6. applications
    op.create_table(
        "applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'INTERESTED'"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "user_id",
            name="uq_applications_job_user",
        ),
    )
    op.create_index(
        op.f("ix_applications_job_id"),
        "applications",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_applications_status"),
        "applications",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_applications_user_id"),
        "applications",
        ["user_id"],
        unique=False,
    )

    # 7. application_status_history
    op.create_table(
        "application_status_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(length=50), nullable=False),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_status_history_application_id"),
        "application_status_history",
        ["application_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop application and matching tables in reverse dependency order."""
    op.drop_index(
        op.f("ix_application_status_history_application_id"),
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")

    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_status"), table_name="applications")
    op.drop_index(op.f("ix_applications_job_id"), table_name="applications")
    op.drop_table("applications")

    op.drop_index(op.f("ix_ai_evidence_ai_analysis_id"), table_name="ai_evidence")
    op.drop_table("ai_evidence")

    op.drop_table("ai_analyses")

    op.drop_index(
        op.f("ix_requirement_matches_requirement_id"),
        table_name="requirement_matches",
    )
    op.drop_index(
        op.f("ix_requirement_matches_match_result_id"),
        table_name="requirement_matches",
    )
    op.drop_table("requirement_matches")

    op.drop_index(
        op.f("ix_match_results_search_profile_id"),
        table_name="match_results",
    )
    op.drop_index(op.f("ix_match_results_job_id"), table_name="match_results")
    op.drop_index(
        op.f("ix_match_results_base_profile_id"),
        table_name="match_results",
    )
    op.drop_table("match_results")

    op.drop_index(
        op.f("ix_job_requirements_normalized_skill"),
        table_name="job_requirements",
    )
    op.drop_index(
        op.f("ix_job_requirements_job_id"),
        table_name="job_requirements",
    )
    op.drop_table("job_requirements")
