"""Custom endpoint configuration and unchanged strict AI guardrails, offline."""

import json

import httpx
import pytest
from pydantic import ValidationError

from backend.application.matching.ai.schema import AIOutput
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.llm.fake_provider import FakeProvider
from backend.infrastructure.llm.openai_provider import OpenAIProvider
from backend.interfaces.api.dependencies.matching import get_ai_provider
from tests.test_ai_matching_phase_3 import setup_match
from tests.test_match_retrieval_phase_2 import database_api as database_api
from tests.test_match_retrieval_phase_2 import pg_session as pg_session


def completion(content):
    return httpx.Response(
        200,
        json={"choices": [{"finish_reason": "stop", "message": {"content": content}}]},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["", "/"])
async def test_custom_url_placeholder_and_strict_request(suffix, caplog):
    def respond(request):
        assert str(request.url) == "http://127.0.0.1:1234/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer lm-studio"
        payload = json.loads(request.content)
        assert payload["model"] == "exact-local-model-id"
        assert payload["response_format"]["json_schema"] == {
            "name": "jobscope_analysis",
            "strict": True,
            "schema": AIOutput.model_json_schema(),
        }
        assert payload["store"] is False
        assert payload["max_completion_tokens"] == 4000
        assert "tools" not in payload
        return completion(json.dumps(FakeProvider().output))

    provider = OpenAIProvider(
        "lm-studio",
        "exact-local-model-id",
        30,
        True,
        httpx.MockTransport(respond),
        base_url="http://127.0.0.1:1234/v1" + suffix,
    )
    output = await provider.analyze(
        "system", "PRIVATE_SYNTHETIC_INPUT", AIOutput.model_json_schema()
    )
    assert AIOutput.model_validate_json(output).ai_score == 94
    assert "PRIVATE_SYNTHETIC_INPUT" not in caplog.text


@pytest.mark.parametrize("value", [None, "", "  "])
def test_blank_setting_keeps_hosted_default(value):
    settings = Settings(_env_file=None, ai_base_url=value, openai_api_key="test")
    provider = get_ai_provider(settings)
    assert provider._base_url == "https://api.openai.com/v1"
    assert provider.cache_identity == "openai"


def test_environment_setting_reaches_dependency(monkeypatch):
    monkeypatch.setenv("AI_BASE_URL", "http://127.0.0.1:1234/v1/")
    monkeypatch.setenv("OPENAI_API_KEY", "lm-studio")
    monkeypatch.setenv("AI_MODEL", "exact-local-model-id")
    monkeypatch.setenv("AI_ENABLED", "true")
    provider = get_ai_provider(Settings(_env_file=None))
    assert provider._base_url == "http://127.0.0.1:1234/v1"
    assert provider.model == "exact-local-model-id"
    assert provider.enabled and provider._key == "lm-studio"


@pytest.mark.parametrize(
    "value",
    [
        "file:///tmp/model",
        "http://",
        "http://user:password@host/v1",
        "https://host/v1?key=secret",
        "https://host/v1#fragment",
    ],
)
def test_base_url_rejects_credentials_and_non_http_targets(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ai_base_url=value)


def test_endpoint_identity_separates_cache_without_exposing_url():
    hosted = OpenAIProvider("test", "same-model", 30)
    first = OpenAIProvider("test", "same-model", 30, base_url="http://server-a:1234/v1")
    normalized = OpenAIProvider(
        "test", "same-model", 30, base_url="http://server-a:1234/v1/"
    )
    other = OpenAIProvider("test", "same-model", 30, base_url="http://server-b:1234/v1")
    assert first.cache_identity == normalized.cache_identity
    assert len({hosted.cache_identity, first.cache_identity, other.cache_identity}) == 3
    assert "server-a" not in first.cache_identity


@pytest.mark.asyncio
async def test_custom_endpoint_still_requires_explicit_key():
    def no_http(request):
        raise AssertionError("Missing key must not send HTTP")

    from backend.application.matching.ai.errors import AIError

    provider = OpenAIProvider(
        "",
        "local-model",
        30,
        True,
        httpx.MockTransport(no_http),
        base_url="http://127.0.0.1:1234/v1",
    )
    with pytest.raises(AIError, match="not configured"):
        await provider.analyze("system", "synthetic", {})


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["network", "malformed", "extra-field", "wrong-type"])
async def test_local_failure_or_invalid_output_preserves_deterministic(
    database_api, kind
):
    client, app, _, headers, match, _ = await setup_match(database_api)
    calls = []

    def respond(request):
        calls.append(request)
        assert str(request.url).startswith("http://127.0.0.1:1234/v1/")
        if kind == "network":
            raise httpx.ConnectError("PRIVATE_LOCAL_ERROR", request=request)
        if kind == "malformed":
            return completion("not JSON PRIVATE_LOCAL_ERROR")
        changes = {"final_score": 100} if kind == "extra-field" else {"ai_score": "90"}
        return completion(json.dumps(FakeProvider().output | changes))

    provider = OpenAIProvider(
        "lm-studio",
        "exact-local-model-id",
        30,
        True,
        httpx.MockTransport(respond),
        base_url="http://127.0.0.1:1234/v1",
    )
    app.dependency_overrides[get_ai_provider] = lambda: provider
    lookup = (
        f"/api/matches/job/{match['job_id']}"
        f"?search_profile_id={match['search_profile_id']}"
    )
    assert (await client.get(lookup, headers=headers)).json() == match
    assert not calls  # Retrieval never triggers local inference.
    response = await client.post(f"/api/matches/{match['id']}/ai", headers=headers)
    assert response.status_code == (503 if kind == "network" else 502)
    assert response.json()["error"]["code"] == (
        "AI_PROVIDER_UNAVAILABLE" if kind == "network" else "AI_INVALID_OUTPUT"
    )
    assert "PRIVATE_LOCAL_ERROR" not in response.text
    assert (await client.get(lookup, headers=headers)).json() == match
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_changing_endpoint_invalidates_cached_analysis(database_api):
    client, app, _, headers, match, _ = await setup_match(database_api)
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return completion(json.dumps(FakeProvider().output))

    def provider(base):
        return OpenAIProvider(
            "test", "same-model", 30, True, httpx.MockTransport(respond), base_url=base
        )

    first = provider("http://server-a:1234/v1")
    app.dependency_overrides[get_ai_provider] = lambda: first
    path = f"/api/matches/{match['id']}/ai"
    assert (await client.post(path, headers=headers)).json()["ai_analysis"][
        "cached"
    ] is False
    assert (await client.post(path, headers=headers)).json()["ai_analysis"][
        "cached"
    ] is True
    second = provider("http://server-b:1234/v1")
    app.dependency_overrides[get_ai_provider] = lambda: second
    assert (await client.post(path, headers=headers)).json()["ai_analysis"][
        "cached"
    ] is False
    assert len(calls) == 2
