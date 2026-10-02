"""One fixed-host HTTP adapter; no SDK, tools, redirects or automatic retries."""

import httpx

from backend.application.matching.ai.errors import AIError


class OpenAIProvider:
    provider = "openai"

    def __init__(
        self,
        key: str,
        model: str,
        timeout: float,
        enabled: bool = False,
        transport=None,
    ):
        self._key = key
        self.model = model
        self.timeout = timeout
        self.enabled = enabled
        self._transport = transport

    async def analyze(self, system: str, context: str, schema: dict) -> str:
        if not self.enabled or not self._key:
            raise AIError("AI_PROVIDER_NOT_CONFIGURED")
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._key}"},
                    json={
                        "model": self.model,
                        "store": False,
                        "max_completion_tokens": 4000,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": context},
                        ],
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "jobscope_analysis",
                                "strict": True,
                                "schema": schema,
                            },
                        },
                    },
                )
            if response.status_code == 429:
                raise AIError("AI_RATE_LIMITED", 429)
            if response.status_code in (401, 403):
                raise AIError("AI_PROVIDER_NOT_CONFIGURED")
            if response.status_code != 200:
                raise AIError()
            choice = response.json()["choices"][0]
            if choice["message"].get("refusal"):
                raise AIError("AI_REFUSED", 422)
            if choice.get("finish_reason") != "stop":
                raise AIError("AI_INVALID_OUTPUT", 502)
            content = choice["message"]["content"]
            if not isinstance(content, str) or len(content) > 200_000:
                raise AIError("AI_INVALID_OUTPUT", 502)
            return content
        except httpx.TimeoutException:
            raise AIError("AI_PROVIDER_TIMEOUT", 504) from None
        except httpx.RequestError:
            raise AIError() from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise AIError("AI_INVALID_OUTPUT", 502) from None
