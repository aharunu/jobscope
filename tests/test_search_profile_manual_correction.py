"""Canonical SearchProfile PATCH survives fresh database-backed reads."""

import pytest

from tests.test_application_tracking_phase_1 import database_api as database_api
from tests.test_application_tracking_phase_1 import pg_session as pg_session


@pytest.mark.asyncio
async def test_search_profile_edit_persists_on_fresh_reads(database_api):
    client, _, _, user, _, _ = database_api
    headers = {"X-User-Id": str(user)}
    created = await client.post(
        "/api/search-profiles",
        headers=headers,
        json={"name": "Original", "seniority": "Junior"},
    )
    assert created.status_code == 201
    identity = created.json()["id"]
    updates = {
        "name": "Edited Search",
        "seniority": "Senior",
        "target_roles": ["Backend Engineer"],
        "target_skills": ["Python", "SQL"],
        "locations": ["Washington, DC"],
        "work_modes": ["Remote", "Hybrid"],
        "industries": ["FinTech"],
        "salary_min": 100000,
        "salary_max": 150000,
    }
    updated = await client.patch(
        f"/api/search-profiles/{identity}", headers=headers, json=updates
    )
    assert updated.status_code == 200
    authoritative = updated.json()
    detail = await client.get(f"/api/search-profiles/{identity}", headers=headers)
    listing = await client.get("/api/search-profiles", headers=headers)
    assert detail.status_code == listing.status_code == 200
    persisted = detail.json()
    assert next(p for p in listing.json() if p["id"] == identity) == persisted
    for field in authoritative:
        if field.startswith("salary_"):
            assert float(persisted[field]) == float(authoritative[field])
        else:
            assert persisted[field] == authoritative[field]
    for field, value in updates.items():
        actual = authoritative[field]
        assert (
            float(actual) == value if field.startswith("salary_") else actual == value
        )
    invalid = await client.patch(
        f"/api/search-profiles/{identity}",
        headers=headers,
        json={"seniority": ["Junior", "Senior"]},
    )
    assert invalid.status_code == 422
    assert (
        await client.get(f"/api/search-profiles/{identity}", headers=headers)
    ).json()["seniority"] == "Senior"
