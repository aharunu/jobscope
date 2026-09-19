"""Tests for matching, requirement, and application models and domain entities."""

import importlib
import sys
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID

from backend.domain.application import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
)
from backend.domain.job import (
    JobRequirement,
    RequirementLevel,
    RequirementType,
)
from backend.domain.matching import (
    AIAnalysis,
    AIEvidence,
    MatchResult,
    MatchStatus,
    RequirementMatch,
)
from backend.infrastructure.database import (
    AIAnalysisModel,
    AIEvidenceModel,
    ApplicationModel,
    ApplicationStatusHistoryModel,
    Base,
    BaseModel,
    BaseProfileModel,
    JobModel,
    JobRequirementModel,
    MatchResultModel,
    RequirementMatchModel,
    SearchProfileModel,
    UserModel,
    UUIDPrimaryKeyMixin,
)
from backend.infrastructure.database.migrations import env as alembic_env

# ============================================================================
# 1. Domain Layer Independence & Pure Python Verification
# ============================================================================


def test_domain_entity_independence() -> None:
    """Verify matching and application domains have zero persistence imports."""
    for mod_name in [
        "backend.domain.matching.enums",
        "backend.domain.matching.entities",
        "backend.domain.application.enums",
        "backend.domain.application.entities",
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


def test_matching_domain_entities_and_defaults() -> None:
    """Verify matching domain entities defaults and slots."""
    job_id = uuid.uuid4()
    bp_id = uuid.uuid4()
    sp_id = uuid.uuid4()

    # MatchResult
    mr = MatchResult(
        job_id=job_id,
        base_profile_id=bp_id,
        search_profile_id=sp_id,
        deterministic_score=Decimal("85.50"),
        final_score=Decimal("85.50"),
        confidence=Decimal("90.00"),
    )
    assert isinstance(mr.id, uuid.UUID)
    assert mr.ai_score is None
    assert mr.ai_adjustment == Decimal("0.0")
    assert mr.created_at is None
    assert mr.updated_at is None

    # RequirementMatch
    req_id = uuid.uuid4()
    rm = RequirementMatch(
        match_result_id=mr.id,
        requirement_id=req_id,
        match_status=MatchStatus.MATCHED,
        score=Decimal("100.00"),
        reason="Python skill verified from profile experience.",
    )
    assert isinstance(rm.id, uuid.UUID)
    assert rm.evidence is None
    assert rm.is_blocker is False

    # AIAnalysis
    ai = AIAnalysis(
        match_result_id=mr.id,
        model="gemini-1.5-pro",
        provider="google",
        ai_score=Decimal("88.00"),
        assessment="STRONG",
        summary="Candidate matches 90% of required skills.",
    )
    assert isinstance(ai.id, uuid.UUID)
    assert ai.fingerprint is None
    assert ai.created_at is None

    # AIEvidence
    ev = AIEvidence(
        ai_analysis_id=ai.id,
        claim="Proven 5+ years with async Python",
        evidence_type="EXPERIENCE",
        source_reference="TechCorp Senior Role",
        reason="Lead backend architect handling async workflows.",
    )
    assert isinstance(ev.id, uuid.UUID)


def test_application_domain_entities_and_defaults() -> None:
    """Verify application domain entities defaults and slots."""
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Application
    app = Application(
        job_id=job_id,
        user_id=user_id,
    )
    assert isinstance(app.id, uuid.UUID)
    assert app.status is ApplicationStatus.INTERESTED
    assert app.notes is None
    assert app.created_at is None
    assert app.updated_at is None

    # ApplicationStatusHistory
    hist = ApplicationStatusHistory(
        application_id=app.id,
        from_status=ApplicationStatus.INTERESTED,
        to_status=ApplicationStatus.APPLIED,
    )
    assert isinstance(hist.id, uuid.UUID)
    assert hist.from_status is ApplicationStatus.INTERESTED
    assert hist.to_status is ApplicationStatus.APPLIED
    assert hist.changed_at is None


def test_job_requirement_domain_entity_and_defaults() -> None:
    """Verify JobRequirement domain entity defaults and slots."""
    job_id = uuid.uuid4()
    req = JobRequirement(
        job_id=job_id,
        type=RequirementType.SKILL,
        description="Must have 3+ years experience with PostgreSQL",
    )
    assert isinstance(req.id, uuid.UUID)
    assert req.type is RequirementType.SKILL
    assert req.normalized_skill is None
    assert req.required_level is RequirementLevel.REQUIRED
    assert req.importance == "MEDIUM"
    assert req.criticality == "NORMAL"
    assert req.evidence is None
    assert req.created_at is None
    assert req.updated_at is None


def test_enums_definitions() -> None:
    """Verify enum inheritance and values."""
    assert issubclass(MatchStatus, str)
    assert MatchStatus.MATCHED == "MATCHED"
    assert MatchStatus.PARTIAL == "PARTIAL"
    assert MatchStatus.NOT_MATCHED == "NOT_MATCHED"
    assert MatchStatus.UNKNOWN == "UNKNOWN"

    assert issubclass(ApplicationStatus, str)
    assert ApplicationStatus.INTERESTED == "INTERESTED"
    assert ApplicationStatus.APPLYING == "APPLYING"
    assert ApplicationStatus.APPLIED == "APPLIED"
    assert ApplicationStatus.INTERVIEW == "INTERVIEW"
    assert ApplicationStatus.OFFER == "OFFER"
    assert ApplicationStatus.REJECTED == "REJECTED"

    assert issubclass(RequirementType, str)
    assert RequirementType.SKILL == "SKILL"
    assert RequirementType.EXPERIENCE == "EXPERIENCE"
    assert RequirementType.EDUCATION == "EDUCATION"
    assert RequirementType.LANGUAGE == "LANGUAGE"
    assert RequirementType.CERTIFICATION == "CERTIFICATION"
    assert RequirementType.OTHER == "OTHER"

    assert issubclass(RequirementLevel, str)
    assert RequirementLevel.REQUIRED == "REQUIRED"
    assert RequirementLevel.PREFERRED == "PREFERRED"


# ============================================================================
# 2. ORM Inheritance and Table Names
# ============================================================================


def test_orm_inheritance() -> None:
    """Verify ORM model base class inheritance."""
    assert issubclass(MatchResultModel, BaseModel)
    assert issubclass(ApplicationModel, BaseModel)
    assert issubclass(JobRequirementModel, BaseModel)

    # Immutable / specialized models inherit Base and UUIDPrimaryKeyMixin
    for model_cls in [
        RequirementMatchModel,
        AIAnalysisModel,
        AIEvidenceModel,
        ApplicationStatusHistoryModel,
    ]:
        assert issubclass(model_cls, Base)
        assert issubclass(model_cls, UUIDPrimaryKeyMixin)
        assert not issubclass(model_cls, BaseModel)


def test_orm_table_names() -> None:
    """Verify table names match design document."""
    assert MatchResultModel.__tablename__ == "match_results"
    assert RequirementMatchModel.__tablename__ == "requirement_matches"
    assert AIAnalysisModel.__tablename__ == "ai_analyses"
    assert AIEvidenceModel.__tablename__ == "ai_evidence"
    assert ApplicationModel.__tablename__ == "applications"
    assert ApplicationStatusHistoryModel.__tablename__ == "application_status_history"
    assert JobRequirementModel.__tablename__ == "job_requirements"


# ============================================================================
# 3. MatchResultModel Metadata & Score Constraints Audit
# ============================================================================


def test_match_results_metadata() -> None:
    """Verify match_results columns, precision, and unique constraint."""
    table = MatchResultModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable

    assert isinstance(table.c.job_id.type, UUID)
    assert not table.c.job_id.nullable
    assert table.c.job_id.index

    assert isinstance(table.c.base_profile_id.type, UUID)
    assert not table.c.base_profile_id.nullable
    assert table.c.base_profile_id.index

    assert isinstance(table.c.search_profile_id.type, UUID)
    assert not table.c.search_profile_id.nullable
    assert table.c.search_profile_id.index

    # Numeric precision & scale
    assert isinstance(table.c.deterministic_score.type, Numeric)
    assert table.c.deterministic_score.type.precision == 5
    assert table.c.deterministic_score.type.scale == 2
    assert not table.c.deterministic_score.nullable

    assert isinstance(table.c.ai_score.type, Numeric)
    assert table.c.ai_score.type.precision == 5
    assert table.c.ai_score.type.scale == 2
    assert table.c.ai_score.nullable

    assert isinstance(table.c.ai_adjustment.type, Numeric)
    assert table.c.ai_adjustment.type.precision == 4
    assert table.c.ai_adjustment.type.scale == 2
    assert table.c.ai_adjustment.nullable
    assert table.c.ai_adjustment.server_default is not None
    assert "0.0" in str(table.c.ai_adjustment.server_default.arg)

    assert isinstance(table.c.final_score.type, Numeric)
    assert table.c.final_score.type.precision == 5
    assert table.c.final_score.type.scale == 2
    assert not table.c.final_score.nullable

    assert isinstance(table.c.confidence.type, Numeric)
    assert table.c.confidence.type.precision == 5
    assert table.c.confidence.type.scale == 2
    assert not table.c.confidence.nullable

    # Verify NO CheckConstraint exists on the table per design fidelity
    check_constraints = [c for c in table.constraints if isinstance(c, CheckConstraint)]
    assert len(check_constraints) == 0

    # Timestamps
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert not table.c.created_at.nullable
    assert table.c.created_at.server_default is not None

    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert not table.c.updated_at.nullable
    assert table.c.updated_at.server_default is not None

    # Unique constraint on (job_id, base_profile_id, search_profile_id)
    uqs = [
        c
        for c in table.constraints
        if isinstance(c, UniqueConstraint)
        and {col.name for col in c.columns}
        == {"job_id", "base_profile_id", "search_profile_id"}
    ]
    assert len(uqs) == 1
    assert uqs[0].name == "uq_match_results_job_base_search"


# ============================================================================
# 4. RequirementMatchModel Metadata
# ============================================================================


def test_requirement_matches_metadata() -> None:
    """Verify requirement_matches columns, non-native enum, and immutability."""
    table = RequirementMatchModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable

    assert isinstance(table.c.match_result_id.type, UUID)
    assert not table.c.match_result_id.nullable
    assert table.c.match_result_id.index

    assert isinstance(table.c.requirement_id.type, UUID)
    assert not table.c.requirement_id.nullable
    assert table.c.requirement_id.index

    # Non-native enum
    assert isinstance(table.c.match_status.type, SQLEnum)
    assert table.c.match_status.type.native_enum is False
    assert table.c.match_status.type.length == 50
    assert not table.c.match_status.nullable

    assert isinstance(table.c.score.type, Numeric)
    assert table.c.score.type.precision == 5
    assert table.c.score.type.scale == 2
    assert not table.c.score.nullable

    assert isinstance(table.c.evidence.type, Text)
    assert table.c.evidence.nullable

    assert isinstance(table.c.reason.type, Text)
    assert not table.c.reason.nullable

    assert isinstance(table.c.is_blocker.type, Boolean)
    assert not table.c.is_blocker.nullable
    assert table.c.is_blocker.server_default is not None
    assert "false" in str(table.c.is_blocker.server_default.arg).lower()

    # Immutable row: no timestamps
    assert "created_at" not in table.c
    assert "updated_at" not in table.c


# ============================================================================
# 5. AIAnalysisModel & AIEvidenceModel Metadata
# ============================================================================


def test_ai_analyses_metadata() -> None:
    """Verify ai_analyses columns, uniqueness of match_result_id, and created_at."""
    table = AIAnalysisModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable

    assert isinstance(table.c.match_result_id.type, UUID)
    assert not table.c.match_result_id.nullable
    assert table.c.match_result_id.unique

    assert isinstance(table.c.model.type, String)
    assert table.c.model.type.length == 100
    assert not table.c.model.nullable

    assert isinstance(table.c.provider.type, String)
    assert table.c.provider.type.length == 50
    assert not table.c.provider.nullable

    assert isinstance(table.c.ai_score.type, Numeric)
    assert table.c.ai_score.type.precision == 5
    assert table.c.ai_score.type.scale == 2
    assert not table.c.ai_score.nullable

    assert isinstance(table.c.assessment.type, String)
    assert table.c.assessment.type.length == 50
    assert not table.c.assessment.nullable

    assert isinstance(table.c.summary.type, Text)
    assert not table.c.summary.nullable

    assert isinstance(table.c.fingerprint.type, String)
    assert table.c.fingerprint.type.length == 64
    assert table.c.fingerprint.nullable

    # Only created_at, NO updated_at
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert not table.c.created_at.nullable
    assert table.c.created_at.server_default is not None
    assert "updated_at" not in table.c


def test_ai_evidence_metadata() -> None:
    """Verify ai_evidence columns and immutability (no timestamps)."""
    table = AIEvidenceModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable

    assert isinstance(table.c.ai_analysis_id.type, UUID)
    assert not table.c.ai_analysis_id.nullable
    assert table.c.ai_analysis_id.index

    assert isinstance(table.c.claim.type, Text)
    assert not table.c.claim.nullable

    assert isinstance(table.c.evidence_type.type, String)
    assert table.c.evidence_type.type.length == 50
    assert not table.c.evidence_type.nullable

    assert isinstance(table.c.source_reference.type, Text)
    assert not table.c.source_reference.nullable

    assert isinstance(table.c.reason.type, Text)
    assert not table.c.reason.nullable

    # Immutable row: no timestamps
    assert "created_at" not in table.c
    assert "updated_at" not in table.c


# ============================================================================
# 6. ApplicationModel & ApplicationStatusHistoryModel Metadata
# ============================================================================


def test_applications_metadata() -> None:
    """Verify applications columns, non-native enum, defaults, and unique constraint."""
    table = ApplicationModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable

    assert isinstance(table.c.job_id.type, UUID)
    assert not table.c.job_id.nullable
    assert table.c.job_id.index

    assert isinstance(table.c.user_id.type, UUID)
    assert not table.c.user_id.nullable
    assert table.c.user_id.index

    # Status non-native enum with 'INTERESTED' server default
    assert isinstance(table.c.status.type, SQLEnum)
    assert table.c.status.type.native_enum is False
    assert table.c.status.type.length == 50
    assert not table.c.status.nullable
    assert table.c.status.index
    assert table.c.status.server_default is not None
    assert "'INTERESTED'" in str(table.c.status.server_default.arg)

    assert isinstance(table.c.notes.type, Text)
    assert table.c.notes.nullable

    # Unique constraint on (job_id, user_id)
    uqs = [
        c
        for c in table.constraints
        if isinstance(c, UniqueConstraint)
        and {col.name for col in c.columns} == {"job_id", "user_id"}
    ]
    assert len(uqs) == 1
    assert uqs[0].name == "uq_applications_job_user"

    # Timestamps
    assert isinstance(table.c.created_at.type, DateTime)
    assert not table.c.created_at.nullable
    assert isinstance(table.c.updated_at.type, DateTime)
    assert not table.c.updated_at.nullable


def test_application_status_history_metadata() -> None:
    """Verify application_status_history columns: strictly NOT NULL from_status."""
    table = ApplicationStatusHistoryModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable

    assert isinstance(table.c.application_id.type, UUID)
    assert not table.c.application_id.nullable
    assert table.c.application_id.index

    # from_status and to_status are strictly NOT NULL
    assert isinstance(table.c.from_status.type, SQLEnum)
    assert table.c.from_status.type.native_enum is False
    assert table.c.from_status.type.length == 50
    assert not table.c.from_status.nullable

    assert isinstance(table.c.to_status.type, SQLEnum)
    assert table.c.to_status.type.native_enum is False
    assert table.c.to_status.type.length == 50
    assert not table.c.to_status.nullable

    # changed_at timestamp only (no created_at / updated_at)
    assert isinstance(table.c.changed_at.type, DateTime)
    assert table.c.changed_at.type.timezone is True
    assert not table.c.changed_at.nullable
    assert table.c.changed_at.server_default is not None

    assert "created_at" not in table.c
    assert "updated_at" not in table.c


# ============================================================================
# 7. JobRequirementModel Metadata
# ============================================================================


def test_job_requirements_metadata() -> None:
    """Verify job_requirements columns, enums, string types, and defaults."""
    table = JobRequirementModel.__table__

    assert isinstance(table.c.id.type, UUID)
    assert not table.c.id.nullable

    assert isinstance(table.c.job_id.type, UUID)
    assert not table.c.job_id.nullable
    assert table.c.job_id.index

    # type is RequirementType enum
    assert isinstance(table.c.type.type, SQLEnum)
    assert table.c.type.type.native_enum is False
    assert table.c.type.type.length == 50
    assert not table.c.type.nullable

    assert isinstance(table.c.description.type, Text)
    assert not table.c.description.nullable

    assert isinstance(table.c.normalized_skill.type, String)
    assert table.c.normalized_skill.type.length == 150
    assert table.c.normalized_skill.nullable
    assert table.c.normalized_skill.index

    # required_level is RequirementLevel enum
    assert isinstance(table.c.required_level.type, SQLEnum)
    assert table.c.required_level.type.native_enum is False
    assert table.c.required_level.type.length == 50
    assert not table.c.required_level.nullable
    assert table.c.required_level.server_default is not None
    assert "'REQUIRED'" in str(table.c.required_level.server_default.arg)

    # importance is String(50), default 'MEDIUM'
    assert isinstance(table.c.importance.type, String)
    assert table.c.importance.type.length == 50
    assert not table.c.importance.nullable
    assert table.c.importance.server_default is not None
    assert "'MEDIUM'" in str(table.c.importance.server_default.arg)

    # criticality is String(50), default 'NORMAL'
    assert isinstance(table.c.criticality.type, String)
    assert table.c.criticality.type.length == 50
    assert not table.c.criticality.nullable
    assert table.c.criticality.server_default is not None
    assert "'NORMAL'" in str(table.c.criticality.server_default.arg)

    assert isinstance(table.c.evidence.type, Text)
    assert table.c.evidence.nullable

    assert isinstance(table.c.created_at.type, DateTime)
    assert not table.c.created_at.nullable
    assert isinstance(table.c.updated_at.type, DateTime)
    assert not table.c.updated_at.nullable


# ============================================================================
# 8. Foreign Keys & OnDelete Rules
# ============================================================================


def test_foreign_keys_and_ondelete_rules() -> None:
    """Verify ON DELETE CASCADE across all Phase 2.4 relationships."""
    # job_requirements.job_id -> jobs.id
    fks = {fk.parent.name: fk for fk in JobRequirementModel.__table__.foreign_keys}
    assert fks["job_id"].column.table.name == "jobs"
    assert fks["job_id"].ondelete == "CASCADE"

    # match_results FKs
    mr_fks = {fk.parent.name: fk for fk in MatchResultModel.__table__.foreign_keys}
    assert mr_fks["job_id"].column.table.name == "jobs"
    assert mr_fks["job_id"].ondelete == "CASCADE"
    assert mr_fks["base_profile_id"].column.table.name == "base_profiles"
    assert mr_fks["base_profile_id"].ondelete == "CASCADE"
    assert mr_fks["search_profile_id"].column.table.name == "search_profiles"
    assert mr_fks["search_profile_id"].ondelete == "CASCADE"

    # requirement_matches FKs
    rm_fks = {fk.parent.name: fk for fk in RequirementMatchModel.__table__.foreign_keys}
    assert rm_fks["match_result_id"].column.table.name == "match_results"
    assert rm_fks["match_result_id"].ondelete == "CASCADE"
    assert rm_fks["requirement_id"].column.table.name == "job_requirements"
    assert rm_fks["requirement_id"].ondelete == "CASCADE"

    # ai_analyses FK
    ai_fks = {fk.parent.name: fk for fk in AIAnalysisModel.__table__.foreign_keys}
    assert ai_fks["match_result_id"].column.table.name == "match_results"
    assert ai_fks["match_result_id"].ondelete == "CASCADE"

    # ai_evidence FK
    ev_fks = {fk.parent.name: fk for fk in AIEvidenceModel.__table__.foreign_keys}
    assert ev_fks["ai_analysis_id"].column.table.name == "ai_analyses"
    assert ev_fks["ai_analysis_id"].ondelete == "CASCADE"

    # applications FKs
    app_fks = {fk.parent.name: fk for fk in ApplicationModel.__table__.foreign_keys}
    assert app_fks["job_id"].column.table.name == "jobs"
    assert app_fks["job_id"].ondelete == "CASCADE"
    assert app_fks["user_id"].column.table.name == "users"
    assert app_fks["user_id"].ondelete == "CASCADE"

    # application_status_history FK
    hist_fks = {
        fk.parent.name: fk
        for fk in ApplicationStatusHistoryModel.__table__.foreign_keys
    }
    assert hist_fks["application_id"].column.table.name == "applications"
    assert hist_fks["application_id"].ondelete == "CASCADE"


# ============================================================================
# 9. Relationships and Cascades
# ============================================================================


def test_relationships_and_cascades() -> None:
    """Verify bidirectional relationships and cascade delete configurations."""
    # JobModel
    assert JobModel.requirements.property.cascade.delete_orphan
    assert JobModel.match_results.property.cascade.delete_orphan
    assert JobModel.applications.property.cascade.delete_orphan

    # UserModel
    assert UserModel.applications.property.cascade.delete_orphan

    # BaseProfileModel & SearchProfileModel
    assert BaseProfileModel.match_results.property.cascade.delete_orphan
    assert SearchProfileModel.match_results.property.cascade.delete_orphan

    # MatchResultModel
    assert MatchResultModel.requirement_matches.property.cascade.delete_orphan
    assert MatchResultModel.ai_analysis.property.cascade.delete_orphan
    assert MatchResultModel.ai_analysis.property.uselist is False

    # AIAnalysisModel
    assert AIAnalysisModel.evidence_list.property.cascade.delete_orphan

    # ApplicationModel
    assert ApplicationModel.status_history.property.cascade.delete_orphan


# ============================================================================
# 10. Domain <-> ORM Conversions (Roundtrip)
# ============================================================================


def test_match_result_roundtrip_conversion() -> None:
    """Verify MatchResult to_domain / from_domain roundtrip."""
    now = datetime.now(UTC)
    domain_mr = MatchResult(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        base_profile_id=uuid.uuid4(),
        search_profile_id=uuid.uuid4(),
        deterministic_score=Decimal("82.00"),
        ai_score=Decimal("86.00"),
        ai_adjustment=Decimal("4.00"),
        final_score=Decimal("86.00"),
        confidence=Decimal("95.00"),
        created_at=now,
        updated_at=now,
    )
    model = MatchResultModel.from_domain(domain_mr)
    reconstructed = model.to_domain()
    assert reconstructed == domain_mr


def test_requirement_match_roundtrip_conversion() -> None:
    """Verify RequirementMatch to_domain / from_domain roundtrip."""
    domain_rm = RequirementMatch(
        id=uuid.uuid4(),
        match_result_id=uuid.uuid4(),
        requirement_id=uuid.uuid4(),
        match_status=MatchStatus.MATCHED,
        score=Decimal("95.00"),
        evidence="3 years with FastAPI documented in experience #1",
        reason="Matched candidate experience directly",
        is_blocker=False,
    )
    model = RequirementMatchModel.from_domain(domain_rm)
    reconstructed = model.to_domain()
    assert reconstructed == domain_rm


def test_ai_analysis_and_evidence_roundtrip_conversion() -> None:
    """Verify AIAnalysis and AIEvidence to_domain / from_domain roundtrip."""
    now = datetime.now(UTC)
    domain_ai = AIAnalysis(
        id=uuid.uuid4(),
        match_result_id=uuid.uuid4(),
        model="gemini-1.5-pro",
        provider="google",
        ai_score=Decimal("91.00"),
        assessment="STRONG",
        summary="Strong architectural alignment.",
        fingerprint="fp123456hash",
        created_at=now,
    )
    model_ai = AIAnalysisModel.from_domain(domain_ai)
    assert model_ai.to_domain() == domain_ai

    domain_ev = AIEvidence(
        id=uuid.uuid4(),
        ai_analysis_id=domain_ai.id,
        claim="Deep domain understanding",
        evidence_type="PROJECT",
        source_reference="JobScope implementation",
        reason="Demonstrated clean architecture principles",
    )
    model_ev = AIEvidenceModel.from_domain(domain_ev)
    assert model_ev.to_domain() == domain_ev


def test_application_and_history_roundtrip_conversion() -> None:
    """Verify Application and ApplicationStatusHistory roundtrip."""
    now = datetime.now(UTC)
    domain_app = Application(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        status=ApplicationStatus.APPLIED,
        notes="Applied via company career portal",
        created_at=now,
        updated_at=now,
    )
    model_app = ApplicationModel.from_domain(domain_app)
    assert model_app.to_domain() == domain_app

    domain_hist = ApplicationStatusHistory(
        id=uuid.uuid4(),
        application_id=domain_app.id,
        from_status=ApplicationStatus.INTERESTED,
        to_status=ApplicationStatus.APPLIED,
        changed_at=now,
    )
    model_hist = ApplicationStatusHistoryModel.from_domain(domain_hist)
    assert model_hist.to_domain() == domain_hist


def test_job_requirement_roundtrip_conversion() -> None:
    """Verify JobRequirement to_domain / from_domain roundtrip."""
    now = datetime.now(UTC)
    domain_req = JobRequirement(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Experience with PostgreSQL schema design",
        normalized_skill="PostgreSQL",
        required_level=RequirementLevel.REQUIRED,
        importance="HIGH",
        criticality="BLOCKER",
        evidence="Must have demonstrated PostgreSQL knowledge",
        created_at=now,
        updated_at=now,
    )
    model_req = JobRequirementModel.from_domain(domain_req)
    assert model_req.to_domain() == domain_req


# ============================================================================
# 11. Model Repr Tests
# ============================================================================


def test_model_reprs() -> None:
    """Verify __repr__ methods on all new models."""
    mr_id = uuid.uuid4()
    mr = MatchResultModel(
        id=mr_id,
        final_score=Decimal("88.00"),
        confidence=Decimal("92.00"),
    )
    assert repr(mr) == (
        f"<MatchResultModel id={mr_id} final_score=88.00 confidence=92.00>"
    )

    rm_id = uuid.uuid4()
    rm = RequirementMatchModel(
        id=rm_id,
        match_status=MatchStatus.MATCHED,
        score=Decimal("100.00"),
    )
    assert (
        repr(rm)
        == f"<RequirementMatchModel id={rm_id} match_status='MATCHED' score=100.00>"
    )

    ai_id = uuid.uuid4()
    ai = AIAnalysisModel(
        id=ai_id,
        model="gemini-1.5-pro",
        ai_score=Decimal("90.00"),
    )
    assert repr(ai) == (
        f"<AIAnalysisModel id={ai_id} model='gemini-1.5-pro' ai_score=90.00>"
    )

    ev_id = uuid.uuid4()
    ev = AIEvidenceModel(
        id=ev_id,
        evidence_type="SKILL",
    )
    assert repr(ev) == f"<AIEvidenceModel id={ev_id} evidence_type='SKILL'>"

    app_id = uuid.uuid4()
    job_id = uuid.uuid4()
    app = ApplicationModel(
        id=app_id,
        status=ApplicationStatus.INTERESTED,
        job_id=job_id,
    )
    assert (
        repr(app)
        == f"<ApplicationModel id={app_id} status='INTERESTED' job_id={job_id}>"
    )

    hist_id = uuid.uuid4()
    hist = ApplicationStatusHistoryModel(
        id=hist_id,
        from_status=ApplicationStatus.INTERESTED,
        to_status=ApplicationStatus.APPLIED,
    )
    assert repr(hist) == (
        f"<ApplicationStatusHistoryModel id={hist_id} "
        f"from_status='INTERESTED' to_status='APPLIED'>"
    )

    req_id = uuid.uuid4()
    req = JobRequirementModel(
        id=req_id,
        type=RequirementType.SKILL,
        normalized_skill="Python",
    )
    assert (
        repr(req)
        == f"<JobRequirementModel id={req_id} type='SKILL' normalized_skill='Python'>"
    )


# ============================================================================
# 12. Alembic Metadata Discovery and Migration Chain
# ============================================================================


def test_alembic_metadata_discovery() -> None:
    """Verify Alembic target_metadata contains all 7 new tables."""
    tables = alembic_env.target_metadata.tables
    expected_tables = [
        "job_requirements",
        "match_results",
        "requirement_matches",
        "ai_analyses",
        "ai_evidence",
        "applications",
        "application_status_history",
    ]
    for tbl in expected_tables:
        assert tbl in tables, f"Table {tbl} not discovered in Alembic metadata"


def test_migration_file_structure_and_revision_chain() -> None:
    """Verify migration 0004 links to 0003_jobs_and_sources."""
    mod = importlib.import_module(
        "backend.infrastructure.database.migrations.versions.20260919_0004_matching_and_applications_create_tables"
    )
    assert mod.revision == "0004_matching_and_applications"
    assert mod.down_revision == "0003_jobs_and_sources"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")


# ============================================================================
# 13. Schema Fidelity & Negative Column Checks (Approved Plan Conformance)
# ============================================================================


def test_schema_fidelity_negative_checks() -> None:
    """Explicitly verify that unapproved fields are absent across domain and ORM."""
    # 1. JobRequirement: required_level & evidence present, level absent
    req_cols = JobRequirementModel.__table__.c
    assert "required_level" in req_cols
    assert "evidence" in req_cols
    assert "level" not in req_cols
    assert hasattr(JobRequirement, "required_level")
    assert hasattr(JobRequirement, "evidence")
    assert not hasattr(JobRequirement, "level")

    # 2. MatchResult: scores, adjustment, confidence present; status & summary absent
    mr_cols = MatchResultModel.__table__.c
    for col in [
        "deterministic_score",
        "ai_score",
        "ai_adjustment",
        "final_score",
        "confidence",
        "created_at",
        "updated_at",
    ]:
        assert col in mr_cols
    assert "status" not in mr_cols
    assert "summary" not in mr_cols
    assert not hasattr(MatchResult, "status")
    assert not hasattr(MatchResult, "summary")

    # Unique constraint must be on (job_id, base_profile_id, search_profile_id)
    uqs = [
        c
        for c in MatchResultModel.__table__.constraints
        if isinstance(c, UniqueConstraint)
        and {col.name for col in c.columns}
        == {"job_id", "base_profile_id", "search_profile_id"}
    ]
    assert len(uqs) == 1
    assert uqs[0].name == "uq_match_results_job_base_search"

    # 3. RequirementMatch: match_status, score, evidence, reason, is_blocker present;
    # confidence & assessment absent
    rm_cols = RequirementMatchModel.__table__.c
    for col in ["match_status", "score", "evidence", "reason", "is_blocker"]:
        assert col in rm_cols
    assert "confidence" not in rm_cols
    assert "assessment" not in rm_cols
    assert not hasattr(RequirementMatch, "confidence")
    assert not hasattr(RequirementMatch, "assessment")

    # 4. AIAnalysis: model, provider, ai_score, assessment, summary,
    # fingerprint present; analysis_type, model_name, prompt_tokens,
    # completion_tokens, ai_adjustment, raw_response absent
    ai_cols = AIAnalysisModel.__table__.c
    for col in [
        "model",
        "provider",
        "ai_score",
        "assessment",
        "summary",
        "fingerprint",
        "created_at",
    ]:
        assert col in ai_cols
    for unapproved in [
        "analysis_type",
        "model_name",
        "prompt_tokens",
        "completion_tokens",
        "ai_adjustment",
        "raw_response",
    ]:
        assert unapproved not in ai_cols
        assert not hasattr(AIAnalysis, unapproved)

    # 5. AIEvidence: claim, evidence_type, source_reference, reason present;
    # field_reference, snippet, relevance_score absent
    ev_cols = AIEvidenceModel.__table__.c
    for col in ["claim", "evidence_type", "source_reference", "reason"]:
        assert col in ev_cols
    for unapproved in ["field_reference", "snippet", "relevance_score"]:
        assert unapproved not in ev_cols
        assert not hasattr(AIEvidence, unapproved)

    # 6. Application: job_id, user_id, status, notes, created_at, updated_at present;
    # match_result_id, cv_id, applied_at absent
    app_cols = ApplicationModel.__table__.c
    for col in [
        "job_id",
        "user_id",
        "status",
        "notes",
        "created_at",
        "updated_at",
    ]:
        assert col in app_cols
    for unapproved in ["match_result_id", "cv_id", "applied_at"]:
        assert unapproved not in app_cols
        assert not hasattr(Application, unapproved)

    # 7. ApplicationStatusHistory: application_id, from_status, to_status,
    # changed_at present; reason absent
    hist_cols = ApplicationStatusHistoryModel.__table__.c
    for col in ["application_id", "from_status", "to_status", "changed_at"]:
        assert col in hist_cols
    assert "reason" not in hist_cols
    assert not hasattr(ApplicationStatusHistory, "reason")
