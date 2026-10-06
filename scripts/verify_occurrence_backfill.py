"""Read-only migration acceptance: counts, FK attribution and coverage."""

import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.database.engine import create_database_engine


async def main():
    engine = create_database_engine(get_settings().model_copy(update={"debug": False}))
    async with engine.connect() as conn:
        output = {
            table: await conn.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in (
                "jobs",
                "job_occurrences",
                "raw_jobs",
                "job_requirements",
                "applications",
                "match_results",
            )
        }
        output["jobs_without_occurrences"] = await conn.scalar(
            text(
                "SELECT count(*) FROM jobs j WHERE NOT EXISTS"
                "(SELECT 1 FROM job_occurrences o WHERE o.job_id=j.id)"
            )
        )
        output["raw_without_occurrence"] = await conn.scalar(
            text("SELECT count(*) FROM raw_jobs WHERE occurrence_id IS NULL")
        )
        output["raw_attribution_mismatch"] = await conn.scalar(
            text(
                "SELECT count(*) FROM raw_jobs r JOIN job_occurrences o "
                "ON o.id=r.occurrence_id WHERE r.job_id!=o.job_id "
                "OR r.source_id!=o.source_id"
            )
        )
    before = json.loads(
        Path("docs/agent-reports/dedup_calibration_a5.json").read_text(encoding="utf-8")
    )["counts"]
    output["baseline_counts_unchanged"] = all(
        output[key] == value for key, value in before.items()
    )
    target = Path("docs/agent-reports/occurrence_backfill_a5.json")
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
