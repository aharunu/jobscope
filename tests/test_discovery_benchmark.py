"""Benchmark aggregation distinguishes missing usage and real zero counts."""

from scripts.benchmark_discovery import summarize


def test_missing_usage_is_not_reported_as_zero_or_counted_as_measurement():
    rows = [
        {
            "model": "gpt-6-luna",
            "status": "completed",
            "wall_seconds": 10,
            "input_tokens": 80,
            "cached_input_tokens": 40,
            "output_tokens": 20,
            "total_tokens": 100,
        },
        {"model": "gpt-6-luna", "status": "failed", "wall_seconds": 120},
        {
            "model": "gpt-6.1-terra",
            "status": "completed",
            "wall_seconds": 5,
            "input_tokens": 40,
            "cached_input_tokens": 10,
            "output_tokens": 10,
            "total_tokens": 50,
        },
    ]
    luna, terra = summarize(rows)
    assert luna["runs"] == 2 and luna["measured_usage_runs"] == 1
    assert luna["total_tokens"] == 100 and luna["input_cache_percent"] == 50
    assert luna["token_share_percent"] == 66.67
    assert terra["token_share_percent"] == 33.33


def test_empty_benchmark_has_no_fabricated_usage():
    assert all(s["total_tokens"] is None for s in summarize([]))


def test_selected_pairs_are_kept_separate_by_effort():
    rows = [
        {
            "model": "gpt-6-luna",
            "effort": "high",
            "status": "completed",
            "wall_seconds": 8,
            "input_tokens": 80,
            "output_tokens": 20,
            "total_tokens": 100,
        },
        {
            "model": "gpt-6-luna",
            "effort": "xhigh",
            "status": "completed",
            "wall_seconds": 20,
            "input_tokens": 160,
            "output_tokens": 40,
            "total_tokens": 200,
        },
        {
            "model": "gpt-6.1-sol",
            "effort": "medium",
            "status": "completed",
            "wall_seconds": 6,
            "input_tokens": 40,
            "output_tokens": 10,
            "total_tokens": 50,
        },
    ]
    luna, sol = summarize(rows, (("gpt-6-luna", "high"), ("gpt-6.1-sol", "medium")))
    assert luna["runs"] == 1 and luna["total_tokens"] == 100
    assert sol["effort"] == "medium" and sol["total_tokens"] == 50


async def test_missing_benchmark_input_gives_setup_guidance(tmp_path):
    from argparse import Namespace

    import pytest

    from scripts.benchmark_discovery import MODELS, run

    with pytest.raises(ValueError, match="exactly ten distinct companies"):
        await run(Namespace(models=MODELS, input=tmp_path / "missing.md"))
