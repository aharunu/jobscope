"""Local read-only profiler of an already-started ingestion run."""

import argparse
import json
import re
import statistics
import subprocess
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


def get(path):
    with urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=20) as response:
        return json.load(response)


def snapshot(run_id, logs=False, output=None):
    root = "/api/ingestion/runs/" + run_id
    run = get(root)
    units = get(root + "/sources")["items"]
    responses, details = Counter(), Counter()
    if logs:
        command = [
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "logs",
            "--no-color",
            "--since",
            run["created_at"],
            "backend",
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode:
            raise RuntimeError("Docker log access failed; raw diagnostics withheld")
        tagged_responses, tagged_details, active_sources = Counter(), Counter(), set()
        current = None
        for line in result.stdout.splitlines():
            tagged = re.search(
                r"acquisition_http_response source=([\w-]+) "
                r"status=\d+ detail=(True|False)",
                line,
            )
            if tagged and tagged[1] in active_sources:
                tagged_responses[tagged[1]] += 1
                tagged_details[tagged[1]] += tagged[2] == "True"
            match = re.search(
                r"ingestion_source_started run="
                + re.escape(run_id)
                + r" source=([\w-]+)",
                line,
            )
            if match:
                current = match[1]
                active_sources.add(current)
            if current and "httpx: HTTP Request:" in line:
                responses[current] += 1
                if re.search(r"/postings/[^/\s?]+", line):
                    details[current] += 1
            if (
                "ingestion_source_completed run=" + run_id in line
                or "ingestion_source_failed run=" + run_id in line
            ):
                ended = re.search(r"source=([\w-]+)", line)
                if ended:
                    active_sources.discard(ended[1])
                current = None
        if tagged_responses:
            responses, details = tagged_responses, tagged_details
    safe = []
    grouped = defaultdict(list)
    for unit in units:
        row = {
            key: unit[key]
            for key in (
                "source_id",
                "source_name",
                "ats_type",
                "status",
                "started_at",
                "finished_at",
                "jobs_discovered",
                "error_type",
                "warnings",
            )
        }
        row["seconds"] = round((unit["duration_ms"] or 0) / 1000, 3)
        if logs:
            row["logged_http_responses"] = responses[unit["source_id"]]
            row["smartrecruiters_detail_responses"] = details[unit["source_id"]]
            row["detail_responses"] = details[unit["source_id"]]
        safe.append(row)
        if unit["status"] in ("COMPLETED", "PARTIAL", "FAILED"):
            grouped[unit["ats_type"]].append(row)
    providers = []
    for ats, rows in grouped.items():
        values = sorted(row["seconds"] for row in rows)
        providers.append(
            {
                "ats": ats,
                "measured_sources": len(rows),
                "seconds": round(sum(values), 2),
                "median_seconds": round(statistics.median(values), 2),
                "max_seconds": max(values),
                "failed": sum(row["status"] == "FAILED" for row in rows),
                "jobs": sum(row["jobs_discovered"] for row in rows),
                "logged_http_responses": sum(
                    row.get("logged_http_responses", 0) for row in rows
                )
                if logs
                else None,
            }
        )
    payload = {
        "captured_at": datetime.now(UTC).isoformat(),
        "run": run,
        "providers": sorted(providers, key=lambda row: row["seconds"], reverse=True),
        "sources": safe,
        "http_counts_available": logs,
        "http_count_limit": (
            "Logged responses only; attempts failing before a response are not counted."
        ),
    }
    target = Path(output or "docs/agent-reports/ingestion_profile.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": run["status"],
                "progress": run["progress"],
                "providers": payload["providers"],
                "slowest": sorted(
                    [r for r in safe if r["seconds"]],
                    key=lambda row: row["seconds"],
                    reverse=True,
                )[:8],
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--logs", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    snapshot(args.run_id, args.logs, args.output)
