"""create crawl run tables

Revision ID: 0005_crawl_runs
Revises: 0004_matching_and_applications
Create Date: 2026-09-19 15:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_crawl_runs"
down_revision: str | None = "0004_matching_and_applications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create crawl_runs and crawl_run_jobs tables."""
    # 1. crawl_runs
    op.create_table(
        "crawl_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'RUNNING'"),
            nullable=False,
        ),
        sa.Column(
            "jobs_found",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "jobs_created",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "jobs_updated",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "jobs_closed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "error_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_crawl_runs_source_id"),
        "crawl_runs",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_crawl_runs_status"),
        "crawl_runs",
        ["status"],
        unique=False,
    )

    # 2. crawl_run_jobs
    op.create_table(
        "crawl_run_jobs",
        sa.Column(
            "crawl_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(
            ["crawl_run_id"],
            ["crawl_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("crawl_run_id", "job_id"),
    )
    op.create_index(
        op.f("ix_crawl_run_jobs_job_id"),
        "crawl_run_jobs",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop crawl_run_jobs and crawl_runs tables in reverse dependency order."""
    op.drop_index(
        op.f("ix_crawl_run_jobs_job_id"),
        table_name="crawl_run_jobs",
    )
    op.drop_table("crawl_run_jobs")

    op.drop_index(op.f("ix_crawl_runs_status"), table_name="crawl_runs")
    op.drop_index(op.f("ix_crawl_runs_source_id"), table_name="crawl_runs")
    op.drop_table("crawl_runs")
