"""Deterministic experience category evaluator."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import RequirementType
from backend.domain.matching.category_weights import EXPERIENCE_WEIGHT
from backend.domain.matching.enums import MatchStatus
from backend.domain.matching.evaluators.base import (
    CategoryEvaluationResult,
    CategoryEvaluator,
    EvaluatedRequirement,
)
from backend.domain.matching.normalization import extract_required_years
from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile


class ExperienceEvaluator(CategoryEvaluator):
    """Deterministic evaluator for professional experience duration and seniority."""

    def evaluate(
        self,
        job: Job,
        requirements: list[JobRequirement],
        base_profile: BaseProfile,
        search_profile: SearchProfile,
    ) -> CategoryEvaluationResult:
        """Evaluate candidate experience against job requirements."""
        # 1. Calculate candidate's total years of experience from ProfileExperience
        today = datetime.now(UTC).date()
        total_candidate_days = 0

        for exp in base_profile.experiences:
            start = exp.start_date
            if not start:
                continue
            end = exp.end_date if exp.end_date and not exp.is_current else today
            if end >= start:
                total_candidate_days += (end - start).days

        candidate_has_exp_records = bool(base_profile.experiences)
        candidate_years = round(total_candidate_days / 365.25, 1)

        # 2. Check for explicit EXPERIENCE requirements on job
        exp_reqs = [r for r in requirements if r.type == RequirementType.EXPERIENCE]

        # Case A: Job has no explicit EXPERIENCE requirements
        if not exp_reqs:
            # Fallback check on job description for experience pattern if
            # requirements extractor didn't tag it
            req_years = None
            if job.description:
                req_years = extract_required_years(job.description)

            if req_years is None:
                return CategoryEvaluationResult(
                    category="EXPERIENCE",
                    status=MatchStatus.UNKNOWN,
                    score=Decimal("1.00"),
                    weight=EXPERIENCE_WEIGHT,
                    reason="Job does not specify an explicit experience requirement.",
                    details=[
                        f"Candidate total experience: {candidate_years} years"
                        if candidate_has_exp_records
                        else "No experience records in profile."
                    ],
                    total_signals=1,
                    known_signals=0,
                )

        # Case B: Evaluate each explicit requirement
        evaluated_reqs: list[EvaluatedRequirement] = []
        scores: list[Decimal] = []
        statuses: list[MatchStatus] = []
        known_count = 0

        target_reqs = exp_reqs if exp_reqs else []

        for req in target_reqs:
            is_blocker = (
                req.criticality.upper() in ("BLOCKER", "CRITICAL")
                or req.importance.upper() == "BLOCKER"
            )
            required_years = extract_required_years(req.description)

            if required_years is None:
                # Could not parse numeric years from requirement text
                desc_snippet = req.description[:40]
                evaluated_reqs.append(
                    EvaluatedRequirement(
                        requirement_id=req.id,
                        match_status=MatchStatus.UNKNOWN,
                        score=Decimal("0.50"),
                        reason=f"Could not extract duration from: '{desc_snippet}'.",
                        evidence=None,
                        is_blocker=is_blocker,
                    )
                )
                continue

            if not candidate_has_exp_records:
                evaluated_reqs.append(
                    EvaluatedRequirement(
                        requirement_id=req.id,
                        match_status=MatchStatus.UNKNOWN,
                        score=Decimal("0.50"),
                        reason="Profile contains no work experience entries.",
                        evidence=None,
                        is_blocker=is_blocker,
                    )
                )
                continue

            # Deterministic comparison
            known_count += 1
            if candidate_years >= required_years:
                st = MatchStatus.MATCHED
                sc = Decimal("1.00")
                reason = (
                    f"Candidate has {candidate_years} years experience, satisfying "
                    f"requirement of {required_years}+ years."
                )
                evidence = f"Total verified work experience: {candidate_years} years"
            elif candidate_years >= (required_years * 0.65) or candidate_years >= (
                required_years - 1.0
            ):
                st = MatchStatus.PARTIAL
                ratio = round(candidate_years / required_years, 2)
                sc = Decimal(str(max(0.40, min(0.85, ratio))))
                reason = (
                    f"Candidate has {candidate_years} years experience, "
                    f"partially meeting requirement of {required_years}+ years."
                )
                evidence = (
                    f"Partial duration: {candidate_years} / {required_years} years"
                )
            else:
                st = MatchStatus.NOT_MATCHED
                sc = Decimal("0.00")
                reason = (
                    f"Candidate has {candidate_years} years experience, below "
                    f"requirement of {required_years}+ years."
                )
                evidence = (
                    f"Insufficient duration: {candidate_years} vs {required_years}+ yrs"
                )

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

        if not candidate_has_exp_records and target_reqs:
            return CategoryEvaluationResult(
                category="EXPERIENCE",
                status=MatchStatus.UNKNOWN,
                score=Decimal("0.50"),
                weight=EXPERIENCE_WEIGHT,
                reason="Profile has no experience entries to evaluate requirement.",
                evaluated_requirements=evaluated_reqs,
                details=["Profile has zero experience records."],
                total_signals=len(target_reqs),
                known_signals=0,
            )

        if scores:
            avg_score = (sum(scores) / Decimal(len(scores))).quantize(Decimal("0.01"))
            if all(s == MatchStatus.MATCHED for s in statuses):
                cat_status = MatchStatus.MATCHED
            elif any(s == MatchStatus.NOT_MATCHED for s in statuses):
                cat_status = (
                    MatchStatus.NOT_MATCHED
                    if avg_score < Decimal("0.40")
                    else MatchStatus.PARTIAL
                )
            else:
                cat_status = MatchStatus.PARTIAL

            cat_reason = f"Candidate experience: {candidate_years} years."
        else:
            avg_score = Decimal("0.50")
            cat_status = MatchStatus.UNKNOWN
            cat_reason = "No deterministic experience requirements evaluated."

        return CategoryEvaluationResult(
            category="EXPERIENCE",
            status=cat_status,
            score=avg_score,
            weight=EXPERIENCE_WEIGHT,
            reason=cat_reason,
            evaluated_requirements=evaluated_reqs,
            details=[
                f"Verified experience: {candidate_years} years "
                f"across {len(base_profile.experiences)} positions."
            ],
            total_signals=max(1, len(target_reqs)),
            known_signals=known_count,
        )
