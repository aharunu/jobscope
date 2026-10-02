"""Owned job lookup and layered core workflow against real PostgreSQL/API."""

import uuid

import pytest

from backend.infrastructure.llm.fake_provider import FakeProvider
from backend.interfaces.api.dependencies.matching import get_ai_provider
from tests.test_application_tracking_phase_1 import database_api as database_api
from tests.test_application_tracking_phase_1 import pg_session as pg_session
from tests.test_match_retrieval_phase_2 import prepare_profile


@pytest.mark.asyncio
async def test_job_lookup_scope_filters_pagination_and_validation(database_api):
    client, _, _, user, other, job = database_api
    headers = {"X-User-Id": str(user)}
    query = f"/api/applications?job_id={job}"
    assert (await client.get(query, headers=headers)).json()["items"] == []
    created = await client.post(
        "/api/applications", headers=headers, json={"job_id": str(job)}
    )
    assert created.status_code == 201
    found = (await client.get(query, headers=headers)).json()
    assert found["total"] == 1
    assert found["items"][0]["id"] == created.json()["id"]
    assert found["items"][0]["job"]["id"] == str(job)
    assert (await client.get(query + "&offset=1", headers=headers)).json() == {
        "items": [],
        "total": 1,
        "limit": 50,
        "offset": 1,
    }
    assert (await client.get(query + "&status=APPLIED", headers=headers)).json()[
        "total"
    ] == 0
    assert (await client.get(query + "&status=INTERESTED", headers=headers)).json()[
        "total"
    ] == 1
    assert (await client.get(query, headers={"X-User-Id": str(other)})).json()[
        "items"
    ] == []
    assert (
        await client.get(f"/api/applications?job_id={uuid.uuid4()}", headers=headers)
    ).json()["total"] == 0
    assert (
        await client.get("/api/applications?job_id=invalid", headers=headers)
    ).status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("use_ai", [False, True])
async def test_profile_match_optional_ai_tracking_reopen_history_delete(
    database_api, use_ai
):
    client, app, _, user, _, job = database_api
    headers = {"X-User-Id": str(user)}
    search = await prepare_profile(client, user)
    assert (await client.get(f"/api/jobs/{job}", headers=headers)).status_code == 200
    match = await client.post(
        "/api/matches",
        headers=headers,
        json={"job_id": str(job), "search_profile_id": search},
    )
    assert match.status_code == 200, match.text
    provider = FakeProvider()
    if use_ai:
        app.dependency_overrides[get_ai_provider] = lambda: provider
        analyzed = await client.post(
            f"/api/matches/{match.json()['id']}/ai", headers=headers
        )
        assert analyzed.status_code == 200, analyzed.text
        assert provider.calls == 1
    assert (
        await client.get(f"/api/applications?job_id={job}", headers=headers)
    ).json()["total"] == 0
    created = await client.post(
        "/api/applications", headers=headers, json={"job_id": str(job)}
    )
    assert created.status_code == 201
    application = created.json()
    assert application["status"] == "INTERESTED" and application["status_history"] == []
    path = f"/api/applications/{application['id']}"
    for target in ["APPLYING", "APPLIED", "INTERVIEW"]:
        response = await client.patch(
            path + "/status", headers=headers, json={"status": target}
        )
        assert response.status_code == 200
    for note in ["First note", "Edited note", None]:
        response = await client.patch(
            path + "/notes", headers=headers, json={"notes": note}
        )
        assert response.status_code == 200 and response.json()["notes"] == note
        assert response.json()["status"] == "INTERVIEW"
    reopened = (await client.get(path, headers=headers)).json()
    assert [(h["from_status"], h["to_status"]) for h in reopened["status_history"]] == [
        ("INTERESTED", "APPLYING"),
        ("APPLYING", "APPLIED"),
        ("APPLIED", "INTERVIEW"),
    ]
    assert (
        await client.get(f"/api/applications?job_id={job}", headers=headers)
    ).json()["items"][0]["status"] == "INTERVIEW"
    if use_ai:
        assert (
            await client.post(
                f"/api/matches/{match.json()['id']}/ai?force=true", headers=headers
            )
        ).status_code == 200
        assert (await client.get(path, headers=headers)).json()["status"] == "INTERVIEW"
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.get(path + "/history", headers=headers)).status_code == 404
    assert (await client.get(f"/api/jobs/{job}", headers=headers)).status_code == 200
    assert (
        await client.get(f"/api/applications?job_id={job}", headers=headers)
    ).json()["items"] == []
