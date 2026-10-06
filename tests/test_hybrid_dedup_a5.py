"""Deterministic safety, real PostgreSQL transactions and occurrence regressions."""

import asyncio
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.application.common.exceptions import JobScopeError
from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
)
from backend.application.job_processing.normalizer import JobNormalizer
from backend.domain.job.dedup import normalize, project, score_pair
from backend.domain.job.enums import JobStatus
from backend.domain.matching.deterministic_engine import DeterministicMatchEngine
from backend.domain.source.entities import Source
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.database.crawl_persistence import build_ingestion_service
from backend.infrastructure.database.dedup_review import SQLAlchemyDedupReview
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.historical_dedup import analyze_historical
from backend.infrastructure.database.models.application import (
    ApplicationModel,
    ApplicationStatusHistoryModel,
)
from backend.infrastructure.database.models.base_profile import BaseProfileModel
from backend.infrastructure.database.models.crawl_run import CrawlRunModel
from backend.infrastructure.database.models.dedup import (
    DedupCandidateModel as Candidate,
)
from backend.infrastructure.database.models.dedup import (
    JobMergeRecordModel as Merge,
)
from backend.infrastructure.database.models.dedup import (
    JobOccurrenceModel as Occurrence,
)
from backend.infrastructure.database.models.job import (
    JobModel,
    JobRequirementModel,
    RawJobModel,
)
from backend.infrastructure.database.models.matching import (
    AIAnalysisModel,
    AIEvidenceModel,
    MatchResultModel,
    RequirementMatchModel,
)
from backend.infrastructure.database.models.search_profile import SearchProfileModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.occurrence_store import (
    add_candidate,
)
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
)
from backend.infrastructure.database.repositories.matching_repository import (
    SQLAlchemyMatchResultRepository,
)
from backend.interfaces.api.dependencies.database import get_db_session
from backend.interfaces.api.main import create_app

DESCRIPTION = "Required Python and SQL experience. " + " ".join(
    f"technicalskill{i}" for i in range(60)
)


@pytest.fixture
async def db():
    engine = create_database_engine(get_settings().model_copy(update={"debug": False}))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    prefix = uuid.uuid4().hex
    sources = [
        Source(
            name=f"Dedup test {prefix}-{i}",
            company=f"Employer {prefix}",
            url=f"https://jobs.lever.co/{prefix}-{i}",
            ats_type="lever" if i == 0 else "greenhouse",
            active=True,
        )
        for i in range(4)
    ]
    users = [UserModel(), UserModel()]
    async with factory() as session, session.begin():
        session.add_all([SourceModel.from_domain(s) for s in sources] + users)
    try:
        yield factory, [RuntimeSourceDTO.from_domain(s) for s in sources], users
    finally:
        async with factory() as session, session.begin():
            ids = [s.id for s in sources]
            await session.execute(
                delete(CrawlRunModel).where(CrawlRunModel.source_id.in_(ids))
            )
            await session.execute(delete(JobModel).where(JobModel.source_id.in_(ids)))
            await session.execute(delete(SourceModel).where(SourceModel.id.in_(ids)))
            await session.execute(
                delete(UserModel).where(UserModel.id.in_([u.id for u in users]))
            )
        await engine.dispose()


def posting(source, identity="1", reference="REQ-1", **metadata):
    return DiscoveredJobDTO(
        identity,
        f"https://jobs.example.com/{source.id}/{identity}",
        metadata.pop("title", "Software Engineer"),
        '{"provider":"full raw observation"}',
        "application/json",
        {
            "company": source.company,
            "description": DESCRIPTION,
            "location": "Istanbul",
            "employment_type": "Full-time",
            **({"requisition_id": reference} if reference else {}),
            **metadata,
        },
    )


async def ingest(
    db, source_index=0, jobs=None, complete=True, suppression=None, warnings=None
):
    factory, sources, _ = db
    source = sources[source_index]
    async with factory() as session, session.begin():
        return await build_ingestion_service(session).ingest_crawl_result(
            source,
            CrawlResultDTO(
                source.id,
                source.ats_type,
                jobs=jobs if jobs is not None else [posting(source)],
                is_complete=complete,
                closure_suppression_reason=suppression,
                warnings=warnings or [],
            ),
        )


async def rows(db, model):
    async with db[0]() as session:
        return list((await session.scalars(select(model))).all())


async def own_jobs(db):
    async with db[0]() as session:
        return list(
            (
                await session.scalars(
                    select(JobModel).where(
                        JobModel.source_id.in_([s.id for s in db[1]])
                    )
                )
            ).all()
        )


def test_normalization_preserves_seniority_and_meaningful_terms():
    assert normalize("  ACME, Inc. ") == "acme inc"
    assert normalize("Ｓｅｎｉｏｒ Engineer") == "senior engineer"
    assert normalize("Senior Engineer") != normalize("Engineer")


@pytest.mark.parametrize(
    "changes,refs,outcome",
    [
        ({"company": "Different employer"}, ("R", "R"), "NEW_JOB"),
        ({"title": "Senior Software Engineer"}, ("R", "R"), "NEW_JOB"),
        ({}, ("R", "OTHER"), "NEW_JOB"),
        ({}, (None, None), "REVIEW"),
        ({"location": "Madrid"}, ("R", "R"), "NEW_JOB"),
        ({}, ("R", "R"), "AUTO_MERGE"),
    ],
)
def test_false_positive_guards(changes, refs, outcome):
    source = RuntimeSourceDTO.from_domain(
        Source(
            name="Employer",
            company="Employer",
            url="https://jobs.lever.co/test",
            ats_type="lever",
        )
    )
    left = JobNormalizer().normalize(posting(source), source)
    right = replace(left, canonical_url="https://other.example.com/job", **changes)
    assert score_pair(left, right, *refs).outcome == outcome


async def test_same_identity_and_strong_duplicate_one_logical_job(db):
    await ingest(db)
    second = await ingest(db)
    assert second.jobs_unchanged == 1
    duplicate = await ingest(db, 1)
    assert duplicate.jobs_created == 0 and duplicate.jobs_updated == 1
    jobs = await own_jobs(db)
    assert len(jobs) == 1
    async with db[0]() as session:
        occurrences = (
            await session.scalars(
                select(Occurrence).where(Occurrence.job_id == jobs[0].id)
            )
        ).all()
        assert len(occurrences) == 2 and {o.source_id for o in occurrences} == {
            s.id for s in db[1][:2]
        }
        assert any(
            o.dedup_outcome == "AUTO_MERGE" and o.dedup_signals["reference_equal"]
            for o in occurrences
        )
        raw = (
            await session.scalars(
                select(RawJobModel).where(RawJobModel.job_id == jobs[0].id)
            )
        ).all()
        assert len(raw) == 2 and {r.occurrence_id for r in raw} == {
            o.id for o in occurrences
        }
        detail = await SQLAlchemyJobRepository(session).get_job_detail(jobs[0].id)
        assert len(detail.occurrences) == 2
        assert (
            len(await SQLAlchemyJobRepository(session).list_jobs(source_id=db[1][1].id))
            == 1
        )
        assert (
            await SQLAlchemyJobRepository(session).count_jobs(
                company=db[1][0].company, ats_type="greenhouse"
            )
            == 1
        )


async def test_ambiguous_stays_separate_keep_separate_is_durable(db):
    await ingest(db, jobs=[posting(db[1][0], reference=None)])
    await ingest(db, 1, jobs=[posting(db[1][1], reference=None)])
    assert len(await own_jobs(db)) == 2
    async with db[0]() as session, session.begin():
        jobs = await own_jobs(db)
        candidate = await session.scalar(
            select(Candidate).where(Candidate.left_job_id.in_([j.id for j in jobs]))
        )
        assert candidate.outcome == "REVIEW"
        await SQLAlchemyDedupReview(session).resolve(candidate.id)
        decision = score_pair(jobs[0].to_domain(), jobs[1].to_domain())
        await add_candidate(
            session, candidate.right_job_id, candidate.left_job_id, decision
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Candidate)
                .where(
                    Candidate.left_job_id == candidate.left_job_id,
                    Candidate.right_job_id == candidate.right_job_id,
                )
            )
            == 1
        )
        assert candidate.resolution == "KEEP_SEPARATE"


async def test_rich_projection_and_occurrence_lifecycle_guards(db):
    await ingest(db)
    await ingest(db, 1)
    await ingest(
        db,
        1,
        jobs=[posting(db[1][1], description="Software Engineer", employment_type=None)],
    )
    logical = (await own_jobs(db))[0]
    assert logical.description == DESCRIPTION and logical.employment_type == "Full-time"
    # Keep a separate visible vacancy to avoid the unchanged zero-result anomaly guard.
    other = posting(db[1][0], identity="other", reference="OTHER", title="Manager")
    await ingest(db, 0, jobs=[posting(db[1][0]), other])
    for complete, suppression, warnings in [
        (False, None, []),
        (True, "INGESTION_POLICY_FILTER_ACTIVE", []),
        (True, None, ["coverage_warning"]),
    ]:
        await ingest(
            db,
            0,
            jobs=[other],
            complete=complete,
            suppression=suppression,
            warnings=warnings,
        )
        async with db[0]() as session:
            assert (
                await session.scalar(
                    select(Occurrence).where(
                        Occurrence.job_id == logical.id,
                        Occurrence.source_id == db[1][0].id,
                    )
                )
            ).status == "ACTIVE"
    await ingest(db, 0, jobs=[other])
    async with db[0]() as session:
        assert (await session.get(JobModel, logical.id)).status == JobStatus.ACTIVE
        assert (
            await session.scalar(
                select(Occurrence).where(
                    Occurrence.job_id == logical.id, Occurrence.source_id == db[1][0].id
                )
            )
        ).status == "CLOSED"
    other_b = posting(
        db[1][1], identity="other", reference="OTHER-B", title="Accountant"
    )
    await ingest(db, 1, jobs=[other_b])
    async with db[0]() as session:
        assert (await session.get(JobModel, logical.id)).status == JobStatus.CLOSED
    await ingest(db, 0, jobs=[posting(db[1][0]), other])
    async with db[0]() as session:
        assert (await session.get(JobModel, logical.id)).status == JobStatus.ACTIVE


async def ambiguous_pair(db):
    await ingest(db, jobs=[posting(db[1][0], reference=None)])
    await ingest(db, 1, jobs=[posting(db[1][1], reference=None)])
    jobs = await own_jobs(db)
    async with db[0]() as session:
        candidate = await session.scalar(
            select(Candidate).where(Candidate.left_job_id.in_([j.id for j in jobs]))
        )
    return jobs, candidate.id


async def test_atomic_merge_preserves_application_history_matches_raw_and_alias(db):
    jobs, candidate_id = await ambiguous_pair(db)
    async with db[0]() as session, session.begin():
        app = ApplicationModel(
            job_id=jobs[1].id, user_id=db[2][0].id, notes="Must survive"
        )
        session.add(app)
        await session.flush()
        history = ApplicationStatusHistoryModel(
            application_id=app.id,
            from_status="INTERESTED",
            to_status="APPLIED",
            changed_at=datetime.now(UTC),
        )
        session.add(history)
        base = BaseProfileModel(user_id=db[2][0].id, name="A5 test candidate")
        session.add(base)
        await session.flush()
        search = SearchProfileModel(base_profile_id=base.id, name="A5 match test")
        session.add(search)
        await session.flush()
        match = MatchResultModel(
            job_id=jobs[0].id,
            base_profile_id=base.id,
            search_profile_id=search.id,
            deterministic_score=Decimal(50),
            final_score=Decimal(50),
            confidence=Decimal(50),
        )
        session.add(match)
        await session.flush()
        match_id, app_id, history_id = match.id, app.id, history.id
        requirement = await session.scalar(
            select(JobRequirementModel).where(JobRequirementModel.job_id == jobs[0].id)
        )
        requirement_match = RequirementMatchModel(
            match_result_id=match.id,
            requirement_id=requirement.id,
            match_status="MATCHED",
            score=Decimal(100),
            reason="Historical evidence",
        )
        analysis = AIAnalysisModel(
            match_result_id=match.id,
            provider="test",
            model="test",
            ai_score=Decimal(50),
            assessment="POSSIBLE_FIT",
            summary="Historical analysis",
        )
        session.add_all([requirement_match, analysis])
        await session.flush()
        evidence = AIEvidenceModel(
            ai_analysis_id=analysis.id,
            claim="Python",
            evidence_type="job_requirement",
            source_reference=str(requirement.id),
            reason="Historical evidence",
            source_quote="Python",
        )
        session.add(evidence)
        await session.flush()
        requirement_match_id, analysis_id, evidence_id = (
            requirement_match.id,
            analysis.id,
            evidence.id,
        )
        await SQLAlchemyDedupReview(session).resolve(candidate_id, merge=True)
    async with db[0]() as session:
        assert (await session.get(ApplicationModel, app_id)).job_id == jobs[1].id
        assert (await session.get(ApplicationModel, app_id)).notes == "Must survive"
        assert await session.get(ApplicationStatusHistoryModel, history_id)
        assert (await session.get(MatchResultModel, match_id)).invalidated
        assert await session.get(RequirementMatchModel, requirement_match_id)
        assert await session.get(AIAnalysisModel, analysis_id)
        assert await session.get(AIEvidenceModel, evidence_id)
        assert (
            await SQLAlchemyMatchResultRepository(session).get_by_id(match_id) is None
        )
        retired = await session.get(JobModel, jobs[0].id)
        assert retired.merged_into_id == jobs[1].id
        assert (
            await SQLAlchemyJobRepository(session).get_job_detail(retired.id)
        ).id == jobs[1].id
        assert (
            len(
                await SQLAlchemyJobRepository(session).list_jobs(
                    company=db[1][0].company
                )
            )
            == 1
        )
        raw = (
            await session.scalars(
                select(RawJobModel).where(RawJobModel.job_id == jobs[1].id)
            )
        ).all()
        assert len(raw) == 2 and all(r.occurrence_id for r in raw)
        assert await session.scalar(
            select(Merge.id).where(Merge.source_job_id == retired.id)
        )
        assert await session.scalar(
            select(JobRequirementModel.id).where(
                JobRequirementModel.job_id == retired.id,
                JobRequirementModel.archived.is_(True),
            )
        )
        current = await SQLAlchemyJobRepository(session).get_job_detail(jobs[1].id)
        recalculated = DeterministicMatchEngine().evaluate(
            current, base.to_domain(), search.to_domain(), current.requirements
        )
        persisted = await SQLAlchemyMatchResultRepository(session).save(recalculated)
        assert persisted.job_id == current.id and persisted.ai_analysis is None
        assert (
            await session.scalar(
                select(func.count())
                .select_from(MatchResultModel)
                .where(
                    MatchResultModel.job_id.in_([j.id for j in jobs]),
                    MatchResultModel.invalidated.is_(False),
                )
            )
            == 1
        )


async def test_conflicting_applications_block_merge_without_loss(db):
    jobs, candidate_id = await ambiguous_pair(db)
    async with db[0]() as session, session.begin():
        session.add_all(
            [
                ApplicationModel(job_id=j.id, user_id=db[2][0].id, notes=f"Notes {i}")
                for i, j in enumerate(jobs)
            ]
        )
        occurrences = (
            await session.scalars(
                select(Occurrence).where(Occurrence.job_id.in_([j.id for j in jobs]))
            )
        ).all()
        for occurrence in occurrences:
            occurrence.reference = "SAME-EMPLOYER-REFERENCE"
        await session.flush()
        analysis = await analyze_historical(session, limit=5000)
        suggestion = next(
            row
            for row in analysis["candidates"]
            if {row["left_job_id"], row["right_job_id"]} == {str(j.id) for j in jobs}
        )
        assert suggestion["outcome"] == "REVIEW"
        assert suggestion["signals"]["application_conflict"]
    with pytest.raises(JobScopeError, match="same user"):
        async with db[0]() as session, session.begin():
            await SQLAlchemyDedupReview(session).resolve(candidate_id, merge=True)
    async with db[0]() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ApplicationModel)
                .where(ApplicationModel.job_id.in_([j.id for j in jobs]))
            )
            == 2
        )
        assert (await session.get(Candidate, candidate_id)).resolved_at is None


async def test_merge_rollback_no_half_state(db):
    jobs, candidate_id = await ambiguous_pair(db)
    with pytest.raises(RuntimeError, match="rollback"):
        async with db[0]() as session, session.begin():
            await SQLAlchemyDedupReview(session).resolve(candidate_id, merge=True)
            raise RuntimeError("rollback")
    async with db[0]() as session:
        for job in jobs:
            assert (await session.get(JobModel, job.id)).merged_into_id is None
        assert (await session.get(Candidate, candidate_id)).resolved_at is None
        assert (
            await session.scalar(
                select(Merge.id).where(Merge.source_job_id.in_([j.id for j in jobs]))
            )
            is None
        )


async def test_concurrent_sources_use_one_logical_job(db):
    await asyncio.gather(ingest(db, 0), ingest(db, 1))
    assert len(await own_jobs(db)) == 1


async def test_concurrent_multi_item_sources_in_reverse_order(db):
    a, b = db[1][:2]
    left = [posting(a), posting(a, identity="manager", reference="R2", title="Manager")]
    right = [
        posting(b, identity="manager", reference="R2", title="Manager"),
        posting(b),
    ]
    await asyncio.wait_for(
        asyncio.gather(ingest(db, 0, jobs=left), ingest(db, 1, jobs=right)), timeout=10
    )
    assert len(await own_jobs(db)) == 2


async def test_candidate_cap_cannot_automatically_merge(db):
    a, b = db[1][:2]
    await ingest(db, jobs=[posting(a, identity=str(i)) for i in range(51)])
    await ingest(db, 1, jobs=[posting(b)])
    jobs = await own_jobs(db)
    assert len(jobs) == 52
    async with db[0]() as session:
        newest = await session.scalar(
            select(Occurrence).where(Occurrence.source_id == b.id)
        )
        assert (
            newest.dedup_outcome == "REVIEW" and newest.dedup_signals["candidate_cap"]
        )


async def test_multiple_strong_candidates_are_review_not_arbitrary_auto_merge(db):
    a, b = db[1][:2]
    await ingest(db, jobs=[posting(a, identity="1"), posting(a, identity="2")])
    await ingest(db, 1, jobs=[posting(b)])
    assert len(await own_jobs(db)) == 3
    async with db[0]() as session:
        occurrence = await session.scalar(
            select(Occurrence).where(Occurrence.source_id == b.id)
        )
        assert occurrence.dedup_outcome == "REVIEW"
        assert occurrence.dedup_signals["multiple_auto_candidates"]
        candidates = (
            await session.scalars(
                select(Candidate).where(
                    (Candidate.left_job_id == occurrence.job_id)
                    | (Candidate.right_job_id == occurrence.job_id)
                )
            )
        ).all()
        assert len(candidates) == 2 and all(c.outcome == "REVIEW" for c in candidates)


async def test_nonmatch_occurrence_retains_contradiction_audit(db):
    await ingest(db)
    await ingest(db, 1, jobs=[posting(db[1][1], reference="CONFLICT")])
    async with db[0]() as session:
        occurrence = await session.scalar(
            select(Occurrence).where(Occurrence.source_id == db[1][1].id)
        )
        assert occurrence.dedup_outcome == "NEW_JOB"
        assert occurrence.dedup_signals["reference_conflict"]
        assert occurrence.dedup_signals["candidate_count"] == 1


def test_country_publication_and_html_richness_guards():
    source = RuntimeSourceDTO.from_domain(
        Source(
            name="Employer",
            company="Employer",
            url="https://jobs.lever.co/test",
            ats_type="lever",
        )
    )
    left = JobNormalizer().normalize(posting(source), source)
    left.published_at = datetime.now(UTC)
    right = replace(left, canonical_url="https://other.example.com/job")
    assert score_pair(left, right, "R", "R", "TR", "ES").outcome == "NEW_JOB"
    right.published_at = left.published_at - timedelta(days=181)
    assert score_pair(left, right, "R", "R", "TR", "TR").outcome == "REVIEW"
    assert (
        score_pair(
            replace(left, location="Unknown"),
            replace(left, location="Unknown"),
            "R",
            "R",
        ).outcome
        == "REVIEW"
    )
    poor = replace(left, description='<div class="' + "x" * 2000 + '">Short</div>')
    assert project(left, poor, alternate=True).description == DESCRIPTION


async def test_review_api_confirmed_merge_resolves_retired_job(db):
    jobs, candidate_id = await ambiguous_pair(db)
    app = create_app()

    async def session_dep():
        async with db[0]() as session, session.begin():
            yield session

    app.dependency_overrides[get_db_session] = session_dep
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        result = await client.post(
            f"/api/dedup/candidates/{candidate_id}/merge", json={"confirm": True}
        )
        assert result.status_code == 200 and result.json()["resolution"] == "MERGED"
        details = [(await client.get(f"/api/jobs/{job.id}")).json() for job in jobs]
        assert details[0]["id"] == details[1]["id"]
        assert len(details[0]["occurrences"]) == 2


async def test_historical_analysis_is_nonmutating_and_uses_production_signals(db):
    jobs, _ = await ambiguous_pair(db)
    async with db[0]() as session:
        before = await session.scalar(select(func.count()).select_from(Candidate))
        result = await analyze_historical(session, limit=5000)
        pair = {str(j.id) for j in jobs}
        suggestion = next(
            row
            for row in result["candidates"]
            if {row["left_job_id"], row["right_job_id"]} == pair
        )
        assert (
            suggestion["outcome"] == "REVIEW" and suggestion["signals"]["company_exact"]
        )
        assert result["dry_run"] and result["merges_performed"] == 0
        assert (
            await session.scalar(select(func.count()).select_from(Candidate)) == before
        )


async def test_review_api_confirmation_and_resolution(db):
    jobs, candidate_id = await ambiguous_pair(db)
    app = create_app()

    async def session_dep():
        async with db[0]() as session, session.begin():
            yield session

    app.dependency_overrides[get_db_session] = session_dep
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/dedup/candidates/{candidate_id}")
        assert response.status_code == 200 and len(response.json()["jobs"]) == 2
        assert (
            await client.post(f"/api/dedup/candidates/{candidate_id}/merge", json={})
        ).status_code == 422
        assert (
            await client.post(
                f"/api/dedup/candidates/{candidate_id}/merge", json={"confirm": False}
            )
        ).status_code == 422
        assert (
            await client.post(f"/api/dedup/candidates/{candidate_id}/keep-separate")
        ).json()["resolution"] == "KEEP_SEPARATE"
        assert (await client.get(f"/api/jobs/{jobs[0].id}")).json()["occurrences"]
