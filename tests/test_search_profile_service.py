"""Unit tests for SearchProfileService.

Validates candidate User -> BaseProfile -> SearchProfile ownership chain,
input validations, and scoped operations.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from backend.application.profile_management.exceptions import (
    ProfileValidationError,
    SearchProfileNotFoundError,
)
from backend.application.profile_management.search_profile_service import (
    SearchProfileService,
)
from backend.domain.profile.entities import BaseProfile
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository

# ============================================================================
# In-Memory Test Doubles
# ============================================================================


class InMemoryBaseProfileRepository(BaseProfileRepository):
    """In-memory test double for BaseProfileRepository."""

    def __init__(self, profiles: list[BaseProfile] | None = None) -> None:
        self.profiles: dict[uuid.UUID, BaseProfile] = {
            p.id: p for p in (profiles or [])
        }

    async def get_by_id(self, profile_id: uuid.UUID) -> BaseProfile | None:
        return self.profiles.get(profile_id)

    async def get_by_user_id(self, user_id: uuid.UUID) -> BaseProfile | None:
        for p in self.profiles.values():
            if p.user_id == user_id:
                return p
        return None

    async def save(self, profile: BaseProfile) -> BaseProfile:
        self.profiles[profile.id] = profile
        return profile


class InMemorySearchProfileRepository(SearchProfileRepository):
    """In-memory test double for SearchProfileRepository."""

    def __init__(self, items: list[SearchProfile] | None = None) -> None:
        self.items: dict[uuid.UUID, SearchProfile] = {sp.id: sp for sp in (items or [])}

    async def get_by_id(self, search_profile_id: uuid.UUID) -> SearchProfile | None:
        return self.items.get(search_profile_id)

    async def get_by_id_and_base_profile_id(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> SearchProfile | None:
        sp = self.items.get(search_profile_id)
        if sp and sp.base_profile_id == base_profile_id:
            return sp
        return None

    async def list_by_base_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[SearchProfile]:
        return [
            sp for sp in self.items.values() if sp.base_profile_id == base_profile_id
        ]

    async def save(self, search_profile: SearchProfile) -> SearchProfile:
        self.items[search_profile.id] = search_profile
        return search_profile

    async def delete(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        sp = self.items.get(search_profile_id)
        if sp and sp.base_profile_id == base_profile_id:
            del self.items[search_profile_id]
            return True
        return False


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def base_profile_repo() -> InMemoryBaseProfileRepository:
    return InMemoryBaseProfileRepository()


@pytest.fixture
def search_profile_repo() -> InMemorySearchProfileRepository:
    return InMemorySearchProfileRepository()


@pytest.fixture
def service(
    base_profile_repo: InMemoryBaseProfileRepository,
    search_profile_repo: InMemorySearchProfileRepository,
) -> SearchProfileService:
    return SearchProfileService(
        base_profile_repo=base_profile_repo,
        search_profile_repo=search_profile_repo,
    )


# ============================================================================
# 1. List Search Profiles Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_search_profiles_auto_provisions_base_profile(
    service: SearchProfileService,
    base_profile_repo: InMemoryBaseProfileRepository,
) -> None:
    user_id = uuid.uuid4()
    profiles = await service.list_search_profiles(user_id=user_id)
    assert profiles == []

    # Auto-provisioned base profile exists
    bp = await base_profile_repo.get_by_user_id(user_id)
    assert bp is not None
    assert bp.user_id == user_id


@pytest.mark.asyncio
async def test_list_search_profiles_filters_by_base_profile(
    service: SearchProfileService,
    base_profile_repo: InMemoryBaseProfileRepository,
    search_profile_repo: InMemorySearchProfileRepository,
) -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    bp_a = BaseProfile(id=uuid.uuid4(), user_id=user_a, name="User A")
    bp_b = BaseProfile(id=uuid.uuid4(), user_id=user_b, name="User B")
    await base_profile_repo.save(bp_a)
    await base_profile_repo.save(bp_b)

    sp_a1 = SearchProfile(base_profile_id=bp_a.id, name="User A Backend")
    sp_a2 = SearchProfile(base_profile_id=bp_a.id, name="User A Frontend")
    sp_b1 = SearchProfile(base_profile_id=bp_b.id, name="User B DevOps")
    await search_profile_repo.save(sp_a1)
    await search_profile_repo.save(sp_a2)
    await search_profile_repo.save(sp_b1)

    result_a = await service.list_search_profiles(user_id=user_a)
    assert len(result_a) == 2
    assert {sp.name for sp in result_a} == {"User A Backend", "User A Frontend"}

    result_b = await service.list_search_profiles(user_id=user_b)
    assert len(result_b) == 1
    assert result_b[0].name == "User B DevOps"


# ============================================================================
# 2. Get Search Profile Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_search_profile_success(
    service: SearchProfileService,
    base_profile_repo: InMemoryBaseProfileRepository,
    search_profile_repo: InMemorySearchProfileRepository,
) -> None:
    user_id = uuid.uuid4()
    bp = BaseProfile(id=uuid.uuid4(), user_id=user_id, name="Candidate")
    await base_profile_repo.save(bp)

    sp = SearchProfile(
        base_profile_id=bp.id,
        name="Target Role",
        target_roles=["Backend Engineer"],
    )
    await search_profile_repo.save(sp)

    fetched = await service.get_search_profile(user_id=user_id, search_profile_id=sp.id)
    assert fetched.id == sp.id
    assert fetched.name == "Target Role"
    assert fetched.target_roles == ["Backend Engineer"]


@pytest.mark.asyncio
async def test_get_search_profile_not_found(service: SearchProfileService) -> None:
    user_id = uuid.uuid4()
    with pytest.raises(SearchProfileNotFoundError):
        await service.get_search_profile(
            user_id=user_id, search_profile_id=uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_get_search_profile_cross_user_forbidden(
    service: SearchProfileService,
    base_profile_repo: InMemoryBaseProfileRepository,
    search_profile_repo: InMemorySearchProfileRepository,
) -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    bp_a = BaseProfile(id=uuid.uuid4(), user_id=user_a, name="User A")
    bp_b = BaseProfile(id=uuid.uuid4(), user_id=user_b, name="User B")
    await base_profile_repo.save(bp_a)
    await base_profile_repo.save(bp_b)

    sp_a = SearchProfile(base_profile_id=bp_a.id, name="Confidential A")
    await search_profile_repo.save(sp_a)

    # User B tries to get User A's search profile -> 404
    with pytest.raises(SearchProfileNotFoundError):
        await service.get_search_profile(user_id=user_b, search_profile_id=sp_a.id)


# ============================================================================
# 3. Create Search Profile Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_search_profile_success(
    service: SearchProfileService,
    base_profile_repo: InMemoryBaseProfileRepository,
) -> None:
    user_id = uuid.uuid4()
    sp = await service.create_search_profile(
        user_id=user_id,
        name="  Senior Python Engineer  ",
        target_roles=["  Backend Engineer  ", "Python Developer", ""],
        seniority="  Senior  ",
        target_skills=["Python", "FastAPI", "  "],
        locations=["London", "  Remote UK  "],
        work_modes=["remote", "hybrid"],
        industries=["Fintech"],
        salary_min=Decimal("80000.00"),
        salary_max=Decimal("120000.00"),
    )
    assert sp.name == "Senior Python Engineer"
    assert sp.target_roles == ["Backend Engineer", "Python Developer"]
    assert sp.seniority == "Senior"
    assert sp.target_skills == ["Python", "FastAPI"]
    assert sp.locations == ["London", "Remote UK"]
    assert sp.work_modes == ["remote", "hybrid"]
    assert sp.industries == ["Fintech"]
    assert sp.salary_min == Decimal("80000.00")
    assert sp.salary_max == Decimal("120000.00")


@pytest.mark.asyncio
async def test_create_search_profile_validation_empty_name(
    service: SearchProfileService,
) -> None:
    user_id = uuid.uuid4()
    with pytest.raises(ProfileValidationError, match="name cannot be empty"):
        await service.create_search_profile(user_id=user_id, name="   ")


@pytest.mark.asyncio
async def test_create_search_profile_validation_name_too_long(
    service: SearchProfileService,
) -> None:
    user_id = uuid.uuid4()
    with pytest.raises(ProfileValidationError, match="cannot exceed 150 characters"):
        await service.create_search_profile(user_id=user_id, name="A" * 151)


@pytest.mark.asyncio
async def test_create_search_profile_validation_negative_salary(
    service: SearchProfileService,
) -> None:
    user_id = uuid.uuid4()
    with pytest.raises(
        ProfileValidationError, match="Minimum salary cannot be negative"
    ):
        await service.create_search_profile(
            user_id=user_id, name="Role", salary_min=Decimal("-100")
        )

    with pytest.raises(
        ProfileValidationError, match="Maximum salary cannot be negative"
    ):
        await service.create_search_profile(
            user_id=user_id, name="Role", salary_max=Decimal("-50")
        )


@pytest.mark.asyncio
async def test_create_search_profile_validation_salary_inversion(
    service: SearchProfileService,
) -> None:
    user_id = uuid.uuid4()
    with pytest.raises(
        ProfileValidationError, match="Minimum salary cannot exceed maximum salary"
    ):
        await service.create_search_profile(
            user_id=user_id,
            name="Role",
            salary_min=Decimal("100000"),
            salary_max=Decimal("50000"),
        )


# ============================================================================
# 4. Update Search Profile Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_search_profile_partial(
    service: SearchProfileService,
    base_profile_repo: InMemoryBaseProfileRepository,
) -> None:
    user_id = uuid.uuid4()
    created = await service.create_search_profile(
        user_id=user_id,
        name="Initial Title",
        target_roles=["Engineer"],
        salary_min=Decimal("50000"),
        salary_max=Decimal("80000"),
    )

    # Only update name
    updated = await service.update_search_profile(
        user_id=user_id,
        search_profile_id=created.id,
        updates={"name": "Updated Title"},
    )
    assert updated.name == "Updated Title"
    assert updated.target_roles == ["Engineer"]
    assert updated.salary_min == Decimal("50000")
    assert updated.salary_max == Decimal("80000")


@pytest.mark.asyncio
async def test_update_search_profile_cross_field_salary_validation(
    service: SearchProfileService,
) -> None:
    user_id = uuid.uuid4()
    created = await service.create_search_profile(
        user_id=user_id,
        name="Job Target",
        salary_min=Decimal("60000"),
        salary_max=Decimal("90000"),
    )

    # Updating salary_min to 100000 when salary_max is 90000 must fail
    with pytest.raises(
        ProfileValidationError, match="Minimum salary cannot exceed maximum salary"
    ):
        await service.update_search_profile(
            user_id=user_id,
            search_profile_id=created.id,
            updates={"salary_min": Decimal("100000")},
        )

    # Updating salary_max to 50000 when salary_min is 60000 must fail
    with pytest.raises(
        ProfileValidationError, match="Minimum salary cannot exceed maximum salary"
    ):
        await service.update_search_profile(
            user_id=user_id,
            search_profile_id=created.id,
            updates={"salary_max": Decimal("50000")},
        )


@pytest.mark.asyncio
async def test_update_search_profile_cross_user_forbidden(
    service: SearchProfileService,
    base_profile_repo: InMemoryBaseProfileRepository,
    search_profile_repo: InMemorySearchProfileRepository,
) -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    bp_a = BaseProfile(id=uuid.uuid4(), user_id=user_a, name="User A")
    bp_b = BaseProfile(id=uuid.uuid4(), user_id=user_b, name="User B")
    await base_profile_repo.save(bp_a)
    await base_profile_repo.save(bp_b)

    sp_a = SearchProfile(base_profile_id=bp_a.id, name="Confidential A")
    await search_profile_repo.save(sp_a)

    with pytest.raises(SearchProfileNotFoundError):
        await service.update_search_profile(
            user_id=user_b,
            search_profile_id=sp_a.id,
            updates={"name": "Malicious Update"},
        )


# ============================================================================
# 5. Delete Search Profile Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_search_profile_success(
    service: SearchProfileService,
    search_profile_repo: InMemorySearchProfileRepository,
) -> None:
    user_id = uuid.uuid4()
    created = await service.create_search_profile(
        user_id=user_id,
        name="To Delete",
    )
    assert created.id in search_profile_repo.items

    await service.delete_search_profile(user_id=user_id, search_profile_id=created.id)
    assert created.id not in search_profile_repo.items


@pytest.mark.asyncio
async def test_delete_search_profile_cross_user_forbidden(
    service: SearchProfileService,
    base_profile_repo: InMemoryBaseProfileRepository,
    search_profile_repo: InMemorySearchProfileRepository,
) -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    bp_a = BaseProfile(id=uuid.uuid4(), user_id=user_a, name="User A")
    bp_b = BaseProfile(id=uuid.uuid4(), user_id=user_b, name="User B")
    await base_profile_repo.save(bp_a)
    await base_profile_repo.save(bp_b)

    sp_a = SearchProfile(base_profile_id=bp_a.id, name="Confidential A")
    await search_profile_repo.save(sp_a)

    with pytest.raises(SearchProfileNotFoundError):
        await service.delete_search_profile(user_id=user_b, search_profile_id=sp_a.id)

    # Confirm it was not deleted
    assert sp_a.id in search_profile_repo.items
