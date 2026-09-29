"""Deterministic location and work mode category evaluator."""

from __future__ import annotations

from decimal import Decimal

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.matching.category_weights import LOCATION_WORK_MODE_WEIGHT
from backend.domain.matching.enums import MatchStatus
from backend.domain.matching.evaluators.base import (
    CategoryEvaluationResult,
    CategoryEvaluator,
)
from backend.domain.matching.normalization import normalize_location
from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile


class LocationEvaluator(CategoryEvaluator):
    """Deterministic evaluator for geographic location and work mode compatibility."""

    def evaluate(
        self,
        job: Job,
        requirements: list[JobRequirement],
        base_profile: BaseProfile,
        search_profile: SearchProfile,
    ) -> CategoryEvaluationResult:
        """Compare Job location/work_mode against SearchProfile preferences."""
        job_loc_raw = job.location.strip() if job.location else ""
        job_mode_raw = job.work_mode.strip() if job.work_mode else ""

        pref_locs = [
            loc.strip() for loc in search_profile.locations if loc and loc.strip()
        ]
        pref_modes = [
            m.strip().lower() for m in search_profile.work_modes if m and m.strip()
        ]

        # Case 1: Missing metadata -> UNKNOWN (Do not penalize as NOT_MATCHED)
        if not job_loc_raw and not job_mode_raw:
            return CategoryEvaluationResult(
                category="LOCATION_WORK_MODE",
                status=MatchStatus.UNKNOWN,
                score=Decimal("0.50"),
                weight=LOCATION_WORK_MODE_WEIGHT,
                reason="Job posting does not specify location or work mode metadata.",
                details=["Location and work mode are absent on job posting."],
                total_signals=1,
                known_signals=0,
            )

        if not pref_locs and not pref_modes:
            return CategoryEvaluationResult(
                category="LOCATION_WORK_MODE",
                status=MatchStatus.UNKNOWN,
                score=Decimal("0.50"),
                weight=LOCATION_WORK_MODE_WEIGHT,
                reason="Search profile contains no location or work mode preferences.",
                details=["No preferences configured on search profile."],
                total_signals=1,
                known_signals=0,
            )

        norm_job_loc = normalize_location(job_loc_raw)
        norm_job_mode = job_mode_raw.lower()

        # Is job remote?
        job_is_remote = "remote" in norm_job_mode or "remote" in norm_job_loc
        candidate_accepts_remote = any("remote" in m for m in pref_modes) or any(
            "remote" in normalize_location(loc_pref) for loc_pref in pref_locs
        )

        # 1. Work Mode match determination
        mode_evaluated = False
        mode_matched = False
        if norm_job_mode and pref_modes:
            mode_evaluated = True
            if (
                job_is_remote
                and candidate_accepts_remote
                or norm_job_mode in pref_modes
                or "hybrid" in norm_job_mode
                and any("hybrid" in m for m in pref_modes)
                or ("on-site" in norm_job_mode or "onsite" in norm_job_mode)
                and any("on-site" in m or "onsite" in m for m in pref_modes)
            ):
                mode_matched = True

        # 2. Location match determination
        loc_evaluated = False
        loc_matched = False
        if norm_job_loc and pref_locs:
            loc_evaluated = True
            if job_is_remote and candidate_accepts_remote:
                loc_matched = True
            else:
                for pl in pref_locs:
                    norm_pl = normalize_location(pl)
                    if norm_pl and (norm_pl in norm_job_loc or norm_job_loc in norm_pl):
                        loc_matched = True
                        break

        # 3. Combine results
        details = []
        if job_loc_raw:
            details.append(f"Job location: {job_loc_raw}")
        if job_mode_raw:
            details.append(f"Job work mode: {job_mode_raw}")
        if pref_locs:
            details.append(f"Preferred locations: {', '.join(pref_locs)}")
        if pref_modes:
            details.append(f"Preferred work modes: {', '.join(pref_modes)}")

        if job_is_remote and candidate_accepts_remote:
            return CategoryEvaluationResult(
                category="LOCATION_WORK_MODE",
                status=MatchStatus.MATCHED,
                score=Decimal("1.00"),
                weight=LOCATION_WORK_MODE_WEIGHT,
                reason="Work mode is Remote, matching candidate preference.",
                details=details,
                total_signals=1,
                known_signals=1,
            )

        if mode_evaluated and loc_evaluated:
            if mode_matched and loc_matched:
                st = MatchStatus.MATCHED
                sc = Decimal("1.00")
                reason = "Both location and work mode match candidate preferences."
            elif mode_matched or loc_matched:
                st = MatchStatus.PARTIAL
                sc = Decimal("0.50")
                reason = "Either location or work mode matches, but not both."
            else:
                st = MatchStatus.NOT_MATCHED
                sc = Decimal("0.00")
                reason = "Explicit mismatch on both location and work mode."
        elif mode_evaluated:
            if mode_matched:
                st = MatchStatus.MATCHED
                sc = Decimal("1.00")
                reason = f"Work mode '{job_mode_raw}' matches candidate preference."
            else:
                st = MatchStatus.NOT_MATCHED
                sc = Decimal("0.00")
                modes_str = ", ".join(pref_modes)
                reason = (
                    f"Work mode '{job_mode_raw}' conflicts with preferred "
                    f"modes: {modes_str}."
                )
        elif loc_evaluated:
            if loc_matched:
                st = MatchStatus.MATCHED
                sc = Decimal("1.00")
                reason = f"Location '{job_loc_raw}' matches candidate preference."
            else:
                st = MatchStatus.NOT_MATCHED
                sc = Decimal("0.00")
                locs_str = ", ".join(pref_locs)
                reason = (
                    f"Location '{job_loc_raw}' does not match preferred "
                    f"locations: {locs_str}."
                )
        else:
            st = MatchStatus.UNKNOWN
            sc = Decimal("0.50")
            reason = "Insufficient metadata to compare location/work mode."

        return CategoryEvaluationResult(
            category="LOCATION_WORK_MODE",
            status=st,
            score=sc,
            weight=LOCATION_WORK_MODE_WEIGHT,
            reason=reason,
            details=details,
            total_signals=1,
            known_signals=1 if st != MatchStatus.UNKNOWN else 0,
        )
