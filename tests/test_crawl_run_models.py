"""Tests for CrawlRun and CrawlRunJob domain entities and ORM persistence models."""

import importlib
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Integer,
    PrimaryKeyConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID

from backend.domain.crawl import (
    CrawlJobAction,
    CrawlRun,
    CrawlRunJob,
    CrawlStatus,
)
from backend.infrastructure.database import (
    Base,
    BaseModel,
    CrawlRunJobModel,
    CrawlRunModel,
    JobModel,
    SourceModel,
    UUIDPrimaryKeyMixin,
)
from backend.infrastructure.database.migrations import env as alembic_env

# ============================================================================
# 1. Domain Layer Independence & Pure Python Verification
# ============================================================================


def test_domain_entity_independence() -> None:
    """Verify crawl domain has zero persistence imports."""
    for mod_name in [
        "backend.domain.crawl.enums",
        "backend.domain.crawl.entities",
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


def test_crawl_domain_entities_and_defaults() -> None:
    """Verify CrawlRun and CrawlRunJob domain entities instantiation and defaults."""
    source_id = uuid.uuid4()
    run = CrawlRun(source_id=source_id)

    assert isinstance(run.id, uuid.UUID)
    assert run.source_id == source_id
    assert run.status is CrawlStatus.RUNNING
    assert run.started_at is None
    assert run.finished_at is None
    assert run.jobs_found == 0
    assert run.jobs_created == 0
    assert run.jobs_updated == 0
    assert run.jobs_closed == 0
    assert run.error_count == 0
    assert run.created_at is None

    job_id = uuid.uuid4()
    link = CrawlRunJob(
        crawl_run_id=run.id,
        job_id=job_id,
        action=CrawlJobAction.CREATED,
    )
    assert link.crawl_run_id == run.id
    assert link.job_id == job_id
    assert link.action is CrawlJobAction.CREATED


def test_enums_definitions() -> None:
    """Verify enum inheritance and members."""
    assert issubclass(CrawlStatus, str)
    assert CrawlStatus.RUNNING == "RUNNING"
    assert CrawlStatus.COMPLETED == "COMPLETED"
    assert CrawlStatus.FAILED == "FAILED"
    assert CrawlStatus.PARTIAL == "PARTIAL"

    assert issubclass(CrawlJobAction, str)
    assert CrawlJobAction.CREATED == "CREATED"
    assert CrawlJobAction.UPDATED == "UPDATED"
    assert CrawlJobAction.UNCHANGED == "UNCHANGED"
    assert CrawlJobAction.CLOSED == "CLOSED"


# ============================================================================
# 2. ORM Inheritance and Table Names
# ============================================================================


def test_orm_inheritance() -> None:
    """Verify ORM model base class inheritance."""
    # CrawlRunModel has UUID primary key, but no updated_at (Base, UUIDPrimaryKeyMixin)
    assert issubclass(CrawlRunModel, Base)
    assert issubclass(CrawlRunModel, UUIDPrimaryKeyMixin)
    assert not issubclass(CrawlRunModel, BaseModel)

    # CrawlRunJobModel has composite PK, does not use UUIDPrimaryKeyMixin
    assert issubclass(CrawlRunJobModel, Base)
    assert not issubclass(CrawlRunJobModel, UUIDPrimaryKeyMixin)
    assert not issubclass(CrawlRunJobModel, BaseModel)


def test_orm_table_names() -> None:
    """Verify table names match design document."""
    assert CrawlRunModel.__tablename__ == "crawl_runs"
    assert CrawlRunJobModel.__tablename__ == "crawl_run_jobs"


# ============================================================================
# 3. Column Metadata & Server Defaults
# ============================================================================


def test_crawl_runs_metadata() -> None:
    """Verify crawl_runs columns, types, nullabilities, and server defaults."""
    table = CrawlRunModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable

    assert isinstance(table.c.source_id.type, UUID)
    assert not table.c.source_id.nullable
    assert table.c.source_id.index

    # started_at
    assert isinstance(table.c.started_at.type, DateTime)
    assert table.c.started_at.type.timezone is True
    assert not table.c.started_at.nullable
    assert table.c.started_at.server_default is not None

    # finished_at (nullable)
    assert isinstance(table.c.finished_at.type, DateTime)
    assert table.c.finished_at.type.timezone is True
    assert table.c.finished_at.nullable

    # status non-native enum
    assert isinstance(table.c.status.type, SQLEnum)
    assert table.c.status.type.native_enum is False
    assert table.c.status.type.length == 50
    assert not table.c.status.nullable
    assert table.c.status.index
    assert table.c.status.server_default is not None
    assert "'RUNNING'" in str(table.c.status.server_default.arg)

    # Counters: INT NOT NULL, server default 0
    for col_name in [
        "jobs_found",
        "jobs_created",
        "jobs_updated",
        "jobs_closed",
        "error_count",
    ]:
        col = table.c[col_name]
        assert isinstance(col.type, Integer)
        assert not col.nullable
        assert col.server_default is not None
        assert "0" in str(col.server_default.arg)

    # created_at
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert not table.c.created_at.nullable
    assert table.c.created_at.server_default is not None


def test_crawl_run_jobs_metadata() -> None:
    """Verify crawl_run_jobs composite PK, columns, and indexes."""
    table = CrawlRunJobModel.__table__

    assert isinstance(table.c.crawl_run_id.type, UUID)
    assert not table.c.crawl_run_id.nullable
    assert table.c.crawl_run_id.primary_key

    assert isinstance(table.c.job_id.type, UUID)
    assert not table.c.job_id.nullable
    assert table.c.job_id.primary_key
    assert table.c.job_id.index

    # Composite primary key
    pks = [c for c in table.constraints if isinstance(c, PrimaryKeyConstraint)]
    assert len(pks) == 1
    assert {col.name for col in pks[0].columns} == {"crawl_run_id", "job_id"}

    # action non-native enum
    assert isinstance(table.c.action.type, SQLEnum)
    assert table.c.action.type.native_enum is False
    assert table.c.action.type.length == 50
    assert not table.c.action.nullable


# ============================================================================
# 4. Foreign Keys & OnDelete Rules
# ============================================================================


def test_foreign_keys_and_ondelete_rules() -> None:
    """Verify ON DELETE CASCADE across crawl_runs and crawl_run_jobs."""
    # crawl_runs.source_id -> sources.id
    cr_fks = {fk.parent.name: fk for fk in CrawlRunModel.__table__.foreign_keys}
    assert cr_fks["source_id"].column.table.name == "sources"
    assert cr_fks["source_id"].ondelete == "CASCADE"

    # crawl_run_jobs foreign keys
    crj_fks = {fk.parent.name: fk for fk in CrawlRunJobModel.__table__.foreign_keys}
    assert crj_fks["crawl_run_id"].column.table.name == "crawl_runs"
    assert crj_fks["crawl_run_id"].ondelete == "CASCADE"
    assert crj_fks["job_id"].column.table.name == "jobs"
    assert crj_fks["job_id"].ondelete == "CASCADE"


# ============================================================================
# 5. Relationships & Cascades
# ============================================================================


def test_relationships_and_cascades() -> None:
    """Verify bidirectional relationships and cascades."""
    # SourceModel.crawl_runs
    assert SourceModel.crawl_runs.property.cascade.delete_orphan
    assert SourceModel.crawl_runs.property.back_populates == "source"

    # CrawlRunModel.crawl_run_jobs
    assert CrawlRunModel.crawl_run_jobs.property.cascade.delete_orphan
    assert CrawlRunModel.crawl_run_jobs.property.back_populates == "crawl_run"

    # JobModel.crawl_run_jobs
    assert JobModel.crawl_run_jobs.property.cascade.delete_orphan
    assert JobModel.crawl_run_jobs.property.back_populates == "job"

    # CrawlRunJobModel relationships
    assert CrawlRunJobModel.crawl_run.property.back_populates == "crawl_run_jobs"
    assert CrawlRunJobModel.job.property.back_populates == "crawl_run_jobs"


# ============================================================================
# 6. Domain <-> ORM Conversions (Roundtrip)
# ============================================================================


def test_crawl_run_roundtrip_conversion() -> None:
    """Verify CrawlRun to_domain / from_domain roundtrip."""
    now = datetime.now(UTC)
    domain_run = CrawlRun(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        status=CrawlStatus.COMPLETED,
        started_at=now,
        finished_at=now,
        jobs_found=42,
        jobs_created=10,
        jobs_updated=5,
        jobs_closed=2,
        error_count=0,
        created_at=now,
    )
    model = CrawlRunModel.from_domain(domain_run)
    reconstructed = model.to_domain()
    assert reconstructed == domain_run


def test_crawl_run_job_roundtrip_conversion() -> None:
    """Verify CrawlRunJob to_domain / from_domain roundtrip."""
    domain_link = CrawlRunJob(
        crawl_run_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        action=CrawlJobAction.UPDATED,
    )
    model = CrawlRunJobModel.from_domain(domain_link)
    reconstructed = model.to_domain()
    assert reconstructed == domain_link


# ============================================================================
# 7. Model Reprs
# ============================================================================


def test_model_reprs() -> None:
    """Verify __repr__ implementations."""
    run_id = uuid.uuid4()
    source_id = uuid.uuid4()
    run = CrawlRunModel(
        id=run_id,
        source_id=source_id,
        status=CrawlStatus.RUNNING,
    )
    assert repr(run) == (
        f"<CrawlRunModel id={run_id} source_id={source_id} status='RUNNING'>"
    )

    job_id = uuid.uuid4()
    link = CrawlRunJobModel(
        crawl_run_id=run_id,
        job_id=job_id,
        action=CrawlJobAction.CREATED,
    )
    assert repr(link) == (
        f"<CrawlRunJobModel crawl_run_id={run_id} job_id={job_id} action='CREATED'>"
    )


# ============================================================================
# 8. Schema Fidelity & Negative Column Checks
# ============================================================================


def test_schema_fidelity_negative_checks() -> None:
    """Verify absence of unapproved fields."""
    cr_cols = CrawlRunModel.__table__.c
    # crawl_runs has NO updated_at
    assert "updated_at" not in cr_cols
    assert not hasattr(CrawlRun, "updated_at")

    crj_cols = CrawlRunJobModel.__table__.c
    # crawl_run_jobs has NO surrogate id, created_at, or updated_at
    assert "id" not in crj_cols
    assert "created_at" not in crj_cols
    assert "updated_at" not in crj_cols
    assert not hasattr(CrawlRunJob, "id")
    assert not hasattr(CrawlRunJob, "created_at")
    assert not hasattr(CrawlRunJob, "updated_at")


# ============================================================================
# 9. Alembic Metadata Discovery and Migration Chain
# ============================================================================


def test_alembic_metadata_discovery() -> None:
    """Verify Alembic target_metadata contains crawl_runs and crawl_run_jobs."""
    tables = alembic_env.target_metadata.tables
    assert "crawl_runs" in tables
    assert "crawl_run_jobs" in tables


def test_migration_file_structure_and_revision_chain() -> None:
    """Verify migration 0005 links to 0004_matching_and_applications."""
    mod = importlib.import_module(
        "backend.infrastructure.database.migrations.versions.20260919_0005_crawl_runs_create_tables"
    )
    assert mod.revision == "0005_crawl_runs"
    assert mod.down_revision == "0004_matching_and_applications"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")
