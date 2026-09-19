"""Tests for CV domain entities and ORM persistence models."""

import importlib
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.domain.cv import (
    CV,
    CVStatus,
)
from backend.infrastructure.database import (
    Base,
    BaseModel,
    BaseProfileModel,
    CVModel,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from backend.infrastructure.database.migrations import env as alembic_env

# ============================================================================
# 1. Domain Layer Independence & Pure Python Verification
# ============================================================================


def test_domain_entity_independence() -> None:
    """Verify CV domain has zero persistence or framework imports."""
    for mod_name in [
        "backend.domain.cv.enums",
        "backend.domain.cv.entities",
    ]:
        mod = sys.modules.get(mod_name)
        assert mod is not None, f"Module {mod_name} is not loaded"
        for attr_name, attr_val in mod.__dict__.items():
            if hasattr(attr_val, "__module__") and attr_val.__module__:
                err_msg = (
                    f"Domain module {mod_name} imports from persistence: "
                    f"{attr_name} ({attr_val.__module__})"
                )
                assert "sqlalchemy" not in attr_val.__module__.lower(), err_msg
                assert "alembic" not in attr_val.__module__.lower(), err_msg


def test_cv_domain_entity_instantiation_and_defaults() -> None:
    """Verify CV domain entity instantiation, string file_type, and defaults."""
    base_profile_id = uuid.uuid4()
    cv = CV(
        base_profile_id=base_profile_id,
        filename="resume_alice.pdf",
        file_type="pdf",
        raw_content="Experienced Software Engineer with Python expertise...",
    )

    assert isinstance(cv.id, uuid.UUID)
    assert cv.base_profile_id == base_profile_id
    assert cv.filename == "resume_alice.pdf"
    assert cv.file_type == "pdf"
    assert isinstance(cv.file_type, str)
    assert cv.raw_content.startswith("Experienced Software")
    assert cv.parsed_data == {}
    assert cv.status is CVStatus.PENDING_REVIEW
    assert cv.created_at is None


def test_enums_definitions() -> None:
    """Verify enum inheritance, members, and absence of CVFileType."""
    assert issubclass(CVStatus, str)
    assert CVStatus.PENDING_REVIEW == "PENDING_REVIEW"
    assert CVStatus.APPROVED == "APPROVED"
    assert CVStatus.REJECTED == "REJECTED"

    # Strict compliance: CVFileType enum must NOT exist
    cv_domain_mod = sys.modules.get("backend.domain.cv")
    assert cv_domain_mod is not None
    assert not hasattr(cv_domain_mod, "CVFileType")
    cv_enums_mod = sys.modules.get("backend.domain.cv.enums")
    assert cv_enums_mod is not None
    assert not hasattr(cv_enums_mod, "CVFileType")


# ============================================================================
# 2. ORM Inheritance and Table Names
# ============================================================================


def test_orm_inheritance() -> None:
    """Verify ORM model base class inheritance."""
    # CVModel has UUID primary key, but no updated_at (Base, UUIDPrimaryKeyMixin)
    assert issubclass(CVModel, Base)
    assert issubclass(CVModel, UUIDPrimaryKeyMixin)
    assert not issubclass(CVModel, BaseModel)
    assert not issubclass(CVModel, TimestampMixin)


def test_orm_table_names() -> None:
    """Verify table name matches design document."""
    assert CVModel.__tablename__ == "cvs"


# ============================================================================
# 3. Column Metadata & Server Defaults
# ============================================================================


def test_cvs_metadata() -> None:
    """Verify cvs columns, types, nullabilities, and defaults."""
    table = CVModel.__table__

    # id
    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable
    assert table.c.id.primary_key
    assert table.c.id.server_default is not None

    # base_profile_id
    assert isinstance(table.c.base_profile_id.type, UUID)
    assert not table.c.base_profile_id.nullable
    assert table.c.base_profile_id.index

    # filename
    assert isinstance(table.c.filename.type, String)
    assert table.c.filename.type.length == 255
    assert not table.c.filename.nullable

    # file_type
    assert isinstance(table.c.file_type.type, String)
    assert table.c.file_type.type.length == 50
    assert not table.c.file_type.nullable

    # raw_content
    assert isinstance(table.c.raw_content.type, Text)
    assert not table.c.raw_content.nullable

    # parsed_data
    assert isinstance(table.c.parsed_data.type, JSONB)
    assert not table.c.parsed_data.nullable
    assert table.c.parsed_data.server_default is not None
    assert "'{}'::jsonb" in str(table.c.parsed_data.server_default.arg)

    # status non-native enum (NO INDEX)
    assert isinstance(table.c.status.type, SQLEnum)
    assert table.c.status.type.native_enum is False
    assert table.c.status.type.length == 50
    assert not table.c.status.nullable
    assert not table.c.status.index
    assert table.c.status.server_default is not None
    assert "'PENDING_REVIEW'" in str(table.c.status.server_default.arg)

    # created_at
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert not table.c.created_at.nullable
    assert table.c.created_at.server_default is not None


# ============================================================================
# 4. Foreign Keys & OnDelete Rules
# ============================================================================


def test_foreign_keys_and_ondelete_rules() -> None:
    """Verify ON DELETE CASCADE from cvs.base_profile_id -> base_profiles.id."""
    fks = {fk.parent.name: fk for fk in CVModel.__table__.foreign_keys}
    assert "base_profile_id" in fks
    assert fks["base_profile_id"].column.table.name == "base_profiles"
    assert fks["base_profile_id"].ondelete == "CASCADE"


# ============================================================================
# 5. Relationships & Cascades
# ============================================================================


def test_relationships_and_cascades() -> None:
    """Verify bidirectional relationship and cascades between BaseProfile and CV."""
    # BaseProfileModel.cvs
    assert BaseProfileModel.cvs.property.cascade.delete_orphan
    assert BaseProfileModel.cvs.property.back_populates == "base_profile"

    # CVModel.base_profile
    assert CVModel.base_profile.property.back_populates == "cvs"


# ============================================================================
# 6. Domain <-> ORM Conversions
# ============================================================================


def test_cv_to_domain_and_from_domain() -> None:
    """Verify roundtrip conversion between domain entity and ORM model."""
    base_profile_id = uuid.uuid4()
    now_dt = datetime.now(UTC)

    cv_domain = CV(
        base_profile_id=base_profile_id,
        filename="developer_cv.pdf",
        file_type="pdf",
        raw_content="Python, FastAPI, PostgreSQL engineer...",
        parsed_data={"skills": ["Python", "PostgreSQL"], "years": 5},
        status=CVStatus.APPROVED,
        created_at=now_dt,
    )

    orm_model = CVModel.from_domain(cv_domain)
    assert orm_model.id == cv_domain.id
    assert orm_model.base_profile_id == base_profile_id
    assert orm_model.filename == "developer_cv.pdf"
    assert orm_model.file_type == "pdf"
    assert orm_model.raw_content == "Python, FastAPI, PostgreSQL engineer..."
    assert orm_model.parsed_data == {
        "skills": ["Python", "PostgreSQL"],
        "years": 5,
    }
    assert orm_model.status == CVStatus.APPROVED
    assert orm_model.created_at == now_dt

    reconverted = orm_model.to_domain()
    assert reconverted.id == cv_domain.id
    assert reconverted.base_profile_id == base_profile_id
    assert reconverted.filename == cv_domain.filename
    assert reconverted.file_type == "pdf"
    assert reconverted.raw_content == cv_domain.raw_content
    assert reconverted.parsed_data == cv_domain.parsed_data
    assert reconverted.status == CVStatus.APPROVED
    assert reconverted.created_at == now_dt


def test_cv_from_domain_without_created_at() -> None:
    """Verify from_domain works when created_at is None."""
    cv_domain = CV(
        base_profile_id=uuid.uuid4(),
        filename="resume.docx",
        file_type="docx",
        raw_content="Docx content...",
    )
    orm_model = CVModel.from_domain(cv_domain)
    assert orm_model.id == cv_domain.id
    assert orm_model.created_at is None


# ============================================================================
# 7. Model Repr
# ============================================================================


def test_cv_model_repr() -> None:
    """Verify string representation of CVModel."""
    cv_id = uuid.uuid4()
    bp_id = uuid.uuid4()
    model = CVModel(
        id=cv_id,
        base_profile_id=bp_id,
        filename="my_cv.pdf",
        file_type="pdf",
        raw_content="content",
        status=CVStatus.PENDING_REVIEW,
    )
    repr_str = repr(model)
    assert f"id={cv_id}" in repr_str
    assert f"base_profile_id={bp_id}" in repr_str
    assert "filename='my_cv.pdf'" in repr_str
    assert "status='PENDING_REVIEW'" in repr_str


# ============================================================================
# 8. Schema Fidelity Negative Checks
# ============================================================================


def test_schema_fidelity_negative_checks() -> None:
    """Verify absence of unapproved fields and absence of status index."""
    cols = CVModel.__table__.c

    # cvs has NO updated_at
    assert "updated_at" not in cols
    assert not hasattr(CV, "updated_at")

    # cvs has NO user_id (linked only via base_profile_id)
    assert "user_id" not in cols
    assert not hasattr(CV, "user_id")

    # cvs has NO job_id or application_id
    assert "job_id" not in cols
    assert not hasattr(CV, "job_id")
    assert "application_id" not in cols
    assert not hasattr(CV, "application_id")

    # status has NO index
    assert not cols["status"].index

    # file_type is NOT an enum column
    assert not isinstance(cols["file_type"].type, SQLEnum)


# ============================================================================
# 9. Alembic Metadata Discovery and Migration Chain
# ============================================================================


def test_alembic_metadata_discovery() -> None:
    """Verify Alembic target_metadata contains cvs."""
    tables = alembic_env.target_metadata.tables
    assert "cvs" in tables


def test_migration_file_structure_and_revision_chain() -> None:
    """Verify migration 0006 links linearly to 0005_crawl_runs."""
    mod = importlib.import_module(
        "backend.infrastructure.database.migrations.versions.20260919_0006_cvs_create_table"
    )
    assert mod.revision == "0006_cvs"
    assert mod.down_revision == "0005_crawl_runs"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")
