"""Offline discovery exercises link chains, boundaries and adapter verification."""

from argparse import Namespace

import httpx
import pytest

from backend.application.job_discovery.dtos import SafeHttpResponseDTO, SourceCreateDTO
from backend.application.job_discovery.exceptions import AdapterExecutionError
from backend.infrastructure.http.safe_client import HttpSafeClient
from scripts.discover_sources import discover, public_candidate, render, run
from scripts.source_discovery_agent import AgentResult


class Pages:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append(url)
        value = self.pages[url]
        if isinstance(value, Exception):
            raise value
        if isinstance(value, SafeHttpResponseDTO):
            return value
        return SafeHttpResponseDTO(200, url, text=value)


def seed(url="https://company.example/career"):
    return SourceCreateDTO(
        name="Example", company="Example", url=url, ats_type="custom"
    )


async def test_three_page_career_chain_iframe_is_verified_without_detail():
    client = Pages(
        {
            "https://company.example/career": '<a href="https://careers.example/">Career</a>',
            "https://careers.example/": (
                '<a href="/life">Life at work</a><a href="/join-us">Join us</a>'
                '<a href="/open-positions">Open Positions</a>'
            ),
            "https://careers.example/open-positions": '<iframe src="https://acme.hrpeak.com/jobs"></iframe>',
            "https://acme.hrpeak.com/jobs": '<table id="C_G"></table>',
        }
    )
    result = await discover(seed(), client)
    assert len(result.findings) == 1
    found = result.findings[0]
    assert found.provider == "hrpeak" and found.status == "adapter_readable"
    assert found.jobs == 0
    assert len(found.chain) == 4 and len(result.visited) == 3
    assert len(client.calls) == 4
    assert "iframe" in found.evidence
    assert "acquisition_coverage_not_proven" in found.warning


async def test_supported_link_and_duplicates_need_no_extra_page_fetch():
    client = Pages(
        {
            seed().url: '<a href="https://acme.hrpeak.com/jobs">Jobs</a>' * 2,
        }
    )
    result = await discover(seed(), client, verify=False)
    assert len(result.findings) == 1 and len(client.calls) == 1
    assert result.findings[0].status == "linked_candidate"


async def test_hrpeak_root_and_jobs_collapse_to_one_board():
    client = Pages(
        {
            seed().url: (
                '<a href="https://acme.hrpeak.com/">Careers</a>'
                '<a href="https://acme.hrpeak.com/jobs">Jobs</a>'
            ),
            "https://acme.hrpeak.com/jobs": '<table id="C_G"></table>',
        }
    )
    result = await discover(seed(), client)
    assert len(result.findings) == 1
    assert result.findings[0].url == "https://acme.hrpeak.com/jobs"
    assert len(client.calls) == 2


async def test_unsupported_provider_is_recorded_without_fetching():
    url = "https://live.peoplise.com/logo/career"
    result = await discover(seed(url), Pages({}))
    assert result.findings[0].status == "unsupported_provider"
    assert result.findings[0].url == url


async def test_kariyer_root_and_password_page_are_not_employer_boards():
    profile = "https://www.kariyer.net/firma-profil/example-123"
    client = Pages(
        {
            seed().url: (
                '<a href="http://www.kariyer.net/">Kariyer</a>'
                '<a href="http://www.kariyer.net/Website/TeknikDestek/sifremiunuttum/s1.aspx">Forgot</a>'
                f'<a href="{profile}">Jobs</a>'
            )
        }
    )
    result = await discover(seed(), client, verify=False)
    assert [f.url for f in result.findings] == [profile]
    assert client.calls == [seed().url]


async def test_one_failed_branch_does_not_hide_other_board():
    client = Pages(
        {
            seed().url: '<a href="/career/broken">Careers</a><a href="/jobs">Jobs</a>',
            "https://company.example/career/broken": AdapterExecutionError("failed"),
            "https://company.example/jobs": '<a href="https://acme.hrpeak.com/jobs">Jobs</a>',
        }
    )
    result = await discover(seed(), client, verify=False)
    assert result.findings and result.issues


async def test_adapter_failure_remains_candidate_not_verified():
    client = Pages({"https://acme.hrpeak.com/jobs": "<html>Challenge</html>"})
    result = await discover(seed("https://acme.hrpeak.com/jobs"), client)
    assert result.findings[0].status == "verification_failed"
    assert result.findings[0].warning == "MALFORMED_ADAPTER_RESULT"


async def test_traversal_is_bounded_and_unresolved_is_explicit():
    client = Pages(
        {
            seed().url: '<a href="/career/next">Careers</a>',
            "https://company.example/career/next": '<a href="/career/more">Careers</a>',
        }
    )
    result = await discover(seed(), client, max_pages=2)
    assert len(client.calls) == 2
    assert not result.findings
    assert any("limit" in issue for issue in result.issues)
    assert any("browser/agent" in issue for issue in result.issues)


async def test_redirected_html_uses_final_origin_without_refetch():
    client = Pages(
        {
            seed().url: SafeHttpResponseDTO(
                200,
                "https://careers.example/home",
                text='<a href="https://acme.hrpeak.com/jobs">Open positions</a>',
            ),
        }
    )
    result = await discover(seed(), client, verify=False)
    assert len(client.calls) == 1
    assert result.findings[0].chain == (
        seed().url,
        "https://careers.example/home",
        "https://acme.hrpeak.com/jobs",
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://user:password@example.com/jobs",
        "javascript:alert(1)",
        "https://www.linkedin.com/jobs",
        "https://www.iskur.gov.tr/ilan",
        "https://example.com/login",
        "https://example.com/career?token=secret",
    ],
)
def test_sensitive_or_hands_off_links_are_excluded(url):
    assert public_candidate(url, seed().url) is None


async def test_private_target_uses_existing_ssrf_guard():
    requests = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: (
                requests.append(request) or httpx.Response(200, text="unused")
            )
        )
    ) as transport:
        result = await discover(
            seed("http://127.0.0.1/career"), HttpSafeClient(client=transport)
        )
    assert not requests and not result.findings
    assert result.issues


async def test_report_preserves_input_and_does_not_create_importable_source_rows():
    result = await discover(seed("https://live.peoplise.com/logo/career"), Pages({}))
    text = render([result], "input.md")
    assert "unsupported_provider" in text and "Chain:" in text
    assert "- **" not in text


async def test_cli_refuses_to_overwrite_input(tmp_path):
    path = tmp_path / "pilot.md"
    path.write_text("original", encoding="utf-8")
    with pytest.raises(ValueError, match="overwrite"):
        await run(Namespace(input=path, output=path))
    assert path.read_text(encoding="utf-8") == "original"


async def test_cli_automatically_uses_selected_agent_with_company_limit(
    tmp_path, monkeypatch
):
    from scripts import discover_sources as tool

    input_path = tmp_path / "pilot.md"
    output = tmp_path / "report.md"
    input_path.write_text(
        "## Companies\n- **One** — `https://one.example/career`\n"
        "- **Two** — `https://two.example/career`\n",
        encoding="utf-8",
    )
    calls = []

    async def unresolved(source, *_args, **_kwargs):
        return tool.Discovery(source.name, source.url)

    class Agent:
        def __init__(self, *, model, effort, timeout):
            self.model, self.effort = model, effort
            calls.append((model, effort, timeout))

        async def research(self, source, issues):
            calls.append(source.name)
            return AgentResult(candidates=[], unresolved_reason="No public evidence")

    monkeypatch.setattr(tool, "discover", unresolved)
    monkeypatch.setattr(tool, "CodexDiscoveryAgent", Agent)
    await tool.run(
        Namespace(
            input=input_path,
            output=output,
            max_sources=10,
            no_agent=False,
            agent_model="gpt-6.1-terra",
            agent_effort="medium",
            agent_timeout=30,
            no_env_proxy=True,
            max_pages=3,
            max_depth=3,
            no_verify=False,
            agent_max_sources=1,
        )
    )
    assert calls == [("gpt-6.1-terra", "medium", 30), "One"]
    report = output.read_text(encoding="utf-8")
    assert "limit_reached" in report and "gpt-6.1-terra (medium)" in report
    assert input_path.read_text(encoding="utf-8").startswith("## Companies")


@pytest.mark.parametrize(
    "target",
    [
        "https://www.linkedin.com/jobs",
        "https://www.iskur.gov.tr/ilan",
        "https://company.example/login",
        "https://company.example/jobs?token=secret",
    ],
)
async def test_redirect_policy_blocks_target_before_request(monkeypatch, target):
    from scripts import discover_sources as tool

    monkeypatch.setattr(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        lambda url: (True, None, None),
    )
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if len(requests) == 1:
            return httpx.Response(302, headers={"location": target})
        return httpx.Response(200, text="blocked destination")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
        client = HttpSafeClient(
            client=transport, request_url_policy=tool.discovery_url_allowed
        )
        result = await discover(seed(), client, verify=False)
    assert requests == [seed().url]
    assert result.issues and not result.findings


async def test_missing_local_input_gives_setup_guidance(tmp_path):
    with pytest.raises(ValueError, match="Create a local Markdown catalog"):
        await run(Namespace(input=tmp_path / "missing.md", output=tmp_path / "out.md"))


async def test_allowed_redirect_still_follows_career_page(monkeypatch):
    from scripts.discover_sources import discovery_url_allowed

    monkeypatch.setattr(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        lambda url: (True, None, None),
    )
    requests = []
    final = "https://careers.example/jobs"

    def handler(request):
        requests.append(str(request.url))
        if len(requests) == 1:
            return httpx.Response(302, headers={"location": final})
        return httpx.Response(200, text="No current vacancies")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
        client = HttpSafeClient(
            client=transport, request_url_policy=discovery_url_allowed
        )
        await discover(seed(), client, verify=False)
    assert requests == [seed().url, final]
