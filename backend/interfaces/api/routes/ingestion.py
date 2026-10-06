"""Ingestion control API; no long-running network work in request handlers."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response

from backend.application.ingestion.runner import IngestionRunner
from backend.application.job_discovery.budget import AcquisitionBudget
from backend.infrastructure.database.crawl_runtime import PostgreSQLCrawlAdmissionGuard
from backend.infrastructure.database.ingestion_store import SQLAlchemyIngestionStore
from backend.infrastructure.database.session import create_session_factory
from backend.interfaces.api.schemas.ingestion import (
    PolicyRequest,
    StartIngestionRequest,
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


def get_runner(request: Request):
    runner = getattr(request.app.state, "ingestion_runner", None)
    if runner is None:
        settings = request.app.state.settings
        engine = request.app.state.db_engine
        runner = IngestionRunner(
            SQLAlchemyIngestionStore(create_session_factory(engine)),
            request.app.state.adapter_registry,
            PostgreSQLCrawlAdmissionGuard(engine),
            lambda: AcquisitionBudget(
                max_requests=settings.crawler_max_source_requests,
                max_bytes=settings.crawler_max_source_bytes,
                max_seconds=settings.crawler_max_source_seconds,
            ),
        )
        request.app.state.ingestion_runner = runner
    return runner


Runner = Annotated[IngestionRunner, Depends(get_runner)]


@router.get("/policies/default")
async def default_policy(runner: Runner):
    return await runner.store.policy()


@router.put("/policies/default")
async def save_default(body: PolicyRequest, runner: Runner):
    return await runner.store.policy(values=body.model_dump())


@router.get("/policies/sources/{source_id}")
async def source_policy(source_id: uuid.UUID, runner: Runner):
    return await runner.store.policy(source_id)


@router.put("/policies/sources/{source_id}")
async def save_source(source_id: uuid.UUID, body: PolicyRequest, runner: Runner):
    return await runner.store.policy(source_id, body.model_dump())


@router.delete("/policies/sources/{source_id}", status_code=204)
async def remove_source(source_id: uuid.UUID, runner: Runner):
    await runner.store.policy(source_id, remove=True)
    return Response(status_code=204)


@router.post("/runs", status_code=202)
async def start_run(body: StartIngestionRequest, runner: Runner):
    return await runner.start(body.model_dump(mode="json"))


@router.get("/runs")
async def list_runs(
    runner: Runner, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)
):
    return await runner.store.list_runs(limit, offset)


@router.get("/runs/{run_id}")
async def run_detail(run_id: uuid.UUID, runner: Runner):
    return await runner.store.detail(run_id)


@router.get("/runs/{run_id}/sources")
async def run_sources(run_id: uuid.UUID, runner: Runner):
    return await runner.store.sources(run_id)


@router.get("/runs/{run_id}/decisions")
async def run_decisions(
    run_id: uuid.UUID,
    runner: Runner,
    decision: Literal["ACCEPTED", "REJECTED"] | None = None,
    source_id: uuid.UUID | None = None,
    reason: str | None = None,
    country: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await runner.store.decisions(
        run_id,
        limit,
        offset,
        decision=decision,
        source_id=source_id,
        reason=reason,
        resolved_country=country,
    )


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: uuid.UUID, runner: Runner):
    return await runner.store.cancel(run_id)
