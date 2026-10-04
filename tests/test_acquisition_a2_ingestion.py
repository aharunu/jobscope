"""Canonical change semantics and closure safety, no live providers."""

import hashlib
import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
)
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.job.enums import JobStatus
from backend.domain.source.entities import Source
from tests.test_greenhouse_crawler_integration import (
    InMemoryCrawlRunRepository,
    InMemoryJobRepository,
    InMemoryRawJobRepository,
)


def setup():
    source = RuntimeSourceDTO.from_domain(
        Source(
            name="A2",
            company="Company",
            url="https://jobs.lever.co/a2",
            ats_type="lever",
        )
    )
    jobs, raw, runs = (
        InMemoryJobRepository(),
        InMemoryRawJobRepository(),
        InMemoryCrawlRunRepository(),
    )
    extraction = AsyncMock()
    service = JobIngestionService(jobs, raw, runs, requirement_service=extraction)
    return source, jobs, raw, runs, service, extraction


def posting(source, **metadata):
    payload = {
        "title": "Engineer",
        "description": "Python engineer",
        "employment_type": "Full-time",
        "work_mode": "Remote",
        "responsibilities": "Build services",
        "salary": "100 USD",
        "location": "Istanbul",
        "company": "Company",
        **metadata,
    }
    return DiscoveredJobDTO(
        external_job_id="1",
        url=f"https://example.com/{source.id}/1",
        title="Engineer",
        raw_content=json.dumps(payload),
        content_type="application/json",
        metadata=payload,
    )


async def ingest(service, source, *items, complete=True):
    return await service.ingest_crawl_result(
        source,
        CrawlResultDTO(
            source_id=source.id,
            ats_type="lever",
            jobs=list(items),
            is_complete=complete,
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("employment_type", "Contract"),
        ("responsibilities", "Design services"),
        ("salary", "200 USD"),
        ("company", "New Company"),
        ("work_mode", "Hybrid"),
        ("description", "New full text"),
        ("location", "Ankara"),
    ],
)
async def test_canonical_field_only_change(field, value):
    source, jobs, raw, _, service, extraction = setup()
    await ingest(service, source, posting(source))
    result = await ingest(service, source, posting(source, **{field: value}))
    job = next(iter(jobs.jobs.values()))
    assert result.jobs_updated == 1 and getattr(job, field) == value
    assert len(raw.raw_jobs) == 2 and extraction.extract_and_persist.call_count == 2


@pytest.mark.asyncio
async def test_old_hash_only_transition_is_unchanged():
    source, jobs, raw, _, service, extraction = setup()
    await ingest(service, source, posting(source))
    job = next(iter(jobs.jobs.values()))
    job.content_hash = hashlib.sha256(b"old four field hash").hexdigest()
    first_seen = job.first_seen_at
    result = await ingest(service, source, posting(source))
    assert result.jobs_unchanged == 1 and result.jobs_updated == 0
    assert job.first_seen_at == first_seen and job.last_seen_at is not None
    assert len(raw.raw_jobs) == 1 and extraction.extract_and_persist.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("absent", [None, ""])
async def test_missing_fields_preserved_but_raw_faithful(absent):
    source, jobs, raw, _, service, _ = setup()
    await ingest(service, source, posting(source))
    partial = posting(
        source,
        employment_type=absent,
        work_mode=absent,
        responsibilities=absent,
        salary=absent,
        location=absent,
        description="Changed",
    )
    result = await ingest(service, source, partial)
    job = next(iter(jobs.jobs.values()))
    assert result.jobs_updated == 1
    assert (
        job.employment_type,
        job.work_mode,
        job.responsibilities,
        job.salary,
        job.location,
    ) == ("Full-time", "Remote", "Build services", "100 USD", "Istanbul")
    assert raw.raw_jobs[-1].raw_content == partial.raw_content
    assert json.loads(raw.raw_jobs[-1].raw_content)["salary"] == absent


@pytest.mark.asyncio
async def test_missing_description_does_not_replace_with_json_or_title():
    source, jobs, raw, _, service, _ = setup()
    await ingest(service, source, posting(source))
    item = replace(
        posting(source),
        title=None,
        raw_content='{"id":"1"}',
        metadata={"description": "Untitled", "description_available": False},
    )
    result = await ingest(service, source, item)
    assert result.jobs_unchanged == 1 and len(raw.raw_jobs) == 1
    assert next(iter(jobs.jobs.values())).description == "Python engineer"


@pytest.mark.asyncio
async def test_url_change_safe_for_same_identity_and_publication_is_metadata_only():
    source, jobs, raw, _, service, extraction = setup()
    await ingest(service, source, posting(source))
    moved = replace(posting(source), url=f"https://example.com/{source.id}/moved")
    result = await ingest(service, source, moved)
    assert (
        result.jobs_updated == 1
        and next(iter(jobs.jobs.values())).canonical_url == moved.url
    )
    dated = replace(
        moved, metadata={**moved.metadata, "published_at": "2026-10-04T00:00:00Z"}
    )
    result = await ingest(service, source, dated)
    assert result.jobs_unchanged == 1 and len(raw.raw_jobs) == 2
    assert extraction.extract_and_persist.call_count == 2
    assert next(iter(jobs.jobs.values())).published_at == datetime(
        2026, 10, 4, tzinfo=UTC
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("external_id", [None, "different"])
async def test_cross_source_collision_skipped_without_ownership_mutation(external_id):
    a, jobs, raw, runs, service, _ = setup()
    await ingest(service, a, posting(a))
    owner = next(iter(jobs.jobs.values()))
    old_seen = owner.last_seen_at
    b = replace(a, id=uuid.uuid4())
    absent = replace(
        owner,
        id=uuid.uuid4(),
        source_id=b.id,
        external_job_id="absent",
        canonical_url=f"https://example.com/{b.id}/absent",
    )
    await jobs.save(absent)
    conflict = replace(posting(b), url=owner.canonical_url, external_job_id=external_id)
    result = await ingest(service, b, conflict, posting(b))
    assert result.status == CrawlStatus.PARTIAL and result.error_count == 1
    assert result.errors == ["JOB_URL_OWNERSHIP_CONFLICT"]
    assert result.jobs_created == 1 and result.jobs_closed == 0
    assert owner.source_id == a.id and owner.last_seen_at == old_seen
    assert absent.status == JobStatus.ACTIVE


@pytest.mark.asyncio
async def test_incomplete_without_warning_is_partial_and_no_closure():
    source, jobs, _, _, service, _ = setup()
    await ingest(service, source, posting(source))
    result = await ingest(service, source, complete=False)
    assert (
        result.status == CrawlStatus.PARTIAL
        and "acquisition_incomplete" in result.warnings
    )
    assert (
        result.jobs_closed == 0
        and next(iter(jobs.jobs.values())).status == JobStatus.ACTIVE
    )
