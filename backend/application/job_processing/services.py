"""Job ingestion and persistence service."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
)
from backend.application.job_processing.dtos import JobIngestionResultDTO
from backend.application.job_processing.normalizer import JobNormalizer
from backend.domain.crawl.entities import CrawlRun
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository, RawJobRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class JobIngestionService:
    """Orchestrates normalization, deduplication, and persistence of crawled jobs."""

    job_repo: JobRepository
    raw_job_repo: RawJobRepository
    crawl_run_repo: CrawlRunRepository
    normalizer: JobNormalizer = field(default_factory=JobNormalizer)

    async def ingest_crawl_result(
        self,
        source: RuntimeSourceDTO,
        crawl_result: CrawlResultDTO,
        crawl_run_id: uuid.UUID | None = None,
    ) -> JobIngestionResultDTO:
        """Process a crawl result: normalize, deduplicate, and record audit run.

        Transaction boundary note:
        This service executes against an existing database session. Repositories
        invoke session.flush() only; the outer transaction owner commits/rolls back.
        """
        now = datetime.now(UTC)

        # 1. Initialize or load CrawlRun record
        if crawl_run_id is not None:
            existing_run = await self.crawl_run_repo.get_by_id(crawl_run_id)
            if existing_run is not None:
                crawl_run = existing_run
                crawl_run.jobs_found = len(crawl_result.jobs)
            else:
                crawl_run = CrawlRun(
                    id=crawl_run_id,
                    source_id=source.id,
                    status=CrawlStatus.RUNNING,
                    started_at=now,
                    jobs_found=len(crawl_result.jobs),
                )
                crawl_run = await self.crawl_run_repo.create_run(crawl_run)
        else:
            crawl_run = CrawlRun(
                source_id=source.id,
                status=CrawlStatus.RUNNING,
                started_at=now,
                jobs_found=len(crawl_result.jobs),
            )
            crawl_run = await self.crawl_run_repo.create_run(crawl_run)

        jobs_created = 0
        jobs_updated = 0
        jobs_unchanged = 0
        jobs_closed = 0
        errors: list[str] = []
        warnings: list[str] = list(crawl_result.warnings)

        # 2. Process each discovered job
        for discovered in crawl_result.jobs:
            try:
                action = await self._process_discovered_job(
                    source=source,
                    discovered=discovered,
                    run_id=crawl_run.id,
                    now=now,
                )
                if action == CrawlJobAction.CREATED:
                    jobs_created += 1
                elif action == CrawlJobAction.UPDATED:
                    jobs_updated += 1
                elif action == CrawlJobAction.UNCHANGED:
                    jobs_unchanged += 1
            except Exception as exc:
                err_msg = (
                    f"Error processing job external_id={discovered.external_job_id!r} "
                    f"url={discovered.url!r}: {exc}"
                )
                logger.error(err_msg, exc_info=True)
                errors.append(err_msg)

        # 3. Determine final status
        error_count = len(errors)
        if error_count > 0:
            if (jobs_created + jobs_updated + jobs_unchanged) > 0:
                final_status = CrawlStatus.PARTIAL
            else:
                final_status = CrawlStatus.FAILED
        elif warnings:
            final_status = CrawlStatus.PARTIAL
        else:
            final_status = CrawlStatus.COMPLETED

        # 4. Finalize and persist CrawlRun update
        crawl_run.status = final_status
        crawl_run.finished_at = datetime.now(UTC)
        crawl_run.jobs_created = jobs_created
        crawl_run.jobs_updated = jobs_updated
        crawl_run.jobs_closed = jobs_closed
        crawl_run.error_count = error_count
        await self.crawl_run_repo.update_run(crawl_run)

        return JobIngestionResultDTO(
            crawl_run_id=crawl_run.id,
            source_id=source.id,
            status=final_status,
            jobs_found=len(crawl_result.jobs),
            jobs_created=jobs_created,
            jobs_updated=jobs_updated,
            jobs_unchanged=jobs_unchanged,
            jobs_closed=jobs_closed,
            error_count=error_count,
            warnings=warnings,
            errors=errors,
        )

    async def _process_discovered_job(
        self,
        source: RuntimeSourceDTO,
        discovered: DiscoveredJobDTO,
        run_id: uuid.UUID,
        now: datetime,
    ) -> CrawlJobAction:
        """Normalize, deduplicate, persist, and record action for discovered job."""
        canonical = self.normalizer.normalize(discovered, source)

        # Mandatory Deduplication Identity Lookup:
        # If external_job_id is present, lookup MUST use only
        # (source_id, external_job_id).
        # Do NOT fall back to canonical_url when external_job_id exists.
        # canonical_url is the fallback ONLY when external_job_id is missing/null.
        existing: Job | None = None
        if canonical.external_job_id:
            existing = await self.job_repo.get_by_source_and_external_id(
                source.id,
                canonical.external_job_id,
            )
        else:
            existing = await self.job_repo.get_by_canonical_url(canonical.canonical_url)

        if existing is None:
            # --- CREATED ---
            canonical.first_seen_at = now
            canonical.last_seen_at = now
            canonical.status = JobStatus.ACTIVE
            saved_job = await self.job_repo.save(canonical)

            raw_job = RawJob(
                job_id=saved_job.id,
                source_id=source.id,
                raw_content=discovered.raw_content,
                content_type=discovered.content_type,
                fetched_at=now,
            )
            await self.raw_job_repo.save(raw_job)

            await self.crawl_run_repo.record_job_action(
                run_id=run_id,
                job_id=saved_job.id,
                action=CrawlJobAction.CREATED,
            )
            return CrawlJobAction.CREATED

        # Existing job found: preserve first_seen_at, touch last_seen_at
        existing.last_seen_at = now

        # Re-open if previously closed
        if existing.status == JobStatus.CLOSED:
            existing.status = JobStatus.ACTIVE
            existing.closed_at = None

        if canonical.content_hash != existing.content_hash:
            # --- UPDATED ---
            existing.title = canonical.title
            existing.description = canonical.description
            existing.responsibilities = canonical.responsibilities
            existing.location = canonical.location
            existing.work_mode = canonical.work_mode
            existing.employment_type = canonical.employment_type
            existing.salary = canonical.salary
            if canonical.published_at is not None:
                existing.published_at = canonical.published_at
            existing.canonical_url = canonical.canonical_url
            existing.content_hash = canonical.content_hash
            existing.company = canonical.company

            saved_job = await self.job_repo.save(existing)

            # Store updated raw snapshot
            raw_job = RawJob(
                job_id=saved_job.id,
                source_id=source.id,
                raw_content=discovered.raw_content,
                content_type=discovered.content_type,
                fetched_at=now,
            )
            await self.raw_job_repo.save(raw_job)

            await self.crawl_run_repo.record_job_action(
                run_id=run_id,
                job_id=saved_job.id,
                action=CrawlJobAction.UPDATED,
            )
            return CrawlJobAction.UPDATED

        # --- UNCHANGED ---
        saved_job = await self.job_repo.save(existing)

        await self.crawl_run_repo.record_job_action(
            run_id=run_id,
            job_id=saved_job.id,
            action=CrawlJobAction.UNCHANGED,
        )
        return CrawlJobAction.UNCHANGED
