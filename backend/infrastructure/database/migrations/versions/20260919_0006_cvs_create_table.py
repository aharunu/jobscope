"""create cvs table

Revision ID: 0006_cvs
Revises: 0005_crawl_runs
Create Date: 2026-09-19 17:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_cvs"
down_revision: str | None = "0005_crawl_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create cvs table."""
    op.create_table(
        "cvs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "base_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "file_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "raw_content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "parsed_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING_REVIEW",
                "APPROVED",
                "REJECTED",
                name="cv_status_enum",
                native_enum=False,
                length=50,
            ),
            server_default=sa.text("'PENDING_REVIEW'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["base_profile_id"],
            ["base_profiles.id"],
            name="fk_cvs_base_profile_id_base_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cvs"),
    )
    op.create_index(
        "ix_cvs_base_profile_id",
        "cvs",
        ["base_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop cvs table and its index."""
    op.drop_index("ix_cvs_base_profile_id", table_name="cvs")
    op.drop_table("cvs")
