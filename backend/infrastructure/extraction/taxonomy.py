"""Deterministic taxonomy definitions and regex patterns for requirement extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.domain.job.enums import RequirementType


@dataclass(frozen=True, slots=True)
class TaxonomyEntry:
    """Pre-compiled deterministic taxonomy rule."""

    canonical_name: str
    canonical_key: str
    category: RequirementType
    pattern: re.Pattern[str]


# -----------------------------------------------------------------------------
# 1. Technical Skills
# -----------------------------------------------------------------------------
TECHNICAL_SKILLS: list[tuple[str, str, str]] = [
    # (canonical_name, canonical_key, regex_pattern)
    ("Python", "python", r"\bpython\b"),
    ("Java", "java", r"\bjava\b(?!\s*script)"),
    ("JavaScript", "javascript", r"\bjavascript\b|\bjs\b"),
    ("TypeScript", "typescript", r"\btypescript\b|\bts\b"),
    ("SQL", "sql", r"\bsql\b"),
    ("PostgreSQL", "postgresql", r"\bpostgresql\b|\bpostgres\b"),
    ("Docker", "docker", r"\bdocker\b"),
    ("Kubernetes", "kubernetes", r"\bkubernetes\b|\bk8s\b"),
    ("FastAPI", "fastapi", r"\bfastapi\b"),
    ("Spring Boot", "spring_boot", r"\bspring\s+boot\b|\bspring\s+framework\b"),
    ("TensorFlow", "tensorflow", r"\btensorflow\b|\btf\b"),
    ("PyTorch", "pytorch", r"\bpytorch\b"),
    ("AWS", "aws", r"\baws\b|\bamazon\s+web\s+services\b"),
    ("Azure", "azure", r"\bazure\b|\bmicrosoft\s+azure\b"),
    ("GCP", "gcp", r"\bgcp\b|\bgoogle\s+cloud(?:\s+platform)?\b"),
    ("Git", "git", r"\bgit\b(?!\s*lab|\s*hub)"),
    ("React", "react", r"\breact(?:\.js)?\b"),
    ("Node.js", "nodejs", r"\bnode(?:\.js)?\b"),
    ("Go", "go", r"\bgolang\b|\bgo\s+language\b"),
    ("C++", "cpp", r"(?:\bc\+\+|\bcpp)\b"),
    ("C#", "csharp", r"(?:\bc#|\bcsharp)\b"),
    ("Rust", "rust", r"\brust\b"),
    ("Redis", "redis", r"\bredis\b"),
    ("Linux", "linux", r"\blinux\b"),
    ("GraphQL", "graphql", r"\bgraphql\b"),
    ("Kafka", "kafka", r"\bkafka\b|\bapache\s+kafka\b"),
    ("CI/CD", "ci_cd", r"\bci/cd\b|\bci-cd\b|\bcontinuous\s+integration\b"),
    ("REST API", "rest_api", r"\brest(?:ful)?(?:\s+api)?\b"),
    ("MongoDB", "mongodb", r"\bmongodb\b|\bmongo\b"),
    ("Elasticsearch", "elasticsearch", r"\belasticsearch\b"),
    ("HTML", "html", r"\bhtml5?\b"),
    ("CSS", "css", r"\bcss3?\b"),
]

# -----------------------------------------------------------------------------
# 2. Education Qualifications
# -----------------------------------------------------------------------------
EDUCATION_ENTRIES: list[tuple[str, str, str]] = [
    (
        "Bachelor's Degree",
        "bachelors_degree",
        r"\b(?:bachelor'?s(?:\s+degree)?|b\.?s\.?c?|b\.?a\.?|undergraduate(?:\s+degree)?|lisans)\b",
    ),
    (
        "Master's Degree",
        "masters_degree",
        r"\b(?:master'?s(?:\s+degree)?|m\.?s\.?c?|m\.?a\.?|graduate(?:\s+degree)?|yüksek\s+lisans)\b",
    ),
    (
        "PhD",
        "phd",
        r"\b(?:ph\.?d\.?|doctorate|doktora)\b",
    ),
    (
        "Computer Science",
        "computer_science",
        r"\bcomputer\s+science\b",
    ),
    (
        "Computer Engineering",
        "computer_engineering",
        r"\bcomputer\s+engineering\b|\bbilgisayar\s+mühendisliği\b",
    ),
    (
        "Mathematics",
        "mathematics",
        r"\bmathematics\b|\bapplied\s+mathematics\b|\bmatematik\b",
    ),
]

# -----------------------------------------------------------------------------
# 3. Languages
# -----------------------------------------------------------------------------
LANGUAGE_ENTRIES: list[tuple[str, str, str]] = [
    ("English", "english", r"\benglish\b|\bingilizce\b"),
    ("German", "german", r"\bgerman\b|\balmanca\b"),
    ("Turkish", "turkish", r"\bturkish\b|\btürkçe\b"),
    ("French", "french", r"\bfrench\b|\bfransızca\b"),
    ("Spanish", "spanish", r"\bspanish\b|\bispanyolca\b"),
]

# -----------------------------------------------------------------------------
# 4. Certifications
# -----------------------------------------------------------------------------
CERTIFICATION_ENTRIES: list[tuple[str, str, str]] = [
    ("AWS Certified", "aws_certified", r"\baws\s+certified(?:\s+[\w\s]+)?\b"),
    (
        "Certified Kubernetes Administrator (CKA)",
        "cka",
        r"\b(?:cka|ckad|certified\s+kubernetes\s+administrator)\b",
    ),
    (
        "Project Management Professional (PMP)",
        "pmp",
        r"\b(?:pmp|project\s+management\s+professional)\b",
    ),
    ("CISSP", "cissp", r"\bcissp\b"),
]


def compile_taxonomy() -> list[TaxonomyEntry]:
    """Compile all deterministic taxonomy entries into pre-compiled objects."""
    entries: list[TaxonomyEntry] = []

    for name, key, pat in TECHNICAL_SKILLS:
        entries.append(
            TaxonomyEntry(
                canonical_name=name,
                canonical_key=key,
                category=RequirementType.SKILL,
                pattern=re.compile(pat, re.IGNORECASE),
            )
        )

    for name, key, pat in EDUCATION_ENTRIES:
        entries.append(
            TaxonomyEntry(
                canonical_name=name,
                canonical_key=key,
                category=RequirementType.EDUCATION,
                pattern=re.compile(pat, re.IGNORECASE),
            )
        )

    for name, key, pat in LANGUAGE_ENTRIES:
        entries.append(
            TaxonomyEntry(
                canonical_name=name,
                canonical_key=key,
                category=RequirementType.LANGUAGE,
                pattern=re.compile(pat, re.IGNORECASE),
            )
        )

    for name, key, pat in CERTIFICATION_ENTRIES:
        entries.append(
            TaxonomyEntry(
                canonical_name=name,
                canonical_key=key,
                category=RequirementType.CERTIFICATION,
                pattern=re.compile(pat, re.IGNORECASE),
            )
        )

    return entries


# Experience pattern with named groups to guard against false positives
# Matches "2+ years", "at least 3 years", "minimum 1 year", "3-5 years of experience"
EXPERIENCE_PATTERN = re.compile(
    r"(?i)\b(?:(?P<prefix>at\s+least|minimum|min\.?)\s+)?"
    r"(?P<years>\d+(?:\s*-\s*\d+)?)"
    r"(?P<plus>\+)?"
    r"\s*years?(?:\s+(?:of|in))?(?:\s+[\w/]+)?(?P<exp>\s+experience)?\b"
)
