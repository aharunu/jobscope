"""Durable, sequential background execution with cooperative cancellation."""

import asyncio
import logging
import time
import uuid
from typing import Protocol

from backend.application.common.exceptions import JobScopeError
from backend.application.job_discovery.budget import acquisition_scope
from backend.application.job_discovery.exceptions import SourceBusyError

logger = logging.getLogger(__name__)
INGESTION_LEASE_ID = uuid.UUID("d8eb7b14-8c39-5c23-a12a-9b1000000004")


class IngestionStore(Protocol):
    async def create_run(self, request): ...
    async def detail(self, run_id): ...
    async def mark_running(self, run_id, source_run_id=None): ...
    async def complete_source(
        self, run_id, unit_id, source, policy, result, mode, duration
    ): ...
    async def fail_source(self, run_id, unit_id, code, duration): ...
    async def finish(self, run_id, forced=None): ...
    async def interrupt_stale(self): ...
    async def cancel(self, run_id): ...


class IngestionRunner:
    def __init__(self, store: IngestionStore, registry, guard, budget_factory):
        self.store, self.registry, self.guard = store, registry, guard
        self.budget_factory = budget_factory
        self.tasks: dict[uuid.UUID, asyncio.Task] = {}

    async def reconcile(self):
        try:
            async with self.guard.hold(INGESTION_LEASE_ID):
                await self.store.interrupt_stale()
        except SourceBusyError:
            pass  # A different worker is live; it owns those records.

    async def start(self, request):
        lease = self.guard.hold(INGESTION_LEASE_ID)
        try:
            await lease.__aenter__()
        except SourceBusyError as exc:
            raise JobScopeError(
                "An ingestion run is already active", "INGESTION_RUN_BUSY", 409
            ) from exc
        try:
            await self.store.interrupt_stale()
            run, units = await self.store.create_run(request)
            logger.info(
                "ingestion_run_started run=%s mode=%s sources=%d",
                run["id"],
                run["mode"],
                len(units),
            )
            task = asyncio.create_task(self._execute(run, units, lease))
            self.tasks[run["id"]] = task
            task.add_done_callback(lambda _: self.tasks.pop(run["id"], None))
            return run
        except BaseException:
            await lease.__aexit__(None, None, None)
            raise

    async def _execute(self, run, units, lease):
        run_id = run["id"]
        try:
            await self.store.mark_running(run_id)
            for unit_id, source, policy in units:
                if (await self.store.detail(run_id))["cancel_requested_at"]:
                    break
                start = time.perf_counter()
                try:
                    async with self.guard.hold(source.id):
                        await self.store.mark_running(run_id, unit_id)
                        logger.info(
                            "ingestion_source_started run=%s source=%s "
                            "policy=%s filter_active=%s",
                            run_id,
                            source.id,
                            policy.origin,
                            policy.active,
                        )
                        adapter = self.registry.get_adapter(source.ats_type)
                        budget = self.budget_factory()
                        with acquisition_scope(budget):
                            async with asyncio.timeout(budget.remaining_seconds()):
                                result = await adapter.crawl(source)
                                budget.remaining_seconds()
                        await self.store.complete_source(
                            run_id,
                            unit_id,
                            source,
                            policy,
                            result,
                            run["mode"],
                            (time.perf_counter() - start) * 1000,
                        )
                        logger.info(
                            "ingestion_source_completed run=%s source=%s discovered=%d",
                            run_id,
                            source.id,
                            len(result.jobs),
                        )
                except Exception as exc:
                    code = getattr(
                        exc,
                        "code",
                        "SOURCE_TIMEOUT"
                        if isinstance(exc, TimeoutError)
                        else "INGESTION_SOURCE_FAILURE",
                    )
                    logger.warning(
                        "ingestion_source_failed run=%s source=%s type=%s",
                        run_id,
                        source.id,
                        type(exc).__name__,
                    )
                    await self.store.fail_source(
                        run_id, unit_id, code, (time.perf_counter() - start) * 1000
                    )
            await self.store.finish(run_id)
            logger.info("ingestion_run_completed run=%s", run_id)
        except Exception as exc:
            logger.error(
                "ingestion_run_failed run=%s type=%s", run_id, type(exc).__name__
            )
            await self.store.finish(run_id, "FAILED")
        finally:
            await lease.__aexit__(None, None, None)

    async def shutdown(self):
        tasks = list(self.tasks.items())
        for run_id, _ in tasks:
            await self.store.cancel(run_id)
        if tasks:
            await asyncio.gather(*(task for _, task in tasks))
