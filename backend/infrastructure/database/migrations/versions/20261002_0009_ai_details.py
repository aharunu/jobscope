"""Persist required analysis sections, verification quotes and baseline confidence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009_ai_details"
down_revision = "0008_match_snapshot"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("strengths", "gaps", "risks"):
        op.add_column(
            "ai_analyses", sa.Column(name, JSONB(), nullable=False, server_default="[]")
        )
    op.add_column(
        "ai_analyses",
        sa.Column("deterministic_confidence", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column("ai_evidence", sa.Column("source_quote", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("ai_evidence", "source_quote")
    for name in ("deterministic_confidence", "risks", "gaps", "strengths"):
        op.drop_column("ai_analyses", name)
