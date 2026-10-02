"""Outbound LLM port; no vendor imports."""

from typing import Protocol


class LLMProvider(Protocol):
    provider: str
    model: str

    async def analyze(self, system: str, context: str, schema: dict) -> str:
        """Return a JSON document, or raise a safe application error."""
