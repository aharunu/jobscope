"""Tests for Source, Job, and RawJob models, entities, and discovery."""

import datetime
import importlib
import sys
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.domain.job import (
    Job,
    JobStatus,
    RawJob,
)
from backend.domain.source import Source
from backend.infrastructure.database import (
    Base,
    BaseModel,
    JobModel,
    RawJobModel,
    SourceModel,
    UUIDPrimaryKeyMixin,
)
from backend.infrastructure.database.migrations import env as alembic_env

# ============================================================================
# 1. Domain Layer Independence & Pure Python Verification
# ============================================================================


def test_domain_entity_independence() -> None:
    """Verify source and job domains have zero SQLAlchemy imports."""
    for mod_name in [
        "backend.domain.source.entities",
        "backend.domain.job.enums",
        "backend.domain.job.entities",
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


def test_source_domain_entity_instantiation_and_defaults() -> None:
    """Verify Source domain entity default values and slots."""
    source = Source(
        name="Greenhouse Board",
        url="https://boards.greenhouse.io/test",
        ats_type="greenhouse",
    )
    assert isinstance(source.id, uuid.UUID)
    assert source.name == "Greenhouse Board"
    assert source.url == "https://boards.greenhouse.io/test"
    assert source.ats_type == "greenhouse"
    assert source.company is None
    assert source.country is None
    assert source.active is True
    assert source.adapter_config == {}
    assert source.pagination_config == {}
    assert source.endpoint_config == {}
    assert source.rate_limit_config == {}
    assert source.metadata == {}
    assert source.created_at is None
    assert source.updated_at is None


def test_job_status_enum() -> None:
    """Verify JobStatus enum values and str inheritance."""
    assert issubclass(JobStatus, str)
    assert JobStatus.ACTIVE == "ACTIVE"
    assert JobStatus.CLOSED == "CLOSED"
    assert JobStatus("ACTIVE") is JobStatus.ACTIVE
    assert JobStatus("CLOSED") is JobStatus.CLOSED


def test_job_domain_entity_instantiation_and_defaults() -> None:
    """Verify Job domain entity default values and slots."""
    source_id = uuid.uuid4()
    job = Job(
        source_id=source_id,
        canonical_url="https://jobs.example.com/p/123",
        company="Example Corp",
        title="Software Engineer",
        description="Write code.",
        content_hash="abc123hash",
    )
    assert isinstance(job.id, uuid.UUID)
    assert job.source_id == source_id
    assert job.canonical_url == "https://jobs.example.com/p/123"
    assert job.company == "Example Corp"
    assert job.title == "Software Engineer"
    assert job.description == "Write code."
    assert job.content_hash == "abc123hash"
    assert job.external_job_id is None
    assert job.responsibilities is None
    assert job.location is None
    assert job.work_mode is None
    assert job.employment_type is None
    assert job.salary is None
    assert job.published_at is None
    assert job.first_seen_at is None
    assert job.last_seen_at is None
    assert job.closed_at is None
    assert job.status is JobStatus.ACTIVE
    assert job.created_at is None
    assert job.updated_at is None


def test_raw_job_domain_entity_instantiation_and_defaults() -> None:
    """Verify RawJob domain entity default values and slots."""
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()
    raw_job = RawJob(
        job_id=job_id,
        source_id=source_id,
        raw_content='{"title": "SE"}',
        content_type="application/json",
    )
    assert isinstance(raw_job.id, uuid.UUID)
    assert raw_job.job_id == job_id
    assert raw_job.source_id == source_id
    assert raw_job.raw_content == '{"title": "SE"}'
    assert raw_job.content_type == "application/json"
    assert raw_job.fetched_at is None


# ============================================================================
# 2. ORM Inheritance, Table Names, and Declarative Metadata
# ============================================================================


def test_orm_inheritance() -> None:
    """Verify ORM model base class inheritance."""
    assert issubclass(SourceModel, BaseModel)
    assert issubclass(JobModel, BaseModel)
    assert issubclass(RawJobModel, Base)
    assert issubclass(RawJobModel, UUIDPrimaryKeyMixin)
    # RawJobModel must NOT inherit BaseModel (it lacks created_at/updated_at)
    assert not issubclass(RawJobModel, BaseModel)


def test_orm_table_names() -> None:
    """Verify table names match design document."""
    assert SourceModel.__tablename__ == "sources"
    assert JobModel.__tablename__ == "jobs"
    assert RawJobModel.__tablename__ == "raw_jobs"


# ============================================================================
# 3. SourceModel Column & Metadata Specifications
# ============================================================================


def test_source_model_columns() -> None:
    """Verify SourceModel column definitions, types, nullability, and defaults."""
    table = SourceModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable
    assert table.c.id.primary_key

    assert isinstance(table.c.name.type, String)
    assert table.c.name.type.length == 150
    assert not table.c.name.nullable

    assert isinstance(table.c.company.type, String)
    assert table.c.company.type.length == 150
    assert table.c.company.nullable

    assert isinstance(table.c.url.type, Text)
    assert not table.c.url.nullable

    assert isinstance(table.c.country.type, String)
    assert table.c.country.type.length == 50
    assert table.c.country.nullable

    assert isinstance(table.c.ats_type.type, String)
    assert table.c.ats_type.type.length == 50
    assert not table.c.ats_type.nullable

    assert isinstance(table.c.active.type, Boolean)
    assert not table.c.active.nullable
    assert table.c.active.server_default is not None
    assert "true" in str(table.c.active.server_default.arg).lower()

    for col_name in [
        "adapter_config",
        "pagination_config",
        "endpoint_config",
        "rate_limit_config",
        "metadata",
    ]:
        col = table.c[col_name]
        assert isinstance(col.type, JSONB)
        assert not col.nullable
        assert col.server_default is not None
        assert "'{}'::jsonb" in str(col.server_default.arg).lower()

    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert not table.c.created_at.nullable

    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert not table.c.updated_at.nullable


def test_source_model_metadata_column_and_key() -> None:
    """Verify physical column is 'metadata' and ORM attribute is 'metadata_'."""
    table = SourceModel.__table__
    # Physical column in DB must be "metadata"
    assert "metadata" in table.c
    col = table.c["metadata"]
    assert col.name == "metadata"

    # ORM mapper attribute name is "metadata_"
    from sqlalchemy import inspect

    mapper = inspect(SourceModel)
    assert "metadata_" in [a.key for a in mapper.column_attrs]

    # Base.metadata is preserved as MetaData and not conflicted
    import sqlalchemy as sa

    assert isinstance(SourceModel.metadata, sa.MetaData)

    # Attribute access on model instance via metadata_
    source_model = SourceModel(
        name="Test",
        url="https://test.com",
        ats_type="custom",
        metadata_={"tier": 1},
    )
    assert source_model.metadata_ == {"tier": 1}
    source_model.metadata_ = {"tier": 2, "flag": True}
    assert source_model.metadata_ == {"tier": 2, "flag": True}


# ============================================================================
# 4. JobModel Column, Enum, and Constraint Specifications
# ============================================================================


def test_job_model_columns() -> None:
    """Verify JobModel column definitions, types, nullability, and lengths."""
    table = JobModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable
    assert table.c.id.primary_key

    # source_id FK
    assert isinstance(table.c.source_id.type, UUID)
    assert not table.c.source_id.nullable
    assert table.c.source_id.index

    # external_job_id
    assert isinstance(table.c.external_job_id.type, String)
    assert table.c.external_job_id.type.length == 255
    assert table.c.external_job_id.nullable

    # canonical_url
    assert isinstance(table.c.canonical_url.type, Text)
    assert not table.c.canonical_url.nullable
    assert table.c.canonical_url.unique

    # company & title
    assert isinstance(table.c.company.type, String)
    assert table.c.company.type.length == 255
    assert not table.c.company.nullable
    assert table.c.company.index

    assert isinstance(table.c.title.type, String)
    assert table.c.title.type.length == 255
    assert not table.c.title.nullable
    assert table.c.title.index

    # description & responsibilities
    assert isinstance(table.c.description.type, Text)
    assert not table.c.description.nullable
    assert isinstance(table.c.responsibilities.type, Text)
    assert table.c.responsibilities.nullable

    # location, work_mode, employment_type, salary
    assert isinstance(table.c.location.type, String)
    assert table.c.location.type.length == 255
    assert table.c.location.nullable

    assert isinstance(table.c.work_mode.type, String)
    assert table.c.work_mode.type.length == 50
    assert table.c.work_mode.nullable

    assert isinstance(table.c.employment_type.type, String)
    assert table.c.employment_type.type.length == 50
    assert table.c.employment_type.nullable

    assert isinstance(table.c.salary.type, String)
    assert table.c.salary.type.length == 255
    assert table.c.salary.nullable

    # timestamps
    assert isinstance(table.c.published_at.type, DateTime)
    assert table.c.published_at.type.timezone is True
    assert table.c.published_at.nullable

    assert isinstance(table.c.first_seen_at.type, DateTime)
    assert table.c.first_seen_at.type.timezone is True
    assert not table.c.first_seen_at.nullable
    assert table.c.first_seen_at.index
    assert table.c.first_seen_at.server_default is not None
    assert "now()" in str(table.c.first_seen_at.server_default.arg).lower()

    assert isinstance(table.c.last_seen_at.type, DateTime)
    assert table.c.last_seen_at.type.timezone is True
    assert not table.c.last_seen_at.nullable
    assert table.c.last_seen_at.server_default is not None
    assert "now()" in str(table.c.last_seen_at.server_default.arg).lower()

    assert isinstance(table.c.closed_at.type, DateTime)
    assert table.c.closed_at.type.timezone is True
    assert table.c.closed_at.nullable

    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert not table.c.created_at.nullable

    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert not table.c.updated_at.nullable

    # content_hash
    assert isinstance(table.c.content_hash.type, String)
    assert table.c.content_hash.type.length == 64
    assert not table.c.content_hash.nullable


def test_job_status_column_non_native_enum_and_default() -> None:
    """Verify JobModel.status is non-native VARCHAR(50) enum with 'ACTIVE' default."""
    table = JobModel.__table__
    col = table.c.status

    assert isinstance(col.type, SQLEnum)
    assert col.type.native_enum is False
    assert col.type.length == 50
    assert not col.nullable
    assert col.index
    assert col.server_default is not None
    assert "'ACTIVE'" in str(col.server_default.arg)


def test_job_unique_constraints() -> None:
    """Verify unique constraint on (source_id, external_job_id) and canonical_url."""
    table = JobModel.__table__

    # canonical_url is unique
    assert table.c.canonical_url.unique

    # Composite unique constraint
    composite_uqs = [
        c
        for c in table.constraints
        if isinstance(c, UniqueConstraint)
        and {col.name for col in c.columns} == {"source_id", "external_job_id"}
    ]
    assert len(composite_uqs) == 1
    assert composite_uqs[0].name == "uq_source_external_job_id"


# ============================================================================
# 5. RawJobModel Column Specifications
# ============================================================================


def test_raw_job_model_columns() -> None:
    """Verify RawJobModel column definitions, types, nullability, and immutability."""
    table = RawJobModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable
    assert table.c.id.primary_key

    assert isinstance(table.c.job_id.type, UUID)
    assert not table.c.job_id.nullable
    assert table.c.job_id.index

    assert isinstance(table.c.source_id.type, UUID)
    assert not table.c.source_id.nullable
    assert table.c.source_id.index

    assert isinstance(table.c.raw_content.type, Text)
    assert not table.c.raw_content.nullable

    assert isinstance(table.c.content_type.type, String)
    assert table.c.content_type.type.length == 50
    assert not table.c.content_type.nullable

    assert isinstance(table.c.fetched_at.type, DateTime)
    assert table.c.fetched_at.type.timezone is True
    assert not table.c.fetched_at.nullable
    assert table.c.fetched_at.server_default is not None
    assert "now()" in str(table.c.fetched_at.server_default.arg).lower()

    # Verify absence of created_at / updated_at (immutable raw archive)
    assert "created_at" not in table.c
    assert "updated_at" not in table.c


# ============================================================================
# 6. Foreign Keys & OnDelete Rules
# ============================================================================


def test_foreign_keys_and_ondelete_rules() -> None:
    """Verify FKs and ondelete rules: RESTRICT for job->source, CASCADE for raw_job."""
    # jobs.source_id -> sources.id ON DELETE RESTRICT
    job_fks = list(JobModel.__table__.foreign_keys)
    assert len(job_fks) == 1
    fk = job_fks[0]
    assert fk.column.table.name == "sources"
    assert fk.column.name == "id"
    assert fk.ondelete == "RESTRICT"

    # raw_jobs FKs
    raw_job_fks = {fk.parent.name: fk for fk in RawJobModel.__table__.foreign_keys}
    assert "job_id" in raw_job_fks
    assert raw_job_fks["job_id"].column.table.name == "jobs"
    assert raw_job_fks["job_id"].column.name == "id"
    assert raw_job_fks["job_id"].ondelete == "CASCADE"

    assert "source_id" in raw_job_fks
    assert raw_job_fks["source_id"].column.table.name == "sources"
    assert raw_job_fks["source_id"].column.name == "id"
    assert raw_job_fks["source_id"].ondelete == "CASCADE"


# ============================================================================
# 7. Relationships & Cascade Configurations
# ============================================================================


def test_source_model_relationships() -> None:
    """Verify SourceModel.jobs relationship has NO cascade delete."""
    jobs_rel = SourceModel.jobs.property
    assert jobs_rel.back_populates == "source"
    # Source deletion MUST NOT cascade to jobs (ON DELETE RESTRICT)
    cascade_str = jobs_rel.cascade
    assert "delete" not in cascade_str
    assert "delete-orphan" not in cascade_str


def test_job_model_relationships() -> None:
    """Verify JobModel relationships and cascade rules."""
    source_rel = JobModel.source.property
    assert source_rel.back_populates == "jobs"

    raw_jobs_rel = JobModel.raw_jobs.property
    assert raw_jobs_rel.back_populates == "job"
    assert raw_jobs_rel.cascade.delete
    assert raw_jobs_rel.cascade.delete_orphan


def test_raw_job_model_relationships() -> None:
    """Verify RawJobModel relationships."""
    job_rel = RawJobModel.job.property
    assert job_rel.back_populates == "raw_jobs"

    source_rel = RawJobModel.source.property
    assert source_rel.mapper.class_ is SourceModel


# ============================================================================
# 8. Domain <-> ORM Conversions (to_domain / from_domain)
# ============================================================================


def test_source_to_domain_and_from_domain() -> None:
    """Verify bi-directional conversion between Source domain and SourceModel."""
    now = datetime.datetime.now(datetime.UTC)
    source_id = uuid.uuid4()
    domain_source = Source(
        id=source_id,
        name="Getir Greenhouse",
        company="Getir",
        url="https://boards.greenhouse.io/getir",
        country="TR",
        ats_type="greenhouse",
        active=True,
        adapter_config={"board_token": "getir"},
        pagination_config={"type": "offset", "limit": 50},
        endpoint_config={"headers": {"X-Custom": "val"}},
        rate_limit_config={"max_retries": 3, "backoff": 1.5},
        metadata={"priority": "high"},
        created_at=now,
        updated_at=now,
    )

    # from_domain
    model = SourceModel.from_domain(domain_source)
    assert model.id == source_id
    assert model.name == "Getir Greenhouse"
    assert model.company == "Getir"
    assert model.url == "https://boards.greenhouse.io/getir"
    assert model.country == "TR"
    assert model.ats_type == "greenhouse"
    assert model.active is True
    assert model.adapter_config == {"board_token": "getir"}
    assert model.pagination_config == {"type": "offset", "limit": 50}
    assert model.endpoint_config == {"headers": {"X-Custom": "val"}}
    assert model.rate_limit_config == {"max_retries": 3, "backoff": 1.5}
    assert model.metadata_ == {"priority": "high"}
    assert model.created_at == now
    assert model.updated_at == now

    # to_domain
    reconstructed = model.to_domain()
    assert reconstructed.id == domain_source.id
    assert reconstructed.name == domain_source.name
    assert reconstructed.company == domain_source.company
    assert reconstructed.url == domain_source.url
    assert reconstructed.country == domain_source.country
    assert reconstructed.ats_type == domain_source.ats_type
    assert reconstructed.active == domain_source.active
    assert reconstructed.adapter_config == domain_source.adapter_config
    assert reconstructed.pagination_config == domain_source.pagination_config
    assert reconstructed.endpoint_config == domain_source.endpoint_config
    assert reconstructed.rate_limit_config == domain_source.rate_limit_config
    assert reconstructed.metadata == domain_source.metadata
    assert reconstructed.created_at == domain_source.created_at
    assert reconstructed.updated_at == domain_source.updated_at


def test_source_from_domain_without_timestamps() -> None:
    """Verify from_domain works when created_at and updated_at are None."""
    domain_source = Source(
        name="Lever Board",
        url="https://jobs.lever.co/example",
        ats_type="lever",
    )
    model = SourceModel.from_domain(domain_source)
    assert model.name == "Lever Board"
    assert model.created_at is None
    assert model.updated_at is None


def test_job_to_domain_and_from_domain() -> None:
    """Verify bi-directional conversion between Job domain and JobModel."""
    now = datetime.datetime.now(datetime.UTC)
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()
    domain_job = Job(
        id=job_id,
        source_id=source_id,
        external_job_id="ext-999",
        canonical_url="https://jobs.lever.co/example/ext-999",
        company="TechCorp",
        title="Senior Python Engineer",
        description="Write clean code and design architectures.",
        responsibilities="Lead team; review PRs.",
        location="Istanbul / Remote",
        work_mode="Remote",
        employment_type="Full-time",
        salary="100k - 120k",
        published_at=now,
        first_seen_at=now,
        last_seen_at=now,
        closed_at=None,
        status=JobStatus.ACTIVE,
        content_hash="abcde1234567890f",
        created_at=now,
        updated_at=now,
    )

    # from_domain
    model = JobModel.from_domain(domain_job)
    assert model.id == job_id
    assert model.source_id == source_id
    assert model.external_job_id == "ext-999"
    assert model.canonical_url == "https://jobs.lever.co/example/ext-999"
    assert model.company == "TechCorp"
    assert model.title == "Senior Python Engineer"
    assert model.description == "Write clean code and design architectures."
    assert model.responsibilities == "Lead team; review PRs."
    assert model.location == "Istanbul / Remote"
    assert model.work_mode == "Remote"
    assert model.employment_type == "Full-time"
    assert model.salary == "100k - 120k"
    assert model.published_at == now
    assert model.first_seen_at == now
    assert model.last_seen_at == now
    assert model.closed_at is None
    assert model.status == JobStatus.ACTIVE
    assert model.content_hash == "abcde1234567890f"
    assert model.created_at == now
    assert model.updated_at == now

    # to_domain
    reconstructed = model.to_domain()
    assert reconstructed.id == domain_job.id
    assert reconstructed.source_id == domain_job.source_id
    assert reconstructed.external_job_id == domain_job.external_job_id
    assert reconstructed.canonical_url == domain_job.canonical_url
    assert reconstructed.company == domain_job.company
    assert reconstructed.title == domain_job.title
    assert reconstructed.description == domain_job.description
    assert reconstructed.responsibilities == domain_job.responsibilities
    assert reconstructed.location == domain_job.location
    assert reconstructed.work_mode == domain_job.work_mode
    assert reconstructed.employment_type == domain_job.employment_type
    assert reconstructed.salary == domain_job.salary
    assert reconstructed.published_at == domain_job.published_at
    assert reconstructed.first_seen_at == domain_job.first_seen_at
    assert reconstructed.last_seen_at == domain_job.last_seen_at
    assert reconstructed.closed_at == domain_job.closed_at
    assert reconstructed.status == domain_job.status
    assert reconstructed.content_hash == domain_job.content_hash
    assert reconstructed.created_at == domain_job.created_at
    assert reconstructed.updated_at == domain_job.updated_at


def test_job_from_domain_without_timestamps() -> None:
    """Verify from_domain works when optional timestamps are None."""
    domain_job = Job(
        source_id=uuid.uuid4(),
        canonical_url="https://example.com/job/1",
        company="Startup",
        title="Backend Dev",
        description="Python dev wanted",
        content_hash="hash123",
    )
    model = JobModel.from_domain(domain_job)
    assert model.company == "Startup"
    assert model.first_seen_at is None
    assert model.last_seen_at is None
    assert model.created_at is None
    assert model.updated_at is None


def test_raw_job_to_domain_and_from_domain() -> None:
    """Verify bi-directional conversion between RawJob domain and RawJobModel."""
    now = datetime.datetime.now(datetime.UTC)
    raw_id = uuid.uuid4()
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()
    domain_raw = RawJob(
        id=raw_id,
        job_id=job_id,
        source_id=source_id,
        raw_content="<html><body>Job details</body></html>",
        content_type="text/html",
        fetched_at=now,
    )

    # from_domain
    model = RawJobModel.from_domain(domain_raw)
    assert model.id == raw_id
    assert model.job_id == job_id
    assert model.source_id == source_id
    assert model.raw_content == "<html><body>Job details</body></html>"
    assert model.content_type == "text/html"
    assert model.fetched_at == now

    # to_domain
    reconstructed = model.to_domain()
    assert reconstructed.id == domain_raw.id
    assert reconstructed.job_id == domain_raw.job_id
    assert reconstructed.source_id == domain_raw.source_id
    assert reconstructed.raw_content == domain_raw.raw_content
    assert reconstructed.content_type == domain_raw.content_type
    assert reconstructed.fetched_at == domain_raw.fetched_at


def test_raw_job_from_domain_without_fetched_at() -> None:
    """Verify RawJob from_domain without fetched_at leaves it unset for ORM default."""
    domain_raw = RawJob(
        job_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        raw_content="{}",
        content_type="application/json",
    )
    model = RawJobModel.from_domain(domain_raw)
    assert model.fetched_at is None


# ============================================================================
# 9. Model Repr Tests
# ============================================================================


def test_model_reprs() -> None:
    """Verify __repr__ formats for SourceModel, JobModel, and RawJobModel."""
    source_id = uuid.uuid4()
    source = SourceModel(
        id=source_id,
        name="Ashby",
        url="https://ashbyhq.com",
        ats_type="ashby",
    )
    assert repr(source) == f"<SourceModel id={source_id} name='Ashby' ats_type='ashby'>"

    job_id = uuid.uuid4()
    job = JobModel(
        id=job_id,
        company="Acme",
        title="Lead Architect",
    )
    assert repr(job) == f"<JobModel id={job_id} company='Acme' title='Lead Architect'>"

    raw_id = uuid.uuid4()
    raw = RawJobModel(
        id=raw_id,
        content_type="text/html",
    )
    assert repr(raw) == f"<RawJobModel id={raw_id} content_type='text/html'>"


# ============================================================================
# 10. Alembic Metadata Discovery and Migration Chain
# ============================================================================


def test_alembic_metadata_discovery() -> None:
    """Verify Alembic target_metadata contains sources, jobs, and raw_jobs tables."""
    tables = alembic_env.target_metadata.tables
    assert "sources" in tables
    assert "jobs" in tables
    assert "raw_jobs" in tables


def test_migration_file_structure_and_revision_chain() -> None:
    """Verify migration 0003_jobs_and_sources links to 0002_profiles."""
    mod = importlib.import_module(
        "backend.infrastructure.database.migrations.versions.20260919_0003_jobs_and_sources_create_tables"
    )
    assert mod.revision == "0003_jobs_and_sources"
    assert mod.down_revision == "0002_profiles"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")
