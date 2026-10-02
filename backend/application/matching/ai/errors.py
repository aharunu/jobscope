"""Public AI failures never include provider exceptions or input payloads."""

from backend.application.common.exceptions import JobScopeError


class AIError(JobScopeError):
    def __init__(self, code="AI_PROVIDER_UNAVAILABLE", status_code=503):
        messages = {
            "AI_PROVIDER_NOT_CONFIGURED": "Optional AI provider is not configured.",
            "AI_PROVIDER_TIMEOUT": "AI provider timed out. Please retry explicitly.",
            "AI_RATE_LIMITED": "AI provider is rate limited. Please retry later.",
            "AI_INVALID_OUTPUT": "AI provider returned an invalid structured analysis.",
            "AI_REFUSED": "AI provider could not analyze this input.",
            "AI_INPUT_TOO_LARGE": "Context exceeds the AI analysis size limit.",
        }
        super().__init__(
            messages.get(code, "AI analysis is temporarily unavailable."),
            code=code,
            status_code=status_code,
        )
