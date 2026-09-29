"""Deterministic education category evaluator."""

from __future__ import annotations

import re
from decimal import Decimal

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import RequirementType
from backend.domain.matching.category_weights import EDUCATION_WEIGHT
from backend.domain.matching.enums import MatchStatus
from backend.domain.matching.evaluators.base import (
    CategoryEvaluationResult,
    CategoryEvaluator,
    EvaluatedRequirement,
)
from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile

# Deterministic degree hierarchy ranking
DEGREE_LEVELS: dict[str, int] = {
    "phd": 3,
    "doctorate": 3,
    "doktora": 3,
    "master": 2,
    "masters": 2,
    "msc": 2,
    "ma": 2,
    "graduate": 2,
    "yüksek lisans": 2,
    "bachelor": 1,
    "bachelors": 1,
    "bsc": 1,
    "ba": 1,
    "undergraduate": 1,
    "lisans": 1,
    "associate": 0,
    "ön lisans": 0,
}


def _parse_degree_level(degree_str: str) -> int:
    """Return numeric rank for an educational degree string."""
    cleaned = degree_str.strip().lower()
    for keyword, rank in DEGREE_LEVELS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", cleaned):
            return rank
    return 0


class EducationEvaluator(CategoryEvaluator):
    """Deterministic evaluator for educational qualifications and degrees."""

    def evaluate(
        self,
        job: Job,
        requirements: list[JobRequirement],
        base_profile: BaseProfile,
        search_profile: SearchProfile,
    ) -> CategoryEvaluationResult:
        """Evaluate candidate education background against job requirements."""
        edu_reqs = [r for r in requirements if r.type == RequirementType.EDUCATION]

        # Case 1: Job does not specify education requirements
        if not edu_reqs:
            return CategoryEvaluationResult(
                category="EDUCATION",
                status=MatchStatus.UNKNOWN,
                score=Decimal("1.00"),
                weight=EDUCATION_WEIGHT,
                reason="Job does not specify an education requirement.",
                details=["No explicit education requirements in job posting."],
                total_signals=1,
                known_signals=0,
            )

        candidate_has_edu = bool(base_profile.educations)
        if not candidate_has_edu:
            evaluated_reqs = [
                EvaluatedRequirement(
                    requirement_id=req.id,
                    match_status=MatchStatus.UNKNOWN,
                    score=Decimal("0.50"),
                    reason="Profile contains no education records.",
                    evidence=None,
                    is_blocker=(
                        req.criticality.upper() in ("BLOCKER", "CRITICAL")
                        or req.importance.upper() == "BLOCKER"
                    ),
                )
                for req in edu_reqs
            ]
            return CategoryEvaluationResult(
                category="EDUCATION",
                status=MatchStatus.UNKNOWN,
                score=Decimal("0.50"),
                weight=EDUCATION_WEIGHT,
                reason=(
                    "Profile contains no education records to evaluate requirements."
                ),
                evaluated_requirements=evaluated_reqs,
                details=["Candidate education records are empty."],
                total_signals=len(edu_reqs),
                known_signals=0,
            )

        # Candidate highest degree level and fields of study
        max_candidate_degree = max(
            _parse_degree_level(e.degree) for e in base_profile.educations
        )
        candidate_fields = {
            e.field_of_study.strip().lower()
            for e in base_profile.educations
            if e.field_of_study
        }

        evaluated_reqs = []
        scores: list[Decimal] = []
        statuses: list[MatchStatus] = []

        for req in edu_reqs:
            is_blocker = (
                req.criticality.upper() in ("BLOCKER", "CRITICAL")
                or req.importance.upper() == "BLOCKER"
            )
            req_text = req.description.strip().lower()
            req_degree_level = _parse_degree_level(req_text)

            # Degree level check
            degree_satisfied = max_candidate_degree >= req_degree_level

            # Field check if mentioned in requirement
            field_matched = False
            matching_field_name = ""
            for field in candidate_fields:
                if field in req_text or (
                    req.normalized_skill and field == req.normalized_skill.lower()
                ):
                    field_matched = True
                    matching_field_name = field
                    break

            if degree_satisfied and (field_matched or req_degree_level > 0):
                st = MatchStatus.MATCHED
                sc = Decimal("1.00")
                reason = (
                    f"Candidate education satisfies requirement '{req.description}'."
                )
                evidence = f"Verified degree rank {max_candidate_degree}" + (
                    f" with field: '{matching_field_name}'"
                    if matching_field_name
                    else ""
                )
            elif degree_satisfied or field_matched:
                st = MatchStatus.PARTIAL
                sc = Decimal("0.60")
                reason = (
                    "Candidate education partially matches requirement "
                    f"'{req.description}'."
                )
                evidence = (
                    f"Degree level: {max_candidate_degree}, "
                    f"Field match: {field_matched}"
                )
            else:
                st = MatchStatus.NOT_MATCHED
                sc = Decimal("0.00")
                reason = (
                    "Candidate education does not satisfy requirement "
                    f"'{req.description}'."
                )
                evidence = f"Candidate fields: {', '.join(candidate_fields)}"

            evaluated_reqs.append(
                EvaluatedRequirement(
                    requirement_id=req.id,
                    match_status=st,
                    score=sc,
                    reason=reason,
                    evidence=evidence,
                    is_blocker=is_blocker,
                )
            )
            scores.append(sc)
            statuses.append(st)

        avg_score = (sum(scores) / Decimal(len(scores))).quantize(Decimal("0.01"))
        if all(s == MatchStatus.MATCHED for s in statuses):
            cat_status = MatchStatus.MATCHED
            cat_reason = "All education requirements satisfied."
        elif any(s == MatchStatus.NOT_MATCHED for s in statuses):
            cat_status = (
                MatchStatus.NOT_MATCHED
                if avg_score < Decimal("0.40")
                else MatchStatus.PARTIAL
            )
            cat_reason = "One or more education requirements not fully satisfied."
        else:
            cat_status = MatchStatus.PARTIAL
            cat_reason = "Education requirements partially satisfied."

        return CategoryEvaluationResult(
            category="EDUCATION",
            status=cat_status,
            score=avg_score,
            weight=EDUCATION_WEIGHT,
            reason=cat_reason,
            evaluated_requirements=evaluated_reqs,
            details=[f"Evaluated {len(edu_reqs)} education requirements."],
            total_signals=len(edu_reqs),
            known_signals=len(edu_reqs),
        )
