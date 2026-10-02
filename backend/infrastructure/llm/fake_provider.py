"""Deterministic test adapter; never selected by production dependency injection."""

import json


class FakeProvider:
    provider = "fake"
    model = "test-model"

    def __init__(self, output=None, error=None):
        self.output = (
            output
            if output is not None
            else {
                "ai_score": 94,
                "assessment": "STRONG",
                "summary": "Supplied skill evidence aligns.",
                "strengths": ["Python"],
                "gaps": [],
                "risks": [],
                "evidence": [
                    {
                        "claim": "Python skill recorded",
                        "evidence_type": "SKILL",
                        "source_reference": "profile.skills[0]",
                        "source_quote": "Python",
                        "reason": "The supplied skill names Python.",
                    }
                ],
            }
        )
        self.error = error
        self.calls = 0

    async def analyze(self, system: str, context: str, schema: dict) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        return self.output if isinstance(self.output, str) else json.dumps(self.output)
