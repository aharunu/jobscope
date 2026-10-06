# Maintenance and diagnostics

Run Python tools from the repository root with the project virtual environment
active. They use the existing settings and database URL; check the target environment
before running them. Installed `venv`/`node_modules` and Docker dependency volumes
are intentionally retained, not periodically deleted by repository cleanup.

## Developer and startup tools

- `python scripts/dev.py --help`: common test, lint, format, run, migrate and check
  tasks. `migrate` applies schema changes; `check` runs format/lint/tests and does
  not include frontend validation.
- `scripts/docker_backend_start.py`: required container entry point. It constructs
  the internal database URL, applies migrations and starts the configured command.
- `start.ps1` / `stop.ps1`: documented local Docker wrappers; see
  [the development runbook](local-development.md).

## Read-only run profiler

```powershell
python -m scripts.profile_ingestion --help
python -m scripts.profile_ingestion EXISTING_RUN_ID
```

Profiles an already-started run through the local backend at port 8000; it does not
start, cancel or persist ingestion. Output defaults to ignored
`docs/agent-reports/ingestion_profile.json`; `--output` chooses another file.
`--logs` additionally reads Docker backend logs and extracts per-Source HTTP/detail
counts. It does not print the raw log. Tagged acquisition log entries are preferred;
legacy sequential attribution is a best-effort fallback and cannot accurately
attribute concurrent Sources. Logged responses exclude attempts that failed before
a response. Per-Source durations overlap and must not be summed as wall time.

## Dedup and migration integrity

```powershell
python -m scripts.analyze_historical_dedup --limit 1000
python -m scripts.calibrate_dedup
python -m scripts.verify_occurrence_backfill
```

Historical analysis defaults to a non-mutating dry run and writes candidate results
locally. `--record-candidates` explicitly writes review suggestions, never merges
Jobs. Review decisions through `/dedup`; do not infer merge safety from basic
company/title/location equality.

Calibration reads existing data and writes sanitized block/count summaries to
`docs/agent-reports/dedup_calibration_a5.json`. The backfill verifier **reads that
file as its baseline**, checks occurrence/raw provenance coverage and writes
`docs/agent-reports/occurrence_backfill_a5.json`. Preserve the old baseline before
rerunning calibration if verifying before/after migration counts. Legitimate
subsequent ingestion changes counts, so an old baseline mismatch alone does not
prove corruption. The retained original A5 baseline is not an ongoing invariant
that the application must keep 667 Jobs forever.

Use `python -m alembic check` for schema/model drift without applying migrations.
See [verification commands](local-development.md) for complete backend/frontend
regression. Do not run data cleanup or historical merges merely to tidy files.
