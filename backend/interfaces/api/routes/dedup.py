"""Explicit review endpoints; no merge occurs on GET."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict

from backend.infrastructure.database.dedup_review import SQLAlchemyDedupReview
from backend.interfaces.api.dependencies.database import DbSession

router = APIRouter(prefix="/dedup/candidates", tags=["Dedup review"])


class MergeConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirm: Literal[True]


@router.get("")
async def candidates(
    session: DbSession,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    pending: bool = True,
):
    return await SQLAlchemyDedupReview(session).listing(limit, offset, pending)


@router.get("/{candidate_id}")
async def candidate(candidate_id: UUID, session: DbSession):
    return await SQLAlchemyDedupReview(session).detail(candidate_id)


@router.post("/{candidate_id}/merge")
async def merge(candidate_id: UUID, body: MergeConfirmation, session: DbSession):
    return await SQLAlchemyDedupReview(session).resolve(candidate_id, merge=True)


@router.post("/{candidate_id}/keep-separate")
async def keep(candidate_id: UUID, session: DbSession):
    return await SQLAlchemyDedupReview(session).resolve(candidate_id)
