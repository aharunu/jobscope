"""Read-only sanitized local-data inventory before dedup threshold selection."""

import asyncio
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import text

from backend.infrastructure.database.engine import get_engine


async def main():
    engine = get_engine()
    async with engine.connect() as conn:
        rows = (
            (
                await conn.execute(
                    text(
                        "SELECT id, source_id, company, title, location, "
                        "description FROM jobs"
                    )
                )
            )
            .mappings()
            .all()
        )
        raw = (
            (await conn.execute(text("SELECT raw_content FROM raw_jobs")))
            .scalars()
            .all()
        )
        counts = {
            table: await conn.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in (
                "jobs",
                "raw_jobs",
                "job_requirements",
                "applications",
                "match_results",
            )
        }
    blocks = defaultdict(list)
    for row in rows:
        blocks[
            (row["company"].casefold().strip(), row["title"].casefold().strip())
        ].append(row)
    evidence = Counter()
    for value in raw:
        try:
            item = json.loads(value)
        except (ValueError, TypeError):
            continue
        if isinstance(item, dict):
            for key in (
                "requisition_id",
                "requisitionId",
                "jobRequisitionId",
                "internal_job_id",
            ):
                if item.get(key):
                    evidence[key] += 1
    repeated = [values for values in blocks.values() if len(values) > 1]
    cross = [values for values in repeated if len({v["source_id"] for v in values}) > 1]
    output = {
        "counts": counts,
        "repeated_company_title_blocks": len(repeated),
        "cross_source_blocks": len(cross),
        "raw_reference_keys": dict(evidence),
        "examples": [
            {
                "block": hashlib.sha256(str(key).encode()).hexdigest()[:12],
                "jobs": len(values),
                "sources": len({v["source_id"] for v in values}),
                "distinct_locations": len({v["location"] for v in values}),
                "description_lengths": sorted(len(v["description"]) for v in values),
            }
            for key, values in blocks.items()
            if len(values) > 1
        ][:20],
    }
    target = Path("docs/agent-reports/dedup_calibration_a5.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
