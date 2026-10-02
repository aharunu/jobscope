"""Persist deterministic display data that previously existed only in memory."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_match_snapshot"
down_revision = "0007_job_filter_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "match_results",
        sa.Column("category_scores", JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column("match_results", sa.Column("explanation", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("match_results", "explanation")
    op.drop_column("match_results", "category_scores")
