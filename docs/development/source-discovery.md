# Read-only career-board discovery

## Modular catalog and phased workflow

`data/turkish-job-sources.md` remains the editable canonical catalog. Its original
rows, annotations and provenance remain intact. The entire `data/source-discovery/`
working directory and local `data/discovery*.md` inputs are ignored by Git.
`data/source-discovery/` contains derived provider modules and small phase inputs;
edit the canonical file and
regenerate these inputs rather than maintaining two independent catalogs.

```powershell
.\venv\Scripts\python.exe -m scripts.discovery_phases prepare
.\venv\Scripts\python.exe -m scripts.discovery_phases status
```

Preparation is entirely local: no HTTP, model, database or catalog-sync calls.
`README.md` indexes supported ATS modules, known unsupported platforms, external
boards, unknown career pages, hands-off/unsafe URLs and rows needing URL repair.
Source rows remain verbatim in catalog modules; category, group, alternate URLs,
access tiers and duplicate provenance are preserved. Parser-invalid rows remain
in `catalog/url-review.md`. Known ATS platforms found in alternate URLs also enter
the adapter backlog. Provider recognition is not reachability verification.

The discovery queue contains unresolved career pages and external boards needing
alternate-source research. Exact company/seed repeats are queued once; distinct
employer/URL pairs remain separate. Existing ATS Sources are not merged. If an
external board row has a corporate alternate, that alternate becomes the seed.
Known unsupported ATS boards enter `adapter-backlog.md` directly, saving discovery
calls when the platform has already been identified. The prepared manifest is
the authority for active modules/phases; obsolete files left after regeneration
are not loaded by the phase runner.

Default phases contain ten entries (`prepare --batch-size 1..25` changes this).
Run exactly one pending phase, or select a phase explicitly:

```powershell
.\venv\Scripts\python.exe -m scripts.discovery_phases run --no-env-proxy
.\venv\Scripts\python.exe -m scripts.discovery_phases run --phase 1 --no-env-proxy
```

Every phase uses the existing bounded HTTP-first discovery. Unresolved cases and
failed adapter checks default to **GPT-6 Luna xhigh**, reusing saved Codex
authentication. Select **GPT-6.1 Terra medium** for the next pending phase:

```powershell
.\venv\Scripts\python.exe -m scripts.discovery_phases run --agent-model gpt-6.1-terra --no-env-proxy
```

`--agent-model gpt-6-luna` selects Luna again. Without `--agent-effort`, Luna uses
`xhigh` and Terra uses `medium`; an explicit `--agent-effort` overrides this.
The selected pair is saved in phase state and agent diagnostics. Changing models
continues the existing queue without repeating completed phases. To repeat a
completed phase with another model, use `--phase N --retry`; this replaces that
phase's reports rather than creating a benchmark comparison.

Each run prints its phase, source count and selected model when it starts, then
elapsed wall time as `HH:MM:SS.s` and seconds when it exits, including failed runs.
This includes HTTP discovery, agent fallback, Preview checks and report generation.
To run ten pending phases sequentially and also see the combined time:

```powershell
$discoveryTimer = [System.Diagnostics.Stopwatch]::StartNew()
try {
    foreach ($i in 1..10) {
        .\venv\Scripts\python.exe -m scripts.discovery_phases run --agent-model gpt-6.1-terra --no-env-proxy
        if ($LASTEXITCODE -ne 0) { break }
    }
} finally {
    $discoveryTimer.Stop()
    Write-Host "Total elapsed: $($discoveryTimer.Elapsed)"
}
```

Omit `--agent-model gpt-6.1-terra` to use Luna xhigh. One default phase processes
ten sources; ten phases process up to one hundred sources.

External Kariyer.net findings may invoke agent research for alternative boards;
newly identified unsupported ATS boards are recorded without redundant research.
Each phase allows at most one agent call per queued entry (240 seconds per call),
so phase size also bounds account usage. `--no-agent` runs the classic path only;
such a run does not consume the agent-enabled progress slot. An agent-completed
phase also counts as complete in classic mode; changing to `--no-agent` cannot
replace those results without an explicit `--phase N --retry`.

The runner writes ignored local files under `data/source-discovery/results/`:

- `phase-NNN.md` and `.json`: evidence, candidate status and model diagnostics.
- `catalog-candidates.md`: supported-provider findings awaiting review; failed
  verification remains visible and is not approval to promote a URL.
- `adapter-candidates.md`: new unsupported/custom findings for future adapters
  or custom-host review. A custom host alone does not establish an ATS family.
- `phase-NNN-review.md` and `.json`: automatic triage of saved evidence,
  including catalog matches, possible URL variants, shared populations, exclusions,
  unresolved records and adapter/binding work. These are rule-based signals, not
  human approval or a fresh ownership/readability check.
- `summary.md` and `.json`: one cumulative entry point for all current phases,
  with platform worklists, action counts, unresolved/incomplete research and
  company/URL evidence deduplicated across phases. Individual observations remain
  available for provenance.

Review notes and the summary regenerate automatically after each phase and when
prepared modules refresh existing results. They require no additional HTTP or
model calls. Rebuild them from existing results at any time:

```powershell
.\venv\Scripts\python.exe -m scripts.discovery_phases review
```

The review command takes the same local lock and does not advance the phase queue.
Existing handwritten review Markdown is preserved in content-hashed
`phase-NNN-review-manual-*.md` backups before its standard path becomes generated.
Raw reports/JSON and processing state remain unchanged. Decisions to promote a
source or implement an adapter still require evidence/contract inspection; the
automatic triage is designed to locate those decisions from one summary rather
than require reading every phase report.

`state.json` records that a phase was processed, not that every company succeeded.
The next command skips that phase. Inspect unresolved entries and explicitly use
`--phase N --retry` to repeat it; reports for that phase are replaced. A lock blocks
concurrent phase dispatch. After a hard crash, inspect the PID in `.run.lock` and
remove the stale lock only after confirming that its process has stopped.
Catalog/phase hashes reject stale inputs and changed phases become pending again.
Candidate inventories only include results matching the current phase manifest.

Review ownership/evidence before adding discovered URLs to the canonical catalog,
implement missing adapters as separate work, then explicitly sync Sources. No
source activation, job ingestion, adapter creation or database write is automatic.

This command discovers candidate ATS boards from a small Markdown input. It does
not alter the canonical catalog, Source registry, Jobs or application history.
It uses the existing safe HTTP client, provider classifiers and adapter Preview
contracts; it needs no database or AI credentials.

## Run a pilot

Create `data/discovery-pilot.md` locally before running the pilot. This ignored
input is not shipped with the repository. Choose company career URLs from
`data/turkish-job-sources.md` or your own research; use an H2 section heading and
the canonical catalog row format:

```markdown
## Companies to inspect
- **Company** — `https://example.com/careers/` — open — Optional notes.
```

Replace the example with a real company URL, then run from the repository root:

```powershell
.\venv\Scripts\python.exe -m scripts.discover_sources --input data/discovery-pilot.md
```

The default output is `docs/agent-reports/discovered-job-sources.md`, an ignored
local report. Every run replaces this report atomically; use a different output
path to retain previous runs. Input and canonical catalog overwrite are rejected.

```powershell
.\venv\Scripts\python.exe -m scripts.discover_sources --input data/discovery-pilot.md --output docs/agent-reports/discovery-second.md
```

`--no-env-proxy` ignores HTTP proxy environment variables when those variables
point at an unavailable local proxy. Normal TLS validation and SSRF protection
remain enabled. Use `--no-verify` to gather links without adapter requests.

## Discovery and interpretation

The tool parses public anchors and iframe sources, follows career-related links,
and prioritizes open positions over general career/about pages. It records HTTP
redirects and the full observed link chain. It recognizes supported providers
using the same binding rules as ingestion. HRPeak root and `/jobs` links collapse
to one board. Certain known unsupported providers, including Peoplise, are reported
without pretending that they are crawlable.

The default limits per input row are three HTML pages, depth three, three candidate
boards, twenty physical HTTP attempts, eight MiB and sixty seconds. Adapter Preview
requests share the same request/byte/time budget. Each response is limited to two
MiB; requests to the same host are paced at least one second apart. `--max-pages`,
`--max-depth` and `--max-sources` accept 1–100; the input default is at most ten rows.
An input exceeding that limit is rejected rather than silently truncated.

Reports distinguish:

- `linked_candidate`: a board URL was observed, verification was disabled.
- `adapter_readable`: the existing adapter returned a Preview result. Zero jobs
  can be valid. This is not proof of company ownership, full population coverage,
  or successful detail enrichment; HTML adapters may return PARTIAL warnings.
- `verification_failed`: a board was found but the adapter could not read it.
- `unsupported_provider`: a known board platform lacks an acquisition adapter.
- No candidate: page errors, limits and browser/agent follow-up needs are listed.

The discovery path uses GET requests. Adapter verification uses existing read-only
Preview contracts, including provider-owned search POSTs where necessary. It never
submits applications or credentials. Login/application links and LinkedIn/İŞKUR
targets are excluded before each physical request, including redirect hops and
adapter Preview requests. Every physical request and redirect uses existing SSRF/DNS
validation; query strings carrying common credential keys are excluded from link
traversal. Only selected links and structured diagnostics enter the report, not
full pages, cookies or request headers.

## Review and promote

Review the observed chain to confirm that a board belongs to the employer. Add
the board URL alongside the corporate career URL in the existing canonical row,
then run the explicit catalog sync and refresh ingestion. Existing Sources are
preserved by the sync contract. This tool never deletes old URLs or deactivates
Sources because a page is unreachable.

## Agent fallback and authentication

When classic discovery has no candidate or an adapter verification fails, the
command automatically runs Codex CLI web research. Defaults are `gpt-6-luna` with
`xhigh`, at most three company fallbacks per command, and 240 seconds per agent
call. `--agent-model` and `--agent-effort` select an exact model/effort pair;
the command never silently falls
back to another model. `--agent-timeout` accepts 30–600 seconds and
`--agent-max-sources` bounds calls. `--no-agent` retains classic-only behavior.
Known unsupported-provider findings alone do not trigger research, since finding
a platform does not implement its adapter.

Codex reuses its saved CLI sign-in; check `codex login status`, or run `codex login`
if signed out. No credentials are copied into JobScope, reports or prompts. This
local CLI path does not need a separate Sign in with ChatGPT DevKit integration.
The devkit is relevant to an application-managed account connection, a separate
workflow from this local command.

To use the other benchmark configuration:

```powershell
.\venv\Scripts\python.exe -m scripts.discover_sources --agent-model gpt-6.1-terra --agent-effort medium --no-env-proxy
```

Each invocation runs ephemerally in a temporary directory outside the repository,
with a read-only sandbox, user configuration ignored and only public web research
requested. Shell, apps, computer/browser control and multi-agent features are
disabled. The model uses the built-in web tool, not a local browser. Structured
output is schema validated. Candidate URLs and evidence chains pass URL/DNS
safety checks; recognized boards pass through existing Preview verification.
`agent_candidate` remains unverified, while `agent_adapter_readable` only means
Preview returned. Neither proves company ownership. Missing CLI/auth/model access,
timeouts and invalid output remain explicit report failures.

The command never guesses tenant names, solves challenges or schedules recurring
work. JavaScript-only pages that web research cannot inspect remain unresolved.
The original HTTP pilot found MilSOFT's HRPeak board, reported Logo as unsupported
Peoplise, and reported Architecht's HTTP 403. Agent evidence is recorded separately
from the classical link chain.

## Model benchmark

Create the ignored local `data/discovery-benchmark.md` first, using the pilot row
format with exactly ten distinct companies under an H2 heading. No benchmark
input is shipped with the repository. Use `--input PATH` for a different local
file. Create any additional company set before invoking the examples below.

```powershell
.\venv\Scripts\python.exe -m scripts.benchmark_discovery --no-env-proxy
```

For the Luna high / Sol medium pair, keep the original results in place:

```powershell
.\venv\Scripts\python.exe -m scripts.benchmark_discovery --no-env-proxy --models gpt-6-luna:high gpt-6.1-sol:medium --output docs/agent-reports/discovery-benchmark-luna-high-sol-medium
```

The second, non-overlapping company set compares Luna efforts directly:

```powershell
.\venv\Scripts\python.exe -m scripts.benchmark_discovery --no-env-proxy --input data/discovery-benchmark-luna-new-companies.md --models gpt-6-luna:high gpt-6-luna:xhigh --output docs/agent-reports/discovery-benchmark-luna-new-companies
```

The default local ten-company input is `data/discovery-benchmark.md`. By default GPT-6 Luna
`xhigh` and GPT-6.1 Terra `medium` receive the same seed, prompt, tools and per-call
timeout (default 120 seconds). Agents run even when classic discovery succeeds,
so this measures the agent stage across ten paired cases, not production fallback
frequency. Each pair runs concurrently; invocation order alternates by company.
This is one sample per case, not a statistically stable performance ranking.

The ignored output directory `docs/agent-reports/discovery-benchmark/` contains
incremental `results.json` and `report.md`. The runner reads numeric usage from
Codex JSONL turn-completion events, then discards raw events. It records input,
cached input, output and total tokens, cache percentage, token share, agent wall
time and independently checked candidate statuses. Adapter validation time is
excluded from agent latency. Missing usage is null, never zero. Token percentages
are not billing or account-quota percentages; different models can have different
quota weights. Account-wide usage snapshots include other concurrent activity.
