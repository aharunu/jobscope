"""Task-local detail enrichment choices, supplied by acquisition callers."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from backend.application.job_discovery.dtos import DiscoveredJobDTO


@dataclass(frozen=True)
class DetailPlan:
    preview: bool = False
    reject_without_detail: Callable[[DiscoveredJobDTO], bool] | None = None
    country_codes: tuple[str, ...] = ()

    def defer(self, summary: DiscoveredJobDTO | None) -> str | None:
        if summary is None:
            return None
        if self.preview:
            return "PREVIEW"
        if self.reject_without_detail and self.reject_without_detail(summary):
            return "COUNTRY_POLICY"
        return None


current_detail_plan: ContextVar[DetailPlan | None] = ContextVar(
    "acquisition_detail_plan", default=None
)


def acquisition_countries() -> tuple[str, ...]:
    """Only callers with an active policy excluding unknown geography opt in."""
    plan = current_detail_plan.get()
    return plan.country_codes if plan else ()


@contextmanager
def detail_scope(plan: DetailPlan) -> Iterator[None]:
    token = current_detail_plan.set(plan)
    try:
        yield
    finally:
        current_detail_plan.reset(token)
