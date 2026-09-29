"""Deterministic evaluator for Language, Certification, and Other requirements."""

from __future__ import annotations

from decimal import Decimal

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import RequirementType
from backend.domain.matching.category_weights import OTHER_WEIGHT
from backend.domain.matching.enums import MatchStatus
from backend.domain.matching.evaluators.base import (
    CategoryEvaluationResult,
    CategoryEvaluator,
    EvaluatedRequirement,
)
from backend.domain.matching.normalization import normalize_skill
from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile


class OtherRequirementEvaluator(CategoryEvaluator):
    """Deterministic evaluator for Language, Certification, and Other requirements."""

    def evaluate(
        self,
        job: Job,
        requirements: list[JobRequirement],
        base_profile: BaseProfile,
        search_profile: SearchProfile,
    ) -> CategoryEvaluationResult:
        """Evaluate non-core requirements (Language, Certifications, Other)."""
        other_types = {
            RequirementType.LANGUAGE,
            RequirementType.CERTIFICATION,
            RequirementType.OTHER,
        }
        target_reqs = [r for r in requirements if r.type in other_types]

        if not target_reqs:
            return CategoryEvaluationResult(
                category="OTHER",
                status=MatchStatus.UNKNOWN,
                score=Decimal("1.00"),
                weight=OTHER_WEIGHT,
                reason=(
                    "Job specifies no language, certification, or other requirements."
                ),
                details=["No Language, Certification, or Other requirements found."],
                total_signals=0,
                known_signals=0,
            )

        # Profile pool for language & certifications
        profile_skills_norm = {
            normalize_skill(s.name): s.name
            for s in base_profile.skills
            if s.name and s.name.strip()
        }
        has_profile_skills = bool(profile_skills_norm)

        evaluated_reqs: list[EvaluatedRequirement] = []
        scores: list[Decimal] = []
        statuses: list[MatchStatus] = []
        known_count = 0

        for req in target_reqs:
            is_blocker = (
                req.criticality.upper() in ("BLOCKER", "CRITICAL")
                or req.importance.upper() == "BLOCKER"
            )
            target_str = (
                req.normalized_skill.strip()
                if req.normalized_skill and req.normalized_skill.strip()
                else req.description.strip()
            )
            norm_target = normalize_skill(target_str)

            if req.type == RequirementType.LANGUAGE:
                if not has_profile_skills:
                    st = MatchStatus.UNKNOWN
                    sc = Decimal("0.50")
                    reason = (
                        "Profile has no skill/language entries to evaluate "
                        f"'{target_str}'."
                    )
                    evidence = None
                elif norm_target in profile_skills_norm:
                    st = MatchStatus.MATCHED
                    sc = Decimal("1.00")
                    matched_lang = profile_skills_norm[norm_target]
                    reason = (
                        f"Language requirement '{target_str}' satisfied by "
                        f"profile skill '{matched_lang}'."
                    )
                    evidence = f"Language verified: {matched_lang}"
                    known_count += 1
                else:
                    st = MatchStatus.NOT_MATCHED
                    sc = Decimal("0.00")
                    reason = (
                        f"Language '{target_str}' not listed in candidate "
                        "profile skills."
                    )
                    evidence = None
                    known_count += 1

            elif req.type == RequirementType.CERTIFICATION:
                if not has_profile_skills:
                    st = MatchStatus.UNKNOWN
                    sc = Decimal("0.50")
                    reason = (
                        "Profile contains no certification records to evaluate "
                        f"'{target_str}'."
                    )
                    evidence = None
                elif norm_target in profile_skills_norm:
                    st = MatchStatus.MATCHED
                    sc = Decimal("1.00")
                    reason = f"Certification '{target_str}' found in candidate profile."
                    evidence = (
                        f"Verified certification: {profile_skills_norm[norm_target]}"
                    )
                    known_count += 1
                else:
                    st = MatchStatus.NOT_MATCHED
                    sc = Decimal("0.00")
                    reason = (
                        f"Certification '{target_str}' not found in candidate profile."
                    )
                    evidence = None
                    known_count += 1

            else:  # RequirementType.OTHER
                # General requirement without automated objective verification
                st = MatchStatus.UNKNOWN
                sc = Decimal("0.50")
                reason = (
                    f"Requirement '{req.description}' requires qualitative evaluation."
                )
                evidence = None

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
            cat_reason = "All language/certification/other requirements satisfied."
        elif any(s == MatchStatus.NOT_MATCHED for s in statuses):
            cat_status = (
                MatchStatus.NOT_MATCHED
                if avg_score < Decimal("0.40")
                else MatchStatus.PARTIAL
            )
            cat_reason = "One or more secondary requirements not satisfied."
        elif any(s == MatchStatus.UNKNOWN for s in statuses):
            cat_status = MatchStatus.UNKNOWN
            cat_reason = "Secondary requirements have incomplete evidence."
        else:
            cat_status = MatchStatus.PARTIAL
            cat_reason = "Secondary requirements partially satisfied."

        return CategoryEvaluationResult(
            category="OTHER",
            status=cat_status,
            score=avg_score,
            weight=OTHER_WEIGHT,
            reason=cat_reason,
            evaluated_requirements=evaluated_reqs,
            details=[f"Evaluated {len(target_reqs)} secondary/language requirements."],
            total_signals=len(target_reqs),
            known_signals=known_count,
        )
