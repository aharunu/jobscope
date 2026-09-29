"""Unit tests for BaseProfileService application logic."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from backend.application.profile_management.exceptions import (
    ProfileNotFoundError,
    ProfileValidationError,
)
from backend.application.profile_management.services import BaseProfileService
from backend.domain.profile.entities import BaseProfile, ProfileSkill
from backend.domain.profile.repositories import BaseProfileRepository


@pytest.fixture
def mock_repo() -> AsyncMock:
    """Provide a mock BaseProfileRepository conforming to protocol."""
    return AsyncMock(spec=BaseProfileRepository)


@pytest.fixture
def service(mock_repo: AsyncMock) -> BaseProfileService:
    """Provide a BaseProfileService backed by mock repository."""
    return BaseProfileService(base_profile_repo=mock_repo)


@pytest.mark.asyncio
async def test_get_or_create_profile_returns_existing(
    service: BaseProfileService,
    mock_repo: AsyncMock,
) -> None:
    """Should return existing profile if one is already saved."""
    user_id = uuid.uuid4()
    existing = BaseProfile(user_id=user_id, name="Existing User")
    mock_repo.get_by_user_id.return_value = existing

    result = await service.get_or_create_profile(user_id)

    assert result == existing
    mock_repo.get_by_user_id.assert_awaited_once_with(user_id)
    mock_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_profile_creates_new(
    service: BaseProfileService,
    mock_repo: AsyncMock,
) -> None:
    """Should provision a new BaseProfile if user has none."""
    user_id = uuid.uuid4()
    mock_repo.get_by_user_id.return_value = None

    saved_profile = BaseProfile(user_id=user_id, name="Custom Default")
    mock_repo.save.return_value = saved_profile

    result = await service.get_or_create_profile(user_id, default_name="Custom Default")

    assert result == saved_profile
    mock_repo.get_by_user_id.assert_awaited_once_with(user_id)
    mock_repo.save.assert_awaited_once()
    saved_arg = mock_repo.save.call_args[0][0]
    assert saved_arg.user_id == user_id
    assert saved_arg.name == "Custom Default"


@pytest.mark.asyncio
async def test_get_profile_found(
    service: BaseProfileService,
    mock_repo: AsyncMock,
) -> None:
    """Should return profile if found."""
    user_id = uuid.uuid4()
    profile = BaseProfile(user_id=user_id, name="Alice")
    mock_repo.get_by_user_id.return_value = profile

    result = await service.get_profile(user_id)
    assert result == profile


@pytest.mark.asyncio
async def test_get_profile_not_found_raises(
    service: BaseProfileService,
    mock_repo: AsyncMock,
) -> None:
    """Should raise ProfileNotFoundError when profile does not exist."""
    user_id = uuid.uuid4()
    mock_repo.get_by_user_id.return_value = None

    with pytest.raises(ProfileNotFoundError):
        await service.get_profile(user_id)


@pytest.mark.asyncio
async def test_update_profile_success(
    service: BaseProfileService,
    mock_repo: AsyncMock,
) -> None:
    """Should update name and summary preserving child collections."""
    user_id = uuid.uuid4()
    bp_id = uuid.uuid4()
    existing = BaseProfile(
        id=bp_id,
        user_id=user_id,
        name="Old Name",
        summary="Old Summary",
        skills=[ProfileSkill(base_profile_id=bp_id, name="Python")],
    )
    mock_repo.get_by_user_id.return_value = existing
    mock_repo.save.side_effect = lambda p: p

    result = await service.update_profile(
        user_id=user_id,
        name="New Name",
        summary="New Bio",
    )

    assert result.name == "New Name"
    assert result.summary == "New Bio"
    assert len(result.skills) == 1
    assert result.skills[0].name == "Python"
    mock_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_profile_partial_preservation(
    service: BaseProfileService,
    mock_repo: AsyncMock,
) -> None:
    """Updating only name leaves summary untouched."""
    user_id = uuid.uuid4()
    existing = BaseProfile(
        user_id=user_id,
        name="Initial",
        summary="Keep This Summary",
    )
    mock_repo.get_by_user_id.return_value = existing
    mock_repo.save.side_effect = lambda p: p

    result = await service.update_profile(user_id=user_id, name="Updated Name")

    assert result.name == "Updated Name"
    assert result.summary == "Keep This Summary"


@pytest.mark.asyncio
async def test_update_profile_empty_name_rejected(
    service: BaseProfileService,
    mock_repo: AsyncMock,
) -> None:
    """Whitespace-only name raises ProfileValidationError."""
    user_id = uuid.uuid4()
    existing = BaseProfile(user_id=user_id, name="Initial")
    mock_repo.get_by_user_id.return_value = existing

    with pytest.raises(ProfileValidationError, match="cannot be empty"):
        await service.update_profile(user_id=user_id, name="   ")


@pytest.mark.asyncio
async def test_update_profile_not_found_raises(
    service: BaseProfileService,
    mock_repo: AsyncMock,
) -> None:
    """Updating nonexistent profile raises ProfileNotFoundError."""
    user_id = uuid.uuid4()
    mock_repo.get_by_user_id.return_value = None

    with pytest.raises(ProfileNotFoundError):
        await service.update_profile(user_id=user_id, name="New Name")
