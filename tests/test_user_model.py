"""Tests for User domain entity, UserModel, and Alembic discovery."""

import importlib
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID

from backend.domain.user import User
from backend.domain.user.entities import User as EntityUser
from backend.infrastructure.database import (
    Base,
    BaseModel,
    TimestampMixin,
    UserModel,
    UUIDPrimaryKeyMixin,
)
from backend.infrastructure.database.migrations import env as alembic_env
from backend.infrastructure.database.models import UserModel as RegistryUserModel
from backend.infrastructure.database.models.user import UserModel as DirectUserModel


def test_user_orm_model_importability() -> None:
    """Verify UserModel is importable from all intended infrastructure paths."""
    assert UserModel is DirectUserModel
    assert UserModel is RegistryUserModel
    assert issubclass(UserModel, BaseModel)


def test_user_domain_entity_independence() -> None:
    """Verify that domain user entities have zero dependency on SQLAlchemy."""
    domain_module = sys.modules.get("backend.domain.user.entities")
    assert domain_module is not None

    # Check imported module names in domain entity
    for attr_name, attr_val in domain_module.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            err_msg = (
                f"Domain leaked SQLAlchemy dependency: {attr_name} "
                f"from {attr_val.__module__}"
            )
            assert not attr_val.__module__.startswith("sqlalchemy"), err_msg


def test_user_domain_entity_instantiation() -> None:
    """Verify User domain entity initialization and defaults."""
    user = User()
    assert isinstance(user.id, uuid.UUID)
    assert user.created_at is None
    assert user.updated_at is None

    custom_id = uuid.uuid4()
    now = datetime.now(UTC)
    user2 = EntityUser(id=custom_id, created_at=now, updated_at=now)
    assert user2.id == custom_id
    assert user2.created_at == now
    assert user2.updated_at == now


def test_user_orm_model_metadata() -> None:
    """Verify table name, column definitions, constraints, and types in metadata."""
    assert "users" in Base.metadata.tables
    table = Base.metadata.tables["users"]

    assert table.name == "users"

    # id column checks
    assert "id" in table.columns
    id_col = table.columns["id"]
    assert id_col.primary_key is True
    assert isinstance(id_col.type, UUID)
    assert id_col.type.as_uuid is True
    assert id_col.nullable is False
    assert id_col.server_default is not None

    # created_at column checks
    assert "created_at" in table.columns
    created_col = table.columns["created_at"]
    assert isinstance(created_col.type, DateTime)
    assert created_col.type.timezone is True
    assert created_col.nullable is False
    assert created_col.server_default is not None

    # updated_at column checks
    assert "updated_at" in table.columns
    updated_col = table.columns["updated_at"]
    assert isinstance(updated_col.type, DateTime)
    assert updated_col.type.timezone is True
    assert updated_col.nullable is False
    assert updated_col.server_default is not None

    # Primary key constraint
    assert len(table.primary_key.columns) == 1
    assert "id" in table.primary_key.columns


def test_user_orm_inheritance() -> None:
    """Verify UserModel inherits from BaseModel and required mixins."""
    assert issubclass(UserModel, BaseModel)
    assert issubclass(UserModel, UUIDPrimaryKeyMixin)
    assert issubclass(UserModel, TimestampMixin)
    assert issubclass(UserModel, Base)

    # In-memory instantiation
    instance = UserModel()
    assert isinstance(instance.id, uuid.UUID)
    assert repr(instance) == f"<UserModel id={instance.id}>"


def test_user_model_domain_conversion() -> None:
    """Verify bi-directional conversion between UserModel and User domain entity."""
    # ORM -> Domain
    custom_id = uuid.uuid4()
    now = datetime.now(UTC)
    orm_user = UserModel(id=custom_id, created_at=now, updated_at=now)
    domain_user = orm_user.to_domain()

    assert isinstance(domain_user, User)
    assert domain_user.id == custom_id
    assert domain_user.created_at == now
    assert domain_user.updated_at == now

    # Domain -> ORM
    reconverted_orm = UserModel.from_domain(domain_user)
    assert isinstance(reconverted_orm, UserModel)
    assert reconverted_orm.id == custom_id
    assert reconverted_orm.created_at == now
    assert reconverted_orm.updated_at == now

    # Domain with defaults -> ORM
    blank_domain = User()
    blank_orm = UserModel.from_domain(blank_domain)
    assert isinstance(blank_orm.id, uuid.UUID)
    assert blank_orm.id == blank_domain.id


def test_alembic_metadata_discovery() -> None:
    """Verify Alembic target_metadata automatically includes the users table."""
    assert alembic_env.target_metadata is Base.metadata
    assert "users" in alembic_env.target_metadata.tables
    assert alembic_env.target_metadata.tables["users"] is Base.metadata.tables["users"]


def test_migration_script_structure() -> None:
    """Verify the Alembic migration script for users table exists and is valid."""
    migration_mod = importlib.import_module(
        "backend.infrastructure.database.migrations.versions.20260919_0001_users_create_users_table"
    )
    assert migration_mod.revision == "0001_users"
    assert migration_mod.down_revision is None
    assert callable(migration_mod.upgrade)
    assert callable(migration_mod.downgrade)
