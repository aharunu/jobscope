"""Unit tests for JobNormalizer."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from backend.application.job_discovery.dtos import DiscoveredJobDTO, RuntimeSourceDTO
from backend.application.job_processing.normalizer import JobNormalizer
from backend.domain.job.enums import JobStatus


def _create_sample_runtime_source(
    source_id: uuid.UUID | None = None,
    name: str = "Test Company Jobs",
    company: str = "Test Company",
    url: str = "https://jobs.example.com",
    country: str = "TR",
) -> RuntimeSourceDTO:
    return RuntimeSourceDTO(
        id=source_id or uuid.uuid4(),
        name=name,
        url=url,
        ats_type="lever",
        company=company,
        country=country,
        adapter_config={},
        pagination_config={},
        endpoint_config={},
        rate_limit_config={},
        metadata={},
    )


def test_job_normalizer_basic_mapping() -> None:
    """Verify standard mapping of DiscoveredJobDTO to canonical Job entity."""
    normalizer = JobNormalizer()
    source = _create_sample_runtime_source()

    discovered = DiscoveredJobDTO(
        external_job_id="job-12345",
        url="https://jobs.lever.co/testcompany/job-12345?utm_source=linkedin&ref=tracker",
        title="Senior Python Engineer",
        raw_content="{'text': 'Senior Python Engineer'}",
        content_type="application/json",
        metadata={
            "company": "Test Company",
            "location": "Istanbul, Turkey",
            "workplace_type": "hybrid",
            "employment_type": "Full-time",
            "salary": "100k-120k",
            "created_at_upstream": 1711000000000,
            "description": "Building resilient distributed systems.",
        },
    )

    job = normalizer.normalize(discovered, source)

    assert job.source_id == source.id
    assert job.external_job_id == "job-12345"
    # Stripped tracking params
    assert job.canonical_url == "https://jobs.lever.co/testcompany/job-12345"
    assert job.company == "Test Company"
    assert job.title == "Senior Python Engineer"
    assert job.description == "Building resilient distributed systems."
    assert job.location == "Istanbul, Turkey"
    assert job.work_mode == "hybrid"
    assert job.employment_type == "Full-time"
    assert job.salary == "100k-120k"
    assert job.status == JobStatus.ACTIVE
    assert job.published_at is not None
    assert job.published_at.year == 2024
    assert len(job.content_hash) == 64


def test_job_normalizer_url_normalization() -> None:
    """Verify URL normalization strips tracking params and trailing slashes."""
    normalizer = JobNormalizer()
    source = _create_sample_runtime_source()

    discovered = DiscoveredJobDTO(
        external_job_id=None,
        url="https://JOBS.Example.Com/Careers/123/?utm_campaign=spring&fbclid=abc#apply",
        title="Frontend Dev",
        raw_content="raw content",
        content_type="text/plain",
    )

    job = normalizer.normalize(discovered, source)
    assert job.canonical_url == "https://jobs.example.com/Careers/123"


def test_job_normalizer_deterministic_content_hash() -> None:
    """Verify identical content produces identical hash; changed content alters hash."""
    normalizer = JobNormalizer()
    source = _create_sample_runtime_source()

    discovered1 = DiscoveredJobDTO(
        external_job_id="1",
        url="https://example.com/1",
        title="DevOps Engineer",
        raw_content="Managing Kubernetes clusters",
        content_type="text/plain",
        metadata={"location": "Remote", "workplace_type": "remote"},
    )
    discovered2 = DiscoveredJobDTO(
        external_job_id="2",
        url="https://example.com/2",
        title="DevOps Engineer",
        raw_content="Managing Kubernetes clusters",
        content_type="text/plain",
        metadata={"location": "Remote", "workplace_type": "remote"},
    )
    discovered3 = DiscoveredJobDTO(
        external_job_id="1",
        url="https://example.com/1",
        title="DevOps Engineer (Updated)",
        raw_content="Managing Kubernetes clusters",
        content_type="text/plain",
        metadata={"location": "Remote", "workplace_type": "remote"},
    )

    job1 = normalizer.normalize(discovered1, source)
    job2 = normalizer.normalize(discovered2, source)
    job3 = normalizer.normalize(discovered3, source)

    assert job1.content_hash == job2.content_hash
    assert job1.content_hash != job3.content_hash

    # Verify matching manual hash
    expected = hashlib.sha256(
        b"DevOps Engineer\nManaging Kubernetes clusters\nRemote\nremote"
    ).hexdigest()
    assert job1.content_hash == expected


def test_job_normalizer_datetime_parsing() -> None:
    """Verify defensive datetime parsing from milliseconds, seconds, and ISO strings."""
    normalizer = JobNormalizer()

    # None
    assert normalizer._parse_datetime(None) is None
    assert normalizer._parse_datetime("") is None
    assert normalizer._parse_datetime("invalid-date") is None

    # Datetime object
    now = datetime.now(UTC)
    assert normalizer._parse_datetime(now) == now

    # Epoch in milliseconds (e.g. 1711000000000 -> 2024-03-21)
    dt_ms = normalizer._parse_datetime(1711000000000)
    assert dt_ms is not None
    assert dt_ms.year == 2024

    # Epoch in seconds (e.g. 1711000000 -> 2024-03-21)
    dt_s = normalizer._parse_datetime(1711000000)
    assert dt_s is not None
    assert dt_s.year == 2024

    # Numeric string milliseconds
    dt_str = normalizer._parse_datetime("1711000000000")
    assert dt_str is not None
    assert dt_str.year == 2024

    # ISO 8601 string
    dt_iso = normalizer._parse_datetime("2024-05-15T12:00:00Z")
    assert dt_iso is not None
    assert dt_iso.year == 2024
    assert dt_iso.month == 5
    assert dt_iso.day == 15


def test_job_normalizer_fallbacks() -> None:
    """Verify fallback handling for title, description, company, and external_id."""
    normalizer = JobNormalizer()
    source = RuntimeSourceDTO(
        id=uuid.uuid4(),
        name="Fallback Company Name",
        url="https://jobs.example.com",
        ats_type="lever",
        company=None,
        country="DE",
        adapter_config={},
        pagination_config={},
        endpoint_config={},
        rate_limit_config={},
        metadata={},
    )

    discovered = DiscoveredJobDTO(
        external_job_id="   ",  # Blank whitespace
        url="https://jobs.example.com/job/1",
        title=None,
        raw_content="",
        content_type="text/plain",
        metadata={},
    )

    job = normalizer.normalize(discovered, source)
    assert job.external_job_id is None
    assert job.title == "Untitled Position"
    assert (
        job.description == "Untitled Position"
    )  # Fallback to title when raw_content is empty
    assert job.company == "Fallback Company Name"
    assert job.location == "DE"  # Fallback to source.country
