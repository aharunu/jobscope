"""add location and work_mode indexes to jobs table

Revision ID: 0007_job_location_work_mode_indexes
Revises: 0006_cvs
Create Date: 2026-10-01 19:10:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_job_location_work_mode_indexes"
down_revision: str | None = "0006_cvs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create indexes for location and work_mode on canonical jobs."""
    op.create_index(
        op.f("ix_jobs_location"),
        "jobs",
        ["location"],
        unique=False,
    )
    op.create_index(
        op.f("ix_jobs_work_mode"),
        "jobs",
        ["work_mode"],
        unique=False,
    )


def downgrade() -> None:
    """Drop location and work_mode indexes from jobs table."""
    op.drop_index(op.f("ix_jobs_work_mode"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_location"), table_name="jobs")
