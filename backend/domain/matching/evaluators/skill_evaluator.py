"""Deterministic skill category evaluator."""

from __future__ import annotations

from decimal import Decimal

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import RequirementLevel, RequirementType
from backend.domain.matching.category_weights import SKILLS_WEIGHT
from backend.domain.matching.enums import MatchStatus
from backend.domain.matching.evaluators.base import (
    CategoryEvaluationResult,
    CategoryEvaluator,
    EvaluatedRequirement,
)
from backend.domain.matching.normalization import normalize_skill
from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile


class SkillEvaluator(CategoryEvaluator):
    """Deterministic evaluator for technical skills."""

    def evaluate(
        self,
        job: Job,
        requirements: list[JobRequirement],
        base_profile: BaseProfile,
        search_profile: SearchProfile,
    ) -> CategoryEvaluationResult:
        """Compare Job skill requirements against profile skills and projects."""
        # 1. Collect all candidate skill evidence into normalized lookup dict
        # Map: normalized_skill -> (original_name, source_type)
        candidate_skills: dict[str, tuple[str, str]] = {}

        # From BaseProfile primary skills
        for s in base_profile.skills:
            if s.name and s.name.strip():
                norm = normalize_skill(s.name)
                candidate_skills[norm] = (s.name, "BaseProfile.skills")

        # From SearchProfile target skills
        for s in search_profile.target_skills:
            if s and s.strip():
                norm = normalize_skill(s)
                if norm not in candidate_skills:
                    candidate_skills[norm] = (s, "SearchProfile.target_skills")

        # From ProfileExperience skills_used
        for exp in base_profile.experiences:
            for s in exp.skills_used:
                if s and s.strip():
                    norm = normalize_skill(s)
                    if norm not in candidate_skills:
                        candidate_skills[norm] = (
                            s,
                            f"ProfileExperience ({exp.company})",
                        )

        # From ProfileProject skills_used
        for proj in base_profile.projects:
            for s in proj.skills_used:
                if s and s.strip():
                    norm = normalize_skill(s)
                    if norm not in candidate_skills:
                        candidate_skills[norm] = (
                            s,
                            f"ProfileProject ({proj.title})",
                        )

        profile_has_skills = bool(candidate_skills)

        # 2. Filter requirements for SKILL category
        skill_reqs = [r for r in requirements if r.type == RequirementType.SKILL]

        # Edge case: No skill requirements parsed for job
        if not skill_reqs:
            return CategoryEvaluationResult(
                category="SKILLS",
                status=MatchStatus.UNKNOWN,
                score=Decimal("1.00"),
                weight=SKILLS_WEIGHT,
                reason="Job does not specify explicit technical skill requirements.",
                details=["No structured skill requirements found on job posting."],
                total_signals=1,
                known_signals=0,
            )

        evaluated_reqs: list[EvaluatedRequirement] = []
        matched_skills: list[str] = []
        missing_skills: list[str] = []
        partial_skills: list[str] = []

        total_weight = Decimal("0.00")
        weighted_score_sum = Decimal("0.00")
        known_signals = 0

        for req in skill_reqs:
            # Deterministic requirement skill key
            target_name = (
                req.normalized_skill.strip()
                if req.normalized_skill and req.normalized_skill.strip()
                else req.description.strip()
            )
            norm_target = normalize_skill(target_name)

            # Determine priority & blocker status
            is_blocker = (
                req.criticality.upper() in ("BLOCKER", "CRITICAL")
                or req.importance.upper() == "BLOCKER"
            )

            # Weight by required_level and importance
            req_weight = Decimal("1.00")
            if req.required_level == RequirementLevel.PREFERRED:
                req_weight *= Decimal("0.50")

            imp = req.importance.upper()
            if imp == "HIGH":
                req_weight *= Decimal("1.50")
            elif imp == "LOW":
                req_weight *= Decimal("0.50")

            if not profile_has_skills:
                # Profile has zero skill evidence
                status = MatchStatus.UNKNOWN
                score = Decimal("0.50")
                reason = "Profile contains no recorded skills to evaluate requirement."
                evidence = None
            elif norm_target in candidate_skills:
                # Direct or alias normalized match
                orig_name, source_desc = candidate_skills[norm_target]
                status = MatchStatus.MATCHED
                score = Decimal("1.00")
                reason = (
                    f"Skill '{target_name}' satisfied by profile skill '{orig_name}'."
                )
                evidence = f"Found in {source_desc}: '{orig_name}'"
                matched_skills.append(target_name)
                known_signals += 1
            else:
                # Skill is missing from profile
                status = MatchStatus.NOT_MATCHED
                score = Decimal("0.00")
                reason = (
                    f"Required skill '{target_name}' was not found in profile "
                    "skills, experiences, or projects."
                )
                evidence = None
                missing_skills.append(target_name)
                known_signals += 1

            evaluated_reqs.append(
                EvaluatedRequirement(
                    requirement_id=req.id,
                    match_status=status,
                    score=score,
                    reason=reason,
                    evidence=evidence,
                    is_blocker=is_blocker,
                )
            )

            total_weight += req_weight
            weighted_score_sum += score * req_weight

        # Compute normalized category score (0.00 - 1.00)
        if total_weight > Decimal("0.00"):
            category_score = (weighted_score_sum / total_weight).quantize(
                Decimal("0.01")
            )
        else:
            category_score = Decimal("0.00")

        # Determine category-level status
        if not profile_has_skills:
            category_status = MatchStatus.UNKNOWN
            category_reason = "Profile has no skills recorded."
        elif not missing_skills:
            category_status = MatchStatus.MATCHED
            category_reason = f"All {len(matched_skills)} skill requirements satisfied."
        elif matched_skills and missing_skills:
            category_status = MatchStatus.PARTIAL
            matched_sample = ", ".join(matched_skills[:3])
            missing_sample = ", ".join(missing_skills[:3])
            category_reason = (
                f"{len(matched_skills)} skills matched ({matched_sample}), "
                f"{len(missing_skills)} missing ({missing_sample})."
            )
        else:
            category_status = MatchStatus.NOT_MATCHED
            missing_sample = ", ".join(missing_skills[:3])
            category_reason = (
                f"None of the required skills ({missing_sample}) were found in profile."
            )

        details: list[str] = []
        if matched_skills:
            details.append(f"Matched skills: {', '.join(matched_skills)}")
        if missing_skills:
            details.append(f"Missing skills: {', '.join(missing_skills)}")
        if partial_skills:
            details.append(f"Partial skills: {', '.join(partial_skills)}")

        return CategoryEvaluationResult(
            category="SKILLS",
            status=category_status,
            score=category_score,
            weight=SKILLS_WEIGHT,
            reason=category_reason,
            evaluated_requirements=evaluated_reqs,
            details=details,
            total_signals=len(skill_reqs),
            known_signals=known_signals,
        )
