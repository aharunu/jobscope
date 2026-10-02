"""API routes for deterministic matching."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, HTTPException, Query, status

from backend.application.matching.exceptions import (
    BaseProfileNotFoundError,
    JobNotFoundError,
    SearchProfileNotFoundError,
)
from backend.domain.matching.entities import MatchResult
from backend.interfaces.api.dependencies import MatchingServiceDep
from backend.interfaces.api.dependencies.auth import (
    CurrentUserDep,
    ReadOnlyCurrentUserDep,
)
from backend.interfaces.api.dependencies.matching import AIAnalyzerDep
from backend.interfaces.api.schemas.matching import (
    AIAnalysisResponse,
    AIRequest,
    CategoryExplanationResponse,
    MatchExplanationResponse,
    MatchListResponse,
    MatchRequest,
    MatchResultResponse,
    RequirementMatchResponse,
)

router = APIRouter(prefix="/matches", tags=["Matching"])


@router.post("/{match_result_id}/ai", response_model=MatchResultResponse)
async def analyze_match(
    match_result_id: uuid.UUID,
    analyzer: AIAnalyzerDep,
    current_user_id: ReadOnlyCurrentUserDep,
    force: bool = False,
    payload: AIRequest | None = Body(default=None),
) -> MatchResultResponse:
    result, cached = await analyzer.analyze(match_result_id, current_user_id, force)
    return _to_match_response(result, cached)


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

    return _to_match_response(match_result)


def _to_match_response(
    match_result: MatchResult, cached: bool = True
) -> MatchResultResponse:
    """One transport representation for calculation and persisted retrieval."""
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
        ai_score=match_result.ai_score,
        ai_adjustment=match_result.ai_adjustment,
        ai_analysis=AIAnalysisResponse.model_validate(
            match_result.ai_analysis
        ).model_copy(update={"cached": cached})
        if match_result.ai_analysis
        else None,
        final_score=match_result.final_score,
        confidence=match_result.confidence,
        category_scores=match_result.category_scores,
        requirement_matches=req_matches,
        explanation=explanation_response,
        created_at=match_result.created_at,
        updated_at=match_result.updated_at,
    )


@router.get("/job/{job_id}", response_model=MatchResultResponse)
async def get_saved_match(
    job_id: uuid.UUID,
    search_profile_id: uuid.UUID,
    matching_service: MatchingServiceDep,
    current_user_id: ReadOnlyCurrentUserDep,
) -> MatchResultResponse:
    result = await matching_service.get_saved_match(
        job_id, search_profile_id, current_user_id
    )
    return _to_match_response(result)


@router.get("", response_model=MatchListResponse)
async def list_saved_matches(
    matching_service: MatchingServiceDep,
    current_user_id: ReadOnlyCurrentUserDep,
    job_id: uuid.UUID | None = None,
    search_profile_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MatchListResponse:
    items, total = await matching_service.list_saved_matches(
        current_user_id, job_id, search_profile_id, limit, offset
    )
    return MatchListResponse(
        items=[_to_match_response(result) for result in items],
        total=total,
        limit=limit,
        offset=offset,
    )
