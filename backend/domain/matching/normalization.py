"""Deterministic normalization utilities for job matching."""

from __future__ import annotations

import re

# Deterministic alias mapping for technical skills
SKILL_ALIASES: dict[str, str] = {
    "postgres": "postgresql",
    "pgsql": "postgresql",
    "k8s": "kubernetes",
    "golang": "go",
    "js": "javascript",
    "ts": "typescript",
    "tf": "tensorflow",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node",
    "node.js": "node",
    "vuejs": "vue",
    "vue.js": "vue",
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "google cloud": "gcp",
    "microsoft azure": "azure",
    "restful api": "rest api",
    "restful": "rest api",
    "rest": "rest api",
    "c++": "cpp",
    "c#": "csharp",
    "dotnet": ".net",
    "ci-cd": "ci/cd",
    "continuous integration": "ci/cd",
}

# Stopwords for role title token overlap
TITLE_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "for",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "junior",
        "jr",
        "senior",
        "sr",
        "mid",
        "middle",
        "lead",
        "principal",
        "staff",
        "head",
        "entry",
        "level",
        "intern",
        "internship",
        "i",
        "ii",
        "iii",
        "iv",
        "v",
    }
)

# Regex to detect required years of experience in requirement descriptions
_EXPERIENCE_RE = re.compile(
    r"(?i)\b(?:(?:at\s+least|minimum|min\.?)\s+)?"
    r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*\+?"
    r"\s*years?(?:\s+(?:of|in))?(?:\s+[\w/]+)?(?:\s+experience)?\b"
)


def normalize_skill(name: str) -> str:
    """Normalize a skill name deterministically with alias resolution."""
    cleaned = name.strip().lower()
    # Normalize punctuation separators
    cleaned = re.sub(r"[\s_]+", " ", cleaned).strip()
    return SKILL_ALIASES.get(cleaned, cleaned)


def normalize_title(title: str) -> str:
    """Normalize a job or role title deterministically."""
    cleaned = title.strip().lower()
    # Remove special punctuation like brackets, parentheses, pipes, dashes
    cleaned = re.sub(r"[()\[\]/\\|–—\-]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def tokenize_title(title: str) -> set[str]:
    """Tokenize a title into meaningful normalized role tokens without stopwords."""
    norm = normalize_title(title)
    tokens = {t for t in re.findall(r"\b[a-z0-9+#.]+\b", norm) if len(t) > 1}
    return tokens - TITLE_STOPWORDS


def extract_required_years(description: str) -> float | None:
    """Deterministically extract minimum required years from requirement text."""
    match = _EXPERIENCE_RE.search(description)
    if not match:
        return None
    min_years_str = match.group(1)
    try:
        return float(min_years_str)
    except (ValueError, TypeError):
        return None


def normalize_location(location: str | None) -> str:
    """Normalize location string for deterministic matching."""
    if not location:
        return ""
    cleaned = location.strip().lower()
    cleaned = re.sub(r"[,/\\|–—\-]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()
