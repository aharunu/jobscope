"""Tests for profile domain entities, ORM models, and Alembic discovery."""

import datetime
import importlib
import sys
import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.domain.profile import (
    BaseProfile,
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
    ProfileSkill,
)
from backend.domain.search_profile import SearchProfile
from backend.infrastructure.database import (
    Base,
    BaseModel,
    BaseProfileModel,
    ProfileEducationModel,
    ProfileExperienceModel,
    ProfileProjectModel,
    ProfileSkillModel,
    SearchProfileModel,
    TimestampMixin,
    UserModel,
    UUIDPrimaryKeyMixin,
)
from backend.infrastructure.database.migrations import env as alembic_env
from backend.infrastructure.database.models.base_profile import (
    BaseProfileModel as DirectBaseProfileModel,
)
from backend.infrastructure.database.models.search_profile import (
    SearchProfileModel as DirectSearchProfileModel,
)


def test_domain_entity_independence() -> None:
    """Verify profile and search_profile domains have zero SQLAlchemy imports."""
    for mod_name in [
        "backend.domain.profile.entities",
        "backend.domain.search_profile.entities",
    ]:
        mod = sys.modules.get(mod_name)
        assert mod is not None, f"Module {mod_name} is not loaded"
        for attr_name, attr_val in mod.__dict__.items():
            if hasattr(attr_val, "__module__") and attr_val.__module__:
                err_msg = (
                    f"Domain leaked SQLAlchemy dependency: {attr_name} "
                    f"from {attr_val.__module__}"
                )
                assert not attr_val.__module__.startswith("sqlalchemy"), err_msg


def test_domain_entities_instantiation_and_types() -> None:
    """Verify domain entity instantiation, default factories, and types."""
    user_id = uuid.uuid4()
    bp = BaseProfile(user_id=user_id, name="Jane Doe")
    assert isinstance(bp.id, uuid.UUID)
    assert bp.user_id == user_id
    assert bp.name == "Jane Doe"
    assert bp.summary is None
    assert bp.created_at is None
    assert bp.updated_at is None

    # ProfileSkill
    skill = ProfileSkill(
        base_profile_id=bp.id,
        name="Python",
        category="Language",
        years_of_experience=Decimal("5.5"),
        level="Expert",
    )
    assert isinstance(skill.id, uuid.UUID)
    assert skill.base_profile_id == bp.id
    assert skill.years_of_experience == Decimal("5.5")
    assert isinstance(skill.years_of_experience, Decimal)

    # ProfileExperience
    today = datetime.date.today()
    exp = ProfileExperience(
        base_profile_id=bp.id,
        company="TechCorp",
        title="Lead Engineer",
        start_date=today,
    )
    assert isinstance(exp.id, uuid.UUID)
    assert exp.is_current is False
    assert exp.skills_used == []
    assert exp.end_date is None

    # ProfileEducation
    edu = ProfileEducation(
        base_profile_id=bp.id,
        school="State University",
        degree="B.S.",
        field_of_study="Computer Science",
    )
    assert isinstance(edu.id, uuid.UUID)
    assert edu.start_year is None
    assert edu.end_year is None

    # ProfileProject
    proj = ProfileProject(
        base_profile_id=bp.id,
        title="Crawler Engine",
    )
    assert isinstance(proj.id, uuid.UUID)
    assert proj.skills_used == []
    assert proj.url is None

    # SearchProfile
    sp = SearchProfile(
        base_profile_id=bp.id,
        name="AI Engineer",
        salary_min=Decimal("120000.00"),
        salary_max=Decimal("160000.00"),
    )
    assert isinstance(sp.id, uuid.UUID)
    assert sp.target_roles == []
    assert sp.target_skills == []
    assert sp.locations == []
    assert sp.work_modes == []
    assert sp.industries == []
    assert sp.seniority is None
    assert isinstance(sp.salary_min, Decimal)
    assert isinstance(sp.salary_max, Decimal)


def test_orm_models_importability_and_inheritance() -> None:
    """Verify ORM models are importable and inherit from BaseModel."""
    models = [
        (BaseProfileModel, DirectBaseProfileModel),
        (SearchProfileModel, DirectSearchProfileModel),
        (ProfileSkillModel, ProfileSkillModel),
        (ProfileExperienceModel, ProfileExperienceModel),
        (ProfileEducationModel, ProfileEducationModel),
        (ProfileProjectModel, ProfileProjectModel),
    ]
    for model_cls, direct_cls in models:
        assert model_cls is direct_cls
        assert issubclass(model_cls, BaseModel)
        assert issubclass(model_cls, UUIDPrimaryKeyMixin)
        assert issubclass(model_cls, TimestampMixin)
        assert issubclass(model_cls, Base)


def test_base_profile_metadata() -> None:
    """Verify base_profiles table schema, column types, and constraints."""
    table = Base.metadata.tables["base_profiles"]
    assert table.name == "base_profiles"

    # Columns
    assert isinstance(table.c.id.type, UUID)
    assert table.c.id.primary_key is True
    assert table.c.id.nullable is False

    assert isinstance(table.c.user_id.type, UUID)
    assert table.c.user_id.nullable is False

    assert isinstance(table.c.name.type, String)
    assert table.c.name.type.length == 255
    assert table.c.name.nullable is False

    assert isinstance(table.c.summary.type, Text)
    assert table.c.summary.nullable is True

    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert table.c.created_at.nullable is False

    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert table.c.updated_at.nullable is False

    # Foreign Key & Cascade
    fks = list(table.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert fk.target_fullname == "users.id"
    assert fk.ondelete == "CASCADE"

    # Unique constraints: only primary key
    unique_constraints = [
        c for c in table.constraints if getattr(c, "_is_unique", False)
    ]
    assert len(unique_constraints) == 0


def test_profile_skills_metadata() -> None:
    """Verify profile_skills table schema, column types, and constraints."""
    table = Base.metadata.tables["profile_skills"]
    assert table.name == "profile_skills"

    assert isinstance(table.c.id.type, UUID)
    assert table.c.id.primary_key is True

    assert isinstance(table.c.base_profile_id.type, UUID)
    assert table.c.base_profile_id.nullable is False

    assert isinstance(table.c.name.type, String)
    assert table.c.name.type.length == 150
    assert table.c.name.nullable is False

    assert isinstance(table.c.category.type, String)
    assert table.c.category.type.length == 100
    assert table.c.category.nullable is True

    assert isinstance(table.c.years_of_experience.type, Numeric)
    assert table.c.years_of_experience.type.precision == 4
    assert table.c.years_of_experience.type.scale == 1
    assert table.c.years_of_experience.nullable is True

    assert isinstance(table.c.level.type, String)
    assert table.c.level.type.length == 50
    assert table.c.level.nullable is True

    # Foreign Key
    fks = list(table.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "base_profiles.id"
    assert fks[0].ondelete == "CASCADE"


def test_profile_experiences_metadata() -> None:
    """Verify profile_experiences table schema, defaults, and types."""
    table = Base.metadata.tables["profile_experiences"]
    assert table.name == "profile_experiences"

    assert isinstance(table.c.base_profile_id.type, UUID)
    assert table.c.base_profile_id.nullable is False

    assert isinstance(table.c.company.type, String)
    assert table.c.company.type.length == 255
    assert table.c.company.nullable is False

    assert isinstance(table.c.title.type, String)
    assert table.c.title.type.length == 255
    assert table.c.title.nullable is False

    assert isinstance(table.c.description.type, Text)
    assert table.c.description.nullable is True

    assert isinstance(table.c.start_date.type, Date)
    assert table.c.start_date.nullable is False

    assert isinstance(table.c.end_date.type, Date)
    assert table.c.end_date.nullable is True

    assert isinstance(table.c.is_current.type, Boolean)
    assert table.c.is_current.nullable is False
    assert table.c.is_current.server_default is not None

    assert isinstance(table.c.skills_used.type, JSONB)
    assert table.c.skills_used.nullable is False
    assert table.c.skills_used.server_default is not None

    # Foreign Key
    fks = list(table.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "base_profiles.id"
    assert fks[0].ondelete == "CASCADE"


def test_profile_educations_metadata() -> None:
    """Verify profile_educations table schema, types, and constraints."""
    table = Base.metadata.tables["profile_educations"]
    assert table.name == "profile_educations"

    assert isinstance(table.c.base_profile_id.type, UUID)
    assert table.c.base_profile_id.nullable is False

    assert isinstance(table.c.school.type, String)
    assert table.c.school.type.length == 255
    assert table.c.school.nullable is False

    assert isinstance(table.c.degree.type, String)
    assert table.c.degree.type.length == 100
    assert table.c.degree.nullable is False

    assert isinstance(table.c.field_of_study.type, String)
    assert table.c.field_of_study.type.length == 255
    assert table.c.field_of_study.nullable is False

    assert isinstance(table.c.start_year.type, Integer)
    assert table.c.start_year.nullable is True

    assert isinstance(table.c.end_year.type, Integer)
    assert table.c.end_year.nullable is True

    # Foreign Key
    fks = list(table.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "base_profiles.id"
    assert fks[0].ondelete == "CASCADE"


def test_profile_projects_metadata() -> None:
    """Verify profile_projects table schema, types, and constraints."""
    table = Base.metadata.tables["profile_projects"]
    assert table.name == "profile_projects"

    assert isinstance(table.c.base_profile_id.type, UUID)
    assert table.c.base_profile_id.nullable is False

    assert isinstance(table.c.title.type, String)
    assert table.c.title.type.length == 255
    assert table.c.title.nullable is False

    assert isinstance(table.c.description.type, Text)
    assert table.c.description.nullable is True

    assert isinstance(table.c.skills_used.type, JSONB)
    assert table.c.skills_used.nullable is False
    assert table.c.skills_used.server_default is not None

    assert isinstance(table.c.url.type, Text)
    assert table.c.url.nullable is True

    # Foreign Key
    fks = list(table.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "base_profiles.id"
    assert fks[0].ondelete == "CASCADE"


def test_search_profiles_metadata() -> None:
    """Verify search_profiles table schema, types, defaults, and constraints."""
    table = Base.metadata.tables["search_profiles"]
    assert table.name == "search_profiles"

    assert isinstance(table.c.base_profile_id.type, UUID)
    assert table.c.base_profile_id.nullable is False

    assert isinstance(table.c.name.type, String)
    assert table.c.name.type.length == 150
    assert table.c.name.nullable is False

    # JSONB columns with defaults
    for col_name in [
        "target_roles",
        "target_skills",
        "locations",
        "work_modes",
        "industries",
    ]:
        col = table.c[col_name]
        assert isinstance(col.type, JSONB)
        assert col.nullable is False
        assert col.server_default is not None

    assert isinstance(table.c.seniority.type, String)
    assert table.c.seniority.type.length == 50
    assert table.c.seniority.nullable is True

    assert isinstance(table.c.salary_min.type, Numeric)
    assert table.c.salary_min.type.precision == 12
    assert table.c.salary_min.type.scale == 2
    assert table.c.salary_min.nullable is True

    assert isinstance(table.c.salary_max.type, Numeric)
    assert table.c.salary_max.type.precision == 12
    assert table.c.salary_max.type.scale == 2
    assert table.c.salary_max.nullable is True

    # Foreign Key
    fks = list(table.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "base_profiles.id"
    assert fks[0].ondelete == "CASCADE"

    # Unique constraints: only primary key
    unique_constraints = [
        c for c in table.constraints if getattr(c, "_is_unique", False)
    ]
    assert len(unique_constraints) == 0


def test_orm_relationships_and_cascades() -> None:
    """Verify SQLAlchemy relationship definitions and delete-orphan cascades."""
    # UserModel -> base_profiles
    user_bp_rel = UserModel.__mapper__.relationships["base_profiles"]
    assert user_bp_rel.back_populates == "user"
    assert user_bp_rel.cascade.delete is True
    assert user_bp_rel.cascade.delete_orphan is True

    # BaseProfileModel relationships
    bp_mapper = BaseProfileModel.__mapper__
    assert bp_mapper.relationships["user"].back_populates == "base_profiles"

    child_rels = [
        ("search_profiles", "base_profile"),
        ("skills", "base_profile"),
        ("experiences", "base_profile"),
        ("educations", "base_profile"),
        ("projects", "base_profile"),
    ]
    for rel_name, back_pop in child_rels:
        rel = bp_mapper.relationships[rel_name]
        assert rel.back_populates == back_pop
        assert rel.cascade.delete is True
        assert rel.cascade.delete_orphan is True


def test_model_domain_roundtrip_conversion() -> None:
    """Verify bi-directional conversion between ORM models and domain entities."""
    user_id = uuid.uuid4()
    bp_domain = BaseProfile(
        user_id=user_id,
        name="Alice Engineer",
        summary="Senior Backend Engineer",
    )
    bp_orm = BaseProfileModel.from_domain(bp_domain)
    assert bp_orm.id == bp_domain.id
    assert bp_orm.user_id == user_id
    assert bp_orm.name == "Alice Engineer"
    assert bp_orm.summary == "Senior Backend Engineer"

    bp_reconverted = bp_orm.to_domain()
    assert bp_reconverted == bp_domain

    # ProfileSkill conversion
    skill_domain = ProfileSkill(
        base_profile_id=bp_domain.id,
        name="PostgreSQL",
        category="Database",
        years_of_experience=Decimal("4.5"),
        level="Advanced",
    )
    skill_orm = ProfileSkillModel.from_domain(skill_domain)
    assert skill_orm.years_of_experience == Decimal("4.5")
    assert skill_orm.to_domain() == skill_domain

    # ProfileExperience conversion
    exp_domain = ProfileExperience(
        base_profile_id=bp_domain.id,
        company="JobScope Inc",
        title="Staff Engineer",
        start_date=datetime.date(2022, 1, 1),
        is_current=True,
        skills_used=["Python", "FastAPI", "SQLAlchemy"],
    )
    exp_orm = ProfileExperienceModel.from_domain(exp_domain)
    assert exp_orm.is_current is True
    assert exp_orm.skills_used == ["Python", "FastAPI", "SQLAlchemy"]
    assert exp_orm.to_domain() == exp_domain

    # ProfileEducation conversion
    edu_domain = ProfileEducation(
        base_profile_id=bp_domain.id,
        school="MIT",
        degree="Master's",
        field_of_study="EECS",
        start_year=2018,
        end_year=2020,
    )
    edu_orm = ProfileEducationModel.from_domain(edu_domain)
    assert edu_orm.to_domain() == edu_domain

    # ProfileProject conversion
    proj_domain = ProfileProject(
        base_profile_id=bp_domain.id,
        title="Personal Job Intelligence",
        skills_used=["Python", "Docker"],
        url="https://github.com/example/jobscope",
    )
    proj_orm = ProfileProjectModel.from_domain(proj_domain)
    assert proj_orm.to_domain() == proj_domain

    # SearchProfile conversion
    sp_domain = SearchProfile(
        base_profile_id=bp_domain.id,
        name="Backend Lead",
        target_roles=["Backend Lead", "Staff Engineer"],
        seniority="Senior",
        target_skills=["Python", "PostgreSQL"],
        locations=["Berlin", "Remote"],
        work_modes=["Remote", "Hybrid"],
        industries=["Fintech", "Healthtech"],
        salary_min=Decimal("110000.00"),
        salary_max=Decimal("150000.00"),
    )
    sp_orm = SearchProfileModel.from_domain(sp_domain)
    assert sp_orm.salary_min == Decimal("110000.00")
    assert sp_orm.to_domain() == sp_domain


def test_alembic_metadata_discovery_profiles() -> None:
    """Verify Alembic target_metadata discovers all 6 profile-related tables."""
    assert alembic_env.target_metadata is Base.metadata
    for table_name in [
        "base_profiles",
        "profile_skills",
        "profile_experiences",
        "profile_educations",
        "profile_projects",
        "search_profiles",
    ]:
        assert table_name in alembic_env.target_metadata.tables
        assert (
            alembic_env.target_metadata.tables[table_name]
            is Base.metadata.tables[table_name]
        )


def test_migration_script_0002_structure() -> None:
    """Verify 0002_profiles migration exists, is chained, and has callables."""
    mod = importlib.import_module(
        "backend.infrastructure.database.migrations.versions."
        "20260919_0002_profiles_create_profile_tables"
    )
    assert mod.revision == "0002_profiles"
    assert mod.down_revision == "0001_users"
    assert callable(mod.upgrade)
    assert callable(mod.downgrade)
