"""Unit tests for DeterministicRequirementExtractor (Items 1-13)."""

from __future__ import annotations

import uuid

from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus, RequirementLevel, RequirementType
from backend.infrastructure.extraction.deterministic_extractor import (
    DeterministicRequirementExtractor,
)


def _make_job(
    title: str = "Software Engineer",
    description: str = "",
    responsibilities: str | None = None,
) -> Job:
    return Job(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        canonical_url="https://jobs.example.com/123",
        company="TechCorp",
        title=title,
        description=description,
        responsibilities=responsibilities,
        content_hash="dummy_hash",
        status=JobStatus.ACTIVE,
    )


# 1. Technical skill extraction
def test_technical_skill_extraction() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(
        title="Backend Developer",
        description=(
            "We are looking for an engineer proficient in Python and FastAPI.\n"
            "You will work with PostgreSQL, Docker, and Kubernetes on AWS.\n"
            "Git version control is essential."
        ),
    )
    reqs = extractor.extract(job)
    skills = {r.normalized_skill for r in reqs if r.type == RequirementType.SKILL}

    expected = {"Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS", "Git"}
    assert expected.issubset(skills)
    for r in reqs:
        if r.normalized_skill in expected:
            assert r.type == RequirementType.SKILL
            assert r.evidence is not None


# 2. Case normalization
def test_case_normalization() -> None:
    extractor = DeterministicRequirementExtractor()
    job_upper = _make_job(description="Strong knowledge of PYTHON and DOCKER.")
    job_lower = _make_job(description="strong knowledge of python and docker.")
    job_mixed = _make_job(description="Strong knowledge of PyThOn and DoCkEr.")

    reqs_upper = {r.normalized_skill for r in extractor.extract(job_upper)}
    reqs_lower = {r.normalized_skill for r in extractor.extract(job_lower)}
    reqs_mixed = {r.normalized_skill for r in extractor.extract(job_mixed)}

    assert reqs_upper == {"Python", "Docker"}
    assert reqs_lower == {"Python", "Docker"}
    assert reqs_mixed == {"Python", "Docker"}


# 3. Duplicate elimination
def test_duplicate_elimination() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(
        title="Senior Python Developer",
        description=(
            "Python Engineer needed.\n"
            "- Write clean Python code.\n"
            "- Mentor junior Python developers.\n"
            "Requirements: Python 3+ experience."
        ),
    )
    reqs = extractor.extract(job)
    python_reqs = [r for r in reqs if r.normalized_skill == "Python"]

    # Must be deduplicated to exactly one requirement
    assert len(python_reqs) == 1
    assert python_reqs[0].type == RequirementType.SKILL
    assert python_reqs[0].required_level == RequirementLevel.REQUIRED
    assert python_reqs[0].importance == "HIGH"


# 4. Required vs preferred requirements
def test_required_vs_preferred_requirements() -> None:
    extractor = DeterministicRequirementExtractor()
    content = """
    # Requirements:
    - 3+ years experience with Python
    - Strong knowledge of PostgreSQL

    # Nice to have:
    - Experience with Docker and Kubernetes
    - Redis caching
    """
    job = _make_job(description=content)
    reqs = extractor.extract(job)
    by_skill = {r.normalized_skill: r for r in reqs}

    assert by_skill["Python"].required_level == RequirementLevel.REQUIRED
    assert by_skill["PostgreSQL"].required_level == RequirementLevel.REQUIRED

    assert by_skill["Docker"].required_level == RequirementLevel.PREFERRED
    assert by_skill["Kubernetes"].required_level == RequirementLevel.PREFERRED
    assert by_skill["Redis"].required_level == RequirementLevel.PREFERRED


def test_required_takes_precedence_over_preferred() -> None:
    extractor = DeterministicRequirementExtractor()
    content = """
    # Nice to have:
    - Docker experience is a plus

    # Requirements:
    - Docker is mandatory for deployment
    """
    job = _make_job(description=content)
    reqs = extractor.extract(job)
    docker_req = next(r for r in reqs if r.normalized_skill == "Docker")

    assert docker_req.required_level == RequirementLevel.REQUIRED


def test_line_level_override_preferred() -> None:
    extractor = DeterministicRequirementExtractor()
    content = """
    Requirements:
    - Strong Python skills required
    - Knowledge of GraphQL is a plus
    """
    job = _make_job(description=content)
    reqs = extractor.extract(job)
    by_skill = {r.normalized_skill: r for r in reqs}

    assert by_skill["Python"].required_level == RequirementLevel.REQUIRED
    assert by_skill["GraphQL"].required_level == RequirementLevel.PREFERRED


# 5. Experience extraction
def test_experience_extraction() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(
        description=(
            "- 2+ years of experience in backend development.\n"
            "- At least 3 years experience with microservices.\n"
            "- Minimum 1 year experience with cloud platforms."
        )
    )
    reqs = extractor.extract(job)
    exp_reqs = [r for r in reqs if r.type == RequirementType.EXPERIENCE]

    exp_skills = {r.normalized_skill for r in exp_reqs}
    assert "2+ years experience" in exp_skills
    assert "3 years experience" in exp_skills
    assert "1 years experience" in exp_skills


# 6. Education extraction
def test_education_extraction() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(
        description=(
            "Qualifications:\n"
            "- Bachelor's degree in Computer Science or Computer Engineering.\n"
            "- Master's degree in Mathematics is a plus."
        )
    )
    reqs = extractor.extract(job)
    edu_reqs = [r for r in reqs if r.type == RequirementType.EDUCATION]
    edu_skills = {r.normalized_skill: r for r in edu_reqs}

    assert "Bachelor's Degree" in edu_skills
    assert edu_skills["Bachelor's Degree"].required_level == RequirementLevel.REQUIRED
    assert edu_skills["Bachelor's Degree"].criticality == "BLOCKER"

    assert "Computer Science" in edu_skills
    assert "Computer Engineering" in edu_skills

    assert "Master's Degree" in edu_skills
    assert edu_skills["Master's Degree"].required_level == RequirementLevel.PREFERRED

    assert "Mathematics" in edu_skills


# 7. Language extraction
def test_language_extraction() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(
        description=(
            "- Excellent communication skills in English (written and verbal).\n"
            "- Turkish language proficiency required.\n"
            "- German is nice to have."
        )
    )
    reqs = extractor.extract(job)
    lang_reqs = [r for r in reqs if r.type == RequirementType.LANGUAGE]
    by_lang = {r.normalized_skill: r for r in lang_reqs}

    assert "English" in by_lang
    assert by_lang["English"].required_level == RequirementLevel.REQUIRED

    assert "Turkish" in by_lang
    assert by_lang["Turkish"].required_level == RequirementLevel.REQUIRED

    assert "German" in by_lang
    assert by_lang["German"].required_level == RequirementLevel.PREFERRED


# 8. Certification extraction
def test_certification_extraction() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(
        description=(
            "- AWS Certified Solutions Architect preferred.\n"
            "- CKA certification is a plus.\n"
            "- PMP is desirable."
        )
    )
    reqs = extractor.extract(job)
    cert_reqs = [r for r in reqs if r.type == RequirementType.CERTIFICATION]
    cert_skills = {r.normalized_skill for r in cert_reqs}

    assert "AWS Certified" in cert_skills
    assert "Certified Kubernetes Administrator (CKA)" in cert_skills
    assert "Project Management Professional (PMP)" in cert_skills


# 9. Empty or missing description
def test_empty_or_missing_description() -> None:
    extractor = DeterministicRequirementExtractor()
    job_empty = _make_job(title="Engineer", description="")
    job_spaces = _make_job(title="Engineer", description="   \n\t  ")

    assert extractor.extract(job_empty) == []
    assert extractor.extract(job_spaces) == []


# 10. Unrelated text produces no false requirements
def test_unrelated_text_produces_no_false_requirements() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(
        title="Operations Associate",
        description=(
            "We offer competitive salary, health insurance, free coffee, "
            "and team dinners every Friday at our central office. Join us today!"
        ),
    )
    reqs = extractor.extract(job)
    assert reqs == []


# 11. Deterministic repeated extraction
def test_deterministic_repeated_extraction() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(
        title="Staff Python Engineer",
        description=(
            "Requirements:\n"
            "- 5+ years experience in Python and FastAPI.\n"
            "- Deep understanding of PostgreSQL and Redis.\n"
            "- Bachelor's degree in Computer Science.\n"
            "Nice to have:\n"
            "- Docker and Kubernetes.\n"
            "- AWS Certified."
        ),
    )
    first_run = extractor.extract(job)
    for _ in range(5):
        run = extractor.extract(job)
        assert len(run) == len(first_run)
        for r1, r2 in zip(first_run, run, strict=True):
            assert r1.type == r2.type
            assert r1.normalized_skill == r2.normalized_skill
            assert r1.required_level == r2.required_level
            assert r1.importance == r2.importance
            assert r1.criticality == r2.criticality


# 12. Normalization of known equivalent spellings
def test_normalization_of_known_equivalent_spellings() -> None:
    extractor = DeterministicRequirementExtractor()
    job = _make_job(description="Experience with k8s, Postgres, Golang, and JS.")
    reqs = extractor.extract(job)
    skills = {r.normalized_skill for r in reqs if r.type == RequirementType.SKILL}

    assert "Kubernetes" in skills
    assert "PostgreSQL" in skills
    assert "Go" in skills
    assert "JavaScript" in skills


# 13. Distinction between genuinely different skills
def test_distinction_between_genuinely_different_skills() -> None:
    extractor = DeterministicRequirementExtractor()

    # Case A: PostgreSQL alone must NOT extract SQL
    job_pg = _make_job(description="Requires deep knowledge of PostgreSQL.")
    skills_pg = {r.normalized_skill for r in extractor.extract(job_pg)}
    assert "PostgreSQL" in skills_pg
    assert "SQL" not in skills_pg

    # Case B: FastAPI must NOT extract bare API
    job_fastapi = _make_job(description="Build microservices using FastAPI.")
    skills_fastapi = {r.normalized_skill for r in extractor.extract(job_fastapi)}
    assert "FastAPI" in skills_fastapi
    assert "REST API" not in skills_fastapi

    # Case C: JavaScript must NOT extract Java
    job_js = _make_job(description="Frontend work in JavaScript.")
    skills_js = {r.normalized_skill for r in extractor.extract(job_js)}
    assert "JavaScript" in skills_js
    assert "Java" not in skills_js

    # Case D: Java alone must NOT extract JavaScript
    job_java = _make_job(description="Enterprise backend in Java 17.")
    skills_java = {r.normalized_skill for r in extractor.extract(job_java)}
    assert "Java" in skills_java
    assert "JavaScript" not in skills_java

    # Case E: Both PostgreSQL and SQL mentioned explicitly
    job_both = _make_job(description="Must know SQL and PostgreSQL.")
    skills_both = {r.normalized_skill for r in extractor.extract(job_both)}
    assert "SQL" in skills_both
    assert "PostgreSQL" in skills_both
