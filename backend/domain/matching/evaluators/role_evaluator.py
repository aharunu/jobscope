"""Deterministic role category evaluator."""

from __future__ import annotations

from decimal import Decimal

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.matching.category_weights import ROLE_WEIGHT
from backend.domain.matching.enums import MatchStatus
from backend.domain.matching.evaluators.base import (
    CategoryEvaluationResult,
    CategoryEvaluator,
)
from backend.domain.matching.normalization import (
    normalize_title,
    tokenize_title,
)
from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile


class RoleEvaluator(CategoryEvaluator):
    """Deterministic evaluator for role compatibility."""

    def evaluate(
        self,
        job: Job,
        requirements: list[JobRequirement],
        base_profile: BaseProfile,
        search_profile: SearchProfile,
    ) -> CategoryEvaluationResult:
        """Compare Job title against SearchProfile target and preferred roles."""
        job_title = job.title.strip() if job.title else ""
        target_roles = [r.strip() for r in search_profile.target_roles if r.strip()]

        if not job_title or not target_roles:
            return CategoryEvaluationResult(
                category="ROLE",
                status=MatchStatus.UNKNOWN,
                score=Decimal("0.50"),
                weight=ROLE_WEIGHT,
                reason="Insufficient role data available for deterministic evaluation.",
                details=["Job title or profile target roles are missing."],
                total_signals=1,
                known_signals=0,
            )

        norm_job_title = normalize_title(job_title)
        norm_target_roles = [normalize_title(r) for r in target_roles]

        # 1. Exact normalized title match against any target/preferred role
        for orig_role, norm_role in zip(target_roles, norm_target_roles, strict=False):
            if norm_job_title == norm_role:
                return CategoryEvaluationResult(
                    category="ROLE",
                    status=MatchStatus.MATCHED,
                    score=Decimal("1.00"),
                    weight=ROLE_WEIGHT,
                    reason=(
                        f"Job title '{job_title}' exactly matches "
                        f"target role '{orig_role}'."
                    ),
                    details=[f"Exact match on role: {orig_role}"],
                    total_signals=1,
                    known_signals=1,
                )

        # 2. Token overlap analysis
        job_tokens = tokenize_title(job_title)
        best_score = Decimal("0.00")
        best_status = MatchStatus.NOT_MATCHED
        targets_str = ", ".join(target_roles)
        best_reason = (
            f"Job title '{job_title}' does not match target roles: {targets_str}."
        )
        best_details: list[str] = []

        for orig_role in target_roles:
            role_tokens = tokenize_title(orig_role)
            if not job_tokens or not role_tokens:
                continue

            overlap = job_tokens & role_tokens
            if not overlap:
                continue

            overlap_str = ", ".join(sorted(overlap))
            # Subsumption match (e.g. "Software Engineer" in "Senior Software Engineer")
            if overlap in (role_tokens, job_tokens):
                score = Decimal("1.00")
                status = MatchStatus.MATCHED
                reason = (
                    f"Job title '{job_title}' closely matches target role "
                    f"'{orig_role}' with key tokens: {overlap_str}."
                )
            else:
                # Fractional token overlap
                ratio = len(overlap) / max(len(job_tokens), len(role_tokens))
                overlap_str = ", ".join(sorted(overlap))
                if ratio >= 0.5:
                    score = Decimal("0.70")
                    status = MatchStatus.PARTIAL
                    reason = (
                        f"Job title '{job_title}' partially matches target "
                        f"role '{orig_role}' with shared tokens: {overlap_str}."
                    )
                else:
                    score = Decimal("0.40")
                    status = MatchStatus.PARTIAL
                    reason = (
                        f"Job title '{job_title}' has minor token overlap with "
                        f"target role '{orig_role}' on tokens: {overlap_str}."
                    )

            if score > best_score:
                best_score = score
                best_status = status
                best_reason = reason
                best_details = [
                    f"Role evaluated: {orig_role}",
                    f"Matched tokens: {', '.join(sorted(overlap))}",
                ]

        return CategoryEvaluationResult(
            category="ROLE",
            status=best_status,
            score=best_score,
            weight=ROLE_WEIGHT,
            reason=best_reason,
            details=best_details
            or [f"Target roles checked: {', '.join(target_roles)}"],
            total_signals=1,
            known_signals=1,
        )
