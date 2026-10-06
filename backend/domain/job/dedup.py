"""Explainable, conservative cross-source vacancy comparison. No I/O or AI."""

import html
import re
import unicodedata
from dataclasses import dataclass

from backend.domain.job.entities import Job


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return " ".join(re.findall(r"\w+", value, flags=re.UNICODE))


def words(value: str) -> set[str]:
    return set(normalize(html.unescape(re.sub(r"<[^>]*>", " ", value))).split())


@dataclass(frozen=True)
class DedupDecision:
    score: int
    outcome: str
    signals: dict


def guard_decision(decision, **guards):
    """Coverage/ambiguity guards only demote; they never strengthen evidence."""
    return DedupDecision(
        decision.score,
        "REVIEW"
        if decision.outcome == "AUTO_MERGE" and any(guards.values())
        else decision.outcome,
        {**decision.signals, **guards},
    )


def score_pair(
    left: Job,
    right: Job,
    left_ref=None,
    right_ref=None,
    left_country=None,
    right_country=None,
) -> DedupDecision:
    company = bool(normalize(left.company)) and normalize(left.company) == normalize(
        right.company
    )
    title = normalize(left.title) == normalize(right.title)
    unknown_locations = {"", "unknown", "remote", "worldwide", "anywhere", "global"}
    left_location, right_location = normalize(left.location), normalize(right.location)
    known_locations = (
        left_location not in unknown_locations
        and right_location not in unknown_locations
    )
    location = known_locations and left_location == right_location
    location_conflict = known_locations and not location
    ref_equal = bool(left_ref and right_ref) and normalize(left_ref) == normalize(
        right_ref
    )
    ref_conflict = bool(left_ref and right_ref) and not ref_equal
    a, b = words(left.description), words(right.description)
    similarity = len(a & b) / len(a | b) if a | b else 0.0
    substantial = min(len(a), len(b)) >= 40
    same_url = left.canonical_url == right.canonical_url
    country_conflict = bool(
        left_country and right_country and left_country != right_country
    )
    publication_days = (
        abs((left.published_at.date() - right.published_at.date()).days)
        if left.published_at and right.published_at
        else None
    )
    employment_conflict = bool(
        left.employment_type and right.employment_type
    ) and normalize(left.employment_type) != normalize(right.employment_type)
    mode_conflict = bool(left.work_mode and right.work_mode) and normalize(
        left.work_mode
    ) != normalize(right.work_mode)
    description_conflict = substantial and similarity < 0.25
    signals = {
        "company_exact": company,
        "title_exact": title,
        "location_compatible": location,
        "location_conflict": location_conflict,
        "reference_equal": ref_equal,
        "reference_conflict": ref_conflict,
        "same_posting_url": same_url,
        "description_similarity": round(similarity, 4),
        "substantial_descriptions": substantial,
        "description_conflict": description_conflict,
        "employment_conflict": employment_conflict,
        "work_mode_conflict": mode_conflict,
        "country_conflict": country_conflict,
        "country_equal": bool(
            left_country and right_country and left_country == right_country
        ),
        "publication_date_distance_days": publication_days,
    }
    score = (
        30 * company
        + 30 * title
        + 10 * location
        + 20 * (ref_equal or same_url)
        + 10 * (substantial and similarity >= 0.8)
    )
    contradiction = (
        not company
        or not title
        or ref_conflict
        or location_conflict
        or employment_conflict
        or mode_conflict
        or description_conflict
        or country_conflict
    )
    if contradiction:
        outcome = "NEW_JOB"
    elif (
        score >= 90
        and location
        and (ref_equal or same_url)
        and (publication_days is None or publication_days <= 180)
    ):
        outcome = "AUTO_MERGE"
    elif company and title:
        outcome = "REVIEW"
    else:
        outcome = "NEW_JOB"
    return DedupDecision(score, outcome, signals)


def project(target: Job, incoming: Job, *, alternate: bool) -> Job:
    """Preferred source owns corrections; alternate observations only enrich."""
    if not alternate:
        target.title = incoming.title
        target.company = incoming.company
        target.canonical_url = incoming.canonical_url
    # Title-only/missing observations cannot erase full content. Alternate source
    # richness is ranked by cleaned description length; ties preserve preference.
    if (
        incoming.description
        and not (
            len(words(target.description)) >= 40
            and len(words(incoming.description)) < 40
        )
        and (
            not alternate
            or len(
                normalize(html.unescape(re.sub(r"<[^>]*>", " ", incoming.description)))
            )
            > len(normalize(html.unescape(re.sub(r"<[^>]*>", " ", target.description))))
        )
        and normalize(incoming.description) != normalize(incoming.title)
    ):
        target.description = incoming.description
    for key in (
        "responsibilities",
        "location",
        "work_mode",
        "employment_type",
        "salary",
    ):
        value = getattr(incoming, key)
        if key == "location" and normalize(value) in {
            "unknown",
            "remote",
            "worldwide",
            "anywhere",
            "global",
        }:
            continue
        if value and (not alternate or not getattr(target, key)):
            setattr(target, key, value)
    if incoming.published_at and (not alternate or not target.published_at):
        target.published_at = incoming.published_at
    return target
