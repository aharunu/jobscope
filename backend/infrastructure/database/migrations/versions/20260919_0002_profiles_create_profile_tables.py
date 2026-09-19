"""create profile tables

Revision ID: 0002_profiles
Revises: 0001_users
Create Date: 2026-09-19 13:29:36.203453+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_profiles"
down_revision: str | None = "0001_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create profile tables, child sub-tables, and search profiles."""
    # 1. base_profiles
    op.create_table(
        "base_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
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
            ["user_id"],
            ["users.id"],
            name=op.f("fk_base_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_base_profiles")),
    )
    op.create_index(
        op.f("ix_base_profiles_user_id"),
        "base_profiles",
        ["user_id"],
        unique=False,
    )

    # 2. profile_skills
    op.create_table(
        "profile_skills",
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
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column(
            "years_of_experience",
            sa.Numeric(precision=4, scale=1),
            nullable=True,
        ),
        sa.Column("level", sa.String(length=50), nullable=True),
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
            name=op.f("fk_profile_skills_base_profile_id_base_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_skills")),
    )
    op.create_index(
        op.f("ix_profile_skills_base_profile_id"),
        "profile_skills",
        ["base_profile_id"],
        unique=False,
    )

    # 3. profile_experiences
    op.create_table(
        "profile_experiences",
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
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "skills_used",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
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
            name=op.f("fk_profile_experiences_base_profile_id_base_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_experiences")),
    )
    op.create_index(
        op.f("ix_profile_experiences_base_profile_id"),
        "profile_experiences",
        ["base_profile_id"],
        unique=False,
    )

    # 4. profile_educations
    op.create_table(
        "profile_educations",
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
        sa.Column("school", sa.String(length=255), nullable=False),
        sa.Column("degree", sa.String(length=100), nullable=False),
        sa.Column("field_of_study", sa.String(length=255), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
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
            name=op.f("fk_profile_educations_base_profile_id_base_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_educations")),
    )
    op.create_index(
        op.f("ix_profile_educations_base_profile_id"),
        "profile_educations",
        ["base_profile_id"],
        unique=False,
    )

    # 5. profile_projects
    op.create_table(
        "profile_projects",
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
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "skills_used",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=True),
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
            name=op.f("fk_profile_projects_base_profile_id_base_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_projects")),
    )
    op.create_index(
        op.f("ix_profile_projects_base_profile_id"),
        "profile_projects",
        ["base_profile_id"],
        unique=False,
    )

    # 6. search_profiles
    op.create_table(
        "search_profiles",
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
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column(
            "target_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("seniority", sa.String(length=50), nullable=True),
        sa.Column(
            "target_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "locations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "work_modes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "industries",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "salary_min",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            "salary_max",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
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
            name=op.f("fk_search_profiles_base_profile_id_base_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_profiles")),
    )
    op.create_index(
        op.f("ix_search_profiles_base_profile_id"),
        "search_profiles",
        ["base_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop profile tables in reverse dependency order."""
    op.drop_index(
        op.f("ix_search_profiles_base_profile_id"),
        table_name="search_profiles",
    )
    op.drop_table("search_profiles")

    op.drop_index(
        op.f("ix_profile_projects_base_profile_id"),
        table_name="profile_projects",
    )
    op.drop_table("profile_projects")

    op.drop_index(
        op.f("ix_profile_educations_base_profile_id"),
        table_name="profile_educations",
    )
    op.drop_table("profile_educations")

    op.drop_index(
        op.f("ix_profile_experiences_base_profile_id"),
        table_name="profile_experiences",
    )
    op.drop_table("profile_experiences")

    op.drop_index(
        op.f("ix_profile_skills_base_profile_id"),
        table_name="profile_skills",
    )
    op.drop_table("profile_skills")

    op.drop_index(
        op.f("ix_base_profiles_user_id"),
        table_name="base_profiles",
    )
    op.drop_table("base_profiles")
