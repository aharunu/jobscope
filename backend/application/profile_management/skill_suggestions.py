"""Bounded read-only suggestions from the existing extraction vocabulary."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillSuggestions:
    names: tuple[str, ...]

    def search(self, query: str, limit: int = 20) -> list[str]:
        query = " ".join(query.split()).casefold()
        unique = {
            " ".join(name.split()).casefold(): " ".join(name.split())
            for name in self.names
            if name.strip()
        }
        matches = [name for key, name in unique.items() if query in key]
        return sorted(
            matches,
            key=lambda name: (not name.casefold().startswith(query), name.casefold()),
        )[: max(0, min(limit, 20))]
