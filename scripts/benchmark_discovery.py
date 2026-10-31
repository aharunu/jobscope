"""Paired web-discovery benchmark with configurable model/effort pairs."""

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from backend.application.job_discovery.budget import (
    AcquisitionBudget,
    acquisition_scope,
)
from backend.infrastructure.http.safe_client import HttpSafeClient
from backend.infrastructure.parsers.markdown_source_parser import MarkdownSourceParser
from scripts.discover_sources import (
    Discovery,
    agent_fallback,
    discover,
    discovery_url_allowed,
)
from scripts.source_discovery_agent import AgentFailure, CodexDiscoveryAgent

MODELS = (("gpt-6-luna", "xhigh"), ("gpt-6.1-terra", "medium"))


def summarize(rows, models=MODELS):
    summaries = []
    for model, effort in models:
        group = [
            row
            for row in rows
            if row["model"] == model and row.get("effort", effort) == effort
        ]
        measured = [row for row in group if "total_tokens" in row]
        total = sum(row["total_tokens"] for row in measured)
        cached = sum(row.get("cached_input_tokens", 0) for row in measured)
        inputs = sum(row.get("input_tokens", 0) for row in measured)
        summaries.append(
            {
                "model": model,
                "effort": effort,
                "runs": len(group),
                "completed": sum(row["status"] == "completed" for row in group),
                "median_seconds": round(
                    statistics.median([row["wall_seconds"] for row in group]), 2
                )
                if group
                else None,
                "total_seconds": round(sum(row["wall_seconds"] for row in group), 2),
                "measured_usage_runs": len(measured),
                "total_tokens": total if measured else None,
                "input_tokens": inputs if measured else None,
                "cached_input_tokens": cached if measured else None,
                "uncached_input_tokens": inputs - cached if measured else None,
                "output_tokens": sum(row["output_tokens"] for row in measured)
                if measured
                else None,
                "input_cache_percent": round(cached / inputs * 100, 2)
                if inputs
                else None,
                "companies_with_candidates": sum(
                    bool(row.get("findings")) for row in group
                ),
                "companies_with_readable_board": sum(
                    any(
                        f["status"] == "agent_adapter_readable"
                        for f in row.get("findings", [])
                    )
                    for row in group
                ),
            }
        )
    all_tokens = sum(summary["total_tokens"] or 0 for summary in summaries)
    for summary in summaries:
        summary["token_share_percent"] = (
            round(summary["total_tokens"] / all_tokens * 100, 2)
            if all_tokens and summary["total_tokens"] is not None
            else None
        )
    return summaries


def save(output, rows, baselines, models=MODELS):
    payload = {
        "checked_at": datetime.now(UTC).isoformat(),
        "method": (
            "One paired run per company; same prompt/seed; two models run concurrently "
            "per pair. Agent forced for comparison, even if classical discovery "
            "succeeds. Preview time excluded from agent latency."
        ),
        "summaries": summarize(rows, models),
        "classical": baselines,
        "runs": rows,
    }
    path = output / "results.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)
    lines = [
        "# Discovery model benchmark",
        "",
        payload["method"],
        "",
        "CLI-reported input (including cached input) + output tokens. Token share",
        "is a share of measured tokens, not ChatGPT quota percentage or billing cost.",
        "Unavailable usage is null, not zero. Candidates are not proof of ownership.",
        "One run per model/company; live web latency and availability vary.",
        "",
        "| Model | Effort | Completed | Median seconds | Total tokens | "
        "Token share % | Input cache % | Readable board companies |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s in payload["summaries"]:
        lines.append(
            f"| {s['model']} | {s['effort']} | {s['completed']}/{s['runs']} | "
            f"{s['median_seconds']} | {s['total_tokens']} | "
            f"{s['token_share_percent']} | "
            f"{s['input_cache_percent']} | {s['companies_with_readable_board']} |"
        )
    lines += [
        "",
        "| Company | Model | Effort | Seconds | Tokens | Status | Candidates |",
        "|---|---|---|---:|---:|---|---:|",
    ]
    for row in rows:
        name = row["company"].replace("|", "/")
        lines.append(
            f"| {name} | {row['model']} | {row.get('effort', '')} | "
            f"{row['wall_seconds']} | "
            f"{row.get('total_tokens')} | {row['status']} | "
            f"{len(row.get('findings', []))} |"
        )
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def measure(source, client, model, effort, issues, timeout):
    started = time.monotonic()
    row = {"company": source.name, "seed": source.url, "model": model, "effort": effort}
    try:
        result = await CodexDiscoveryAgent(
            model=model, effort=effort, timeout=timeout
        ).research(source, issues)
        row.update(result._metrics)
        row["status"] = "completed"

        class Replay:
            async def research(self, *_):
                return result

        checked = await agent_fallback(
            source, Discovery(source.name, source.url), client, Replay()
        )
        row["findings"] = [
            {
                "url": f.url,
                "provider": f.provider,
                "status": f.status,
                "evidence": f.evidence,
                "chain": list(f.chain),
                "evidence_urls": list(f.evidence_urls),
            }
            for f in checked.findings
        ]
        row["issues"] = checked.issues
        row["unresolved_reason"] = result.unresolved_reason
    except AgentFailure as exc:
        row.update(status="failed", error=str(exc))
    row.setdefault("wall_seconds", round(time.monotonic() - started, 3))
    print(
        f"{source.name} | {model} {effort} | {row['status']} | "
        f"{row['wall_seconds']}s | tokens={row.get('total_tokens')}",
        flush=True,
    )
    return row


async def run(args):
    if len(set(args.models)) != 2:
        raise ValueError("Select two distinct model/effort pairs.")
    if not args.input.is_file():
        raise ValueError(
            "Benchmark input is missing. Create a local Markdown catalog with "
            "exactly ten distinct companies, then pass --input PATH. "
            "See docs/development/source-discovery.md."
        )
    sources, warnings = MarkdownSourceParser().parse_file(str(args.input))
    if len(sources) != 10 or len({s.company for s in sources}) != 10 or warnings:
        raise ValueError(
            "Benchmark requires exactly ten distinct companies and no parser warnings."
        )
    args.output.mkdir(parents=True, exist_ok=True)
    rows, baselines = [], []
    async with (
        httpx.AsyncClient(
            trust_env=not args.no_env_proxy, follow_redirects=False
        ) as transport,
        HttpSafeClient(
            request_url_policy=discovery_url_allowed,
            client=transport,
            min_request_interval_seconds=1.0,
            max_response_bytes=2 * 1024 * 1024,
            max_retries=0,
        ) as client,
    ):
        for index, source in enumerate(sources):
            print(f"Company {index + 1}/10: {source.name}", flush=True)
            started = time.monotonic()
            try:
                async with asyncio.timeout(60):
                    with acquisition_scope(
                        AcquisitionBudget(
                            max_requests=20, max_bytes=8 * 1024 * 1024, max_seconds=60
                        )
                    ):
                        baseline = await discover(source, client, verify=False)
                issues = baseline.issues
                count = len(baseline.findings)
            except TimeoutError:
                issues, count = ["Classical discovery timeout"], 0
            baselines.append(
                {
                    "company": source.name,
                    "seconds": round(time.monotonic() - started, 3),
                    "candidates": count,
                    "issues": issues,
                }
            )
            pair = args.models if index % 2 == 0 else tuple(reversed(args.models))
            tasks = [
                asyncio.create_task(
                    measure(source, client, model, effort, issues, args.timeout)
                )
                for model, effort in pair
            ]
            for task in asyncio.as_completed(tasks):
                rows.append(await task)
                save(args.output, rows, baselines, args.models)
    print(f"Benchmark complete: {args.output / 'report.md'}", flush=True)


def parse_pair(value):
    model, separator, effort = value.rpartition(":")
    if (
        not separator
        or not model
        or effort not in {"low", "medium", "high", "xhigh", "max"}
    ):
        raise argparse.ArgumentTypeError("Use MODEL:EFFORT, e.g. gpt-6-luna:high.")
    return model, effort


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=Path("data/discovery-benchmark.md")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("docs/agent-reports/discovery-benchmark")
    )
    parser.add_argument(
        "--timeout", type=int, choices=range(30, 601), default=120, metavar="30..600"
    )
    parser.add_argument("--no-env-proxy", action="store_true")
    parser.add_argument(
        "--models", type=parse_pair, nargs=2, default=MODELS, metavar="MODEL:EFFORT"
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
