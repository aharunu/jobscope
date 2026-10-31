"""Prepare modular source inputs and run one resumable discovery phase at a time."""

import argparse
import asyncio
import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from backend.domain.source.normalization import normalize_source_url
from backend.infrastructure.ats.factory import create_adapter_registry
from backend.infrastructure.parsers.markdown_source_parser import (
    EXCLUDED_SECTION_PREFIXES,
    MarkdownSourceParser,
    classify_ats_type,
)
from scripts.discover_sources import (
    HANDS_OFF_HOSTS,
    UNSUPPORTED_HOSTS,
    host_matches,
    is_board_candidate,
    public_candidate,
)
from scripts.discover_sources import (
    run as run_discovery,
)
from scripts.discovery_reviews import generate_reviews

DEFAULT_ROOT = Path("data/source-discovery")
CANONICAL = Path("data/turkish-job-sources.md")


class NoNetwork:
    async def get(self, *args, **kwargs):
        raise RuntimeError("Catalog preparation performs no network requests.")

    post_json = get


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def records(path):
    parser = MarkdownSourceParser()
    category, group, enabled = "", "", False
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if line.startswith("## "):
            category, group = line[3:].strip(), ""
            enabled = not any(
                category.lower().startswith(p) for p in EXCLUDED_SECTION_PREFIXES
            )
        elif line.startswith("### "):
            group = line[4:].strip()
        elif enabled and line.startswith("- **"):
            context = f"## {category}\n" + (f"### {group}\n" if group else "")
            sources, warnings = parser.parse_content(context + raw)
            yield {
                "raw": raw,
                "category": category,
                "group": group,
                "line": number,
                "source": sources[0] if sources else None,
                "warnings": warnings,
            }


def catalog_module(title, entries):
    lines = [
        f"# {title}",
        "",
        "Derived from data/turkish-job-sources.md; "
        "edit the canonical catalog and prepare again.",
        "",
    ]
    context = None
    for entry in entries:
        current = entry["category"], entry["group"]
        if context != current:
            lines += [f"## {current[0]}"]
            if current[1]:
                lines += [f"### {current[1]}"]
            context = current
        lines += [entry["raw"], ""]
    return "\n".join(lines)


def prepare(args):
    source, root = args.source.resolve(), args.root.resolve()
    if (root / ".run.lock").exists():
        raise ValueError("A phase is running; prepare after it finishes.")
    if not 1 <= args.batch_size <= 25:
        raise ValueError("Batch size must be between 1 and 25.")
    if root == source or source.is_relative_to(root):
        raise ValueError(
            "Module output must not contain or overwrite the source catalog."
        )
    supported = set(create_adapter_registry(NoNetwork()).list_supported_types())
    modules, queue, platforms = {}, [], {}
    seen = set()
    invalid = []
    for entry in records(source):
        dto = entry["source"]
        if dto is None:
            invalid.append(entry)
            continue
        urls = [dto.url, *dto.metadata.get("alternate_urls", [])]
        allowed = [url for url in urls if public_candidate(url, url)]
        unknown_platform = next(
            (
                domain
                for domain in UNSUPPORTED_HOSTS
                if any(
                    host_matches(urlsplit(url).hostname or "", (domain,))
                    for url in allowed
                )
            ),
            None,
        )
        seed = None
        if dto.ats_type in supported:
            key = f"catalog/supported/{dto.ats_type}.md"
        elif unknown_platform:
            key = f"catalog/unsupported/{unknown_platform}.md"
            platforms.setdefault(unknown_platform, []).append(entry)
        elif not allowed:
            key = "catalog/hands-off-or-unsafe.md"
        elif dto.ats_type == "kariyer_net":
            key = "catalog/external-boards.md"
            seed = next(
                (url for url in allowed if classify_ats_type(url) == "custom"), dto.url
            )
        else:
            key = "catalog/needs-discovery.md"
            seed = allowed[0]
        modules.setdefault(key, []).append(entry)
        if seed and not host_matches(urlsplit(seed).hostname or "", HANDS_OFF_HOSTS):
            identity = ((dto.company or dto.name).casefold(), seed)
            if identity not in seen:
                seen.add(identity)
                queue.append(
                    {
                        "name": dto.name,
                        "company": dto.company,
                        "url": seed,
                        "catalog_line": entry["line"],
                        "module": key,
                        "access_tier": dto.metadata["access_tier"],
                    }
                )
    files = {}
    for name, entries in modules.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(catalog_module(name, entries), encoding="utf-8")
        files[name] = {"rows": len(entries), "sha256": digest(path)}
    review = root / "catalog/url-review.md"
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text(
        "# Rows requiring URL review\n\n"
        + "\n\n".join(
            f"Line {e['line']}: {e['raw']}\nWarnings: {'; '.join(e['warnings'])}"
            for e in invalid
        ),
        encoding="utf-8",
    )
    phases = []
    for offset in range(0, len(queue), args.batch_size):
        number = len(phases) + 1
        items = queue[offset : offset + args.batch_size]
        relative = f"phases/phase-{number:03d}.md"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = [
            f"# Discovery phase {number:03d}",
            "",
            "Generated input; source rows remain in the canonical catalog.",
            "",
            "## Companies",
            "",
        ]
        for item in items:
            text += [
                f"- **{item['name']}** — `{item['url']}` — "
                f"{item['access_tier']} — Original catalog line "
                f"{item['catalog_line']}; discovery only."
            ]
        path.write_text("\n".join(text) + "\n", encoding="utf-8")
        phases.append(
            {
                "number": number,
                "input": relative,
                "sha256": digest(path),
                "sources": items,
            }
        )
    manifest = {
        "version": 1,
        "source": Path(os.path.relpath(source, root)).as_posix(),
        "source_sha256": digest(source),
        "batch_size": args.batch_size,
        "modules": files,
        "phases": phases,
        "source_rows": sum(v["rows"] for v in files.values()),
        "url_review_rows": len(invalid),
        "queued_sources": len(queue),
    }
    atomic_json(root / "manifest.json", manifest)
    backlog = [
        "# Known platforms awaiting adapters",
        "",
        "These platforms were observed in catalog URLs. "
        "Recognition does not prove reachability or ownership. "
        "No adapter is added automatically.",
        "",
        "| Platform | Catalog rows | Module |",
        "|---|---:|---|",
    ]
    for platform, entries in sorted(platforms.items()):
        backlog += [
            f"| {platform} | {len(entries)} | "
            f"[Sources](catalog/unsupported/{platform}.md) |"
        ]
    (root / "adapter-backlog.md").write_text(
        "\n".join(backlog) + "\n", encoding="utf-8"
    )
    index = [
        "# Modular source discovery",
        "",
        "Canonical source: `data/turkish-job-sources.md`. "
        "These modules are derived working inputs, "
        "not a second editable source of truth.",
        "",
        f"Parsed source rows: {manifest['source_rows']}; "
        f"URL review rows: {len(invalid)}; "
        f"unique queued company/URL pairs: {len(queue)}; phases: {len(phases)}.",
        "",
        "| Module | Rows |",
        "|---|---:|",
    ]
    index += [
        f"| [{name}]({name}) | {info['rows']} |" for name, info in sorted(files.items())
    ]
    index += ["", "[Known adapter backlog](adapter-backlog.md)", "", "## Phases", ""]
    index += [
        f"- [{phase['input']}]({phase['input']}) — {len(phase['sources'])} sources"
        for phase in phases
    ]
    (root / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    if (root / "state.json").exists() and (root / "results").is_dir():
        inventories(root)
    print(
        f"Prepared {manifest['source_rows']} rows, "
        f"{len(queue)} queued sources, {len(phases)} phases."
    )


def inventories(root):
    supported, pending = [], []
    unique = {}
    registry = create_adapter_registry(NoNetwork())
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    for phase in manifest["phases"]:
        if state.get(str(phase["number"]), {}).get("sha256") != phase["sha256"]:
            continue
        path = root / "results" / f"phase-{phase['number']:03d}.json"
        if not path.exists():
            continue
        for report in json.loads(path.read_text(encoding="utf-8")):
            for finding in report["findings"]:
                if not is_board_candidate(finding["url"]):
                    continue
                item = (report["name"], finding, path.stem)
                key = (report["name"].casefold(), normalize_source_url(finding["url"]))
                previous = unique.get(key)
                if previous is None or len(finding["evidence"]) > len(
                    previous[1]["evidence"]
                ):
                    unique[key] = item
    for item in unique.values():
        (supported if registry.is_supported(item[1]["provider"]) else pending).append(
            item
        )
    for name, rows in (
        ("catalog-candidates", supported),
        ("adapter-candidates", pending),
    ):
        lines = [
            f"# {name}",
            "",
            "Review candidates only; no automatic catalog promotion, "
            "board ownership approval or adapter implementation.",
            "",
        ]
        for company, finding, phase in rows:
            lines += [
                f"## {company}",
                "",
                f"URL: `{finding['url']}`",
                f"Provider: {finding['provider']}; status: {finding['status']}; "
                f"phase: {phase}",
                f"Evidence: {finding['evidence']}",
                "Chain: " + " → ".join(finding["chain"]),
                "",
            ]
        (root / "results" / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")
    generate_reviews(root, set(registry.list_supported_types()))


async def execute(args):
    lock = args.root.resolve() / ".run.lock"
    try:
        with lock.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
    except FileExistsError as exc:
        raise ValueError("Another phase is running; inspect .run.lock.") from exc
    started = time.perf_counter()
    try:
        if getattr(args, "command", "run") == "review":
            inventories(args.root.resolve())
            print(
                "Review notes and summary refreshed from saved results; "
                "no discovery calls."
            )
        else:
            await _execute(args)
    finally:
        lock.unlink(missing_ok=True)
        elapsed = time.perf_counter() - started
        minutes, seconds = divmod(elapsed, 60)
        hours, minutes = divmod(int(minutes), 60)
        print(
            f"Elapsed ({getattr(args, 'command', 'run')}): "
            f"{hours:02d}:{minutes:02d}:{seconds:04.1f} ({elapsed:.1f} seconds)."
        )


async def _execute(args):
    agent_model = getattr(args, "agent_model", "gpt-6-luna")
    agent_effort = getattr(args, "agent_effort", None) or (
        "medium" if agent_model == "gpt-6.1-terra" else "xhigh"
    )
    root = args.root.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if digest(root / manifest["source"]) != manifest["source_sha256"]:
        raise ValueError("Canonical catalog changed; prepare modules again first.")
    state_path = root / "state.json"
    state = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.exists()
        else {}
    )
    phases = manifest["phases"]

    def processed(phase):
        previous = state.get(str(phase["number"]), {})
        return previous.get("sha256") == phase["sha256"] and (
            previous.get("agent_enabled") is True or args.no_agent
        )

    if args.phase is not None:
        phase = next((p for p in phases if p["number"] == args.phase), None)
        if phase is None:
            raise ValueError("Unknown phase number.")
    else:
        phase = next(
            (p for p in phases if not processed(p)),
            None,
        )
        if phase is None:
            print("All prepared phases have been processed.")
            return
    if processed(phase) and not args.retry:
        raise ValueError("Phase already processed; use --retry for an explicit repeat.")
    input_path = root / phase["input"]
    if (
        not input_path.resolve().is_relative_to(root)
        or digest(input_path) != phase["sha256"]
    ):
        raise ValueError(
            "Phase input changed or escaped the module root; prepare again."
        )
    result_dir = root / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    stem = f"phase-{phase['number']:03d}"
    print(
        f"Starting {stem}: {len(phase['sources'])} sources; "
        f"agent: {'disabled' if args.no_agent else agent_model + ' ' + agent_effort}.",
        flush=True,
    )
    reports = await run_discovery(
        argparse.Namespace(
            input=input_path,
            output=result_dir / f"{stem}.md",
            max_sources=manifest["batch_size"],
            no_agent=args.no_agent,
            agent_model=agent_model,
            agent_effort=agent_effort,
            agent_timeout=240,
            agent_max_sources=manifest["batch_size"],
            max_pages=3,
            max_depth=3,
            no_verify=False,
            no_env_proxy=args.no_env_proxy,
            research_unsupported=False,
            research_external_only=True,
        )
    )
    atomic_json(result_dir / f"{stem}.json", [asdict(report) for report in reports])
    state[str(phase["number"])] = {
        "sha256": phase["sha256"],
        "model": agent_model,
        "effort": agent_effort,
        "agent_enabled": not args.no_agent,
        "status": "processed_review_results",
        "report": f"results/{stem}.md",
    }
    atomic_json(state_path, state)
    inventories(root)
    print(f"Processed phase {phase['number']}; review {result_dir / (stem + '.md')}.")


def status(args):
    root = args.root.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    path = root / "state.json"
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    done = [
        p
        for p in manifest["phases"]
        if (
            state.get(str(p["number"]), {}).get("sha256") == p["sha256"]
            and state.get(str(p["number"]), {}).get("agent_enabled") is True
        )
    ]
    pending = [p for p in manifest["phases"] if p not in done]
    print(
        f"Phases: {len(manifest['phases'])}; processed with agent: {len(done)}; "
        f"pending: {len(pending)}."
    )
    if pending:
        print(f"Next: phase-{pending[0]['number']:03d}")
    if digest(root / manifest["source"]) != manifest["source_sha256"]:
        print("Catalog changed; prepare again before running a phase.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser(
        "prepare", help="Split catalog locally, without network/AI calls."
    )
    prep.add_argument("--source", type=Path, default=CANONICAL)
    prep.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    prep.add_argument("--batch-size", type=int, choices=range(1, 26), default=10)
    start = sub.add_parser(
        "run", help="Run one phase; default selects the next unprocessed phase."
    )
    start.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    start.add_argument("--phase", type=int)
    start.add_argument("--retry", action="store_true")
    start.add_argument("--no-agent", action="store_true")
    start.add_argument(
        "--agent-model",
        choices=["gpt-6-luna", "gpt-6.1-terra"],
        default="gpt-6-luna",
        help="Fallback model (default: gpt-6-luna).",
    )
    start.add_argument(
        "--agent-effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="Defaults to xhigh for Luna, medium for Terra.",
    )
    start.add_argument("--no-env-proxy", action="store_true")
    overview = sub.add_parser(
        "status", help="Show local phase progress without network calls."
    )
    overview.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    refresh = sub.add_parser(
        "review", help="Regenerate notes/summary from saved JSON; no discovery calls."
    )
    refresh.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args)
    elif args.command == "status":
        status(args)
    else:
        asyncio.run(execute(args))


if __name__ == "__main__":
    main()
