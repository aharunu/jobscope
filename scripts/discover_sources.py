"""Bounded, read-only career-board discovery from a small Markdown catalog."""

import argparse
import asyncio
import re
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urldefrag, urljoin, urlsplit

import httpx

from backend.application.job_discovery.budget import (
    AcquisitionBudget,
    acquisition_scope,
)
from backend.application.job_discovery.detail_plan import DetailPlan, detail_scope
from backend.application.job_discovery.dtos import RuntimeSourceDTO
from backend.application.job_discovery.exceptions import CrawlerError
from backend.domain.source.entities import Source
from backend.domain.source.normalization import normalize_source_url
from backend.infrastructure.ats.factory import create_adapter_registry
from backend.infrastructure.ats.source_binding import safe_url
from backend.infrastructure.http.safe_client import HttpSafeClient
from backend.infrastructure.http.ssrf import validate_target_url_safety
from backend.infrastructure.parsers.markdown_source_parser import (
    MarkdownSourceParser,
    classify_ats_type,
)
from scripts.source_discovery_agent import AgentFailure, CodexDiscoveryAgent

CAREER = re.compile(
    r"career|careers|kariyer|join[\s_-]*us|open[\s_-]*positions|"
    r"job|vacanc|açık\s*pozisyon|acik[\s_-]*pozisyon|iş\s*ilan|insan.kaynak",
    re.I,
)
BLOCKED_ACTION = re.compile(
    r"/(?:login|logout|register|candidate|application|apply|delete|unsubscribe)(?:/|$)",
    re.I,
)
UNSUPPORTED_HOSTS = (
    "peoplise.com",
    "talentics.app",
    "peoplebox.biz",
    "onenewone.com",
    "successfactors.eu",
    "successfactors.com",
    "applytojob.com",
    "zohorecruit.com",
)
HANDS_OFF_HOSTS = ("linkedin.com", "iskur.gov.tr")
SECRET_KEYS = {"token", "access_token", "password", "key", "api_key", "signature"}


def host_matches(host, domains):
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def public_candidate(value, base):
    """Normalize links without credentials/fragments; DNS safety stays in HTTP."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        url = urldefrag(urljoin(base, value.strip()))[0]
        parsed = safe_url(url)
        if (
            host_matches(parsed.hostname or "", HANDS_OFF_HOSTS)
            or BLOCKED_ACTION.search(parsed.path)
            or any(k.lower() in SECRET_KEYS for k, _ in parse_qsl(parsed.query))
        ):
            return None
        return url
    except (ValueError, CrawlerError):
        return None


def discovery_url_allowed(url):
    return public_candidate(url, url) is not None


class CareerLinks(HTMLParser):
    """Read public anchors and iframe sources, without executing page scripts."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.anchor = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.anchor = [attrs.get("href"), attrs.get("title") or ""]
        elif tag == "iframe":
            self.links.append((attrs.get("src"), "iframe", "embedded board"))

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            self.links.append((*self.anchor[:1], "anchor", self.anchor[1].strip()))
            self.anchor = None

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor[1] += " " + data


@dataclass
class Finding:
    url: str
    provider: str
    chain: tuple[str, ...]
    evidence: str
    status: str = "linked_candidate"
    jobs: int | None = None
    warning: str = ""
    origin: str = "classical"
    evidence_urls: tuple[str, ...] = ()


@dataclass
class Discovery:
    name: str
    seed: str
    findings: list[Finding] = field(default_factory=list)
    visited: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    agent_status: str = "not_needed"
    agent_model: str = ""
    agent_effort: str = ""
    agent_metrics: dict = field(default_factory=dict)


def is_board_candidate(url):
    """Kariyer.net candidates must identify an employer, not account/site routes."""
    if not public_candidate(url, url):
        return False
    if classify_ats_type(url) != "kariyer_net":
        return True
    return re.fullmatch(r"/firma-profil/[^/]+/?", urlsplit(url).path) is not None


async def discover(source, client, *, max_pages=3, max_depth=3, verify=True):
    """Follow a bounded career link graph; never sync Sources or persist Jobs."""
    report = Discovery(source.name, source.url)
    registry = create_adapter_registry(client)
    seeds = [source.url, *source.metadata.get("alternate_urls", [])]
    queue = deque((url, (url,), "catalog URL") for url in seeds)
    seen, found = set(), set()
    while queue and len(found) < 3:
        url, chain, evidence = queue.popleft()
        url = public_candidate(url, url)
        if not url or url in seen:
            continue
        seen.add(url)
        provider = classify_ats_type(url)
        if provider == "kariyer_net" and not is_board_candidate(url):
            continue
        host = urlsplit(url).hostname or ""
        supported = registry.is_supported(provider)
        if provider == "hrpeak":
            # Tenant root and /jobs identify the same population.
            canonical = f"https://{host}/jobs"
            if canonical in found:
                continue
            if url != canonical:
                chain = (*chain, canonical)
            url = canonical
        if (
            supported
            or provider == "kariyer_net"
            or host_matches(host, UNSUPPORTED_HOSTS)
        ):
            found.add(url)
            finding = Finding(url, provider, chain, evidence)
            if not supported:
                finding.status = "unsupported_provider"
                finding.provider = provider if provider != "custom" else host
            elif verify:
                try:
                    runtime = RuntimeSourceDTO.from_domain(
                        Source(
                            name=source.name,
                            company=source.company,
                            url=url,
                            ats_type=provider,
                            country=source.country,
                        )
                    )
                    with detail_scope(DetailPlan(preview=True)):
                        result = await registry.get_adapter(provider).crawl(runtime)
                    finding.status = "adapter_readable"
                    finding.jobs = len(result.jobs)
                    finding.warning = ", ".join(result.warnings)
                except CrawlerError as exc:
                    finding.status = "verification_failed"
                    finding.warning = exc.code
            report.findings.append(finding)
            continue
        if len(report.visited) >= max_pages:
            if "Page limit reached; more links may exist." not in report.issues:
                report.issues.append("Page limit reached; more links may exist.")
            continue
        report.visited.append(url)
        try:
            response = await client.get(url)
            if response.status_code != 200:
                report.issues.append(f"HTTP {response.status_code}: {url}")
                continue
            final = public_candidate(response.url, url)
            if not final:
                report.issues.append(f"Redirect target requires review: {url}")
                continue
            if final != url:
                chain = (*chain, final)
                final_provider = classify_ats_type(final)
                if (
                    registry.is_supported(final_provider)
                    or final_provider == "kariyer_net"
                    or host_matches(urlsplit(final).hostname or "", UNSUPPORTED_HOSTS)
                ):
                    queue.appendleft((final, chain, "HTTP redirect"))
                    continue
                # The safe client already fetched the redirect target.
                url = final
                seen.add(final)
            content_type = response.headers.get("content-type", "text/html")
            if "html" not in content_type:
                report.issues.append(f"Non-HTML page: {url}")
                continue
            ranked = []
            for href, kind, label in CareerLinks(response.text).links:
                target = public_candidate(href, final)
                if not target or target in seen:
                    continue
                ats = classify_ats_type(target)
                known = registry.is_supported(ats) or ats == "kariyer_net"
                unsupported = host_matches(
                    urlsplit(target).hostname or "", UNSUPPORTED_HOSTS
                )
                if not (
                    known
                    or unsupported
                    or kind == "iframe"
                    or CAREER.search(target + " " + label)
                ):
                    continue
                if len(chain) >= max_depth and not (known or unsupported):
                    continue
                hint = target + " " + label
                priority = (
                    0
                    if known
                    else 1
                    if unsupported or kind == "iframe"
                    else 2
                    if re.search(r"open.*position|jobs|vacanc|açık", hint, re.I)
                    else 3
                    if re.search(r"join", hint, re.I)
                    else 4
                )
                ranked.append((priority, target, kind, label))
            for _, target, kind, label in sorted(ranked, key=lambda item: item[0])[:20]:
                queue.append((target, (*chain, target), f"{kind}: {label[:120]}"))
        except CrawlerError as exc:
            report.issues.append(f"{exc.code}: {url}")
    if queue:
        report.issues.append(
            "Traversal or candidate limit reached; more links may exist."
        )
    if not report.findings:
        report.issues.append(
            "Needs browser/agent review: no supported board established."
        )
    return report


def needs_agent(report, *, research_unsupported=False):
    return not report.findings or any(
        finding.status == "verification_failed"
        or research_unsupported
        and finding.status == "unsupported_provider"
        for finding in report.findings
    )


async def agent_fallback(source, report, client, agent, *, verify=True):
    """Agent claims remain candidates; the existing HTTP adapter verifies reads."""
    report.agent_model = getattr(agent, "model", "")
    report.agent_effort = getattr(agent, "effort", "")
    try:
        result = await agent.research(source, report.issues)
    except AgentFailure as exc:
        report.agent_status = "failed"
        report.issues.append(str(exc))
        return report
    report.agent_status = "unresolved"
    report.agent_metrics = result._metrics
    if result.unresolved_reason:
        report.issues.append("Agent: " + result.unresolved_reason)
    for candidate in result.candidates:
        if not is_board_candidate(candidate.board_url):
            report.issues.append("Agent candidate rejected: not an employer board URL.")
            continue
        urls = [candidate.board_url, *candidate.chain, *candidate.evidence_urls]
        if not all(public_candidate(url, url) for url in urls):
            report.issues.append("Agent candidate rejected: unsafe or sensitive URL.")
            continue
        if normalize_source_url(candidate.chain[0]) != normalize_source_url(
            source.url
        ) or normalize_source_url(candidate.chain[-1]) != normalize_source_url(
            candidate.board_url
        ):
            report.issues.append(
                "Agent candidate rejected: inconsistent evidence chain."
            )
            continue
        targets_safe = True
        for url in set(urls):
            safe, _, _ = await asyncio.to_thread(validate_target_url_safety, url)
            if not safe:
                targets_safe = False
                break
        if not targets_safe:
            report.issues.append(
                "Agent candidate rejected: target safety/DNS check failed."
            )
            continue
        provider = classify_ats_type(candidate.board_url)
        finding = Finding(
            candidate.board_url,
            provider,
            tuple(candidate.chain),
            candidate.explanation,
            status="agent_candidate",
            origin="agent",
            evidence_urls=tuple(candidate.evidence_urls),
        )
        if create_adapter_registry(client).is_supported(provider) and verify:
            try:
                async with asyncio.timeout(60):
                    with acquisition_scope(
                        AcquisitionBudget(
                            max_requests=20,
                            max_bytes=8 * 1024 * 1024,
                            max_seconds=60,
                        )
                    ):
                        checked = await discover(
                            replace(source, url=candidate.board_url, metadata={}),
                            client,
                            max_pages=1,
                            verify=True,
                        )
                if checked.findings:
                    validation = checked.findings[0]
                    finding.status = (
                        "agent_adapter_readable"
                        if validation.status == "adapter_readable"
                        else "verification_failed"
                    )
                    finding.url = validation.url
                    finding.jobs, finding.warning = validation.jobs, validation.warning
            except TimeoutError:
                finding.status = "verification_failed"
                finding.warning = "Agent candidate Preview timed out."
        elif provider == "kariyer_net" or host_matches(
            urlsplit(candidate.board_url).hostname or "",
            UNSUPPORTED_HOSTS,
        ):
            finding.status = "unsupported_provider"
        # Keep a new evidence chain even when the URL repeats a failed classic read.
        report.findings.append(finding)
        report.agent_status = "completed"
    if report.agent_status == "completed":
        report.issues = [
            issue
            for issue in report.issues
            if not issue.startswith("Needs browser/agent review:")
        ]
    return report


def md(value):
    return str(value).replace("\n", " ").replace("\r", " ").replace("`", "'")


def render(reports, input_path):
    lines = [
        "# Career-board discovery report",
        "",
        f"Input: `{md(input_path)}`",
        f"Checked: {datetime.now(UTC).isoformat()}",
        "",
        "Read-only candidates. No catalog, Source or Job records were changed.",
        "adapter_readable means a Preview returned; it does not prove ownership,",
        "full board coverage or successful detail enrichment. Review before import.",
        "",
    ]
    for report in reports:
        lines += [f"## {md(report.name)}", "", f"Seed: `{md(report.seed)}`", ""]
        lines += [f"Agent fallback: {md(report.agent_status)}", ""]
        if report.agent_model:
            lines += [
                f"Agent model: {md(report.agent_model)} ({md(report.agent_effort)})",
                "Agent metrics: " + md(report.agent_metrics),
                "",
            ]
        for finding in report.findings:
            jobs = finding.jobs if finding.jobs is not None else "not checked"
            lines += [
                f"### {md(finding.provider)} — {finding.status}",
                "",
                f"Board: `{md(finding.url)}`",
                f"Evidence: {md(finding.evidence)}",
                f"Origin: {finding.origin}",
                "Evidence URLs: "
                + ", ".join(f"`{md(url)}`" for url in finding.evidence_urls),
                "Chain: " + " → ".join(f"`{md(url)}`" for url in finding.chain),
                f"Preview jobs: {jobs}",
                f"Warnings: {md(finding.warning) or 'none'}",
                "",
            ]
        lines += [f"Pages requested: {len(report.visited)}", ""]
        lines += [f"- {md(issue)}" for issue in report.issues]
        lines.append("")
    return "\n".join(lines)


async def run(args):
    source_path, output = args.input.resolve(), args.output.resolve()
    canonical = Path("data/turkish-job-sources.md").resolve()
    if output in {source_path, canonical}:
        raise ValueError("Output must not overwrite the input or canonical catalog.")
    if not source_path.is_file():
        raise ValueError(
            "Discovery input is missing. Create a local Markdown catalog with a "
            "## Companies heading and - **Company** rows, then pass --input PATH. "
            "See docs/development/source-discovery.md."
        )
    sources, warnings = MarkdownSourceParser().parse_file(str(source_path))
    if not sources:
        raise ValueError(
            "Input has no source rows; use ## heading and - **Company** rows."
        )
    if len(sources) > args.max_sources:
        raise ValueError(
            "Input exceeds --max-sources; use a smaller pilot or raise the limit."
        )
    reports = []
    agent = (
        None
        if args.no_agent
        else CodexDiscoveryAgent(
            model=args.agent_model,
            effort=args.agent_effort,
            timeout=args.agent_timeout,
        )
    )
    agent_calls = 0
    async with (
        httpx.AsyncClient(
            trust_env=not args.no_env_proxy, follow_redirects=False
        ) as transport,
        HttpSafeClient(
            request_url_policy=discovery_url_allowed,
            client=transport,
            max_response_bytes=2 * 1024 * 1024,
            max_retries=0,
            min_request_interval_seconds=1.0,
        ) as client,
    ):
        for source in sources:
            with acquisition_scope(
                AcquisitionBudget(
                    max_requests=20,
                    max_bytes=8 * 1024 * 1024,
                    max_seconds=60,
                )
            ):
                try:
                    async with asyncio.timeout(60):
                        report = await discover(
                            source,
                            client,
                            max_pages=args.max_pages,
                            max_depth=args.max_depth,
                            verify=not args.no_verify,
                        )
                except TimeoutError:
                    report = Discovery(
                        source.name,
                        source.url,
                        issues=["Company timeout; needs review."],
                    )
            research_unsupported = getattr(args, "research_unsupported", False)
            if getattr(args, "research_external_only", False):
                research_unsupported = any(
                    finding.provider == "kariyer_net" for finding in report.findings
                )
            if needs_agent(report, research_unsupported=research_unsupported):
                if agent is None:
                    report.agent_status = "disabled"
                elif agent_calls >= args.agent_max_sources:
                    report.agent_status = "limit_reached"
                    report.issues.append("Agent company limit reached.")
                else:
                    agent_calls += 1
                    print(
                        f"{source.name}: agent fallback "
                        f"({agent.model}, {agent.effort})",
                        flush=True,
                    )
                    report = await agent_fallback(
                        source,
                        report,
                        client,
                        agent,
                        verify=not args.no_verify,
                    )
            reports.append(report)
            print(f"{source.name}: {len(report.findings)} candidates", flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(render(reports, args.input), encoding="utf-8")
    temporary.replace(output)
    print(f"Report: {output}; input warnings: {len(warnings)}")
    return reports


def bounded_int(value):
    number = int(value)
    if not 1 <= number <= 100:
        raise argparse.ArgumentTypeError("Use an integer between 1 and 100.")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/discovery-pilot.md"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/agent-reports/discovered-job-sources.md"),
    )
    parser.add_argument("--max-sources", type=bounded_int, default=10)
    parser.add_argument("--max-pages", type=bounded_int, default=3)
    parser.add_argument("--max-depth", type=bounded_int, default=3)
    parser.add_argument(
        "--no-agent", action="store_true", help="Disable Codex fallback."
    )
    parser.add_argument("--agent-model", default="gpt-6-luna")
    parser.add_argument(
        "--research-unsupported",
        action="store_true",
        help="Research alternate boards when an unsupported board was found.",
    )
    parser.add_argument(
        "--agent-effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        default="xhigh",
    )
    parser.add_argument("--agent-max-sources", type=bounded_int, default=3)
    parser.add_argument(
        "--agent-timeout",
        type=int,
        choices=range(30, 601),
        default=240,
        metavar="30..600",
    )
    parser.add_argument(
        "--no-verify", action="store_true", help="Skip adapter Preview checks."
    )
    parser.add_argument(
        "--no-env-proxy",
        action="store_true",
        help="Ignore system HTTP proxy environment variables.",
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
