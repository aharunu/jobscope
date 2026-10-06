# Optional AI matching

AI runs only from **AI ile Detaylı Analiz Et** after a persisted deterministic match exists. Opening a job, retrieving matches, switching SearchProfiles, calculating deterministic matching, editing profiles and crawling never call AI. Missing configuration or provider errors leave the deterministic result usable.

Configure the root ignored `.env`, then restart the backend:

```dotenv
AI_ENABLED=true
OPENAI_API_KEY=YOUR_API_KEY
AI_MODEL=gpt-4.1-mini-2025-04-14
AI_TIMEOUT_SECONDS=30
AI_BASE_URL=
```

Leave `AI_BASE_URL` blank for hosted OpenAI. For an OpenAI-compatible local server such as LM Studio, start the server, read its exact chat-model ID from `GET http://127.0.0.1:1234/v1/models`, and configure the ignored root `.env`:

```dotenv
AI_ENABLED=true
AI_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_API_KEY=lm-studio
AI_MODEL=EXACT_CHAT_MODEL_ID_FROM_V1_MODELS
AI_TIMEOUT_SECONDS=120
```

Restart the backend after changing settings. `lm-studio` is a harmless explicit placeholder only for a server with authentication disabled; use the server's actual key when authentication is enabled. No hosted credential is needed for local inference. The base URL must include its API prefix (normally `/v1`) and must not contain credentials, query parameters or fragments. The server must support the existing strict `response_format=json_schema` request and return the complete AI output schema; [LM Studio documents this format](https://lmstudio.ai/docs/developer/openai-compat/structured-output). Invalid/truncated output remains an error, with the deterministic result preserved. Changing endpoints invalidates AI cache even when model IDs are equal. No model/server-specific fallback or relaxed validation is used.

The Next.js API rewrite proxy allows 150 seconds so it can relay the backend's bounded 120-second AI request and transaction overhead. Restart the frontend after updating `next.config.mjs` (rebuild before production start); its former 30-second default could return a proxy 500 while a local model's successful analysis continued in the backend. Provider text containing NUL characters is rejected as `AI_INVALID_OUTPUT` / 502 before persistence; it is never stripped or repaired.

The safe template defaults to disabled AI with an empty key. One OpenAI HTTP adapter uses existing `httpx`; the application depends on a provider Protocol, and automated tests use an offline fake or mock HTTP. The pinned model supports [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) according to its [official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini). Requests have a bounded timeout, no automatic retries, no redirects, no tools, a strict JSON schema and `store=false`.

`POST /api/matches/{id}/ai` accepts no trusted client content; an optional empty JSON object is permitted, other body fields are rejected. The backend loads owned Job, BaseProfile, SearchProfile and the saved deterministic evidence. Successful responses use MatchResultResponse with `ai_score`, `ai_adjustment` and nested `ai_analysis` (assessment, summary, strengths, gaps, risks, evidence, provider/model, created timestamp, `cached`). Detail and collection GET return the same saved analysis without provider calls or writes.

Cache fingerprints use canonical JSON/SHA-256 over semantic job/profile/search/deterministic inputs, provider/model, prompt version and schema version, excluding unrelated IDs/timestamps. One latest AIAnalysis per MatchResult is retained. An identical explicit request returns it with `cached=true`; **Re-analyze AI** sends `force=true`. Profile/job/search changes cause a cache miss on the next explicit request, while GET remains read-only. Deterministic re-evaluation clears the old AI projection/cache transactionally. Simultaneous normal AI requests serialize on the MatchResult row and reuse the committed result; the provider timeout bounds each external call while this lock is held.

The backend uses Decimal arithmetic and two-decimal `ROUND_HALF_UP` rounding:

```text
raw adjustment = clamp((AI score - deterministic score) × 0.25, -8, +8)
final score = clamp(deterministic score + accepted adjustment, 0, 100)
```

Alpha 0.25 is an initial calibration constant. Example: deterministic 86, AI 94 → +2 → final 88. Provider output cannot set final score, adjustment or confidence. Any unsupported evidence (or no evidence) disables the entire aggregate AI adjustment, because its contribution cannot be attributed safely. Unmet deterministic blockers prevent a positive adjustment; deterministic requirements/blockers are never rewritten.

Evidence references must match `profile.skills[i]`, `profile.experiences[i]`, `profile.educations[i]` or `profile.projects[i]` in the canonical prompt order, agree with evidence type, and include an exact source quote of at least three characters. Invalid references/type/quotes become `NONE / INSUFFICIENT_EVIDENCE`. This verifies source existence and quotation, not the semantic truth of every inference. Model narrative remains advisory. Confidence is calculated as `baseline + (100 - baseline) × verified_evidence_fraction × 0.25`, clamped to 0–100; the baseline is saved to prevent repeated re-analysis inflation. Missing-data uncertainty is inherited from deterministic confidence. Score disagreement alone does not reduce confidence.

Migration `0009_ai_details` saves previously unsupported strengths/gaps/risks, baseline confidence and source quotes in existing AI tables. Run `alembic upgrade head` before using AI. Both migration directions are tested transactionally.

**Privacy:** An explicit AI request sends the current job's description/responsibilities/requirements and fit metadata, candidate summary/skills/experience/education/projects, search preferences and deterministic scores/evidence to the configured provider (hosted OpenAI by default, or the configured OpenAI-compatible server). Candidate root name/IDs, project URLs, internal settings, keys, headers, application notes and unrelated users are omitted. Prompts/responses are not logged; SQL debug parameters are hidden. Job/profile text is delimited as untrusted JSON data with instructions against prompt injection and invented evidence; this is defensive separation, not perfect injection immunity. Provider costs, terms and account/model availability apply. No real-provider call is part of normal tests.
