"""Real PostgreSQL search ordering/count/pagination regression with rollback."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.source.entities import Source
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
)


@pytest.mark.asyncio
async def test_description_search_priority_count_and_pagination():
    engine = create_database_engine(get_settings().model_copy(update={"debug": False}))
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(
                    bind=connection, expire_on_commit=False
                ) as session:
                    source = Source(
                        name="Search regression",
                        url="https://example.com",
                        ats_type="lever",
                    )
                    session.add(SourceModel.from_domain(source))
                    needle = "needle" + uuid.uuid4().hex
                    jobs = []
                    for i, (title, company, description) in enumerate(
                        [
                            (
                                "Backend Engineer",
                                "Employer",
                                f"<p>Use {needle} &amp; 100% a_b.</p>",
                            ),
                            ("Backend Engineer", needle, "Other experience"),
                            (needle, "Employer", "Other experience"),
                            (
                                "Another role",
                                "Employer",
                                f'<div data-id="{needle}">Other work</div>',
                            ),
                        ]
                    ):
                        job = Job(
                            source_id=source.id,
                            canonical_url=f"https://example.com/{uuid.uuid4()}",
                            company=company,
                            title=title,
                            description=description,
                            content_hash="test",
                            first_seen_at=datetime(2026 - i, 1, 1, tzinfo=UTC),
                        )
                        jobs.append(job)
                        session.add(JobModel.from_domain(job))
                    await session.flush()
                    repo = SQLAlchemyJobRepository(session)
                    args = {"source_id": source.id, "search_query": needle.upper()}
                    assert await repo.count_jobs(**args) == 3
                    result = await repo.list_jobs(**args)
                    assert [j.id for j in result] == [
                        jobs[2].id,
                        jobs[1].id,
                        jobs[0].id,
                    ]
                    title_args = {**args, "search_scope": "title"}
                    assert await repo.count_jobs(**title_args) == 1
                    assert [j.id for j in await repo.list_jobs(**title_args)] == [
                        jobs[2].id
                    ]
                    page = await repo.list_jobs(**args, limit=1, offset=2)
                    assert [j.id for j in page] == [jobs[0].id]
                    for literal in ("%", "a_b"):
                        assert (
                            await repo.count_jobs(
                                source_id=source.id, search_query=literal
                            )
                            == 1
                        )
                    assert await repo.count_jobs(**args, status=JobStatus.CLOSED) == 0
                    unfiltered = await repo.list_jobs(source_id=source.id)
                    assert [j.id for j in unfiltered] == [j.id for j in jobs]
                    exact_jobs = []
                    for title, company, description in [
                        ("Intern", "Employer", "Training position"),
                        ("Internet engineer", "Employer", "Connectivity"),
                        ("Internal auditor", "Employer", "Audit"),
                        ("Internship", "Employer", "Placement"),
                        ("Engineer", "International employer", "Internet skills"),
                        ("Assistant", "Employer", "We need an INTERN, for training."),
                        ("Engineer", "Employer", "intern_developer role"),
                        ("Developer", "Employer", "C++ and data engineer experience."),
                    ]:
                        job = Job(
                            source_id=source.id,
                            canonical_url=f"https://example.com/{uuid.uuid4()}",
                            title=title,
                            company=company,
                            description=description,
                            content_hash="test",
                        )
                        exact_jobs.append(job)
                        session.add(JobModel.from_domain(job))
                    await session.flush()
                    assert (
                        await repo.count_jobs(
                            source_id=source.id, search_query="intern"
                        )
                        == 7
                    )
                    for query in ('"intern"', '"INTERN"'):
                        found = await repo.list_jobs(
                            source_id=source.id, search_query=query
                        )
                        assert [j.id for j in found] == [
                            exact_jobs[0].id,
                            exact_jobs[5].id,
                        ]
                        assert (
                            await repo.count_jobs(
                                source_id=source.id, search_query=query
                            )
                            == 2
                        )
                        page = await repo.list_jobs(
                            source_id=source.id, search_query=query, limit=1, offset=1
                        )
                        assert page[0].id == exact_jobs[5].id
                    title_exact = dict(
                        source_id=source.id,
                        search_query='"intern"',
                        search_scope="title",
                    )
                    assert await repo.count_jobs(**title_exact) == 1
                    assert [j.id for j in await repo.list_jobs(**title_exact)] == [
                        exact_jobs[0].id
                    ]
                    for query in ('"C++"', '"data engineer"'):
                        found = await repo.list_jobs(
                            source_id=source.id, search_query=query
                        )
                        assert [j.id for j in found] == [exact_jobs[7].id]
                    assert (
                        await repo.count_jobs(
                            source_id=source.id, search_query='"intern'
                        )
                        == 0
                    )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
