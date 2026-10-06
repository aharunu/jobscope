"""Resolve country filters from this board's public CXS envelope, never fixed IDs."""

import re

from backend.application.ingestion.policy import ALIASES, folded


def country_facets(root: dict, countries: tuple[str, ...]) -> dict | None:
    """None means unproven mapping; empty dict means reconciled zero matches."""
    if any(code not in ALIASES for code in countries):
        return None  # Unknown/localized labels must never be interpreted as zero jobs.
    pending = [(root.get("facets"), 0)]
    matches = []
    while pending:
        nodes, depth = pending.pop()
        if not isinstance(nodes, list) or depth > 4:
            continue
        for node in nodes:
            if not isinstance(node, dict):
                continue
            key = node.get("facetParameter")
            if isinstance(key, str) and key.replace("_", "").casefold() in {
                "locationcountry",
                "country",
            }:
                matches.append(node)
            else:
                pending.append((node.get("values"), depth + 1))
    if len(matches) != 1:
        return None
    facet = matches[0]
    values = facet.get("values")
    if not isinstance(values, list) or not values:
        return None
    selected, found, seen, total_count = [], set(), set(), 0
    known_labels = {
        folded(name) for code, names in ALIASES.items() for name in [code, *names]
    }
    all_labels_known = True
    for entry in values:
        if not isinstance(entry, dict):
            return None
        identity, label, count = (
            entry.get("id"),
            entry.get("descriptor"),
            entry.get("count"),
        )
        if (
            not isinstance(identity, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identity)
            or identity in seen
            or not isinstance(label, str)
            or type(count) is not int
            or count < 0
        ):
            return None
        seen.add(identity)
        all_labels_known = all_labels_known and folded(label) in known_labels
        total_count += count
        for code in countries:
            names = [code, *ALIASES.get(code, [])]
            if folded(label) in {folded(name) for name in names}:
                selected.append(identity)
                found.add(code)
    # Missing requested labels could mean an incomplete/localized facet list.
    # Only a reconciled population permits interpreting those as zero matches.
    reconciled = type(root.get("total")) is int and total_count == root["total"]
    if found != set(countries) and not (reconciled and all_labels_known):
        return None
    return {facet["facetParameter"]: list(dict.fromkeys(selected))} if selected else {}
