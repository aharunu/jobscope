"""Unit tests for domain URL normalization."""

from backend.domain.source.normalization import normalize_source_url


def test_normalize_trailing_slash_stripped() -> None:
    """Verify trailing slashes are stripped from path."""
    assert (
        normalize_source_url("https://example.com/careers/")
        == "https://example.com/careers"
    )
    assert (
        normalize_source_url("https://example.com/jobs/dev/")
        == "https://example.com/jobs/dev"
    )


def test_normalize_root_slash_preserved() -> None:
    """Verify root slash or bare domain preserves clean base."""
    assert normalize_source_url("https://example.com/") == "https://example.com/"
    assert normalize_source_url("https://example.com") == "https://example.com"


def test_normalize_case_folding() -> None:
    """Verify scheme and netloc are lowercased while path case is preserved."""
    assert (
        normalize_source_url("HTTPS://JOBS.LEVER.CO/Trendyol/Openings")
        == "https://jobs.lever.co/Trendyol/Openings"
    )


def test_normalize_strip_tracking_query_params() -> None:
    """Verify marketing tracking query parameters are removed."""
    url = (
        "https://example.com/careers"
        "?utm_source=linkedin&utm_medium=cpc&utm_campaign=spring"
        "&ref=jobboard&source=feed&fbclid=xyz&gclid=123"
    )
    assert normalize_source_url(url) == "https://example.com/careers"


def test_normalize_preserve_and_sort_functional_params() -> None:
    """Verify non-tracking query parameters are preserved and sorted."""
    url = "https://career5.successfactors.eu/career?company=Koc&locale=tr_TR&jobId=99"
    normalized = normalize_source_url(url)
    assert (
        normalized
        == "https://career5.successfactors.eu/career?company=Koc&jobId=99&locale=tr_TR"
    )


def test_normalize_mixed_tracking_and_functional_params() -> None:
    """Verify tracking parameters are filtered out while functional ones remain."""
    url = (
        "https://example.com/jobs"
        "?utm_source=twitter&locale=en_US&utm_medium=social&siteId=10"
    )
    normalized = normalize_source_url(url)
    assert normalized == "https://example.com/jobs?locale=en_US&siteId=10"


def test_normalize_fragment_stripped() -> None:
    """Verify URL fragments are stripped."""
    assert (
        normalize_source_url("https://example.com/jobs#apply-now")
        == "https://example.com/jobs"
    )


def test_normalize_missing_scheme_defaults_to_https() -> None:
    """Verify URLs without scheme default to https."""
    assert (
        normalize_source_url("career5.successfactors.eu/career?company=koc")
        == "https://career5.successfactors.eu/career?company=koc"
    )


def test_normalize_idempotency() -> None:
    """Verify normalizing an already-normalized URL is completely idempotent."""
    raw = "  HTTPS://jobs.lever.co/trendyol/?utm_source=li#top  "
    first = normalize_source_url(raw)
    second = normalize_source_url(first)
    assert first == "https://jobs.lever.co/trendyol"
    assert first == second


def test_normalize_empty_and_whitespace() -> None:
    """Verify empty or whitespace strings return empty string safely."""
    assert normalize_source_url("") == ""
    assert normalize_source_url("   ") == ""


def test_normalize_malformed_url_safety() -> None:
    """Verify malformed strings do not cause unhandled exceptions."""
    assert normalize_source_url("http://[invalid-ipv6") == ""
