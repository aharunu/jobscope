"""Domain URL normalization utility for job sources."""

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Set of query parameters considered marketing/tracking that should be removed
TRACKING_PARAMS: frozenset[str] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    }
)


def normalize_source_url(url: str) -> str:
    """Normalize a source URL into a deterministic canonical representation.

    Rules:
    1. Strip leading and trailing whitespace.
    2. Ensure an HTTP/HTTPS scheme is present (defaults to https://).
    3. Lowercase scheme and hostname.
    4. Strip URL fragments (#...).
    5. Strip tracking query parameters (utm_*, ref, source, fbclid, gclid).
    6. Sort remaining query parameters for deterministic equivalence.
    7. Strip trailing slashes from path (except when path is empty or root).
    """
    if not url:
        return ""

    cleaned = url.strip()
    if not cleaned:
        return ""

    # Ensure scheme
    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"

    try:
        parsed = urlparse(cleaned)
    except ValueError:
        return ""

    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()

    # If scheme was present but netloc ended up in path, handle safely
    if not netloc and parsed.path:
        # e.g., "http:////" or similar
        return cleaned

    # Normalize path: strip trailing slash if longer than 1 character
    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Normalize query parameters
    query = ""
    if parsed.query:
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        filtered_items = [
            (k, v) for k, v in query_items if k.lower() not in TRACKING_PARAMS
        ]
        filtered_items.sort(key=lambda item: item[0])
        query = urlencode(filtered_items)

    # Omit fragments entirely
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))
