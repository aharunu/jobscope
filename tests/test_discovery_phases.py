"""Lossless catalog partitioning and offline phase orchestration contracts."""

import json
from argparse import Namespace
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import pytest

from backend.infrastructure.parsers.markdown_source_parser import MarkdownSourceParser
from scripts import discovery_phases as tool
from scripts.discover_sources import Discovery, Finding


def setup_catalog(tmp_path):
    source = tmp_path / "catalog.md"
    source.write_text(
        "## Tech\n### Group\n"
        "- **Supported** — `https://acme.hrpeak.com/jobs` — login-to-apply — Notes.\n"
        "- **Unknown** — `https://unknown.example/career` — restricted — Notes.\n"
        "- **Unknown** — `https://unknown.example/career` — restricted — Notes.\n"
        "- **Peoplise** — `https://employer.example/career` + "
        "`https://live.peoplise.com/acme/career` — open\n"
        "- **External** — `https://www.kariyer.net/firma-profil/example` + "
        "`https://external.example/career` — open\n"
        "- **Hands off** — `https://www.linkedin.com/jobs` — restricted\n"
        "- **Missing** — no URL\n",
        encoding="utf-8",
    )
    root = tmp_path / "modules"
    tool.prepare(Namespace(source=source, root=root, batch_size=1))
    return source, root


def semantic_rows(sources):
    return Counter(
        json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) for row in sources
    )


def test_partition_preserves_all_valid_rows_metadata_and_duplicates(tmp_path):
    source, root = setup_catalog(tmp_path)
    original = source.read_bytes()
    parser = MarkdownSourceParser()
    expected, _ = parser.parse_file(str(source))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    actual = []
    for relative in manifest["modules"]:
        rows, _ = parser.parse_file(str(root / relative))
        actual.extend(rows)
    assert semantic_rows(actual) == semantic_rows(expected)
    assert source.read_bytes() == original
    assert manifest["url_review_rows"] == 1
    assert len(manifest["phases"]) == 2  # Exact duplicate queued only once.
    assert (root / "catalog/unsupported/peoplise.com.md").exists()
    assert (root / "catalog/hands-off-or-unsafe.md").exists()
    assert (
        manifest["phases"][0]["sources"][0]["url"] == "https://unknown.example/career"
    )
    assert (
        manifest["phases"][1]["sources"][0]["url"] == "https://external.example/career"
    )
    first, _ = parser.parse_file(str(root / "phases/phase-001.md"))
    assert first[0].metadata["access_tier"] == "restricted"


def test_prepare_is_deterministic_and_keeps_state(tmp_path):
    source, root = setup_catalog(tmp_path)
    before = (root / "manifest.json").read_bytes()
    (root / "state.json").write_text('{"keep":true}', encoding="utf-8")
    tool.prepare(Namespace(source=source, root=root, batch_size=1))
    assert (root / "manifest.json").read_bytes() == before
    assert json.loads((root / "state.json").read_text()) == {"keep": True}


def options(root, **overrides):
    return Namespace(
        root=root,
        phase=None,
        retry=False,
        no_agent=False,
        no_env_proxy=True,
        **overrides,
    )


@pytest.mark.parametrize(
    ("model_options", "model", "effort"),
    [
        ({}, "gpt-6-luna", "xhigh"),
        ({"agent_model": "gpt-6.1-terra"}, "gpt-6.1-terra", "medium"),
        (
            {"agent_model": "gpt-6.1-terra", "agent_effort": "high"},
            "gpt-6.1-terra",
            "high",
        ),
    ],
)
async def test_run_selected_model_and_records_progress(
    tmp_path, monkeypatch, model_options, model, effort
):
    source, root = setup_catalog(tmp_path)
    original = source.read_bytes()
    calls = []

    async def fake_run(args):
        calls.append(args)
        return [
            Discovery(
                "Unknown",
                "https://unknown.example/career",
                findings=[
                    Finding(
                        "https://acme.hrpeak.com/jobs",
                        "hrpeak",
                        (),
                        "proof",
                        status="agent_adapter_readable",
                    ),
                    Finding(
                        "https://live.peoplise.com/new/career",
                        "custom",
                        (),
                        "proof",
                        status="unsupported_provider",
                    ),
                ],
            )
        ]

    monkeypatch.setattr(tool, "run_discovery", fake_run)
    await tool.execute(options(root, **model_options))
    assert len(calls) == 1
    assert calls[0].agent_model == model and calls[0].agent_effort == effort
    assert calls[0].agent_max_sources == 1 and calls[0].research_external_only
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    assert state["1"]["agent_enabled"] is True
    assert state["1"]["model"] == model
    assert state["1"]["effort"] == effort
    assert (root / "results/catalog-candidates.md").exists()
    assert (root / "results/adapter-candidates.md").exists()
    assert (root / "results/phase-001-review.md").exists()
    first_summary = json.loads(
        (root / "results/summary.json").read_text(encoding="utf-8")
    )
    assert first_summary["processed_phases"] == 1
    assert source.read_bytes() == original
    await tool.execute(options(root))
    assert calls[1].input.name == "phase-002.md"
    second_summary = json.loads(
        (root / "results/summary.json").read_text(encoding="utf-8")
    )
    assert second_summary["processed_phases"] == 2
    assert second_summary["distinct_company_urls"] == 2
    explicit = options(root)
    explicit.phase = 1
    with pytest.raises(ValueError, match="already processed"):
        await tool.execute(explicit)
    assert not (root / ".run.lock").exists()


async def test_changed_catalog_or_phase_refuses_network(tmp_path, monkeypatch):
    source, root = setup_catalog(tmp_path)

    async def forbidden(*args):
        pytest.fail("Discovery must not run")

    monkeypatch.setattr(tool, "run_discovery", forbidden)
    path = root / "phases/phase-001.md"
    path.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="Phase input changed"):
        await tool.execute(options(root))
    source.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="Canonical catalog changed"):
        await tool.execute(options(root))


async def test_phase_lock_prevents_duplicate_dispatch(tmp_path):
    _, root = setup_catalog(tmp_path)
    (root / ".run.lock").write_text("existing-run", encoding="utf-8")
    with pytest.raises(ValueError, match="Another phase"):
        await tool.execute(options(root))
    assert (root / ".run.lock").read_text() == "existing-run"


async def test_classic_only_run_remains_pending_for_agent_run(tmp_path, monkeypatch):
    _, root = setup_catalog(tmp_path)
    calls = []

    async def fake_run(args):
        calls.append((args.input.name, args.no_agent))
        return []

    monkeypatch.setattr(tool, "run_discovery", fake_run)
    classic = options(root)
    classic.no_agent = True
    await tool.execute(classic)
    await tool.execute(options(root))
    assert calls == [("phase-001.md", True), ("phase-001.md", False)]


async def test_failed_phase_keeps_progress_pending_and_releases_lock(
    tmp_path, monkeypatch
):
    _, root = setup_catalog(tmp_path)

    async def failed(*args):
        raise RuntimeError("Test failure")

    monkeypatch.setattr(tool, "run_discovery", failed)
    with pytest.raises(RuntimeError, match="Test failure"):
        await tool.execute(options(root))
    assert not (root / ".run.lock").exists()
    assert not (root / "state.json").exists()


async def test_inventories_filter_and_deduplicate(tmp_path, monkeypatch):
    _, root = setup_catalog(tmp_path)
    profile = "https://www.kariyer.net/firma-profil/example-123"

    async def fake_run(args):
        return [
            Discovery(
                "Example",
                "https://unknown.example/career",
                findings=[
                    Finding("https://www.kariyer.net/", "kariyer_net", (), "site root"),
                    Finding(
                        "http://www.kariyer.net/Website/TeknikDestek/sifremiunuttum/s1.aspx",
                        "kariyer_net",
                        (),
                        "account route",
                    ),
                    Finding(profile, "kariyer_net", (), "catalog URL"),
                    Finding(profile, "kariyer_net", (), "Longer agent explanation"),
                ],
            )
        ]

    monkeypatch.setattr(tool, "run_discovery", fake_run)
    await tool.execute(options(root))
    report = (root / "results/adapter-candidates.md").read_text(encoding="utf-8")
    assert report.count("## Example") == 1
    assert profile in report and "Longer agent explanation" in report
    assert "sifremiunuttum" not in report and "site root" not in report


def test_real_partition_matches_canonical_without_network(tmp_path):
    parser = MarkdownSourceParser()
    expected, _ = parser.parse_file("data/turkish-job-sources.md")
    root = tmp_path / "source-discovery"
    tool.prepare(
        Namespace(source=Path("data/turkish-job-sources.md"), root=root, batch_size=10)
    )
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    actual = []
    for relative in manifest["modules"]:
        rows, _ = parser.parse_file(str(root / relative))
        actual.extend(rows)
    assert semantic_rows(actual) == semantic_rows(expected)
    assert manifest["source_sha256"] == tool.digest(tool.CANONICAL)
    assert all(len(p["sources"]) <= 10 for p in manifest["phases"])


@pytest.mark.parametrize("explicit_phase", [None, 1])
async def test_classic_mode_preserves_completed_agent_results(
    tmp_path, monkeypatch, explicit_phase
):
    _, root = setup_catalog(tmp_path)
    calls = []

    async def fake_run(args):
        calls.append(args.input.name)
        return [Discovery("Saved agent finding", "https://unknown.example/career")]

    monkeypatch.setattr(tool, "run_discovery", fake_run)
    await tool.execute(options(root))
    report = root / "results/phase-001.json"
    saved = report.read_bytes()
    saved_state = json.loads((root / "state.json").read_text())["1"]
    classic = options(root)
    classic.no_agent = True
    classic.phase = explicit_phase
    if explicit_phase is not None:
        with pytest.raises(ValueError, match="already processed"):
            await tool.execute(classic)
    else:
        await tool.execute(classic)
        assert calls == ["phase-001.md", "phase-002.md"]
    assert report.read_bytes() == saved
    assert json.loads((root / "state.json").read_text())["1"] == saved_state
