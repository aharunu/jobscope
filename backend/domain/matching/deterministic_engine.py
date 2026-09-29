"""Deterministic match engine foundation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.matching.entities import (
    CategoryExplanation,
    MatchExplanation,
    MatchResult,
    RequirementMatch,
)
from backend.domain.matching.enums import MatchStatus
from backend.domain.matching.evaluators import (
    CategoryEvaluationResult,
    CategoryEvaluator,
    EducationEvaluator,
    ExperienceEvaluator,
    LocationEvaluator,
    OtherRequirementEvaluator,
    RoleEvaluator,
    SkillEvaluator,
)
from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile

BLOCKER_SCORE_CAP = Decimal("40.00")


@dataclass(slots=True)
class DeterministicMatchEngine:
    """Core deterministic matching engine.

    Orchestrates category evaluators, computes weighted scores, applies blocker caps,
    calculates evidence-based confidence, and produces fully explainable MatchResults.
    """

    role_evaluator: CategoryEvaluator = field(default_factory=RoleEvaluator)
    skill_evaluator: CategoryEvaluator = field(default_factory=SkillEvaluator)
    experience_evaluator: CategoryEvaluator = field(default_factory=ExperienceEvaluator)
    location_evaluator: CategoryEvaluator = field(default_factory=LocationEvaluator)
    education_evaluator: CategoryEvaluator = field(default_factory=EducationEvaluator)
    other_evaluator: CategoryEvaluator = field(
        default_factory=OtherRequirementEvaluator
    )

    def evaluate(
        self,
        job: Job,
        base_profile: BaseProfile,
        search_profile: SearchProfile,
        requirements: list[JobRequirement] | None = None,
    ) -> MatchResult:
        """Execute deterministic evaluation between Job and Candidate Profile."""
        # Use provided requirements or fallback to job.requirements
        job_reqs = requirements if requirements is not None else list(job.requirements)

        match_result_id = uuid.uuid4()
        now = datetime.now(UTC)

        # 1. Run all category evaluators
        evaluators = [
            self.role_evaluator,
            self.skill_evaluator,
            self.experience_evaluator,
            self.location_evaluator,
            self.education_evaluator,
            self.other_evaluator,
        ]

        category_results: list[CategoryEvaluationResult] = [
            ev.evaluate(
                job=job,
                requirements=job_reqs,
                base_profile=base_profile,
                search_profile=search_profile,
            )
            for ev in evaluators
        ]

        # 2. Extract category scores and requirement matches
        category_scores: dict[str, Decimal] = {}
        category_explanations: dict[str, CategoryExplanation] = {}
        requirement_matches: list[RequirementMatch] = []

        total_weighted_score = Decimal("0.00")
        total_signals = 0
        known_signals = 0
        unmet_blockers: list[str] = []
        unknown_reasons: list[str] = []

        matched_skills: list[str] = []
        missing_skills: list[str] = []
        partial_matches: list[str] = []

        role_result = ""
        experience_result = ""
        education_result = ""
        location_result = ""

        for res in category_results:
            category_scores[res.category] = res.score
            category_explanations[res.category] = CategoryExplanation(
                category=res.category,
                status=res.status,
                score=res.score,
                reason=res.reason,
                details=list(res.details),
            )

            total_weighted_score += res.score * res.weight
            total_signals += res.total_signals
            known_signals += res.known_signals

            if res.status == MatchStatus.UNKNOWN:
                unknown_reasons.append(f"{res.category}: {res.reason}")

            if res.category == "ROLE":
                role_result = res.reason
            elif res.category == "EXPERIENCE":
                experience_result = res.reason
            elif res.category == "EDUCATION":
                education_result = res.reason
            elif res.category == "LOCATION_WORK_MODE":
                location_result = res.reason

            # Process individual requirement evaluations
            for eq in res.evaluated_requirements:
                if eq.is_blocker and eq.match_status == MatchStatus.NOT_MATCHED:
                    unmet_blockers.append(eq.reason)

                if res.category == "SKILLS":
                    for d in res.details:
                        if d.startswith("Matched skills:") and not matched_skills:
                            matched_skills.extend(
                                [
                                    s.strip()
                                    for s in d.replace("Matched skills:", "").split(",")
                                    if s.strip()
                                ]
                            )
                        elif d.startswith("Missing skills:") and not missing_skills:
                            missing_skills.extend(
                                [
                                    s.strip()
                                    for s in d.replace("Missing skills:", "").split(",")
                                    if s.strip()
                                ]
                            )

                if eq.match_status == MatchStatus.PARTIAL:
                    partial_matches.append(eq.reason)

                requirement_matches.append(
                    RequirementMatch(
                        id=uuid.uuid4(),
                        match_result_id=match_result_id,
                        requirement_id=eq.requirement_id,
                        match_status=eq.match_status,
                        score=eq.score,
                        reason=eq.reason,
                        evidence=eq.evidence,
                        is_blocker=eq.is_blocker,
                    )
                )

        # 3. Overall match score computation (0 - 100)
        overall_score = (total_weighted_score * Decimal("100.00")).quantize(
            Decimal("0.01")
        )
        overall_score = max(Decimal("0.00"), min(Decimal("100.00"), overall_score))

        # 4. Explicit Blocker enforcement
        # If any blocker requirement is NOT_MATCHED, overall score is capped
        if unmet_blockers:
            overall_score = min(overall_score, BLOCKER_SCORE_CAP)

        # 5. Deterministic Confidence calculation (0.00 - 100.00%)
        if total_signals > 0:
            confidence = (
                Decimal(str(known_signals))
                / Decimal(str(total_signals))
                * Decimal("100.00")
            ).quantize(Decimal("0.01"))
        else:
            confidence = Decimal("50.00")
        confidence = max(Decimal("0.00"), min(Decimal("100.00"), confidence))

        # 6. Structured explanation assembly
        summary_parts = [
            f"Overall deterministic score: {overall_score}/100.",
            f"Confidence: {confidence}%.",
        ]
        if unmet_blockers:
            count = len(unmet_blockers)
            summary_parts.append(
                f"Score capped at {BLOCKER_SCORE_CAP} due to {count} unmet blocker(s)."
            )
        if unknown_reasons:
            summary_parts.append(
                f"{len(unknown_reasons)} category signal(s) had incomplete information."
            )

        explanation = MatchExplanation(
            summary=" ".join(summary_parts),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            partial_matches=partial_matches,
            role_result=role_result,
            experience_result=experience_result,
            education_result=education_result,
            location_result=location_result,
            blockers=unmet_blockers,
            unknowns=unknown_reasons,
            category_explanations=category_explanations,
        )

        return MatchResult(
            id=match_result_id,
            job_id=job.id,
            base_profile_id=base_profile.id,
            search_profile_id=search_profile.id,
            deterministic_score=overall_score,
            final_score=overall_score,
            confidence=confidence,
            category_scores=category_scores,
            requirement_matches=requirement_matches,
            explanation=explanation,
            created_at=now,
            updated_at=now,
        )
