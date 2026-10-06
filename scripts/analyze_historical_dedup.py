"""Read-only by default; --record-candidates persists review suggestions only."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.historical_dedup import analyze_historical


async def run(args):
    engine = create_database_engine(get_settings().model_copy(update={"debug": False}))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session, session.begin():
        report = await analyze_historical(session, args.limit, args.record_candidates)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "candidates"}
            | {"candidate_count": len(report["candidates"])}
        )
    )
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--record-candidates", action="store_true")
    parser.add_argument(
        "--output", default="docs/agent-reports/historical_dedup_a5.json"
    )
    asyncio.run(run(parser.parse_args()))
