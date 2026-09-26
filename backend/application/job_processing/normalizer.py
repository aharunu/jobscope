"""ATS-agnostic job normalization service."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from backend.application.job_discovery.dtos import DiscoveredJobDTO, RuntimeSourceDTO
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.source.normalization import normalize_source_url


@dataclass(slots=True)
class JobNormalizer:
    """ATS-agnostic normalizer transforming DiscoveredJobDTO into Job entity."""

    def normalize(
        self,
        discovered: DiscoveredJobDTO,
        source: RuntimeSourceDTO,
    ) -> Job:
        """Map discovered job and source into a canonical Job entity.

        Guarantees:
        - URL normalization via normalize_source_url()
        - Deterministic content_hash computation
        - Safe datetime parsing
        - Defensive handling of empty / missing fields
        """
        canonical_url = normalize_source_url(discovered.url)

        company = (
            str(discovered.metadata.get("company") or "").strip()
            or source.company
            or source.name
            or ""
        )

        title = str(discovered.title or "").strip() or "Untitled Position"

        # Check metadata first (for clean plain/html text), fallback to raw_content
        description = (
            str(
                discovered.metadata.get("description")
                or discovered.metadata.get("description_plain")
                or discovered.raw_content
                or ""
            ).strip()
            or title
        )

        external_job_id = (
            str(discovered.external_job_id).strip()
            if discovered.external_job_id is not None
            and str(discovered.external_job_id).strip()
            else None
        )

        location = (
            discovered.metadata.get("location")
            or discovered.metadata.get("country")
            or source.country
        )
        if location is not None:
            location = str(location).strip() or None

        work_mode = discovered.metadata.get("work_mode") or discovered.metadata.get(
            "workplace_type"
        )
        if work_mode is not None:
            work_mode = str(work_mode).strip() or None

        employment_type = discovered.metadata.get(
            "employment_type"
        ) or discovered.metadata.get("commitment")
        if employment_type is not None:
            employment_type = str(employment_type).strip() or None

        salary = discovered.metadata.get("salary")
        if salary is not None:
            salary = str(salary).strip() or None

        responsibilities = discovered.metadata.get("responsibilities")
        if responsibilities is not None:
            responsibilities = str(responsibilities).strip() or None

        raw_pub_date = (
            discovered.metadata.get("published_at")
            or discovered.metadata.get("created_at_upstream")
            or discovered.metadata.get("posted_at")
        )
        published_at = self._parse_datetime(raw_pub_date)

        content_hash = self.compute_content_hash(
            title=title,
            description=description,
            location=location,
            work_mode=work_mode,
        )

        return Job(
            id=uuid.uuid4(),
            source_id=source.id,
            external_job_id=external_job_id,
            canonical_url=canonical_url,
            company=company,
            title=title,
            description=description,
            responsibilities=responsibilities,
            location=location,
            work_mode=work_mode,
            employment_type=employment_type,
            salary=salary,
            published_at=published_at,
            content_hash=content_hash,
            status=JobStatus.ACTIVE,
        )

    @staticmethod
    def compute_content_hash(
        title: str,
        description: str,
        location: str | None = None,
        work_mode: str | None = None,
    ) -> str:
        """Compute deterministic SHA-256 hash across canonical job fields."""
        content = (
            f"{title.strip()}\n"
            f"{description.strip()}\n"
            f"{(location or '').strip()}\n"
            f"{(work_mode or '').strip()}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_datetime(val: Any) -> datetime | None:
        """Defensively parse datetimes from epoch ms, epoch s, or ISO strings."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val if val.tzinfo is not None else val.replace(tzinfo=UTC)

        # Check for numeric unix epoch timestamp
        if isinstance(val, (int, float)):
            try:
                # Milliseconds heuristic (> 1e11 is year 1973+ in ms)
                if val > 1e11:
                    return datetime.fromtimestamp(val / 1000.0, tz=UTC)
                return datetime.fromtimestamp(val, tz=UTC)
            except (ValueError, OverflowError, OSError):
                return None

        # String representation
        if isinstance(val, str):
            cleaned = val.strip()
            if not cleaned:
                return None

            # Numeric string
            if cleaned.isdigit():
                try:
                    num = int(cleaned)
                    if num > 1e11:
                        return datetime.fromtimestamp(num / 1000.0, tz=UTC)
                    return datetime.fromtimestamp(num, tz=UTC)
                except (ValueError, OverflowError, OSError):
                    return None

            # ISO 8601 string parsing
            try:
                dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
                return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
            except ValueError:
                pass

        return None
