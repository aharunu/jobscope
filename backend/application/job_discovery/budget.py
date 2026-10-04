"""Source-local acquisition accounting shared by adapters' safe HTTP calls."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from backend.application.job_discovery.exceptions import AdapterExecutionError


@dataclass(slots=True)
class AcquisitionBudget:
    max_requests: int = 1000
    max_bytes: int = 128 * 1024 * 1024
    max_seconds: float = 300
    clock: Callable[[], float] = time.monotonic
    requests: int = 0
    bytes_read: int = 0
    started: float = field(init=False)

    def __post_init__(self) -> None:
        self.started = self.clock()

    def remaining_seconds(self) -> float:
        remaining = self.max_seconds - (self.clock() - self.started)
        if remaining <= 0:
            self.exhausted("duration")
        return remaining

    def before_request(self) -> None:
        self.remaining_seconds()
        if self.requests >= self.max_requests:
            self.exhausted("requests")
        self.requests += 1

    def consume_bytes(self, count: int) -> None:
        self.remaining_seconds()
        self.bytes_read += count
        if self.bytes_read > self.max_bytes:
            self.exhausted("bytes")

    def exhausted(self, reason: str) -> None:
        raise AdapterExecutionError(
            message=f"Source acquisition budget exhausted: {reason}",
            code="ACQUISITION_BUDGET_EXHAUSTED",
            details={
                "reason": reason,
                "requests": self.requests,
                "bytes": self.bytes_read,
            },
        )


current_budget: ContextVar[AcquisitionBudget | None] = ContextVar(
    "acquisition_budget", default=None
)


@contextmanager
def acquisition_scope(budget: AcquisitionBudget) -> Iterator[AcquisitionBudget]:
    """One scope per source, never one scope per page/retry/redirect."""
    if current_budget.get() is not None:
        raise RuntimeError("Acquisition budget cannot be reset inside acquisition")
    token = current_budget.set(budget)
    try:
        yield budget
    finally:
        current_budget.reset(token)
