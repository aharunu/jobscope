"""Regression tests for Job Description and Responsibilities cleaning & normalization.

Covers:
1. content_cleaning.normalize_job_description_and_responsibilities:
   - None / empty / whitespace handling
   - Plain text preservation
   - Lever ATS JSON dump unpacking (description, responsibilities, requirements)
   - HTML entity unescaping (&nbsp;, \xa0, quotes)
   - Malformed JSON resilience
2. JobQueryService.get_job mapping with normalized DTO
3. API route GET /api/jobs/{job_id} returning clean, human-readable description
   and responsibilities without raw ATS JSON payload.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.application.job_processing.content_cleaning import (
    clean_html_to_bullets,
    normalize_job_description_and_responsibilities,
)
from backend.application.job_processing.query_service import JobQueryService
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository
from backend.interfaces.api.dependencies.job_processing import get_job_query_service
from backend.interfaces.api.main import create_app

# ==============================================================================
# 1. Content Cleaning Unit Tests
# ==============================================================================


def test_clean_html_to_bullets() -> None:
    """Verify HTML list markup is converted into clean bullet points."""
    html_input = (
        "<li>Lead architecture reviews</li>\n"
        "<li>Mentor junior &amp; mid engineers&nbsp;</li>\n"
        "<li>Ensure 99.9% uptime</li>"
    )
    result = clean_html_to_bullets(html_input)
    assert "- Lead architecture reviews" in result
    assert "- Mentor junior & mid engineers" in result
    assert "- Ensure 99.9% uptime" in result
    assert "&nbsp;" not in result
    assert "<li>" not in result


def test_normalize_empty_and_plain_description() -> None:
    """Verify None, empty strings, and standard plain text are handled properly."""
    # None
    d1, r1 = normalize_job_description_and_responsibilities(None, None)
    assert d1 == ""
    assert r1 is None

    # Whitespace
    d2, r2 = normalize_job_description_and_responsibilities("   \n\t  ", None)
    assert d2 == ""
    assert r2 is None

    # Standard plain text is preserved verbatim
    plain_desc = "Develop high-performance distributed systems in Python."
    plain_resp = "- Own service deployments\n- Conduct code reviews"
    d3, r3 = normalize_job_description_and_responsibilities(plain_desc, plain_resp)
    assert d3 == plain_desc
    assert r3 == plain_resp


def test_normalize_lever_json_payload() -> None:
    """Verify raw Lever ATS JSON dump is parsed into clean content."""
    raw_lever_payload = json.dumps(
        {
            "openingPlain": "Dream Games is looking for an exceptional engineer.",
            "descriptionPlain": "We are seeking an AI Engineer to join our team.",
            "descriptionBody": (
                "<div>We are seeking an AI Engineer to join our team.</div>"
            ),
            "additionalPlain": (
                "We offer comprehensive health coverage and stock options."
            ),
            "lists": [
                {
                    "text": "Responsibilities",
                    "content": (
                        "<li>Build AI creative pipelines</li>\n"
                        "<li>Optimize deep learning inference&nbsp;latency</li>"
                    ),
                },
                {
                    "text": "Requirements",
                    "content": (
                        "<li>5+ years of software engineering experience</li>\n"
                        "<li>Fluency in Python and PyTorch</li>"
                    ),
                },
            ],
            "hostedUrl": "https://jobs.lever.co/dreamgames/abc-123",
            "applyUrl": "https://jobs.lever.co/dreamgames/abc-123/apply",
            "id": "lever-raw-id-456",
        }
    )

    desc, resp = normalize_job_description_and_responsibilities(
        raw_desc=raw_lever_payload,
        raw_resp=None,
    )

    # Raw JSON artifacts must NOT be present
    assert "{" not in desc
    assert "}" not in desc
    assert "hostedUrl" not in desc
    assert "applyUrl" not in desc
    assert "lever-raw-id-456" not in desc
    assert "descriptionBody" not in desc

    # Content must be clean and human-readable
    assert "Dream Games is looking for an exceptional engineer." in desc
    assert "We are seeking an AI Engineer to join our team." in desc
    assert "We offer comprehensive health coverage and stock options." in desc
    assert "Requirements:" in desc
    assert "- 5+ years of software engineering experience" in desc

    # Responsibilities must be cleanly extracted into its own field
    assert resp is not None
    assert "- Build AI creative pipelines" in resp
    assert "- Optimize deep learning inference latency" in resp
    assert "&nbsp;" not in resp
    assert "<li>" not in resp


def test_normalize_malformed_json_fallback() -> None:
    """Verify malformed JSON-like string does not raise error and is preserved."""
    malformed = "{this is not valid json: 123"
    desc, resp = normalize_job_description_and_responsibilities(malformed, None)
    assert desc == malformed
    assert resp is None


# ==============================================================================
# 2. Application Service Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_job_query_service_get_job_normalizes_raw_json() -> None:
    """Verify JobQueryService.get_job unpacks raw JSON into clean JobDetailDTO."""
    mock_repo = AsyncMock(spec=JobRepository)
    job_id = uuid.uuid4()
    raw_payload = json.dumps(
        {
            "descriptionPlain": "Building real-time search services.",
            "lists": [
                {
                    "text": "Responsibilities",
                    "content": "<li>Maintain OpenSearch clusters</li>",
                }
            ],
        }
    )

    dummy_job = Job(
        id=job_id,
        source_id=uuid.uuid4(),
        canonical_url="https://example.com/jobs/123",
        company="SearchCo",
        title="Search Infrastructure Engineer",
        description=raw_payload,
        responsibilities=None,
        content_hash="hash_123456",
        status=JobStatus.ACTIVE,
    )
    mock_repo.get_job_detail.return_value = dummy_job

    service = JobQueryService(job_repo=mock_repo)
    detail_dto = await service.get_job(job_id)

    assert detail_dto is not None
    assert detail_dto.id == job_id
    assert detail_dto.description == "Building real-time search services."
    assert detail_dto.responsibilities == "- Maintain OpenSearch clusters"
    assert "lists" not in detail_dto.description


# ==============================================================================
# 3. API Route Integration Tests
# ==============================================================================


def test_api_get_job_detail_returns_normalized_content() -> None:
    """Verify GET /api/jobs/{id} returns clean description and responsibilities."""
    job_id = uuid.uuid4()
    raw_payload = json.dumps(
        {
            "descriptionPlain": "Full-stack developer needed for modern web portal.",
            "lists": [
                {
                    "text": "Responsibilities",
                    "content": "<li>Develop Next.js frontend and FastAPI backend</li>",
                }
            ],
            "hostedUrl": "https://jobs.lever.co/test/999",
        }
    )

    dummy_job = Job(
        id=job_id,
        source_id=uuid.uuid4(),
        canonical_url="https://example.com/jobs/fullstack",
        company="TechStudio",
        title="Senior Fullstack Engineer",
        description=raw_payload,
        responsibilities=None,
        content_hash="hash_abcdef",
        status=JobStatus.ACTIVE,
        location="Remote",
        work_mode="Remote",
    )

    mock_repo = AsyncMock(spec=JobRepository)
    mock_repo.get_job_detail.return_value = dummy_job
    query_service = JobQueryService(job_repo=mock_repo)

    app = create_app()
    app.dependency_overrides[get_job_query_service] = lambda: query_service

    with TestClient(app) as client:
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert data["id"] == str(job_id)
        assert data["title"] == "Senior Fullstack Engineer"
        assert data["company"] == "TechStudio"

        # Verify no raw JSON is leaked into description
        assert "hostedUrl" not in data["description"]
        assert "{" not in data["description"]
        expected_desc = "Full-stack developer needed for modern web portal."
        assert data["description"] == expected_desc

        # Verify responsibilities is populated
        expected_resp = "- Develop Next.js frontend and FastAPI backend"
        assert data["responsibilities"] == expected_resp
