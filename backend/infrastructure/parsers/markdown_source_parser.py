"""Markdown source catalog parser implementing the CatalogParser application port."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from backend.application.job_discovery.dtos import SourceCreateDTO
from backend.application.job_discovery.ports import CatalogParser
from backend.domain.source.normalization import normalize_source_url

logger = logging.getLogger(__name__)

# Preferred ordering for selecting primary machine-queryable ATS URL
ATS_PREFERENCE: list[str] = [
    "lever",
    "greenhouse",
    "workday",
    "ashby",
    "smartrecruiters",
    "recruitee",
    "personio",
    "workable",
    "bamboohr",
    "hirex",
    "teamtailor",
    "oracle",
    "kariyer_net",
]

# Catalog section prefixes that contain explanatory text rather than job sources
EXCLUDED_SECTION_PREFIXES: tuple[str, ...] = (
    "access tiers",
    "most valuable",
    "honesty notes",
)

URL_REGEX = re.compile(r"https?://[^\s`\"'\)]+")
BACKTICK_REGEX = re.compile(r"`([^`]+)`")


def classify_ats_type(url: str) -> str:
    """Deterministically classify the ATS type from a candidate URL."""
    url_lower = url.lower()
    if "greenhouse.io" in url_lower:
        return "greenhouse"
    if "lever.co" in url_lower:
        return "lever"
    if "workday" in url_lower or "myworkdayjobs" in url_lower:
        return "workday"
    if "ashbyhq.com" in url_lower:
        return "ashby"
    if "smartrecruiters.com" in url_lower:
        return "smartrecruiters"
    if "recruitee.com" in url_lower:
        return "recruitee"
    if "personio" in url_lower:
        return "personio"
    if "workable.com" in url_lower:
        return "workable"
    if "bamboohr.com" in url_lower:
        return "bamboohr"
    if "gethirex.com" in url_lower:
        return "hirex"
    if "teamtailor.com" in url_lower:
        return "teamtailor"
    if "oraclecloud.com" in url_lower:
        return "oracle"
    if "kariyer.net" in url_lower:
        return "kariyer_net"
    return "custom"


def prioritize_urls(urls: list[str]) -> list[str]:
    """Sort URLs prioritizing recognized ATS endpoints over generic pages."""

    def priority_score(u: str) -> int:
        ats = classify_ats_type(u)
        if ats in ATS_PREFERENCE:
            return ATS_PREFERENCE.index(ats)
        if "successfactors" in u.lower():
            return len(ATS_PREFERENCE)
        return len(ATS_PREFERENCE) + 1

    return sorted(urls, key=priority_score)


class MarkdownSourceParser(CatalogParser):
    """Parser for the canonical Markdown job-source catalog."""

    def parse_content(self, content: str) -> tuple[list[SourceCreateDTO], list[str]]:
        """Parse raw catalog text into SourceCreateDTOs and warning messages."""
        lines = content.splitlines()
        sources: list[SourceCreateDTO] = []
        warnings: list[str] = []

        in_source_section = False
        current_category = ""
        current_group = ""

        for line_idx, raw_line in enumerate(lines, 1):
            line_s = raw_line.strip()

            # Handle H2 sections
            if line_s.startswith("## ") and not line_s.startswith("### "):
                sec_title = line_s[3:].strip()
                if any(
                    sec_title.lower().startswith(ex) for ex in EXCLUDED_SECTION_PREFIXES
                ):
                    in_source_section = False
                else:
                    in_source_section = True
                    current_category = sec_title
                    current_group = ""
                continue

            # Handle H3 subsections (groups)
            if line_s.startswith("### "):
                current_group = line_s[4:].strip()
                continue

            # Process candidate source lines
            if in_source_section and line_s.startswith("- **"):
                match = re.match(r"-\s*\*\*([^*]+)\*\*(.*)", line_s)
                if not match:
                    warnings.append(
                        f"Line {line_idx}: Could not match bold name: {line_s[:50]}"
                    )
                    continue

                raw_name = match.group(1).strip()
                rest = match.group(2).strip()

                # Extract explicit URLs and backtick domain/path references
                found_urls = URL_REGEX.findall(line_s)
                for bt in BACKTICK_REGEX.findall(line_s):
                    bt_clean = bt.strip()
                    # Skip tokens with template or placeholder syntax
                    if any(c in bt_clean for c in ("<", ">", "[", "]")):
                        continue
                    if bt_clean.startswith("firma-profil/"):
                        found_urls.append(f"https://www.kariyer.net/{bt_clean}")
                    elif (
                        not bt_clean.startswith("http")
                        and ("." in bt_clean or "/" in bt_clean)
                        and any(
                            ext in bt_clean
                            for ext in (
                                ".com",
                                ".net",
                                ".io",
                                ".eu",
                                ".co",
                                ".org",
                                ".edu",
                            )
                        )
                    ):
                        found_urls.append(f"https://{bt_clean}")

                # Clean and deduplicate URLs
                clean_urls: list[str] = []
                for u in found_urls:
                    u_clean = u.rstrip(".)\",'")
                    if u_clean and u_clean not in clean_urls:
                        clean_urls.append(u_clean)

                if not clean_urls:
                    warnings.append(
                        f"Line {line_idx}: No valid URL found for '{raw_name}'"
                    )
                    continue

                # Prioritize primary machine-queryable ATS endpoint
                sorted_urls = prioritize_urls(clean_urls)
                primary_url = normalize_source_url(sorted_urls[0])
                if not primary_url:
                    warnings.append(
                        f"Line {line_idx}: Unparseable URL for '{raw_name}'"
                    )
                    continue

                alt_urls = [
                    norm for u in sorted_urls[1:] if (norm := normalize_source_url(u))
                ]

                ats_type = classify_ats_type(primary_url)

                # Extract company name cleanly
                company = raw_name
                if "(" in raw_name and raw_name.endswith(")"):
                    candidate = raw_name[: raw_name.rfind("(")].strip()
                    if candidate:
                        company = candidate
                elif " — " in raw_name:
                    company = raw_name.split(" — ")[0].strip()

                # Access tier detection
                access_tier = "open"
                line_lower = line_s.lower()
                if "login-to-apply" in line_lower:
                    access_tier = "login-to-apply"
                elif "restricted" in line_lower:
                    access_tier = "restricted"

                # Notes extraction
                parts = [p.strip() for p in re.split(r"\s*[—–]\s*", rest) if p.strip()]
                notes = parts[-1] if len(parts) >= 2 else ""

                metadata = {
                    "category": current_category,
                    "group": current_group,
                    "access_tier": access_tier,
                    "notes": notes,
                    "alternate_urls": alt_urls,
                }

                sources.append(
                    SourceCreateDTO(
                        name=raw_name,
                        company=company,
                        url=primary_url,
                        ats_type=ats_type,
                        country="TR",
                        active=True,
                        metadata=metadata,
                    )
                )

        return sources, warnings

    def parse_file(self, file_path: str) -> tuple[list[SourceCreateDTO], list[str]]:
        """Parse a catalog file into SourceCreateDTOs and warning messages."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Source catalog file not found at: {file_path}")

        content = path.read_text(encoding="utf-8")
        return self.parse_content(content)
