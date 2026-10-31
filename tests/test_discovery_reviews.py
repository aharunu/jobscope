"""Automatic review preserves evidence/history and never performs discovery."""

import json
from dataclasses import asdict

import pytest

from scripts import discovery_phases as phases
from scripts.discover_sources import Discovery, Finding
from scripts.discovery_reviews import MARKER, generate_reviews
from tests.test_discovery_phases import setup_catalog


def fixture_results(tmp_path):
    source, root = setup_catalog(tmp_path)
    result_dir = root / "results"
    result_dir.mkdir()
    board = "https://new.hrpeak.com/ilan/site.aspx"
    reports = [
        Discovery(
            "Unknown",
            "https://unknown.example/career",
            findings=[
                Finding("https://www.kariyer.net/", "kariyer_net", (), "not a board"),
                Finding(
                    board,
                    "custom",
                    ("https://unknown.example/career", board),
                    "First observation",
                ),
                Finding(
                    board,
                    "custom",
                    ("https://unknown.example/career", board),
                    "Second observation",
                    evidence_urls=("https://proof.example/career",),
                ),
                Finding(
                    "https://unknown.example/career?locale=en",
                    "custom",
                    (),
                    "Possible alias",
                ),
                Finding(
                    "https://acme.hrpeak.com/jobs",
                    "hrpeak",
                    (),
                    "Known readable board",
                    status="adapter_readable",
                ),
            ],
        ),
        Discovery(
            "External",
            "https://external.example/career",
            findings=[
                Finding(board, "custom", (), "Another company, same board"),
            ],
        ),
        Discovery(
            "Failed",
            "https://failed.example/career",
            issues=["Timed out"],
            agent_status="failed",
        ),
    ]
    path = result_dir / "phase-001.json"
    path.write_text(json.dumps([asdict(item) for item in reports]), encoding="utf-8")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    state = {"1": {"sha256": manifest["phases"][0]["sha256"], "agent_enabled": True}}
    (root / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return source, root, board


def test_review_flags_facts_without_claiming_ownership(tmp_path):
    source, root, board = fixture_results(tmp_path)
    before = source.read_bytes()
    summary = generate_reviews(root, {"hrpeak", "hirex"})
    review = json.loads(
        (root / "results/phase-001-review.json").read_text(encoding="utf-8")
    )
    assert len(review["excluded"]) == 1 and review["duplicates"] == 1
    binding = next(
        item
        for item in review["candidates"]
        if item["url"] == board and item["company"] == "Unknown"
    )
    assert len(binding["observations"]) == 2
    assert binding["evidence"] == ["First observation", "Second observation"]
    assert binding["evidence_urls"] == ["https://proof.example/career"]
    assert "verify_existing_adapter_host_or_path_binding" in binding["actions"]
    assert "verify_population_and_company_filter" in binding["actions"]
    alias = next(item for item in review["candidates"] if "locale=" in item["url"])
    assert alias["possible_url_variant"]
    known = next(item for item in review["candidates"] if item["provider"] == "hrpeak")
    assert known["already_in_catalog"] and "preview_readable" in known["actions"]
    assert all(not item["ownership_verified"] for item in review["candidates"])
    assert summary["unresolved"][0]["company"] == "Failed"
    assert source.read_bytes() == before


def test_manual_notes_preserved_and_regeneration_is_idempotent(tmp_path):
    _, root, _ = fixture_results(tmp_path)
    note = root / "results/phase-001-review.md"
    note.write_text("Human scope decision; keep it.", encoding="utf-8")
    raw = (root / "results/phase-001.json").read_bytes()
    state = (root / "state.json").read_bytes()
    generate_reviews(root, {"hrpeak"})
    backups = list(note.parent.glob("phase-001-review-manual-*.md"))
    assert (
        len(backups) == 1 and backups[0].read_text() == "Human scope decision; keep it."
    )
    before = note.read_bytes()
    assert before.decode("utf-8").startswith(MARKER)
    generate_reviews(root, {"hrpeak"})
    assert note.read_bytes() == before
    assert len(list(note.parent.glob("phase-001-review-manual-*.md"))) == 1
    assert (root / "results/phase-001.json").read_bytes() == raw
    assert (root / "state.json").read_bytes() == state


def test_stale_phase_is_excluded_from_summary(tmp_path):
    _, root, _ = fixture_results(tmp_path)
    (root / "state.json").write_text('{"1":{"sha256":"stale"}}', encoding="utf-8")
    summary = generate_reviews(root, {"hrpeak"})
    assert summary["processed_phases"] == 0 and not summary["candidates"]


def test_cross_phase_worklist_deduplicates_without_losing_observations(tmp_path):
    _, root, board = fixture_results(tmp_path)
    report = Discovery(
        "Unknown",
        "https://another.example/career",
        findings=[
            Finding(board, "custom", (), "Later phase observation"),
        ],
    )
    (root / "results/phase-002.json").write_text(
        json.dumps([asdict(report)]),
        encoding="utf-8",
    )
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    state_path = root / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["2"] = {"sha256": manifest["phases"][1]["sha256"], "agent_enabled": True}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    summary = generate_reviews(root, {"hrpeak"})
    binding = next(
        item
        for item in summary["candidates"]
        if item["company"] == "Unknown" and item["url"] == board
    )
    assert binding["phase_numbers"] == [1, 2]
    assert len(binding["observations"]) == 3
    assert "Later phase observation" in binding["evidence"]
    assert summary["candidate_records"] == 5
    assert summary["distinct_company_urls"] == 4


def test_partial_results_do_not_hide_failed_agent_research(tmp_path):
    _, root, board = fixture_results(tmp_path)
    report = Discovery(
        "Unknown",
        "https://unknown.example/career",
        agent_status="failed",
        issues=["Codex failed"],
        findings=[
            Finding(board, "custom", (), "Classic partial observation"),
        ],
    )
    (root / "results/phase-001.json").write_text(
        json.dumps([asdict(report)]),
        encoding="utf-8",
    )
    summary = generate_reviews(root, {"hrpeak"})
    assert not summary["unresolved"]
    assert summary["incomplete_research"][0]["agent_status"] == "failed"
    assert "retry_or_inspect_agent_research" in summary["candidates"][0]["actions"]


async def test_review_command_never_dispatches_discovery(tmp_path, monkeypatch):
    _, root, _ = fixture_results(tmp_path)

    async def forbidden(*args):
        pytest.fail("Review must not run HTTP or agent discovery")

    monkeypatch.setattr(phases, "run_discovery", forbidden)
    from argparse import Namespace

    await phases.execute(Namespace(command="review", root=root))
    assert (root / "results/summary.md").exists()
    assert not (root / ".run.lock").exists()
