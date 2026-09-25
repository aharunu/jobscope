"""API endpoint contract and integration tests for source health probing."""

from __future__ import annotations

import datetime
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.application.job_discovery.dtos import SourceProbeResultDTO
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source import Source
from backend.interfaces.api.dependencies.sources import (
    get_source_health_probe,
    get_source_registry_service,
    get_source_repository,
)
from tests.test_source_api import InMemorySourceRepo
from tests.test_source_probe_service import MockSourceHealthProbe


def _seed_test_sources() -> list[Source]:
    now = datetime.datetime.now(datetime.UTC)
    return [
        Source(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="Trendyol Lever",
            company="Trendyol",
            url="https://jobs.lever.co/trendyol",
            country="TR",
            ats_type="lever",
            active=True,
            created_at=now,
            updated_at=now,
        ),
        Source(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            name="Getir Greenhouse",
            company="Getir",
            url="https://boards.greenhouse.io/getir",
            country="TR",
            ats_type="greenhouse",
            active=True,
            created_at=now,
            updated_at=now,
        ),
        Source(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            name="Inactive Source",
            company="OldCorp",
            url="https://jobs.ashbyhq.com/oldcorp",
            country="TR",
            ats_type="ashby",
            active=False,
            created_at=now,
            updated_at=now,
        ),
    ]


def test_probe_single_source_endpoint_success(app: FastAPI, client: TestClient) -> None:
    """Verify POST /api/sources/{source_id}/probe returns 200 with diagnostics."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    probe = MockSourceHealthProbe()
    service = SourceRegistryService(repository=repo, health_probe=probe)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    target_id = sources[0].id
    response = client.post(f"/api/sources/{target_id}/probe")

    assert response.status_code == 200
    data = response.json()
    assert data["source_id"] == str(target_id)
    assert data["url"] == "https://jobs.lever.co/trendyol"
    assert data["is_reachable"] is True
    assert data["status_code"] == 200
    assert data["latency_ms"] == 12.5
    assert data["redirect_count"] == 0
    assert data["ats_type"] == "lever"
    assert "probed_at" in data
    assert data["error_type"] is None


def test_probe_single_source_endpoint_not_found(
    app: FastAPI, client: TestClient
) -> None:
    """Verify POST /api/sources/{source_id}/probe returns 404 for missing source."""
    repo = InMemorySourceRepo([])
    probe = MockSourceHealthProbe()
    service = SourceRegistryService(repository=repo, health_probe=probe)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    missing_id = uuid.uuid4()
    response = client.post(f"/api/sources/{missing_id}/probe")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_probe_single_source_unreachable_diagnostics(
    app: FastAPI, client: TestClient
) -> None:
    """Verify diagnostic results when a probe reports failure (reachable=False)."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    probe = MockSourceHealthProbe()
    probe.next_result = SourceProbeResultDTO(
        source_id=sources[1].id,
        url=sources[1].url,
        is_reachable=False,
        status_code=403,
        latency_ms=45.0,
        final_url=sources[1].url,
        redirect_count=0,
        error_type="client_error",
        error_message="HTTP client error: 403",
        ats_type=sources[1].ats_type,
    )
    service = SourceRegistryService(repository=repo, health_probe=probe)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.post(f"/api/sources/{sources[1].id}/probe")

    assert response.status_code == 200
    data = response.json()
    assert data["is_reachable"] is False
    assert data["status_code"] == 403
    assert data["error_type"] == "client_error"
    assert "403" in (data["error_message"] or "")


def test_probe_batch_sources_endpoint_success(app: FastAPI, client: TestClient) -> None:
    """Verify POST /api/sources/probe executes batch reachability checks."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    probe = MockSourceHealthProbe()
    service = SourceRegistryService(repository=repo, health_probe=probe)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.post(
        "/api/sources/probe",
        params={"active_only": "true", "max_concurrency": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_probed"] == 2
    assert data["reachable_count"] == 2
    assert data["unreachable_count"] == 0
    assert len(data["results"]) == 2


def test_probe_batch_sources_endpoint_empty(app: FastAPI, client: TestClient) -> None:
    """Verify POST /api/sources/probe with no matching sources returns empty batch."""
    repo = InMemorySourceRepo([])
    probe = MockSourceHealthProbe()
    service = SourceRegistryService(repository=repo, health_probe=probe)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.post("/api/sources/probe")

    assert response.status_code == 200
    data = response.json()
    assert data["total_probed"] == 0
    assert data["reachable_count"] == 0
    assert data["unreachable_count"] == 0
    assert data["results"] == []


def test_probe_health_probe_dependency_injection(
    app: FastAPI, client: TestClient
) -> None:
    """Verify get_source_health_probe dependency can be overridden directly."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    mock_probe = MockSourceHealthProbe()

    # Clear service override and supply repository + probe overrides
    app.dependency_overrides.pop(get_source_registry_service, None)
    app.dependency_overrides[get_source_repository] = lambda: repo
    app.dependency_overrides[get_source_health_probe] = lambda: mock_probe

    target_id = sources[0].id
    response = client.post(f"/api/sources/{target_id}/probe")

    assert response.status_code == 200
    data = response.json()
    assert data["source_id"] == str(target_id)
    assert data["is_reachable"] is True
    assert mock_probe.probed_urls == ["https://jobs.lever.co/trendyol"]
