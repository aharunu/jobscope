"""Persisted retrieval through real profile, matching and database dependencies."""

import importlib
import uuid
from unittest.mock import Mock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, select

from backend.domain.job.enums import RequirementType
from backend.domain.matching.deterministic_engine import DeterministicMatchEngine
from backend.infrastructure.database.models.job import JobRequirementModel
from backend.infrastructure.database.models.matching import MatchResultModel
from backend.infrastructure.database.models.user import UserModel
from tests.test_application_tracking_phase_1 import database_api as database_api
from tests.test_application_tracking_phase_1 import pg_session as pg_session


async def prepare_profile(client, user_id, name="Backend"):
    headers = {"X-User-Id": str(user_id)}
    root = await client.get("/api/profile", headers=headers)
    assert root.status_code == 200
    assert (
        await client.patch(
            "/api/profile",
            headers=headers,
            json={"name": "Candidate", "summary": "Python engineer"},
        )
    ).status_code == 200
    assert (
        await client.post(
            "/api/profile/skills",
            headers=headers,
            json={"name": "Python", "years_of_experience": 5},
        )
    ).status_code == 201
    profile = await client.post(
        "/api/search-profiles",
        headers=headers,
        json={"name": name, "target_roles": ["Engineer"], "target_skills": ["Python"]},
    )
    assert profile.status_code == 201, profile.text
    return profile.json()["id"]


@pytest.mark.asyncio
async def test_full_profile_calculate_retrieve_round_trip_without_writes(
    database_api, monkeypatch
):
    client, _, factory, user_id, _, job_id = database_api
    profile_id = await prepare_profile(client, user_id)
    async with factory() as session:
        session.add(
            JobRequirementModel(
                id=uuid.uuid4(),
                job_id=job_id,
                type=RequirementType.SKILL,
                description="Python programming",
                normalized_skill="Python",
            )
        )
        await session.commit()
    headers = {"X-User-Id": str(user_id)}
    path = f"/api/matches/job/{job_id}?search_profile_id={profile_id}"
    missing = await client.get(path, headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "MATCH_RESULT_NOT_FOUND"
    calculated = await client.post(
        "/api/matches",
        headers=headers,
        json={"job_id": str(job_id), "search_profile_id": profile_id},
    )
    assert calculated.status_code == 200, calculated.text
    saved = calculated.json()
    assert saved["explanation"] and saved["category_scores"]
    assert saved["requirement_matches"]
    assert "Python" in saved["explanation"]["matched_skills"]
    engine = Mock(side_effect=AssertionError("GET must never calculate"))
    monkeypatch.setattr(DeterministicMatchEngine, "evaluate", engine)
    for _ in range(2):
        retrieved = await client.get(path, headers=headers)
        assert retrieved.status_code == 200
        assert retrieved.json() == saved
    async with factory() as session:
        row = await session.get(MatchResultModel, uuid.UUID(saved["id"]))
        assert row.updated_at.isoformat().replace("+00:00", "Z") == saved["updated_at"]
        assert (
            await session.execute(
                select(func.count())
                .select_from(MatchResultModel)
                .where(MatchResultModel.search_profile_id == uuid.UUID(profile_id))
            )
        ).scalar_one() == 1
    engine.assert_not_called()


@pytest.mark.asyncio
async def test_owned_collection_multiple_profiles_filters_and_pagination(database_api):
    client, _, _, user_id, other_id, job_id = database_api
    headers = {"X-User-Id": str(user_id)}
    profile_ids = []
    saved_ids = []
    for name in ("Backend", "General"):
        profile_id = await prepare_profile(client, user_id, name)
        profile_ids.append(profile_id)
        result = await client.post(
            "/api/matches",
            headers=headers,
            json={"job_id": str(job_id), "search_profile_id": profile_id},
        )
        assert result.status_code == 200
        saved_ids.append(result.json()["id"])
    assert saved_ids[0] != saved_ids[1]
    for profile_id, saved_id in zip(profile_ids, saved_ids, strict=True):
        result = await client.get(
            f"/api/matches/job/{job_id}?search_profile_id={profile_id}", headers=headers
        )
        assert result.json()["id"] == saved_id
    listing = (
        await client.get("/api/matches?limit=1&offset=1", headers=headers)
    ).json()
    assert listing["total"] == 2 and len(listing["items"]) == 1
    filtered = (
        await client.get(
            f"/api/matches?job_id={job_id}&search_profile_id={profile_ids[0]}",
            headers=headers,
        )
    ).json()
    assert filtered["total"] == 1 and filtered["items"][0]["id"] == saved_ids[0]
    other_headers = {"X-User-Id": str(other_id)}
    assert (await client.get("/api/matches", headers=other_headers)).json()[
        "items"
    ] == []
    denied = await client.get(
        f"/api/matches/job/{job_id}?search_profile_id={profile_ids[0]}",
        headers=other_headers,
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "SEARCH_PROFILE_NOT_FOUND"
    assert (
        await client.get(
            f"/api/matches?search_profile_id={profile_ids[0]}", headers=other_headers
        )
    ).json()["total"] == 0


@pytest.mark.asyncio
async def test_unknown_identity_get_does_not_create_records(database_api):
    client, _, factory, _, _, _ = database_api
    unknown = uuid.uuid4()
    result = await client.get("/api/matches", headers={"X-User-Id": str(unknown)})
    assert result.status_code == 200 and result.json()["total"] == 0
    async with factory() as session:
        assert await session.get(UserModel, unknown) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query", ["limit=0", "offset=-1", "job_id=bad", "search_profile_id=bad"]
)
async def test_invalid_collection_queries(database_api, query):
    client, _, _, user_id, _, _ = database_api
    assert (
        await client.get(f"/api/matches?{query}", headers={"X-User-Id": str(user_id)})
    ).status_code == 422


@pytest.mark.asyncio
async def test_missing_job_profile_and_invalid_pair_input(database_api):
    client, _, _, user_id, _, job_id = database_api
    profile_id = await prepare_profile(client, user_id)
    headers = {"X-User-Id": str(user_id)}
    for path in (
        f"/api/matches/job/bad?search_profile_id={profile_id}",
        f"/api/matches/job/{job_id}?search_profile_id=bad",
    ):
        assert (await client.get(path, headers=headers)).status_code == 422
    missing_job = await client.get(
        f"/api/matches/job/{uuid.uuid4()}?search_profile_id={profile_id}",
        headers=headers,
    )
    assert missing_job.json()["error"]["code"] == "JOB_NOT_FOUND"
    missing_profile = await client.get(
        f"/api/matches/job/{job_id}?search_profile_id={uuid.uuid4()}", headers=headers
    )
    assert missing_profile.json()["error"]["code"] == "SEARCH_PROFILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_overwrite_returns_latest_snapshot_and_legacy_reads_do_not_backfill(
    database_api,
):
    client, _, factory, user_id, _, job_id = database_api
    profile_id = await prepare_profile(client, user_id)
    headers = {"X-User-Id": str(user_id)}
    payload = {"job_id": str(job_id), "search_profile_id": profile_id}
    first = (await client.post("/api/matches", headers=headers, json=payload)).json()
    second = (await client.post("/api/matches", headers=headers, json=payload)).json()
    assert second["id"] == first["id"]
    assert second["created_at"] == first["created_at"]
    path = f"/api/matches/job/{job_id}?search_profile_id={profile_id}"
    assert (await client.get(path, headers=headers)).json() == second
    async with factory() as session:
        row = await session.get(MatchResultModel, uuid.UUID(second["id"]))
        row.category_scores = {}
        row.explanation = None
        await session.commit()
    legacy = (await client.get(path, headers=headers)).json()
    assert legacy["category_scores"] == {} and legacy["explanation"] is None
    assert (await client.get(path, headers=headers)).json() == legacy


@pytest.mark.asyncio
async def test_inconsistent_base_profile_link_is_not_exposed(database_api):
    client, _, factory, user_id, other_id, job_id = database_api
    profile_id = await prepare_profile(client, user_id)
    await prepare_profile(client, other_id)
    other_base = (
        await client.get("/api/profile", headers={"X-User-Id": str(other_id)})
    ).json()["id"]
    headers = {"X-User-Id": str(user_id)}
    result = (
        await client.post(
            "/api/matches",
            headers=headers,
            json={"job_id": str(job_id), "search_profile_id": profile_id},
        )
    ).json()
    async with factory() as session:
        row = await session.get(MatchResultModel, uuid.UUID(result["id"]))
        row.base_profile_id = uuid.UUID(other_base)
        await session.commit()
    assert (
        await client.get(
            f"/api/matches/job/{job_id}?search_profile_id={profile_id}", headers=headers
        )
    ).status_code == 404
    for owner in (user_id, other_id):
        assert (
            await client.get("/api/matches", headers={"X-User-Id": str(owner)})
        ).json()["total"] == 0


@pytest.mark.asyncio
async def test_snapshot_migration_downgrade_upgrade_is_transactional(
    pg_session, monkeypatch
):
    """Exercise both directions inside a rolled-back transaction; retain local data."""
    migration = importlib.import_module(
        "backend.infrastructure.database.migrations.versions.20261002_0008_match_snapshot"
    )
    connection = await pg_session.connection()

    def verify(sync_connection):
        from sqlalchemy import inspect

        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(sync_connection))
        )
        before = sync_connection.execute(
            select(func.count()).select_from(MatchResultModel)
        ).scalar_one()
        migration.downgrade()
        columns = {
            c["name"] for c in inspect(sync_connection).get_columns("match_results")
        }
        assert "category_scores" not in columns and "explanation" not in columns
        migration.upgrade()
        columns = {
            c["name"] for c in inspect(sync_connection).get_columns("match_results")
        }
        assert {"category_scores", "explanation"} <= columns
        assert (
            sync_connection.execute(
                select(func.count()).select_from(MatchResultModel)
            ).scalar_one()
            == before
        )

    await connection.run_sync(verify)
