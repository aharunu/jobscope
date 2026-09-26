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
from backend.application.job_processing.extraction import (
    RequirementExtractionService,
    RequirementExtractor,
)
from backend.application.job_processing.lifecycle import JobLifecycleService
from backend.application.job_processing.normalizer import JobNormalizer
from backend.domain.crawl.entities import CrawlRun
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import (
    JobRepository,
    JobRequirementRepository,
    RawJobRepository,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class JobIngestionService:
    """Orchestrates normalization, deduplication, and persistence of crawled jobs."""

    job_repo: JobRepository
    raw_job_repo: RawJobRepository
    crawl_run_repo: CrawlRunRepository
    job_requirement_repo: JobRequirementRepository | None = None
    requirement_extractor: RequirementExtractor | None = None
    requirement_service: RequirementExtractionService | None = None
    normalizer: JobNormalizer = field(default_factory=JobNormalizer)
    lifecycle_service: JobLifecycleService | None = None

    def __post_init__(self) -> None:
        if self.lifecycle_service is None:
            self.lifecycle_service = JobLifecycleService(
                job_repo=self.job_repo,
                crawl_run_repo=self.crawl_run_repo,
            )
        if (
            self.requirement_service is None
            and self.job_requirement_repo is not None
            and self.requirement_extractor is not None
        ):
            self.requirement_service = RequirementExtractionService(
                requirement_repo=self.job_requirement_repo,
                extractor=self.requirement_extractor,
            )

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
        seen_job_ids: set[uuid.UUID] = set()

        # 2. Process each discovered job
        for discovered in crawl_result.jobs:
            try:
                action, job_id = await self._process_discovered_job(
                    source=source,
                    discovered=discovered,
                    run_id=crawl_run.id,
                    now=now,
                    warnings=warnings,
                )
                seen_job_ids.add(job_id)
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

        # 3. Determine interim crawl status
        error_count = len(errors)
        if error_count > 0:
            if (jobs_created + jobs_updated + jobs_unchanged) > 0:
                interim_status = CrawlStatus.PARTIAL
            else:
                interim_status = CrawlStatus.FAILED
        elif warnings:
            interim_status = CrawlStatus.PARTIAL
        else:
            interim_status = CrawlStatus.COMPLETED

        # 4. Safe absence-based closure evaluation & execution
        active_jobs = await self.job_repo.get_active_jobs_by_source(source.id)
        active_count = len(active_jobs)

        evaluation = self.lifecycle_service.evaluate_crawl_completeness(
            source=source,
            crawl_result=crawl_result,
            error_count=error_count,
            active_count=active_count,
            crawl_status=interim_status,
        )

        if evaluation.warning and evaluation.warning not in warnings:
            warnings.append(evaluation.warning)

        if evaluation.is_eligible:
            closed_jobs = await self.lifecycle_service.close_absent_jobs(
                source_id=source.id,
                crawl_run_id=crawl_run.id,
                seen_job_ids=seen_job_ids,
                now=now,
            )
            jobs_closed = len(closed_jobs)
        else:
            logger.info(
                "Absence closure skipped for source %s in crawl run %s: %s",
                source.id,
                crawl_run.id,
                evaluation.reason,
            )

        # 5. Determine final crawl status
        if interim_status == CrawlStatus.COMPLETED and warnings:
            final_status = CrawlStatus.PARTIAL
        else:
            final_status = interim_status

        # 6. Finalize CrawlRun update
        # jobs_found strictly preserves its historical meaning: job postings
        # discovered during the network crawl.
        # Invariant: jobs_found = (
        #     jobs_created + jobs_updated + jobs_unchanged + error_count
        # )
        # jobs_closed represents the separate absence-reconciliation outcome.
        jobs_discovered = len(crawl_result.jobs)

        crawl_run.status = final_status
        crawl_run.finished_at = datetime.now(UTC)
        crawl_run.jobs_found = jobs_discovered
        crawl_run.jobs_created = jobs_created
        crawl_run.jobs_updated = jobs_updated
        crawl_run.jobs_closed = jobs_closed
        crawl_run.error_count = error_count
        await self.crawl_run_repo.update_run(crawl_run)

        return JobIngestionResultDTO(
            crawl_run_id=crawl_run.id,
            source_id=source.id,
            status=final_status,
            jobs_found=jobs_discovered,
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
        warnings: list[str] | None = None,
    ) -> tuple[CrawlJobAction, uuid.UUID]:
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

            if self.requirement_service is not None:
                try:
                    await self.requirement_service.extract_and_persist(saved_job)
                except Exception as exc:
                    warn_msg = (
                        f"requirement_extraction_failed_job_{saved_job.id}: {exc}"
                    )
                    logger.warning(
                        "Requirement extraction failed for job %s: %s",
                        saved_job.id,
                        exc,
                        exc_info=True,
                    )
                    if warnings is not None and warn_msg not in warnings:
                        warnings.append(warn_msg)

            await self.crawl_run_repo.record_job_action(
                run_id=run_id,
                job_id=saved_job.id,
                action=CrawlJobAction.CREATED,
            )
            return CrawlJobAction.CREATED, saved_job.id

        # Existing job found: preserve first_seen_at, touch last_seen_at
        existing.last_seen_at = now
        was_closed = existing.status == JobStatus.CLOSED

        # Re-open if previously closed
        if was_closed:
            existing.status = JobStatus.ACTIVE
            existing.closed_at = None

        if canonical.content_hash != existing.content_hash or was_closed:
            # --- UPDATED --- (or REOPEN)
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

            if self.requirement_service is not None:
                try:
                    await self.requirement_service.extract_and_persist(saved_job)
                except Exception as exc:
                    warn_msg = (
                        f"requirement_extraction_failed_job_{saved_job.id}: {exc}"
                    )
                    logger.warning(
                        "Requirement extraction failed for job %s: %s",
                        saved_job.id,
                        exc,
                        exc_info=True,
                    )
                    if warnings is not None and warn_msg not in warnings:
                        warnings.append(warn_msg)

            await self.crawl_run_repo.record_job_action(
                run_id=run_id,
                job_id=saved_job.id,
                action=CrawlJobAction.UPDATED,
            )
            return CrawlJobAction.UPDATED, saved_job.id

        # --- UNCHANGED ---
        saved_job = await self.job_repo.save(existing)

        await self.crawl_run_repo.record_job_action(
            run_id=run_id,
            job_id=saved_job.id,
            action=CrawlJobAction.UNCHANGED,
        )
        return CrawlJobAction.UNCHANGED, saved_job.id
