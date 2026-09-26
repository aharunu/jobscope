"""Deterministic rule-based requirement extractor."""

from __future__ import annotations

import html
import re
import uuid
from typing import ClassVar

from backend.application.job_processing.extraction import RequirementExtractor
from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import RequirementLevel, RequirementType
from backend.infrastructure.extraction.taxonomy import (
    EXPERIENCE_PATTERN,
    TaxonomyEntry,
    compile_taxonomy,
)

# Regex to normalize HTML into line-separated text
_HTML_BLOCK_TAGS = re.compile(r"(?i)<(?:p|br|li|div|h[1-6]|tr)[^>]*>")
_HTML_ANY_TAG = re.compile(r"<[^>]+>")

# Section detection patterns
_PREFERRED_SECTION_RE = re.compile(
    r"(?i)\b(?:nice\s+to\s+have|preferred|bonus|pluses|good\s+to\s+have|desirable|plus)\b"
)
_REQUIRED_SECTION_RE = re.compile(
    r"(?i)\b(?:requirements?|qualifications?|must\s+have|what\s+you\s+need|what\s+we(?:'re|\s+are)\s+looking\s+for|basic\s+qualifications?|minimum\s+qualifications?)\b"
)

# Line-level modifier patterns
_PREFERRED_LINE_RE = re.compile(
    r"(?i)\b(?:nice\s+to\s+have|preferred|bonus|plus|optional|advantageous)\b"
)
_REQUIRED_LINE_RE = re.compile(
    r"(?i)\b(?:must\s+have|required|mandatory|essential|minimum|at\s+least)\b"
)

_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[•\-–—*►]|\d+[.)])\s*")


class DeterministicRequirementExtractor(RequirementExtractor):
    """Deterministic, rule-based extractor producing structured JobRequirements.

    Invariants:
    1. Purely ATS-agnostic: operates on canonical Job entity fields.
    2. Conservative: matches only explicit, confident patterns.
    3. Deterministic: repeated execution on the same job yields identical results.
    4. Deduplicated: duplicate mentions merge into a single canonical requirement,
       with REQUIRED level taking precedence over PREFERRED.
    5. Clean text boundaries: distinguishes 'PostgreSQL' from 'SQL',
       'FastAPI' from 'API', and 'Java' from 'JavaScript'.
    """

    _taxonomy: ClassVar[list[TaxonomyEntry]] = compile_taxonomy()

    def extract(self, job: Job) -> list[JobRequirement]:
        """Extract structured JobRequirements from title, description,
        and responsibilities.
        """
        # Map: (RequirementType, canonical_key) -> JobRequirement
        extracted: dict[tuple[RequirementType, str], JobRequirement] = {}

        # 1. Extract from job title (inherently REQUIRED, HIGH importance)
        if job.title and job.title.strip():
            self._extract_from_text(
                text=job.title,
                job_id=job.id,
                default_level=RequirementLevel.REQUIRED,
                is_title=True,
                output=extracted,
            )

        # 2. Extract from normalized description
        if job.description and job.description.strip():
            self._extract_from_structured_content(
                content=job.description,
                job_id=job.id,
                output=extracted,
            )

        # 3. Extract from responsibilities if provided
        if job.responsibilities and job.responsibilities.strip():
            self._extract_from_structured_content(
                content=job.responsibilities,
                job_id=job.id,
                output=extracted,
            )

        # Deterministic sorting: by category, normalized_skill, then description
        sorted_requirements = sorted(
            extracted.values(),
            key=lambda r: (
                r.type.value,
                r.normalized_skill or "",
                r.description,
            ),
        )

        return sorted_requirements

    def _extract_from_structured_content(
        self,
        content: str,
        job_id: uuid.UUID,
        output: dict[tuple[RequirementType, str], JobRequirement],
    ) -> None:
        """Parse multi-line or HTML content, tracking section headers and lines."""
        # Convert HTML blocks to newlines, unescape entities, and clean
        text_with_newlines = _HTML_BLOCK_TAGS.sub("\n", content)
        clean_text = _HTML_ANY_TAG.sub(" ", text_with_newlines)
        unescaped = html.unescape(clean_text)

        lines = [line.strip() for line in unescaped.splitlines() if line.strip()]

        current_section_level = RequirementLevel.REQUIRED

        for line in lines:
            # Check if line is a section heading
            is_heading = len(line) < 80 and (
                line.endswith(":") or line.startswith("#") or line.isupper()
            )
            if is_heading:
                if _PREFERRED_SECTION_RE.search(line):
                    current_section_level = RequirementLevel.PREFERRED
                    continue
                if _REQUIRED_SECTION_RE.search(line):
                    current_section_level = RequirementLevel.REQUIRED
                    continue

            # Determine line-level override
            line_level = current_section_level
            if _PREFERRED_LINE_RE.search(line):
                line_level = RequirementLevel.PREFERRED
            elif _REQUIRED_LINE_RE.search(line):
                line_level = RequirementLevel.REQUIRED

            clean_line = _BULLET_PREFIX_RE.sub("", line).strip()
            if not clean_line:
                continue

            self._extract_from_text(
                text=clean_line,
                job_id=job_id,
                default_level=line_level,
                is_title=False,
                output=output,
            )

    def _extract_from_text(
        self,
        text: str,
        job_id: uuid.UUID,
        default_level: RequirementLevel,
        is_title: bool,
        output: dict[tuple[RequirementType, str], JobRequirement],
    ) -> None:
        """Scan a single sentence or line against taxonomy rules and
        experience patterns.
        """
        evidence = text[:500].strip()

        # A. Taxonomy matches (Skills, Education, Language, Certification)
        for entry in self._taxonomy:
            if entry.pattern.search(text):
                self._record_match(
                    job_id=job_id,
                    req_type=entry.category,
                    canonical_key=entry.canonical_key,
                    display_name=entry.canonical_name,
                    description=text,
                    evidence=evidence,
                    level=default_level,
                    is_title=is_title,
                    output=output,
                )

        # B. Experience pattern matching
        for match in EXPERIENCE_PATTERN.finditer(text):
            prefix = match.group("prefix")
            years = match.group("years")
            plus = match.group("plus")
            exp_word = match.group("exp")

            # Must have at least one explicit qualifier to prevent false positives
            # e.g. "at least 3 years", "2+ years", "3 years experience"
            if prefix or plus or exp_word:
                years_clean = years.replace(" ", "")
                plus_str = "+" if plus else ""
                canonical_key = f"exp_{years_clean}{plus_str}_years"
                display_name = f"{years_clean}{plus_str} years experience"

                self._record_match(
                    job_id=job_id,
                    req_type=RequirementType.EXPERIENCE,
                    canonical_key=canonical_key,
                    display_name=display_name,
                    description=text,
                    evidence=evidence,
                    level=default_level,
                    is_title=is_title,
                    output=output,
                )

    def _record_match(
        self,
        job_id: uuid.UUID,
        req_type: RequirementType,
        canonical_key: str,
        display_name: str,
        description: str,
        evidence: str,
        level: RequirementLevel,
        is_title: bool,
        output: dict[tuple[RequirementType, str], JobRequirement],
    ) -> None:
        """Deduplicate and reconcile requirement priority."""
        key = (req_type, canonical_key)

        importance = (
            "HIGH" if (is_title or level == RequirementLevel.REQUIRED) else "LOW"
        )
        criticality = "NORMAL"
        if req_type == RequirementType.EDUCATION and level == RequirementLevel.REQUIRED:
            criticality = "BLOCKER"

        if key in output:
            existing = output[key]
            # REQUIRED takes precedence over PREFERRED
            if (
                existing.required_level == RequirementLevel.PREFERRED
                and level == RequirementLevel.REQUIRED
            ):
                existing.required_level = RequirementLevel.REQUIRED
                existing.importance = "HIGH"
            # Upgrade importance if discovered in title
            if is_title and existing.importance != "HIGH":
                existing.importance = "HIGH"
        else:
            output[key] = JobRequirement(
                id=uuid.uuid4(),
                job_id=job_id,
                type=req_type,
                description=description,
                normalized_skill=display_name,
                required_level=level,
                importance=importance,
                criticality=criticality,
                evidence=evidence,
            )
