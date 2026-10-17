"""Shared literal search semantics for database predicates and excerpts."""

import re


def parse_search_query(query: str) -> tuple[str, bool]:
    query = query.strip()
    if len(query) >= 2 and query.startswith('"') and query.endswith('"'):
        term = query[1:-1].strip()
        if term:
            return term, True
    return query, False


def search_regex(query: str) -> str:
    term, exact = parse_search_query(query)
    literal = re.escape(term)
    return rf"(?<!\w){literal}(?!\w)" if exact else literal
