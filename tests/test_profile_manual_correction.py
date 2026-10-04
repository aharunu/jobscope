"""Date safety, skill suggestions and numeric validation against real API/DB."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from backend.application.profile_management.exceptions import ProfileValidationError
from backend.application.profile_management.skill_suggestions import SkillSuggestions
from backend.application.profile_management.validation import validate_skill_years
from backend.infrastructure.database.models.base_profile import ProfileExperienceModel
from backend.infrastructure.database.models.user import UserModel
from tests.test_application_tracking_phase_1 import database_api as database_api
from tests.test_application_tracking_phase_1 import pg_session as pg_session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "updates",
    [
        {"start_date": "0001-01-01"},
        {"start_date": None},
        {"start_date": ""},
        {"start_date": str(date.today() + timedelta(days=1))},
        {"end_date": "2019-01-01"},
        {"end_date": str(date.today() + timedelta(days=1))},
        {"company": " "},
        {"title": " "},
    ],
)
async def test_invalid_experience_create_and_partial_update_not_persisted(
    database_api, updates
):
    client, _, _, user, _, _ = database_api
    headers = {"X-User-Id": str(user)}
    valid = {"company": "Acme", "title": "Engineer", "start_date": "2020-01-01"}
    response = await client.post(
        "/api/profile/experiences", headers=headers, json={**valid, **updates}
    )
    assert response.status_code == 422
    created = await client.post("/api/profile/experiences", headers=headers, json=valid)
    assert created.status_code == 201
    identity = created.json()["id"]
    response = await client.patch(
        f"/api/profile/experiences/{identity}", headers=headers, json=updates
    )
    assert response.status_code == 422
    items = (await client.get("/api/profile/experiences", headers=headers)).json()
    assert (
        len(items) == 1
        and items[0]["start_date"] == "2020-01-01"
        and items[0]["end_date"] is None
    )


@pytest.mark.asyncio
async def test_partial_current_role_clears_existing_end_and_valid_dates_round_trip(
    database_api,
):
    client, _, _, user, _, _ = database_api
    headers = {"X-User-Id": str(user)}
    created = await client.post(
        "/api/profile/experiences",
        headers=headers,
        json={
            "company": "Acme",
            "title": "Engineer",
            "start_date": "2020-01-01",
            "end_date": "2022-01-01",
        },
    )
    assert created.status_code == 201 and created.json()["start_date"] == "2020-01-01"
    path = f"/api/profile/experiences/{created.json()['id']}"
    current = await client.patch(path, headers=headers, json={"is_current": True})
    assert current.status_code == 200 and current.json()["end_date"] is None
    assert (
        await client.patch(path, headers=headers, json={"end_date": "2023-01-01"})
    ).json()["end_date"] is None
    invalid = await client.patch(
        path,
        headers=headers,
        json={
            "is_current": False,
            "start_date": "2024-01-01",
            "end_date": "2023-01-01",
        },
    )
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_legacy_date_read_correction_and_missing_start(database_api):
    client, _, factory, user, _, _ = database_api
    headers = {"X-User-Id": str(user)}
    missing = await client.post(
        "/api/profile/experiences",
        headers=headers,
        json={"company": "Acme", "title": "Engineer"},
    )
    assert missing.status_code == 422
    created = await client.post(
        "/api/profile/experiences",
        headers=headers,
        json={"company": "Acme", "title": "Engineer", "start_date": "1900-01-01"},
    )
    assert created.status_code == 201
    identity = uuid.UUID(created.json()["id"])
    # Test-only invalid legacy row, rolled back by the outer fixture transaction.
    async with factory() as session:
        row = await session.get(ProfileExperienceModel, identity)
        row.start_date = date.min
        await session.commit()
    assert (
        await client.get("/api/profile/experiences", headers=headers)
    ).status_code == 200
    corrected = await client.patch(
        f"/api/profile/experiences/{identity}",
        headers=headers,
        json={"start_date": str(date.today())},
    )
    assert corrected.status_code == 200
    assert corrected.json()["start_date"] == str(date.today())


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, 51, "NaN", "Infinity"])
async def test_skill_years_invalid_api_create_and_patch(database_api, value):
    client, _, _, user, _, _ = database_api
    headers = {"X-User-Id": str(user)}
    assert (
        await client.post(
            "/api/profile/skills",
            headers=headers,
            json={"name": "Custom", "years_of_experience": value},
        )
    ).status_code == 422
    created = await client.post(
        "/api/profile/skills",
        headers=headers,
        json={"name": "Custom", "years_of_experience": 0.5},
    )
    assert created.status_code == 201 and Decimal(
        created.json()["years_of_experience"]
    ) == Decimal("0.5")
    assert (
        await client.patch(
            f"/api/profile/skills/{created.json()['id']}",
            headers=headers,
            json={"years_of_experience": value},
        )
    ).status_code == 422


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "-1", "51"])
def test_service_numeric_guard(value):
    with pytest.raises(ProfileValidationError):
        validate_skill_years(Decimal(value))


def test_suggestions_normalization_deduplication_and_bounds():
    suggestions = SkillSuggestions(
        ("Python", "Python", "  PyTorch  ", "python", "Custom  Runtime")
    )
    assert suggestions.search("  PY  ") == ["python", "PyTorch"]
    assert suggestions.search("runtime") == ["Custom Runtime"]
    assert len(suggestions.search("", 1)) == 1
    assert (
        len(SkillSuggestions(tuple(f"Skill {i}" for i in range(50))).search("")) == 20
    )


@pytest.mark.asyncio
async def test_suggestion_endpoint_readonly_case_insensitive_and_bounded(database_api):
    client, _, factory, _, _, _ = database_api
    unknown = uuid.uuid4()
    headers = {"X-User-Id": str(unknown)}
    response = await client.get("/api/profile/skill-suggestions?q=PY", headers=headers)
    assert response.status_code == 200 and response.json() == ["Python", "PyTorch"]
    assert (
        len(
            (
                await client.get(
                    "/api/profile/skill-suggestions?limit=1", headers=headers
                )
            ).json()
        )
        == 1
    )
    assert (
        await client.get("/api/profile/skill-suggestions?limit=21", headers=headers)
    ).status_code == 422
    assert (
        await client.get(
            "/api/profile/skill-suggestions?q=" + "x" * 101, headers=headers
        )
    ).status_code == 422
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count(UserModel.id)).where(UserModel.id == unknown)
            )
            == 0
        )
