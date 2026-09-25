"""Unit and integration tests for MarkdownSourceParser."""

import pytest

from backend.application.job_discovery.ports import CatalogParser
from backend.infrastructure.parsers.markdown_source_parser import (
    MarkdownSourceParser,
    classify_ats_type,
)


def test_parser_protocol_conformance() -> None:
    """Verify MarkdownSourceParser conforms to the CatalogParser protocol."""
    parser = MarkdownSourceParser()
    assert isinstance(parser, CatalogParser)


def test_classify_ats_type() -> None:
    """Verify ATS classification rules for all supported platforms."""
    assert classify_ats_type("https://boards.greenhouse.io/getir") == "greenhouse"
    assert classify_ats_type("https://jobs.lever.co/trendyol") == "lever"
    assert classify_ats_type("https://koc.wd3.myworkdayjobs.com/careers") == "workday"
    assert classify_ats_type("https://jobs.ashbyhq.com/midas") == "ashby"
    assert (
        classify_ats_type("https://jobs.smartrecruiters.com/hepsiburada")
        == "smartrecruiters"
    )
    assert classify_ats_type("https://insider.recruitee.com") == "recruitee"
    assert classify_ats_type("https://company.jobs.personio.com") == "personio"
    assert classify_ats_type("https://apply.workable.com/tekfen") == "workable"
    assert classify_ats_type("https://company.bamboohr.com/jobs") == "bamboohr"
    assert classify_ats_type("https://gethirex.com/jobs/company") == "hirex"
    assert classify_ats_type("https://career.teamtailor.com") == "teamtailor"
    assert classify_ats_type("https://eeho.fa.em2.oraclecloud.com/hcmUI") == "oracle"
    assert (
        classify_ats_type("https://www.kariyer.net/firma-profil/dogus-1463-5075")
        == "kariyer_net"
    )
    assert classify_ats_type("https://www.company.com/careers") == "custom"


def test_parse_content_single_standard_entry() -> None:
    """Verify standard catalog entry extraction with metadata and notes."""
    content = """
## 3. Tech unicorns, gaming & software scaleups

### Gaming
- **Dream Games** — `https://jobs.lever.co/dreamgames` — open — Royal Match creator
"""
    parser = MarkdownSourceParser()
    sources, warnings = parser.parse_content(content)

    assert len(warnings) == 0
    assert len(sources) == 1
    src = sources[0]
    assert src.name == "Dream Games"
    assert src.company == "Dream Games"
    assert src.url == "https://jobs.lever.co/dreamgames"
    assert src.ats_type == "lever"
    assert src.country == "TR"
    assert src.active is True
    assert src.metadata["category"] == "3. Tech unicorns, gaming & software scaleups"
    assert src.metadata["group"] == "Gaming"
    assert src.metadata["access_tier"] == "open"
    assert "Royal Match" in src.metadata["notes"]


def test_parse_content_prioritizes_ats_url_over_corporate() -> None:
    """Verify ATS endpoint is selected as primary URL over corporate link."""
    content = (
        "## 1. Holdings & conglomerates\n"
        "- **Tekfen Ventures** — `https://careers.tekfen.com/jobs` + "
        "`https://apply.workable.com/tekfen/` — open\n"
    )
    parser = MarkdownSourceParser()
    sources, warnings = parser.parse_content(content)

    assert len(sources) == 1
    src = sources[0]
    assert src.url == "https://apply.workable.com/tekfen"
    assert src.ats_type == "workable"
    assert "https://careers.tekfen.com/jobs" in src.metadata["alternate_urls"]


def test_parse_content_kariyer_net_firma_profil() -> None:
    """Verify firma-profil references in backticks expand to full URLs."""
    content = (
        "## 1. Holdings & conglomerates\n"
        "- **Doğuş Teknoloji** — Kariyer.net "
        "`firma-profil/dogus-teknoloji-164050-226026` — open browse\n"
    )
    parser = MarkdownSourceParser()

    sources, warnings = parser.parse_content(content)

    assert len(sources) == 1
    src = sources[0]
    assert (
        src.url == "https://www.kariyer.net/firma-profil/dogus-teknoloji-164050-226026"
    )
    assert src.ats_type == "kariyer_net"


def test_parse_content_access_tiers() -> None:
    """Verify access_tier detection for open, login-to-apply, and restricted."""
    content = """
## 1. Test Section
- **Alpha Co** — `https://alpha.com/jobs` — open — notes
- **Beta Co** — `https://beta.com/jobs` — login-to-apply — notes
- **Gamma Co** — `https://gamma.com/jobs` — restricted — notes
"""
    parser = MarkdownSourceParser()
    sources, warnings = parser.parse_content(content)

    assert len(sources) == 3
    assert sources[0].metadata["access_tier"] == "open"
    assert sources[1].metadata["access_tier"] == "login-to-apply"
    assert sources[2].metadata["access_tier"] == "restricted"


def test_parse_content_collect_and_report_warnings() -> None:
    """Verify entries without valid URLs produce warning messages."""
    content = """
## 1. Test Section
- **Valid Co** — `https://valid.com/jobs` — open — has url
- **No URL Co** — careers via phone / contact form (no ATS) — restricted — no url here
"""

    parser = MarkdownSourceParser()
    sources, warnings = parser.parse_content(content)

    assert len(sources) == 1
    assert sources[0].name == "Valid Co"
    assert len(warnings) == 1
    assert "No URL Co" in warnings[0]


def test_parse_content_ignores_excluded_sections() -> None:
    """Verify non-source documentation sections are ignored."""
    content = """
## Access tiers
- **open** — public listings
- **restricted** — restricted apply

## Most valuable machine-queryable API endpoints (use these first)
- **Lever**: `https://api.lever.co/v0/postings/<token>`

## 1. Real Sources
- **Actual Company** — `https://actual.com/jobs` — open — valid source
"""
    parser = MarkdownSourceParser()
    sources, warnings = parser.parse_content(content)

    assert len(sources) == 1
    assert sources[0].name == "Actual Company"


def test_parse_file_canonical_catalog() -> None:
    """Verify parsing the real data/turkish-job-sources.md file."""
    parser = MarkdownSourceParser()
    sources, warnings = parser.parse_file("data/turkish-job-sources.md")

    assert len(sources) >= 1800
    assert len(warnings) >= 1
    assert all(src.name for src in sources)
    assert all(src.url for src in sources)
    assert all(src.ats_type for src in sources)


def test_parse_file_missing_raises_filenotfound() -> None:
    """Verify attempting to parse a non-existent file raises FileNotFoundError."""
    parser = MarkdownSourceParser()
    with pytest.raises(FileNotFoundError):
        parser.parse_file("data/non_existent_file.md")
