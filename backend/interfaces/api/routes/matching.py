"""API routes for deterministic matching."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.application.matching.exceptions import (
    BaseProfileNotFoundError,
    JobNotFoundError,
    SearchProfileNotFoundError,
)
from backend.interfaces.api.dependencies import MatchingServiceDep
from backend.interfaces.api.dependencies.auth import CurrentUserDep
from backend.interfaces.api.schemas.matching import (
    CategoryExplanationResponse,
    MatchExplanationResponse,
    MatchRequest,
    MatchResultResponse,
    RequirementMatchResponse,
)

router = APIRouter(prefix="/matches", tags=["Matching"])


@router.post(
    "",
    response_model=MatchResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate deterministic job match",
    description=(
        "Compare a canonical job posting against a search profile and its base profile "
        "using the pure deterministic match engine. Idempotently persists and returns "
        "overall score, category scores, individual evaluations, and explanations."
    ),
)
async def match_job(
    payload: MatchRequest,
    matching_service: MatchingServiceDep,
    current_user_id: CurrentUserDep,
) -> MatchResultResponse:
    """Execute deterministic job matching evaluation."""
    try:
        match_result = await matching_service.match_job(
            job_id=payload.job_id,
            search_profile_id=payload.search_profile_id,
            user_id=current_user_id,
        )

    except JobNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except SearchProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except BaseProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err

    # Transform explanation if present
    explanation_response = None
    if match_result.explanation is not None:
        cat_expl_map = {}
        for (
            cat_name,
            cat_expl,
        ) in match_result.explanation.category_explanations.items():
            cat_expl_map[cat_name] = CategoryExplanationResponse(
                category=cat_expl.category,
                status=cat_expl.status,
                score=cat_expl.score,
                reason=cat_expl.reason,
                details=list(cat_expl.details),
            )

        explanation_response = MatchExplanationResponse(
            summary=match_result.explanation.summary,
            matched_skills=list(match_result.explanation.matched_skills),
            missing_skills=list(match_result.explanation.missing_skills),
            partial_matches=list(match_result.explanation.partial_matches),
            role_result=match_result.explanation.role_result,
            experience_result=match_result.explanation.experience_result,
            education_result=match_result.explanation.education_result,
            location_result=match_result.explanation.location_result,
            blockers=list(match_result.explanation.blockers),
            unknowns=list(match_result.explanation.unknowns),
            category_explanations=cat_expl_map,
        )

    req_matches = [
        RequirementMatchResponse(
            id=rm.id,
            requirement_id=rm.requirement_id,
            match_status=rm.match_status,
            score=rm.score,
            reason=rm.reason,
            evidence=rm.evidence,
            is_blocker=rm.is_blocker,
        )
        for rm in match_result.requirement_matches
    ]

    return MatchResultResponse(
        id=match_result.id,
        job_id=match_result.job_id,
        base_profile_id=match_result.base_profile_id,
        search_profile_id=match_result.search_profile_id,
        overall_score=match_result.final_score,
        deterministic_score=match_result.deterministic_score,
        final_score=match_result.final_score,
        confidence=match_result.confidence,
        category_scores=match_result.category_scores,
        requirement_matches=req_matches,
        explanation=explanation_response,
        created_at=match_result.created_at,
        updated_at=match_result.updated_at,
    )
