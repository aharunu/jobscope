"""Short-lived ingestion transactions. No session escapes to acquisition."""

import logging
import uuid
from dataclasses import asdict, replace
from datetime import UTC, datetime

from sqlalchemy import func, select, update

from backend.application.common.exceptions import JobScopeError
from backend.application.ingestion.policy import PolicySnapshot, resolve_policy
from backend.application.job_discovery.dtos import RuntimeSourceDTO
from backend.domain.source.normalization import normalize_source_url
from backend.infrastructure.database.crawl_persistence import build_ingestion_service
from backend.infrastructure.database.models.ingestion import (
    IngestionDecisionModel as Decision,
)
from backend.infrastructure.database.models.ingestion import (
    IngestionPolicyModel as Policy,
)
from backend.infrastructure.database.models.ingestion import (
    IngestionRunModel as Run,
)
from backend.infrastructure.database.models.ingestion import (
    IngestionSourceRunModel as SourceRun,
)
from backend.infrastructure.database.models.source import SourceModel

COUNT_KEYS = (
    "jobs_discovered",
    "jobs_accepted",
    "jobs_rejected",
    "jobs_created",
    "jobs_updated",
    "jobs_unchanged",
    "jobs_closed",
)
TERMINAL = {"COMPLETED", "PARTIAL", "FAILED", "CANCELLED"}
EXCLUDED_INGESTION_TYPES = ("kariyer_net", "custom")
logger = logging.getLogger(__name__)


def view(model):
    return {
        column.key: getattr(model, column.key)
        for column in model.__table__.columns
        if column.key != "source_snapshot"
    }


def not_found():
    return JobScopeError("Ingestion record not found", "INGESTION_NOT_FOUND", 404)


class SQLAlchemyIngestionStore:
    def __init__(self, factory):
        self.factory = factory

    async def policy(self, source_id=None, values=None, remove=False):
        async with self.factory() as session, session.begin():
            if values is not None or remove:
                await session.execute(select(func.pg_advisory_xact_lock(78743287)))
            if source_id and await session.get(SourceModel, source_id) is None:
                raise not_found()
            row = await session.scalar(
                select(Policy).where(Policy.source_id == source_id)
            )
            if remove:
                if row:
                    await session.delete(row)
                return None
            if values is not None:
                if row is None:
                    row = Policy(source_id=source_id)
                    session.add(row)
                for key in (
                    "allowed_country_codes",
                    "include_unknown_country",
                    "enabled",
                ):
                    setattr(row, key, values[key])
                await session.flush()
            return view(row) if row else None

    async def create_run(self, request):
        async with self.factory() as session, session.begin():
            if await session.scalar(
                select(Run.id).where(Run.status.in_(["PENDING", "RUNNING"]))
            ):
                raise JobScopeError(
                    "An ingestion run is already active", "INGESTION_RUN_BUSY", 409
                )
            preview_policies = {}
            if request.get("from_preview_run_id"):
                preview = await session.get(
                    Run, uuid.UUID(request["from_preview_run_id"])
                )
                if preview is None:
                    raise not_found()
                if (
                    request["mode"] != "PERSIST"
                    or preview.mode != "PREVIEW"
                    or preview.status not in ("COMPLETED", "COMPLETED_WITH_WARNINGS")
                ):
                    raise JobScopeError(
                        "Select a completed preview", "INVALID_INGESTION_PREVIEW", 422
                    )
                previous_units = (
                    await session.scalars(
                        select(SourceRun).where(SourceRun.run_id == preview.id)
                    )
                ).all()
                preview_policies = {
                    unit.source_id: unit.policy_snapshot for unit in previous_units
                }
                if (
                    not preview_policies
                    or len(preview_policies) != preview.sources_total
                ):
                    raise JobScopeError(
                        "Preview source snapshots are incomplete; run a new preview",
                        "INVALID_INGESTION_PREVIEW",
                        422,
                    )
                request = {
                    **request,
                    "source_ids": [str(v) for v in preview_policies],
                    "active_sources_only": preview.scope["active_sources_only"],
                    "ats_types": None,
                }
            ids = [uuid.UUID(v) for v in request.get("source_ids") or []]
            if ids:
                found = set(
                    (
                        await session.scalars(
                            select(SourceModel.id).where(SourceModel.id.in_(ids))
                        )
                    ).all()
                )
                if found != set(ids):
                    raise JobScopeError(
                        "Unknown source IDs", "INVALID_INGESTION_SCOPE", 422
                    )
                if await session.scalar(
                    select(SourceModel.id)
                    .where(
                        SourceModel.id.in_(ids),
                        SourceModel.ats_type.in_(EXCLUDED_INGESTION_TYPES),
                    )
                    .limit(1)
                ):
                    raise JobScopeError(
                        "Kariyer.net/custom sources are not eligible for ingestion",
                        "INVALID_INGESTION_SCOPE",
                        422,
                    )
            if set(request.get("ats_types") or []).intersection(
                EXCLUDED_INGESTION_TYPES
            ):
                raise JobScopeError(
                    "Kariyer.net/custom are not eligible for ingestion",
                    "INVALID_INGESTION_SCOPE",
                    422,
                )
            query = (
                select(SourceModel)
                .where(SourceModel.ats_type.not_in(EXCLUDED_INGESTION_TYPES))
                .order_by(SourceModel.name, SourceModel.id)
            )
            if ids:
                query = query.where(SourceModel.id.in_(ids))
            if request["active_sources_only"]:
                query = query.where(SourceModel.active.is_(True))
            if request.get("ats_types"):
                query = query.where(SourceModel.ats_type.in_(request["ats_types"]))
            sources = list((await session.scalars(query)).all())
            if preview_policies and {source.id for source in sources} != set(
                preview_policies
            ):
                raise JobScopeError(
                    "Preview sources are no longer eligible; run a new preview",
                    "INVALID_INGESTION_PREVIEW",
                    422,
                )
            if not sources:
                raise JobScopeError(
                    "No sources match the selected scope",
                    "INVALID_INGESTION_SCOPE",
                    422,
                )
            policies = {
                p.source_id: p for p in (await session.scalars(select(Policy))).all()
            }
            run = Run(
                mode=request["mode"],
                status="PENDING",
                scope=request,
                sources_total=len(sources),
            )
            session.add(run)
            await session.flush()
            units = []
            for source in sources:
                snapshot = (
                    PolicySnapshot(
                        **{
                            **preview_policies[source.id],
                            "allowed_country_codes": tuple(
                                preview_policies[source.id]["allowed_country_codes"]
                            ),
                        }
                    )
                    if preview_policies
                    else resolve_policy(
                        request,
                        view(policies[source.id]) if source.id in policies else None,
                        view(policies[None]) if None in policies else None,
                    )
                )
                runtime = RuntimeSourceDTO.from_domain(source.to_domain())
                data = asdict(runtime)
                data["id"] = str(runtime.id)
                unit = SourceRun(
                    run_id=run.id,
                    source_id=source.id,
                    source_name=source.name,
                    ats_type=source.ats_type,
                    source_snapshot=data,
                    policy_snapshot={
                        **asdict(snapshot),
                        "allowed_country_codes": list(snapshot.allowed_country_codes),
                    },
                )
                session.add(unit)
                units.append((unit.id, runtime, snapshot))
            await session.flush()
            return view(run), units

    async def detail(self, run_id):
        async with self.factory() as session:
            row = await session.get(Run, run_id)
            if row is None:
                raise not_found()
            data = view(row)
            current = await session.scalar(
                select(SourceRun).where(
                    SourceRun.run_id == run_id, SourceRun.status == "RUNNING"
                )
            )
            data["progress"] = {
                "sources_total": row.sources_total,
                "sources_completed": row.sources_completed,
                "sources_succeeded": row.sources_succeeded,
                "sources_partial": row.sources_partial,
                "sources_failed": row.sources_failed,
                "current_source_id": current.source_id if current else None,
                "current_source_name": current.source_name if current else None,
                "percentage": round(100 * row.sources_completed / row.sources_total, 1)
                if row.sources_total
                else 0,
                **{k: getattr(row, k) for k in COUNT_KEYS},
            }
            return data

    async def list_runs(self, limit=20, offset=0):
        async with self.factory() as session:
            rows = (
                await session.scalars(
                    select(Run)
                    .order_by(Run.created_at.desc(), Run.id)
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
            return {
                "items": [view(r) for r in rows],
                "total": await session.scalar(select(func.count()).select_from(Run)),
            }

    async def sources(self, run_id):
        await self.detail(run_id)
        async with self.factory() as session:
            return {
                "items": [
                    view(r)
                    for r in (
                        await session.scalars(
                            select(SourceRun)
                            .where(SourceRun.run_id == run_id)
                            .order_by(SourceRun.created_at, SourceRun.source_name)
                        )
                    ).all()
                ]
            }

    async def decisions(self, run_id, limit=50, offset=0, **filters):
        await self.detail(run_id)
        async with self.factory() as session:
            query = select(Decision).where(Decision.run_id == run_id)
            for key, value in filters.items():
                if value is not None:
                    query = query.where(getattr(Decision, key) == value)
            total = await session.scalar(
                select(func.count()).select_from(query.subquery())
            )
            rows = (
                await session.scalars(
                    query.order_by(Decision.created_at, Decision.id)
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
            return {
                "items": [view(r) for r in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    async def cancel(self, run_id):
        async with self.factory() as session, session.begin():
            run = await session.get(Run, run_id, with_for_update=True)
            if run is None:
                raise not_found()
            if run.status in ("PENDING", "RUNNING") and run.cancel_requested_at is None:
                run.cancel_requested_at = datetime.now(UTC)
                logger.info("ingestion_run_cancel_requested run=%s", run_id)
        return await self.detail(run_id)

    async def mark_running(self, run_id, source_run_id=None):
        async with self.factory() as session, session.begin():
            model = SourceRun if source_run_id else Run
            row = await session.get(model, source_run_id or run_id)
            row.status, row.started_at = "RUNNING", datetime.now(UTC)

    async def complete_source(
        self, run_id, unit_id, source, policy, result, mode, duration
    ):
        async with self.factory() as session, session.begin():
            unit = await session.get(SourceRun, unit_id)
            accepted = []
            invalid_found = False
            for job in result.jobs:
                decision, reason, country = policy.decide(job)
                invalid_found = invalid_found or reason == "INVALID_DISCOVERED_JOB"
                if decision == "ACCEPTED":
                    if mode == "PERSIST" and job.metadata.get(
                        "acquisition_detail_deferred"
                    ):
                        raise JobScopeError(
                            "Required provider details were not acquired",
                            "INGESTION_DETAILS_REQUIRED",
                            502,
                        )
                    accepted.append(job)
                try:
                    url = normalize_source_url(job.url)
                except ValueError:
                    url = ""
                if reason == "INVALID_DISCOVERED_JOB":
                    url = ""
                session.add(
                    Decision(
                        run_id=run_id,
                        source_run_id=unit_id,
                        source_id=source.id,
                        external_job_id=job.external_job_id,
                        title=job.title,
                        canonical_url=url,
                        location=job.metadata.get("location")
                        if isinstance(job.metadata.get("location"), str)
                        else None,
                        resolved_country=country,
                        decision=decision,
                        reason=reason,
                    )
                )
            unit.jobs_discovered, unit.jobs_accepted = (
                len(result.jobs),
                len(accepted),
            )
            unit.jobs_rejected = len(result.jobs) - len(accepted)
            unit.acquisition_complete = result.is_complete
            warnings = list(result.warnings)
            if not result.is_complete and not warnings:
                warnings.append("acquisition_incomplete")
            if invalid_found:
                warnings.append("invalid_discovered_job")
            unit.status = "PARTIAL" if warnings else "COMPLETED"
            unit.closure_suppression_reason = "PREVIEW_MODE"
            if mode == "PERSIST":
                filtered = replace(
                    result,
                    jobs=accepted,
                    warnings=warnings,
                    closure_suppression_reason="INGESTION_POLICY_FILTER_ACTIVE"
                    if policy.active
                    else None,
                )
                ingested = await build_ingestion_service(session).ingest_crawl_result(
                    source, filtered
                )
                for key in (
                    "jobs_created",
                    "jobs_updated",
                    "jobs_unchanged",
                    "jobs_closed",
                ):
                    setattr(unit, key, getattr(ingested, key))
                unit.status = ingested.status.value
                unit.closure_authorized = ingested.closure_authorized
                unit.closure_suppression_reason = ingested.closure_suppression_reason
                warnings = ingested.warnings
                if ingested.errors:
                    # Ingestion errors are central safe codes, never provider prose.
                    safe_errors = sorted(set(ingested.errors))
                    warnings = [*warnings, *safe_errors]
                    unit.error_type = "INGESTION_ITEM_FAILURE"
                    unit.error_message = (
                        f"{ingested.error_count} accepted posting(s) "
                        "could not be processed: " + "; ".join(safe_errors)
                    )
            unit.warnings, unit.warning_count = warnings[:50], len(warnings)
            unit.finished_at, unit.duration_ms = datetime.now(UTC), duration
            logger.info(
                "ingestion_policy_summary run=%s source=%s accepted=%d rejected=%d",
                run_id,
                source.id,
                unit.jobs_accepted,
                unit.jobs_rejected,
            )
            await session.flush()
            await self._aggregate(session, run_id)

    async def fail_source(self, run_id, unit_id, code, duration):
        async with self.factory() as session, session.begin():
            row = await session.get(SourceRun, unit_id)
            row.status, row.error_type = "FAILED", code
            row.error_message = (
                "Source acquisition or ingestion failed; see safe server diagnostics"
            )
            row.finished_at, row.duration_ms = datetime.now(UTC), duration
            row.closure_suppression_reason = "SOURCE_FAILED"
            await session.flush()
            await self._aggregate(session, run_id)

    async def _aggregate(self, session, run_id):
        run = await session.get(Run, run_id)
        rows = list(
            (
                await session.scalars(
                    select(SourceRun).where(SourceRun.run_id == run_id)
                )
            ).all()
        )
        run.sources_completed = sum(r.status in TERMINAL for r in rows)
        run.sources_succeeded = sum(r.status == "COMPLETED" for r in rows)
        run.sources_partial = sum(r.status == "PARTIAL" for r in rows)
        run.sources_failed = sum(r.status == "FAILED" for r in rows)
        for key in COUNT_KEYS:
            setattr(run, key, sum(getattr(r, key) for r in rows))

    async def finish(self, run_id, forced=None):
        async with self.factory() as session, session.begin():
            run = await session.get(Run, run_id, with_for_update=True)
            cancelled = run.cancel_requested_at is not None
            status = forced or (
                "CANCELLED"
                if cancelled
                else "FAILED"
                if run.sources_failed == run.sources_total
                else "COMPLETED_WITH_WARNINGS"
                if run.sources_failed or run.sources_partial
                else "COMPLETED"
            )
            await session.execute(
                update(SourceRun)
                .where(
                    SourceRun.run_id == run_id,
                    SourceRun.status.in_(["PENDING", "RUNNING"]),
                )
                .values(
                    status="CANCELLED" if cancelled else "FAILED",
                    finished_at=datetime.now(UTC),
                    closure_suppression_reason=status,
                )
            )
            await self._aggregate(session, run_id)
            run.status, run.finished_at = status, datetime.now(UTC)

    async def interrupt_stale(self):
        # Caller holds the cross-worker top-level lease, proving no live run.
        async with self.factory() as session, session.begin():
            ids = list(
                (
                    await session.scalars(
                        select(Run.id).where(Run.status.in_(["PENDING", "RUNNING"]))
                    )
                ).all()
            )
            await session.execute(
                update(SourceRun)
                .where(
                    SourceRun.run_id.in_(ids),
                    SourceRun.status.in_(["PENDING", "RUNNING"]),
                )
                .values(
                    status="FAILED",
                    finished_at=datetime.now(UTC),
                    error_type="INTERRUPTED",
                    closure_suppression_reason="INTERRUPTED",
                )
            )
            for run_id in ids:
                await self._aggregate(session, run_id)
            await session.execute(
                update(Run)
                .where(Run.id.in_(ids))
                .values(status="INTERRUPTED", finished_at=datetime.now(UTC))
            )
