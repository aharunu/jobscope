"""Agent subprocess isolation and untrusted candidate handling, without live AI."""

import asyncio
from pathlib import Path

import pytest

from scripts import source_discovery_agent as runner
from scripts.discover_sources import Discovery, Finding, agent_fallback, needs_agent
from tests.test_discover_sources import Pages, seed


def result(url="https://acme.hrpeak.com/jobs", **overrides):
    item = {
        "board_url": url,
        "chain": [seed().url, url],
        "evidence_urls": [url],
        "explanation": "Official employer career board found through web research.",
        **overrides,
    }
    return runner.AgentResult(
        candidates=[runner.AgentCandidate(**item)], unresolved_reason=""
    )


class FakeAgent:
    async def research(self, source, issues):
        return result()


@pytest.fixture(autouse=True)
def no_real_dns(monkeypatch):
    monkeypatch.setattr(
        "scripts.discover_sources.validate_target_url_safety",
        lambda url: (True, None, None),
    )


async def test_agent_candidate_goes_through_existing_preview():
    report = Discovery(seed().name, seed().url)
    client = Pages({"https://acme.hrpeak.com/jobs": '<table id="C_G"></table>'})
    await agent_fallback(seed(), report, client, FakeAgent())
    assert report.agent_status == "completed"
    finding = report.findings[0]
    assert finding.origin == "agent" and finding.status == "agent_adapter_readable"
    assert finding.jobs == 0 and finding.evidence_urls
    assert len(client.calls) == 1


async def test_agent_failure_keeps_classic_report():
    class Failed:
        async def research(self, *args):
            raise runner.AgentFailure("Codex CLI missing")

    report = Discovery(seed().name, seed().url, issues=["HTTP 403"])
    await agent_fallback(seed(), report, Pages({}), Failed())
    assert report.agent_status == "failed" and report.issues[0] == "HTTP 403"


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/login",
        "https://acme.hrpeak.com/jobs?token=secret",
    ],
)
async def test_sensitive_agent_candidates_are_rejected(url):
    class Unsafe:
        async def research(self, *args):
            return result(url)

    report = await agent_fallback(
        seed(), Discovery("Example", seed().url), Pages({}), Unsafe()
    )
    assert not report.findings and report.agent_status == "unresolved"


async def test_agent_private_evidence_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "scripts.discover_sources.validate_target_url_safety",
        lambda url: (False, "ssrf", "blocked"),
    )
    report = await agent_fallback(
        seed(), Discovery("Example", seed().url), Pages({}), FakeAgent()
    )
    assert not report.findings


async def test_agent_cannot_invent_a_chain_starting_elsewhere():
    class Wrong:
        async def research(self, *args):
            return result(
                chain=["https://other.example", "https://acme.hrpeak.com/jobs"]
            )

    report = await agent_fallback(
        seed(), Discovery("Example", seed().url), Pages({}), Wrong()
    )
    assert not report.findings


def test_agent_only_runs_for_unresolved_or_failed_reads():
    report = Discovery("Example", seed().url)
    assert needs_agent(report)
    report.findings.append(
        Finding(
            "https://example.com", "custom", (), "known", status="unsupported_provider"
        )
    )
    assert not needs_agent(report)
    assert needs_agent(report, research_unsupported=True)
    report.findings[0].status = "verification_failed"
    assert needs_agent(report)
    report.findings[0].status = "adapter_readable"
    assert not needs_agent(report)


def test_environment_excludes_app_and_auth_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("DATABASE_URL", "secret")
    monkeypatch.setenv("CODEX_ACCESS_TOKEN", "secret")
    env = runner.agent_environment()
    assert not {"OPENAI_API_KEY", "DATABASE_URL", "CODEX_ACCESS_TOKEN"} & env.keys()


async def test_codex_uses_exact_model_effort_and_sandbox(monkeypatch):
    observed = {}
    monkeypatch.setattr(runner.shutil, "which", lambda _: "codex.exe")

    class Process:
        returncode = 0

        async def communicate(self, prompt):
            observed["prompt"] = prompt

    async def spawn(*command, **kwargs):
        observed["command"] = command
        observed["cwd"] = kwargs["cwd"]
        path = Path(command[command.index("--output-last-message") + 1])
        path.write_text(result().model_dump_json(), encoding="utf-8")
        return Process()

    monkeypatch.setattr(runner.asyncio, "create_subprocess_exec", spawn)
    answer = await runner.CodexDiscoveryAgent().research(seed(), ["HTTP 403"])
    command = observed["command"]
    assert command[command.index("--model") + 1] == "gpt-6-luna"
    assert 'model_reasoning_effort="xhigh"' in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--ignore-user-config" in command and "--ephemeral" in command
    assert "shell_tool" in command and "--search" in command
    assert not Path(observed["cwd"]).exists()
    assert answer.candidates[0].board_url == "https://acme.hrpeak.com/jobs"
    assert b"HTTP 403" in observed["prompt"]


async def test_codex_timeout_terminates_process(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda _: "codex.exe")

    class Process:
        returncode = None
        killed = False

        async def communicate(self, prompt):
            await asyncio.sleep(1)

        def kill(self):
            self.killed = True

        async def wait(self):
            self.returncode = -1

    process = Process()

    async def spawn(*args, **kwargs):
        return process

    monkeypatch.setattr(runner.asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(runner.AgentFailure, match="timed out"):
        await runner.CodexDiscoveryAgent(timeout=0.01).research(seed(), [])
    assert process.killed


async def test_nonzero_exit_does_not_promote_results(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda _: "codex.exe")

    class Process:
        returncode = 1

        async def communicate(self, prompt):
            return None

    async def spawn(*args, **kwargs):
        return Process()

    monkeypatch.setattr(runner.asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(runner.AgentFailure, match="login status"):
        await runner.CodexDiscoveryAgent().research(seed(), [])


async def test_no_cli_is_actionable(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda _: None)
    with pytest.raises(runner.AgentFailure, match="codex login"):
        await runner.CodexDiscoveryAgent().research(seed(), [])


def test_usage_only_reads_numeric_completed_turn_counters(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        "\n".join(
            [
                "not json",
                "[]",
                '{"type":"turn.completed","usage":null}',
                '{"type":"item.completed","usage":{"input_tokens":999}}',
                '{"type":"turn.completed","usage":{"input_tokens":100,"cached_input_tokens":40,"output_tokens":20}}',
                '{"type":"turn.completed","usage":{"input_tokens":50,"cached_input_tokens":true,"output_tokens":10}}',
            ]
        ),
        encoding="utf-8",
    )
    assert runner.read_usage(events) == {
        "input_tokens": 150,
        "cached_input_tokens": 40,
        "output_tokens": 30,
        "total_tokens": 180,
    }


def test_missing_usage_is_not_zero(tmp_path):
    assert runner.read_usage(tmp_path / "missing") == {}
