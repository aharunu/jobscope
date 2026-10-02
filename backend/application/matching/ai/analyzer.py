"""Owned, explicit, transactional AI analysis over an existing deterministic match."""

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import ValidationError

from backend.application.matching.ai import prompt
from backend.application.matching.ai.errors import AIError
from backend.application.matching.ai.evidence import validate_evidence
from backend.application.matching.ai.provider import LLMProvider
from backend.application.matching.ai.schema import SCHEMA_VERSION, AIOutput
from backend.application.matching.ai.scoring import calculate_scores, rounded
from backend.application.matching.exceptions import MatchResultNotFoundError
from backend.domain.job.repositories import JobRepository
from backend.domain.matching.entities import AIAnalysis, AIEvidence, MatchResult
from backend.domain.matching.repositories import MatchResultRepository
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.repositories import SearchProfileRepository

logger = logging.getLogger(__name__)


class AIAnalyzer:
    def __init__(
        self,
        matches: MatchResultRepository,
        jobs: JobRepository,
        profiles: BaseProfileRepository,
        searches: SearchProfileRepository,
        provider: LLMProvider,
    ):
        self.matches, self.jobs, self.profiles, self.searches = (
            matches,
            jobs,
            profiles,
            searches,
        )
        self.provider = provider

    async def analyze(
        self, match_id: uuid.UUID, user_id: uuid.UUID, force: bool = False
    ) -> tuple[MatchResult, bool]:
        # The row lock serializes AI requests and deterministic overwrites.
        match = await self.matches.get_owned_for_update(match_id, user_id)
        if match is None:
            raise MatchResultNotFoundError()
        profile = await self.profiles.get_by_user_id(user_id)
        search = await self.searches.get_by_id_and_base_profile_id(
            match.search_profile_id, match.base_profile_id
        )
        job = await self.jobs.get_job_detail(match.job_id)
        if not profile or profile.id != match.base_profile_id or not search or not job:
            raise MatchResultNotFoundError()
        old = match.ai_analysis
        baseline = (
            old.deterministic_confidence
            if old and old.deterministic_confidence is not None
            else match.confidence
        )
        context = prompt.build_context(job, profile, search, match, baseline)
        digest = prompt.fingerprint(
            context,
            self.provider.provider,
            self.provider.model,
            prompt.PROMPT_VERSION,
            SCHEMA_VERSION,
        )
        if old and old.fingerprint == digest and not force:
            logger.info("AI analysis cache hit provider=%s", self.provider.provider)
            return match, True
        system, data = prompt.build_prompt(context)
        if len(data) > 150_000:
            raise AIError("AI_INPUT_TOO_LARGE", 422)
        logger.info(
            "AI analysis cache miss provider=%s force=%s", self.provider.provider, force
        )
        try:
            raw = await self.provider.analyze(
                system, data, AIOutput.model_json_schema()
            )
            if not isinstance(raw, str) or len(raw) > 200_000:
                raise AIError("AI_INVALID_OUTPUT", 502)
            output = AIOutput.model_validate_json(raw)
        except AIError:
            logger.warning(
                "AI analysis provider request failed provider=%s",
                self.provider.provider,
            )
            raise
        except (ValidationError, ValueError, TypeError):
            logger.warning(
                "AI analysis output validation failed provider=%s",
                self.provider.provider,
            )
            raise AIError("AI_INVALID_OUTPUT", 502) from None
        except Exception:
            # Never chain raw vendor errors, which may contain keys/prompt data.
            logger.warning(
                "AI analysis request failed provider=%s", self.provider.provider
            )
            raise AIError() from None
        evidence, valid_count = validate_evidence(output.evidence, context)
        score = rounded(Decimal(str(output.ai_score)))
        blocked = bool(match.explanation and match.explanation.blockers) or any(
            r.is_blocker and str(r.match_status) == "NOT_MATCHED"
            for r in match.requirement_matches
        )
        adjustment, final, confidence = calculate_scores(
            match.deterministic_score,
            score,
            baseline,
            valid_count,
            len(evidence),
            blocked,
        )
        analysis = AIAnalysis(
            match_result_id=match.id,
            provider=self.provider.provider,
            model=self.provider.model,
            ai_score=score,
            assessment=output.assessment,
            summary=output.summary,
            fingerprint=digest,
            strengths=output.strengths,
            gaps=output.gaps,
            risks=output.risks,
            deterministic_confidence=baseline,
            created_at=datetime.now(UTC),
        )
        analysis.evidence = [
            AIEvidence(ai_analysis_id=analysis.id, **item.model_dump())
            for item in evidence
        ]
        match.ai_score, match.ai_adjustment, match.final_score, match.confidence = (
            score,
            adjustment,
            final,
            confidence,
        )
        saved = await self.matches.save_ai_analysis(match, analysis)
        logger.info(
            "AI analysis persisted provider=%s verified=%s total=%s",
            self.provider.provider,
            valid_count,
            len(evidence),
        )
        return saved, False
