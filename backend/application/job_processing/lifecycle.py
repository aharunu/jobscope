"""Job lifecycle management and safe absence-based closure service."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from backend.application.job_discovery.dtos import CrawlResultDTO, RuntimeSourceDTO
from backend.domain.crawl.entities import CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AbsenceClosureEvaluation:
    """Evaluation of whether a crawl provides authoritative evidence for closure.

    Attributes:
        is_eligible: True if all completeness and safety criteria are satisfied.
        reason: Explanatory diagnostic rationale for the eligibility decision.
        warning: Optional operational warning emitted if closure was suppressed.
    """

    is_eligible: bool
    reason: str
    warning: str | None = None


class JobLifecycleService:
    """Application service coordinating job lifecycle transitions and safe closure.

    Upholds Clean Architecture:
    - Pure application service with zero infrastructure or ORM dependencies.
    - Enforces safety invariants against partial, failed, or truncated crawls.
    - Prevents false mass-closures caused by scraper breakages, CDN errors,
      or pagination limits.
    - Preserves immutable creation audit timestamps (first_seen_at).
    """

    def __init__(
        self,
        job_repo: JobRepository,
        crawl_run_repo: CrawlRunRepository,
        zero_job_threshold: int = 0,
        allow_zero_job_closure: bool = False,
    ) -> None:
        self._job_repo = job_repo
        self._crawl_run_repo = crawl_run_repo
        self._zero_job_threshold = zero_job_threshold
        self._allow_zero_job_closure = allow_zero_job_closure

    def evaluate_crawl_completeness(
        self,
        source: RuntimeSourceDTO,
        crawl_result: CrawlResultDTO,
        error_count: int,
        active_count: int,
        crawl_status: CrawlStatus | None = None,
    ) -> AbsenceClosureEvaluation:
        """Evaluate if crawl provides authoritative evidence for closing absent jobs.

        Invariants:
        1. Failed or partial crawls must never close jobs.
        2. Incomplete pagination (pagination_max_pages_reached) must never close jobs.
        3. Job-level ingestion or normalization errors must never close jobs.
        4. Zero-job crawls on populated sources must be guarded against mass deletion.
        """
        # Rule 1: Crawl execution status check
        if crawl_status in (CrawlStatus.FAILED, CrawlStatus.PARTIAL):
            return AbsenceClosureEvaluation(
                is_eligible=False,
                reason=(
                    f"Crawl status is {crawl_status.value}; "
                    "absence closure suppressed for safety."
                ),
            )

        # Rule 2: Fail-closed adapter completeness assertion
        # Absence closure requires explicit True assertion. Omission is rejected.
        if not bool(getattr(crawl_result, "is_complete", False)):
            return AbsenceClosureEvaluation(
                is_eligible=False,
                reason=(
                    "Crawl is not explicitly established as complete; "
                    "absence closure suppressed."
                ),
            )

        # Rule 3: Pagination ceiling warning check
        if "pagination_max_pages_reached" in crawl_result.warnings:
            return AbsenceClosureEvaluation(
                is_eligible=False,
                reason="Pagination ceiling reached; incomplete source crawl.",
                warning="pagination_max_pages_reached",
            )

        # Rule 4: Job-level ingestion error check
        if error_count > 0:
            return AbsenceClosureEvaluation(
                is_eligible=False,
                reason=(
                    f"{error_count} job ingestion error(s) occurred; "
                    "cannot establish conclusive evidence of absence."
                ),
            )

        # Rule 5: Zero-job crawl anomaly guard
        # Protects against empty responses, anti-bot blocks, CDN drops, or
        # layout changes silently closing all active jobs on populated boards.
        jobs_found = len(crawl_result.jobs)
        if jobs_found == 0 and active_count > 0:
            if (
                not self._allow_zero_job_closure
                and active_count > self._zero_job_threshold
            ):
                return AbsenceClosureEvaluation(
                    is_eligible=False,
                    reason=(
                        f"Zero jobs discovered while {active_count} active jobs exist. "
                        "Suspected upstream layout change, anti-bot challenge, or "
                        "network drop; mass closure suppressed by zero-job safety "
                        "policy."
                    ),
                    warning="zero_jobs_discovered_closure_suppressed",
                )
            if crawl_result.warnings:
                return AbsenceClosureEvaluation(
                    is_eligible=False,
                    reason="Zero jobs discovered with warnings; closure suppressed.",
                    warning="zero_jobs_with_warnings_closure_suppressed",
                )

        return AbsenceClosureEvaluation(
            is_eligible=True,
            reason="Crawl is authoritative and complete for absence evaluation.",
        )

    async def close_absent_jobs(
        self,
        source_id: uuid.UUID,
        crawl_run_id: uuid.UUID,
        seen_job_ids: set[uuid.UUID],
        now: datetime,
    ) -> list[Job]:
        """Identify, close, persist, and audit absent jobs for source_id.

        Invariants:
        - Only touches ACTIVE jobs for source_id (multi-source isolation).
        - Sets status = JobStatus.CLOSED and closed_at = now.
        - Preserves first_seen_at.
        - Records CrawlRunJob with CrawlJobAction.CLOSED.
        - Does NOT delete any record.
        """
        active_jobs = await self._job_repo.get_active_jobs_by_source(source_id)
        absent_jobs = [job for job in active_jobs if job.id not in seen_job_ids]

        if not absent_jobs:
            return []

        for job in absent_jobs:
            job.status = JobStatus.CLOSED
            job.closed_at = now

        # Bulk persist updated job states
        saved_jobs = await self._job_repo.save_bulk(absent_jobs)

        # Bulk record audit entries
        audit_links = [
            CrawlRunJob(
                crawl_run_id=crawl_run_id,
                job_id=job.id,
                action=CrawlJobAction.CLOSED,
            )
            for job in saved_jobs
        ]
        await self._crawl_run_repo.record_job_actions(audit_links)

        logger.info(
            "Closed %d absent job(s) for source %s in crawl run %s.",
            len(saved_jobs),
            source_id,
            crawl_run_id,
        )
        return saved_jobs
