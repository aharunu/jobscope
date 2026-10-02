"""Mock HTTP adapter checks; no external network or paid requests."""

import json

import httpx
import pytest

from backend.application.matching.ai.errors import AIError
from backend.application.matching.ai.schema import AIOutput
from backend.infrastructure.llm.fake_provider import FakeProvider
from backend.infrastructure.llm.openai_provider import OpenAIProvider


@pytest.mark.asyncio
async def test_adapter_fixed_host_strict_schema_no_tools_and_private_key(caplog):
    def respond(request):
        assert str(request.url) == "https://api.openai.com/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert payload["store"] is False and "tools" not in payload
        assert payload["messages"][0]["role"] == "system"
        assert request.headers["Authorization"] == "Bearer PRIVATE_TEST_VALUE"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps(FakeProvider().output)},
                    }
                ]
            },
        )

    provider = OpenAIProvider(
        "PRIVATE_TEST_VALUE",
        "gpt-4.1-mini-2025-04-14",
        30,
        True,
        httpx.MockTransport(respond),
    )
    output = await provider.analyze(
        "Instructions", "Private profile", AIOutput.model_json_schema()
    )
    assert AIOutput.model_validate_json(output).ai_score == 94
    assert (
        "PRIVATE_TEST_VALUE" not in caplog.text and "Private profile" not in caplog.text
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,code,status",
    [
        ("timeout", "AI_PROVIDER_TIMEOUT", 504),
        ("network", "AI_PROVIDER_UNAVAILABLE", 503),
        (429, "AI_RATE_LIMITED", 429),
        (401, "AI_PROVIDER_NOT_CONFIGURED", 503),
        (500, "AI_PROVIDER_UNAVAILABLE", 503),
        (302, "AI_PROVIDER_UNAVAILABLE", 503),
        ("refusal", "AI_REFUSED", 422),
        ("invalid", "AI_INVALID_OUTPUT", 502),
        ("truncated", "AI_INVALID_OUTPUT", 502),
    ],
)
async def test_provider_failure_categories_never_leak_raw_payload(
    failure, code, status
):
    calls = []

    def respond(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("PRIVATE_TEST_VALUE", request=request)
        if failure == "network":
            raise httpx.ConnectError("PRIVATE_TEST_VALUE", request=request)
        if isinstance(failure, int):
            return httpx.Response(failure, json={"error": "PRIVATE_TEST_VALUE"})
        if failure == "refusal":
            return httpx.Response(
                200, json={"choices": [{"message": {"refusal": "PRIVATE_TEST_VALUE"}}]}
            )
        if failure == "truncated":
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {"content": "PRIVATE_TEST_VALUE"},
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"wrong": "PRIVATE_TEST_VALUE"})

    provider = OpenAIProvider(
        "PRIVATE_TEST_VALUE", "test-model", 1, True, httpx.MockTransport(respond)
    )
    with pytest.raises(AIError) as caught:
        await provider.analyze("system", "input", {})
    assert caught.value.code == code and caught.value.status_code == status
    assert "PRIVATE_TEST_VALUE" not in str(caught.value)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled,key", [(False, "PRIVATE_TEST_VALUE"), (True, "")])
async def test_optional_disabled_or_missing_key_never_sends_request(enabled, key):
    def no_http(request):
        raise AssertionError("Must not send HTTP")

    provider = OpenAIProvider(
        key, "test-model", 1, enabled, httpx.MockTransport(no_http)
    )
    with pytest.raises(AIError, match="not configured"):
        await provider.analyze("system", "input", {})
