"""Deterministic discovery triage from saved results; no network or model calls."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

from backend.domain.source.normalization import normalize_source_url
from backend.infrastructure.parsers.markdown_source_parser import (
    MarkdownSourceParser,
    classify_ats_type,
)
from scripts.discover_sources import UNSUPPORTED_HOSTS, host_matches, is_board_candidate

MARKER = "<!-- jobscope:auto-review:v1 -->"
READABLE = {"adapter_readable", "agent_adapter_readable"}


def text(value):
    return (
        str(value)
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("|", "\\|")
        .replace("`", "'")
    )


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def write_review(path, lines):
    """Preserve earlier human-written review text before generating its replacement."""
    if path.exists():
        previous = path.read_text(encoding="utf-8")
        if not previous.startswith(MARKER):
            identity = hashlib.sha256(previous.encode("utf-8")).hexdigest()[:12]
            backup = path.with_name(f"{path.stem}-manual-{identity}.md")
            if not backup.exists():
                backup.write_text(previous, encoding="utf-8")
    manual = sorted(path.parent.glob(f"{path.stem}-manual-*.md"))
    if manual:
        lines += ["", "## Preserved manual notes", ""]
        lines += [f"- [{item.name}]({item.name})" for item in manual]
    temporary = path.with_suffix(".md.tmp")
    temporary.write_text(MARKER + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)


def url_shape(url):
    parsed = urlsplit(url)
    return parsed.hostname.removeprefix("www."), unquote(parsed.path).rstrip(
        "/"
    ).casefold().replace("ı", "i")


def platform_for(url, seed, catalog):
    provider = classify_ats_type(url)
    host = urlsplit(url).hostname or ""
    if provider != "custom":
        return provider, "recognized URL"
    if host.endswith(".hrpeak.com"):
        return "hrpeak", "host family only; URL binding unverified"
    for suffix in UNSUPPORTED_HOSTS:
        if host_matches(host, (suffix,)):
            return suffix, "known platform host"
    # A catalog note is only a hint, and only applies to the same career host.
    for source in catalog:
        if (
            normalize_source_url(source.url) == normalize_source_url(seed)
            and urlsplit(source.url).hostname == host
            and "successfactors" in source.metadata.get("notes", "").casefold()
        ):
            return "successfactors", "catalog hint; contract unverified"
    return "custom:" + host.removeprefix("www."), "unclassified host"


def generate_reviews(root: Path, supported_types):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    canonical = root / manifest["source"]
    catalog, _ = MarkdownSourceParser().parse_file(str(canonical))
    known = {
        normalize_source_url(url)
        for source in catalog
        for url in [source.url, *source.metadata.get("alternate_urls", [])]
    }
    result_dir = root / "results"
    phases, candidates = [], []
    for phase in manifest["phases"]:
        if state.get(str(phase["number"]), {}).get("sha256") != phase["sha256"]:
            continue
        path = result_dir / f"phase-{phase['number']:03d}.json"
        if not path.exists():
            continue
        reports = json.loads(path.read_text(encoding="utf-8"))
        phase_review = {
            "schema_version": 1,
            "phase": phase["number"],
            "sources": len(reports),
            "raw_findings": 0,
            "excluded": [],
            "duplicates": 0,
            "candidates": [],
            "unresolved": [],
            "incomplete_research": [],
        }
        for report in reports:
            if report["agent_status"] in {"failed", "limit_reached", "disabled"}:
                phase_review["incomplete_research"].append(
                    {
                        "company": report["name"],
                        "agent_status": report["agent_status"],
                        "issues": report["issues"],
                    }
                )
            unique = {}
            for finding in report["findings"]:
                phase_review["raw_findings"] += 1
                if not is_board_candidate(finding["url"]):
                    phase_review["excluded"].append(
                        {
                            "company": report["name"],
                            "url": finding["url"],
                            "reason": "not an admissible employer board URL",
                        }
                    )
                    continue
                url = normalize_source_url(finding["url"])
                if url in unique:
                    phase_review["duplicates"] += 1
                    item = unique[url]
                    if finding["evidence"] not in item["evidence"]:
                        item["evidence"].append(finding["evidence"])
                    item["observations"].append(finding)
                    item["evidence_urls"] = sorted(
                        set(item["evidence_urls"] + finding.get("evidence_urls", []))
                    )
                    if len(finding["chain"]) > len(item["chain"]):
                        item["chain"] = finding["chain"]
                    item["reported_statuses"] = sorted(
                        set(item["reported_statuses"] + [finding["status"]])
                    )
                    continue
                platform, basis = platform_for(finding["url"], report["seed"], catalog)
                item = {
                    "phase": phase["number"],
                    "company": report["name"],
                    "seed": report["seed"],
                    "url": finding["url"],
                    "normalized_url": url,
                    "provider": finding["provider"],
                    "platform": platform,
                    "platform_basis": basis,
                    "reported_statuses": [finding["status"]],
                    "already_in_catalog": url in known,
                    "same_as_seed": url == normalize_source_url(report["seed"]),
                    "possible_url_variant": (
                        url != normalize_source_url(report["seed"])
                        and url_shape(finding["url"]) == url_shape(report["seed"])
                    ),
                    "ownership_verified": False,
                    "evidence": [finding["evidence"]],
                    "evidence_urls": finding.get("evidence_urls", []),
                    "chain": finding["chain"],
                    "issues": report["issues"],
                    "observations": [finding],
                }
                unique[url] = item
            if not unique:
                phase_review["unresolved"].append(
                    {
                        "company": report["name"],
                        "agent_status": report["agent_status"],
                        "issues": report["issues"],
                    }
                )
            for item in unique.values():
                if report["agent_status"] in {"failed", "limit_reached", "disabled"}:
                    item["issues"] = [
                        *item["issues"],
                        "Agent research incomplete: " + report["agent_status"],
                    ]
                phase_review["candidates"].append(item)
                candidates.append(item)
        phases.append(phase_review)

    owners = defaultdict(set)
    for item in candidates:
        owners[item["normalized_url"]].add(item["company"])
    for item in candidates:
        item["shared_with_companies"] = sorted(
            owners[item["normalized_url"]] - {item["company"]}
        )
        actions = ["verify_ownership"]
        if item["already_in_catalog"]:
            actions.append("existing_catalog_reference")
        if item["possible_url_variant"]:
            actions.append("verify_alias_and_preserve_registry_identity")
        if item["shared_with_companies"]:
            actions.append("verify_population_and_company_filter")
        if any(
            issue.startswith("Agent research incomplete:") for issue in item["issues"]
        ):
            actions.append("retry_or_inspect_agent_research")
        if item["provider"] == "kariyer_net":
            actions.append("external_board_reference")
        elif item["provider"] in supported_types:
            actions.append(
                "preview_readable"
                if READABLE.intersection(item["reported_statuses"])
                else "preview_required"
            )
        elif item["platform"] in supported_types:
            actions.append(
                "preview_required"
                if item["platform_basis"] == "recognized URL"
                else "verify_existing_adapter_host_or_path_binding"
            )
        else:
            actions.append("investigate_platform_contract_for_adapter")
        item["actions"] = actions

    for phase in phases:
        stem = f"phase-{phase['phase']:03d}-review"
        write_json(result_dir / f"{stem}.json", phase)
        lines = [
            f"# Phase {phase['phase']:03d} — automatic triage",
            "",
            "Generated from saved results; no network/model calls. "
            "These are review signals, not human approval or verified "
            "employer ownership.",
            "",
            f"Sources: {phase['sources']}; raw findings: {phase['raw_findings']}; "
            f"reviewable company/URL records: {len(phase['candidates'])}; "
            f"excluded: {len(phase['excluded'])}; "
            f"duplicate records collapsed: {phase['duplicates']}.",
            "",
            "| Company | URL | Platform / basis | Catalog | Actions |",
            "|---|---|---|---|---|",
        ]
        for item in phase["candidates"]:
            lines.append(
                f"| {text(item['company'])} | `{text(item['url'])}` | "
                f"{text(item['platform'])}: {text(item['platform_basis'])} | "
                f"{'existing' if item['already_in_catalog'] else 'URL absent'} | "
                f"{text(', '.join(item['actions']))} |"
            )
        for item in phase["candidates"]:
            lines += [
                "",
                f"## {text(item['company'])}",
                "",
                "Evidence: " + text("; ".join(item["evidence"])),
                "Chain: " + " → ".join(f"`{text(url)}`" for url in item["chain"]),
            ]
            lines += (
                ["Shared URL with: " + text(", ".join(item["shared_with_companies"]))]
                if item["shared_with_companies"]
                else []
            )
            lines += [f"- {text(issue)}" for issue in item["issues"]]
        lines += ["", "## Unresolved and excluded", ""]
        lines += [
            f"- {text(item['company'])}: {text('; '.join(item['issues']))}"
            for item in phase["unresolved"]
        ]
        lines += [
            f"- Incomplete research: {text(item['company'])} ({item['agent_status']})"
            for item in phase["incomplete_research"]
        ]
        lines += [
            f"- Excluded {text(item['company'])}: `{text(item['url'])}` "
            f"— {item['reason']}"
            for item in phase["excluded"]
        ]
        lines += [
            "",
            f"Machine-readable details: `{stem}.json`. "
            "Raw phase reports remain unchanged.",
        ]
        write_review(result_dir / f"{stem}.md", lines)

    work = {}
    for item in candidates:
        key = (item["company"].casefold(), item["normalized_url"])
        if key not in work:
            work[key] = {
                **item,
                "phase_numbers": [item["phase"]],
                "source_seeds": [item["seed"]],
            }
        else:
            previous = work[key]
            previous["phase_numbers"] = sorted(
                set(previous["phase_numbers"] + [item["phase"]])
            )
            previous["source_seeds"] = sorted(
                set(previous["source_seeds"] + [item["seed"]])
            )
            previous["observations"] = previous["observations"] + item["observations"]
            previous["evidence"] = sorted(set(previous["evidence"] + item["evidence"]))
            previous["actions"] = sorted(set(previous["actions"] + item["actions"]))
            for field in ("reported_statuses", "evidence_urls", "issues"):
                previous[field] = sorted(set(previous[field] + item[field]))
            previous["possible_url_variant"] |= item["possible_url_variant"]
    work_items = list(work.values())
    families = defaultdict(list)
    for item in work_items:
        families[item["platform"]].append(item)
    summary = {
        "schema_version": 1,
        "prepared_phases": len(manifest["phases"]),
        "processed_phases": len(phases),
        "processed_sources": sum(p["sources"] for p in phases),
        "candidate_records": len(candidates),
        "distinct_urls": len(owners),
        "distinct_company_urls": len(work_items),
        "urls_absent_from_catalog": len(
            {
                item["normalized_url"]
                for item in candidates
                if not item["already_in_catalog"]
            }
        ),
        "unresolved": [item for phase in phases for item in phase["unresolved"]],
        "incomplete_research": [
            item for phase in phases for item in phase["incomplete_research"]
        ],
        "action_counts": dict(
            Counter(action for item in work_items for action in item["actions"])
        ),
        "catalog_matches_prepared": hashlib.sha256(canonical.read_bytes()).hexdigest()
        == manifest["source_sha256"],
        "platforms": [
            {
                "platform": platform,
                "company_count": len({item["company"] for item in items}),
                "phases": sorted(
                    {phase for item in items for phase in item["phase_numbers"]}
                ),
                "urls": sorted({item["url"] for item in items}),
            }
            for platform, items in sorted(families.items())
        ],
        "candidates": work_items,
    }
    write_json(result_dir / "summary.json", summary)
    lines = [
        "# Discovery — cumulative automatic triage",
        "",
        "One entry point for all processed phases. No URL is automatically "
        "approved, synced or promoted to the catalog. "
        "Platform hints and Preview success are not ownership verification.",
        "",
        f"Phases: {len(phases)}/{len(manifest['phases'])}; "
        f"sources: {summary['processed_sources']}; "
        f"candidate records: {len(candidates)}; distinct URLs: {len(owners)}; "
        f"URLs absent from catalog: {summary['urls_absent_from_catalog']}; "
        f"unresolved records: {len(summary['unresolved'])}.",
        "",
        "## Platform worklist",
        "",
        "| Platform / host hint | Companies | Phases |",
        "|---|---:|---|",
    ]
    lines += [
        f"| {text(item['platform'])} | {item['company_count']} | "
        f"{', '.join(str(n) for n in item['phases'])} |"
        for item in summary["platforms"]
    ]
    lines += ["", "## Action counts", ""]
    lines += [
        f"- {action}: {count}"
        for action, count in sorted(summary["action_counts"].items())
    ]
    lines += ["", "## Unresolved", ""]
    lines += [
        f"- {text(item['company'])}: {text('; '.join(item['issues']))}"
        for item in summary["unresolved"]
    ]
    lines += ["", "## Incomplete research", ""]
    lines += [
        f"- {text(item['company'])}: {item['agent_status']}"
        for item in summary["incomplete_research"]
    ]
    lines += ["", "## Phase details", ""]
    lines += [
        f"- [Phase {phase['phase']:03d}](phase-{phase['phase']:03d}-review.md)"
        for phase in phases
    ]
    lines += ["", "Full machine-readable worklist and evidence: `summary.json`."]
    write_review(result_dir / "summary.md", lines)
    return summary
