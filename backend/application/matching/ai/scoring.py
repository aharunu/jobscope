"""Deterministic guardrails around an untrusted aggregate AI score."""

from decimal import ROUND_HALF_UP, Decimal

DEFAULT_AI_ADJUSTMENT_ALPHA = Decimal("0.25")


def clamp(value, lower, upper):
    return max(Decimal(str(lower)), min(Decimal(str(upper)), Decimal(str(value))))


def rounded(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_scores(
    deterministic,
    ai_score,
    baseline_confidence,
    valid_count,
    total_count,
    blocked=False,
):
    coverage = (
        Decimal(valid_count) / Decimal(total_count) if total_count else Decimal(0)
    )
    # An aggregate score cannot be attributed to individual claims. Reject its
    # entire influence if ANY claim is unsupported rather than weighting fiction.
    adjustment = (
        clamp((ai_score - deterministic) * DEFAULT_AI_ADJUSTMENT_ALPHA, -8, 8)
        if total_count and valid_count == total_count
        else Decimal(0)
    )
    if blocked:
        adjustment = min(Decimal(0), adjustment)
    adjustment = rounded(adjustment)
    final = rounded(clamp(deterministic + adjustment, 0, 100))
    # Existing deterministic evidence confidence captures missing category data.
    # Verified evidence may fill part of that uncertainty; disagreement alone
    # never penalizes confidence. No provider confidence is accepted.
    confidence = rounded(
        clamp(
            baseline_confidence
            + (Decimal(100) - baseline_confidence) * coverage * Decimal("0.25"),
            0,
            100,
        )
    )
    return adjustment, final, confidence
