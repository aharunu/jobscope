"""Small shared validation helpers for public provider postings."""

from __future__ import annotations

import urllib.parse
from typing import Any

from backend.infrastructure.ats.runtime_config import TOKEN_PATTERN


def text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    return None


def posting_identity(value: Any) -> str | None:
    """Accept real scalar references, never stringify containers/booleans."""
    if type(value) is int and value > 0:
        return str(value)
    if isinstance(value, str):
        candidate = value.strip()
        if TOKEN_PATTERN.fullmatch(candidate):
            return candidate
    return None


def valid_posting_fields(
    item: dict[str, Any],
    title_key: str,
    *url_keys: str,
    text_keys: tuple[str, ...] = (),
) -> bool:
    for key in (title_key, *text_keys):
        value = item.get(key)
        if value is not None and not isinstance(value, str):
            return False
    for key in url_keys:
        value = item.get(key)
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            return False
        try:
            url = urllib.parse.urlsplit(value.strip())
            if (
                url.scheme not in {"https", "http"}
                or not url.hostname
                or url.username
                or url.password
            ):
                return False
        except ValueError:
            return False
    return True
