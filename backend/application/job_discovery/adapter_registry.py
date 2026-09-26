"""ATS adapter registry for dynamic adapter resolution."""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.job_discovery.exceptions import (
    AdapterUnavailableError,
    UnsupportedATSError,
)
from backend.application.job_discovery.ports import ATSAdapter
from backend.domain.source.enums import is_known_ats_type


class ATSAdapterRegistry:
    """In-memory registry managing ATS adapter instances mapped by ats_type."""

    def __init__(self, adapters: Sequence[ATSAdapter] | None = None) -> None:
        self._adapters: dict[str, ATSAdapter] = {}
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: ATSAdapter) -> None:
        """Register an adapter instance keyed by its normalized ats_type."""
        key = adapter.ats_type.strip().lower()
        self._adapters[key] = adapter

    def get_adapter(self, ats_type: str) -> ATSAdapter:
        """Resolve adapter for the specified ATS type or raise explicit errors."""
        key = ats_type.strip().lower()
        if key in self._adapters:
            return self._adapters[key]

        if is_known_ats_type(key):
            raise AdapterUnavailableError(
                message=f"No adapter is registered for known ATS platform '{key}'.",
                code="ADAPTER_UNAVAILABLE",
                details={"ats_type": key},
            )
        raise UnsupportedATSError(
            message=f"Unsupported ATS platform type '{key}'.",
            code="UNSUPPORTED_ATS_TYPE",
            details={"ats_type": key},
        )

    def is_supported(self, ats_type: str) -> bool:
        """Check whether an active adapter is currently registered for this ATS."""
        return ats_type.strip().lower() in self._adapters

    def list_supported_types(self) -> list[str]:
        """Return deterministic sorted list of registered ATS types."""
        return sorted(self._adapters.keys())
