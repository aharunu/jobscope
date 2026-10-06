"""Regressions traced through the real product audit."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import func, select

from backend.application.job_processing.normalizer import JobNormalizer
from backend.infrastructure.ats.smartrecruiters.adapter import posting_url
from backend.infrastructure.database.models import (
    JobModel,
    JobOccurrenceModel,
    SourceModel,
)
from tests.test_acquisition_a3 import crawl, job, payload
from tests.test_hybrid_dedup_a5 import db as db
from tests.test_hybrid_dedup_a5 import ingest, posting


@pytest.mark.parametrize("board", ["abbvie", "lesaffre", "metromakro", "turcom"])
def test_smartrecruiters_board_case_preserves_posting_path(board):
    url = f"https://jobs.smartrecruiters.com/{board.upper()}/1-CaseSensitive"
    assert posting_url(url, board) == url
    for unsafe in (
        f"https://evil.example.com/{board}/1",
        f"https://jobs.smartrecruiters.com/{board}other/1",
        f"https://jobs.smartrecruiters.com/{board}/",
        f"https://jobs.smartrecruiters.com/{board}%2Fother/1",
    ):
        assert posting_url(unsafe, board) is None


async def test_case_mismatched_smartrecruiters_detail_survives_persist():
    listing, detail = job("smartrecruiters"), job("smartrecruiters")
    listing.pop("jobAd")
    detail["jobAdUrl"] = "https://jobs.smartrecruiters.com/ACME/1-Engineer"
    result, client = await crawl(
        "smartrecruiters", payload("smartrecruiters", [listing]), detail
    )
    assert len(client.calls) == 2
    assert len(result.jobs) == 1 and result.is_complete
    assert result.jobs[0].url == detail["jobAdUrl"]
    assert json.loads(result.jobs[0].raw_content)["detail"] == detail


async def test_long_location_persists_and_preserves_full_raw_observation(db):
    source = db[1][0]
    full = "; ".join([f"Istanbul District {i}" for i in range(40)])
    item = posting(source, location=full)
    canonical = JobNormalizer().normalize(item, source)
    assert len(canonical.location) <= 255 and canonical.location.endswith("…")
    assert item.metadata["location"] == full
    result = await ingest(db, jobs=[item])
    assert result.jobs_created == 1 and not result.errors


@pytest.mark.parametrize("provider", ["lever", "workday", "smartrecruiters"])
async def test_verified_same_provider_posting_attaches_alias_occurrence(db, provider):
    factory, sources, users = db
    token = str(sources[0].id).replace("-", "")
    url = {
        "lever": f"https://jobs.lever.co/{token}",
        "workday": f"https://{token}.wd1.myworkdayjobs.com/en-US/Careers",
        "smartrecruiters": f"https://careers.smartrecruiters.com/{token}",
    }[provider]
    sources = [
        replace(
            s,
            url=url,
            ats_type=provider,
            company="Employer" if i == 0 else "Employer Catalog Alias",
        )
        for i, s in enumerate(sources)
    ]
    async with factory() as session, session.begin():
        for source in sources:
            row = await session.get(SourceModel, source.id)
            row.url, row.ats_type, row.company = (
                source.url,
                source.ats_type,
                source.company,
            )
    configured = factory, sources, users
    first = posting(sources[0])
    second = replace(posting(sources[1]), url=first.url)
    await ingest(configured, jobs=[first])
    result = await ingest(configured, source_index=1, jobs=[second])
    assert not result.errors
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(JobModel)
                .where(JobModel.source_id.in_([s.id for s in sources]))
            )
            == 1
        )
        occurrences = (
            await session.scalars(
                select(JobOccurrenceModel).where(
                    JobOccurrenceModel.source_id.in_([s.id for s in sources])
                )
            )
        ).all()
        assert len(occurrences) == 2
        assert len({o.job_id for o in occurrences}) == 1
        assert occurrences[1].dedup_signals.get("same_provider_posting") or occurrences[
            0
        ].dedup_signals.get("same_provider_posting")


@pytest.mark.parametrize("contradiction", ["board", "identity", "title", "reference"])
async def test_same_url_does_not_bypass_provider_identity_guards(db, contradiction):
    factory, sources, users = db
    sources[1] = replace(
        sources[1],
        url=sources[0].url,
        ats_type="lever",
        company="Different Catalog Label",
    )
    if contradiction == "board":
        sources[1] = replace(sources[1], url=sources[1].url + "-other")
    async with factory() as session, session.begin():
        row = await session.get(SourceModel, sources[1].id)
        row.url, row.ats_type, row.company = (
            sources[1].url,
            sources[1].ats_type,
            sources[1].company,
        )
    first = posting(sources[0])
    second = replace(posting(sources[1]), url=first.url)
    if contradiction == "identity":
        second.external_job_id = "different-posting"
    if contradiction == "title":
        second.title = "Senior Software Engineer"
    if contradiction == "reference":
        second.metadata["requisition_id"] = "different-reference"
    await ingest(db, jobs=[first])
    result = await ingest(db, source_index=1, jobs=[second])
    assert result.errors == ["JOB_URL_OWNERSHIP_CONFLICT"]
