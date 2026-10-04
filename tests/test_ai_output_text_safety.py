"""Invalid provider text must fail safely before PostgreSQL persistence."""

import copy
import json

import httpx
import pytest
from pydantic import ValidationError

from backend.application.matching.ai.schema import AIOutput
from backend.infrastructure.llm.fake_provider import FakeProvider
from backend.infrastructure.llm.openai_provider import OpenAIProvider
from backend.interfaces.api.dependencies.matching import get_ai_provider
from tests.test_ai_matching_phase_3 import setup_match
from tests.test_match_retrieval_phase_2 import database_api as database_api
from tests.test_match_retrieval_phase_2 import pg_session as pg_session


def nul_output(field):
    output = copy.deepcopy(FakeProvider().output)
    if field in ("strengths", "gaps", "risks"):
        output[field] = ["INVALID_PRIVATE_TEXT\x00"]
    elif field == "summary":
        output[field] = "INVALID_PRIVATE_TEXT\x00"
    else:
        output["evidence"][0][field] = "INVALID_PRIVATE_TEXT\x00"
    return output


@pytest.mark.parametrize(
    "field",
    [
        "summary",
        "strengths",
        "gaps",
        "risks",
        "claim",
        "source_reference",
        "source_quote",
        "reason",
    ],
)
def test_nul_in_any_provider_text_is_rejected(field):
    with pytest.raises(ValidationError):
        AIOutput.model_validate_json(json.dumps(nul_output(field)))


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["summary", "strengths", "claim", "source_quote"])
async def test_invalid_forced_local_output_retains_last_analysis_and_cache(
    database_api, field, caplog
):
    client, app, _, headers, match, _ = await setup_match(database_api)
    output = FakeProvider().output
    calls = 0

    def respond(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps(output)},
                    }
                ]
            },
        )

    provider = OpenAIProvider(
        "lm-studio",
        "test-local-model",
        30,
        True,
        httpx.MockTransport(respond),
        base_url="http://127.0.0.1:1234/v1",
    )
    app.dependency_overrides[get_ai_provider] = lambda: provider
    path = f"/api/matches/{match['id']}/ai"
    lookup = (
        f"/api/matches/job/{match['job_id']}"
        f"?search_profile_id={match['search_profile_id']}"
    )
    successful = await client.post(path + "?force=true", headers=headers)
    assert successful.status_code == 200
    before = (await client.get(lookup, headers=headers)).json()
    output = nul_output(field)
    failed = await client.post(path + "?force=true", headers=headers)
    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "AI_INVALID_OUTPUT"
    assert "INVALID_PRIVATE_TEXT" not in failed.text + caplog.text
    assert (await client.get(lookup, headers=headers)).json() == before
    cached = await client.post(path, headers=headers)
    assert cached.status_code == 200
    assert cached.json()["ai_analysis"]["cached"] is True
    assert calls == 2
    output = FakeProvider().output
    recovered = await client.post(path + "?force=true", headers=headers)
    assert recovered.status_code == 200
    assert recovered.json()["ai_analysis"]["cached"] is False
    assert calls == 3
    assert recovered.json()["deterministic_score"] == match["deterministic_score"]
    assert abs(float(recovered.json()["ai_adjustment"])) <= 8
