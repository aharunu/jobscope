"""Comprehensive unit tests for the deterministic matching engine and evaluators."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import RequirementType
from backend.domain.matching.deterministic_engine import (
    BLOCKER_SCORE_CAP,
    DeterministicMatchEngine,
)
from backend.domain.matching.enums import MatchStatus
from backend.domain.matching.evaluators.education_evaluator import (
    EducationEvaluator,
)
from backend.domain.matching.evaluators.experience_evaluator import (
    ExperienceEvaluator,
)
from backend.domain.matching.evaluators.location_evaluator import (
    LocationEvaluator,
)
from backend.domain.matching.evaluators.other_evaluator import (
    OtherRequirementEvaluator,
)
from backend.domain.matching.evaluators.role_evaluator import RoleEvaluator
from backend.domain.matching.evaluators.skill_evaluator import SkillEvaluator
from backend.domain.profile.entities import (
    BaseProfile,
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
    ProfileSkill,
)
from backend.domain.search_profile.entities import SearchProfile

# ============================================================================
# Fixtures
# ============================================================================


def make_job(
    title: str = "Senior Backend Engineer",
    location: str | None = "Istanbul",
    work_mode: str | None = "Hybrid",
    requirements: list[JobRequirement] | None = None,
) -> Job:
    job_id = uuid.uuid4()
    reqs = []
    if requirements:
        for r in requirements:
            reqs.append(
                JobRequirement(
                    id=r.id,
                    job_id=job_id,
                    type=r.type,
                    description=r.description,
                    normalized_skill=r.normalized_skill,
                    required_level=r.required_level,
                    importance=r.importance,
                    criticality=r.criticality,
                    evidence=r.evidence,
                )
            )
    return Job(
        id=job_id,
        source_id=uuid.uuid4(),
        canonical_url="https://jobs.example.com/1",
        company="Acme Corp",
        title=title,
        description="We are looking for an experienced engineer.",
        content_hash="dummyhash",
        location=location,
        work_mode=work_mode,
        requirements=reqs,
    )


def make_profile(
    skills: list[str] | None = None,
    experience_years: float = 3.0,
    education_degree: str = "Bachelor's Degree",
    education_field: str = "Computer Science",
    languages: list[str] | None = None,
) -> BaseProfile:
    user_id = uuid.uuid4()
    bp_id = uuid.uuid4()
    profile_skills = []
    if skills:
        for s in skills:
            profile_skills.append(ProfileSkill(base_profile_id=bp_id, name=s))
    if languages:
        for lang in languages:
            profile_skills.append(
                ProfileSkill(
                    base_profile_id=bp_id,
                    name=lang,
                    category="language",
                )
            )

    experiences = []
    if experience_years > 0:
        days = int(experience_years * 365.25)
        start_date = date.today() - timedelta(days=days)
        experiences.append(
            ProfileExperience(
                base_profile_id=bp_id,
                company="Tech Co",
                title="Software Engineer",
                start_date=start_date,
                is_current=True,
            )
        )

    educations = []
    if education_degree:
        educations.append(
            ProfileEducation(
                base_profile_id=bp_id,
                school="Tech University",
                degree=education_degree,
                field_of_study=education_field,
            )
        )

    return BaseProfile(
        id=bp_id,
        user_id=user_id,
        name="John Doe",
        skills=profile_skills,
        experiences=experiences,
        educations=educations,
    )


def make_search_profile(
    base_profile_id: uuid.UUID,
    target_roles: list[str] | None = None,
    target_skills: list[str] | None = None,
    locations: list[str] | None = None,
    work_modes: list[str] | None = None,
) -> SearchProfile:
    return SearchProfile(
        base_profile_id=base_profile_id,
        name="Main Search",
        target_roles=target_roles or ["Backend Engineer"],
        target_skills=target_skills or [],
        locations=locations or ["Istanbul"],
        work_modes=work_modes or ["Hybrid"],
    )


# ============================================================================
# 1. Role Evaluator Tests
# ============================================================================


def test_role_evaluator_exact_match() -> None:
    evaluator = RoleEvaluator()
    job = make_job(title="AI Engineer")
    bp = make_profile()
    sp = make_search_profile(bp.id, target_roles=["AI Engineer"])

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.MATCHED
    assert res.score == Decimal("1.00")
    assert "exactly matches" in res.reason


def test_role_evaluator_subsumption_and_token_overlap() -> None:
    evaluator = RoleEvaluator()
    job = make_job(title="Senior Backend Software Engineer")
    bp = make_profile()
    sp = make_search_profile(bp.id, target_roles=["Backend Engineer"])

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.MATCHED
    assert res.score == Decimal("1.00")
    assert "closely matches" in res.reason


def test_role_evaluator_partial_overlap() -> None:
    evaluator = RoleEvaluator()
    job = make_job(title="Data Engineer")
    bp = make_profile()
    sp = make_search_profile(bp.id, target_roles=["Data Scientist"])

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.PARTIAL
    assert Decimal("0.40") <= res.score <= Decimal("0.70")


def test_role_evaluator_not_matched() -> None:
    evaluator = RoleEvaluator()
    job = make_job(title="Product Designer")
    bp = make_profile()
    sp = make_search_profile(bp.id, target_roles=["Backend Engineer"])

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.NOT_MATCHED
    assert res.score == Decimal("0.00")


def test_role_evaluator_unknown_when_missing() -> None:
    evaluator = RoleEvaluator()
    job = make_job(title="")
    bp = make_profile()
    sp = make_search_profile(bp.id, target_roles=[])

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.UNKNOWN
    assert res.known_signals == 0


# ============================================================================
# 2. Skill Evaluator Tests
# ============================================================================


def test_skill_evaluator_exact_and_alias_match() -> None:
    evaluator = SkillEvaluator()
    req_py = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Python programming",
        normalized_skill="Python",
    )
    req_pg = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Postgres database",
        normalized_skill="postgresql",
    )
    job = make_job(requirements=[req_py, req_pg])

    # Candidate has "python" and alias "postgres"
    bp = make_profile(skills=["python", "postgres"])
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.MATCHED
    assert res.score == Decimal("1.00")
    assert len(res.evaluated_requirements) == 2
    assert all(
        eq.match_status == MatchStatus.MATCHED for eq in res.evaluated_requirements
    )


def test_skill_evaluator_missing_skills_partial_and_not_matched() -> None:
    evaluator = SkillEvaluator()
    req_py = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Python",
        normalized_skill="Python",
    )
    req_docker = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Docker",
        normalized_skill="Docker",
    )
    job = make_job(requirements=[req_py, req_docker])

    # Candidate only has Python
    bp = make_profile(skills=["Python"])
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.PARTIAL
    assert res.score == Decimal("0.50")
    assert res.evaluated_requirements[0].match_status == MatchStatus.MATCHED
    assert res.evaluated_requirements[1].match_status == MatchStatus.NOT_MATCHED


def test_skill_evaluator_unknown_when_profile_empty() -> None:
    evaluator = SkillEvaluator()
    req_py = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Python",
        normalized_skill="Python",
    )
    job = make_job(requirements=[req_py])
    bp = make_profile(skills=[])  # Empty skills
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.UNKNOWN
    assert res.evaluated_requirements[0].match_status == MatchStatus.UNKNOWN


def test_skill_evaluator_finds_project_skills() -> None:
    evaluator = SkillEvaluator()
    req_k8s = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Kubernetes",
        normalized_skill="Kubernetes",
    )
    job = make_job(requirements=[req_k8s])
    bp = make_profile(skills=["Python"])
    bp.projects.append(
        ProfileProject(
            base_profile_id=bp.id,
            title="Kube Cluster",
            skills_used=["k8s"],
        )
    )
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.MATCHED
    assert res.score == Decimal("1.00")


# ============================================================================
# 3. Experience Evaluator Tests
# ============================================================================


def test_experience_evaluator_satisfied() -> None:
    evaluator = ExperienceEvaluator()
    req = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EXPERIENCE,
        description="3+ years of professional software experience",
    )
    job = make_job(requirements=[req])
    bp = make_profile(experience_years=5.0)
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.MATCHED
    assert res.score == Decimal("1.00")
    assert res.evaluated_requirements[0].match_status == MatchStatus.MATCHED


def test_experience_evaluator_partial() -> None:
    evaluator = ExperienceEvaluator()
    req = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EXPERIENCE,
        description="3+ years of experience",
    )
    job = make_job(requirements=[req])
    # 2.2 years out of 3 years
    bp = make_profile(experience_years=2.2)
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.PARTIAL
    assert Decimal("0.50") <= res.score <= Decimal("0.85")


def test_experience_evaluator_not_matched() -> None:
    evaluator = ExperienceEvaluator()
    req = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EXPERIENCE,
        description="5+ years of experience",
    )
    job = make_job(requirements=[req])
    bp = make_profile(experience_years=1.0)
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.NOT_MATCHED
    assert res.score == Decimal("0.00")


def test_experience_evaluator_unknown_when_no_job_requirement() -> None:
    evaluator = ExperienceEvaluator()
    job = make_job(requirements=[])
    bp = make_profile(experience_years=3.0)
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.UNKNOWN
    assert res.score == Decimal("1.00")
    assert res.known_signals == 0


# ============================================================================
# 4. Education Evaluator Tests
# ============================================================================


def test_education_evaluator_matched() -> None:
    evaluator = EducationEvaluator()
    req = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EDUCATION,
        description="Bachelor's Degree in Computer Science",
        normalized_skill="Computer Science",
    )
    job = make_job(requirements=[req])
    bp = make_profile(
        education_degree="Bachelor's Degree",
        education_field="Computer Science",
    )
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.MATCHED
    assert res.score == Decimal("1.00")


def test_education_evaluator_degree_hierarchy_higher_satisfies() -> None:
    evaluator = EducationEvaluator()
    req = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EDUCATION,
        description="Bachelor's degree required",
    )
    job = make_job(requirements=[req])
    # Candidate has Master's Degree
    bp = make_profile(
        education_degree="Master's Degree",
        education_field="Software Engineering",
    )
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.MATCHED
    assert res.score == Decimal("1.00")


def test_education_evaluator_unknown_when_not_specified() -> None:
    evaluator = EducationEvaluator()
    job = make_job(requirements=[])
    bp = make_profile()
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.UNKNOWN
    assert "Job does not specify an education requirement" in res.reason


# ============================================================================
# 5. Location / Work Mode Evaluator Tests
# ============================================================================


def test_location_evaluator_remote_matched() -> None:
    evaluator = LocationEvaluator()
    job = make_job(location="Anywhere", work_mode="Remote")
    bp = make_profile()
    sp = make_search_profile(bp.id, locations=["Istanbul"], work_modes=["Remote"])

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.MATCHED
    assert res.score == Decimal("1.00")


def test_location_evaluator_explicit_mismatch() -> None:
    evaluator = LocationEvaluator()
    job = make_job(location="Berlin, Germany", work_mode="On-site")
    bp = make_profile()
    sp = make_search_profile(bp.id, locations=["Istanbul"], work_modes=["Remote"])

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.NOT_MATCHED
    assert res.score == Decimal("0.00")


def test_location_evaluator_unknown_when_metadata_absent() -> None:
    evaluator = LocationEvaluator()
    job = make_job(location=None, work_mode=None)
    bp = make_profile()
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, [], bp, sp)
    assert res.status == MatchStatus.UNKNOWN
    assert res.known_signals == 0


# ============================================================================
# 6. Language & Secondary Requirements Evaluator Tests
# ============================================================================


def test_other_evaluator_language_matched_and_missing() -> None:
    evaluator = OtherRequirementEvaluator()
    req_eng = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.LANGUAGE,
        description="Fluent in English",
        normalized_skill="English",
    )
    req_ger = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.LANGUAGE,
        description="German required",
        normalized_skill="German",
    )
    job = make_job(requirements=[req_eng, req_ger])
    bp = make_profile(languages=["English"])
    sp = make_search_profile(bp.id)

    res = evaluator.evaluate(job, job.requirements, bp, sp)
    assert res.status == MatchStatus.PARTIAL
    assert res.score == Decimal("0.50")
    assert res.evaluated_requirements[0].match_status == MatchStatus.MATCHED
    assert res.evaluated_requirements[1].match_status == MatchStatus.NOT_MATCHED


# ============================================================================
# 7. DeterministicMatchEngine Full Integration & Scoring Weights
# ============================================================================


def test_engine_weights_and_overall_score() -> None:
    """Verify weights sum to 100% and overall score is derived correctly."""
    engine = DeterministicMatchEngine()

    req_py = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Python",
        normalized_skill="Python",
    )
    req_exp = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EXPERIENCE,
        description="3+ years of experience",
    )
    req_edu = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EDUCATION,
        description="Bachelor's Degree",
    )
    job = make_job(
        title="Backend Engineer",
        location="Istanbul",
        work_mode="Hybrid",
        requirements=[req_py, req_exp, req_edu],
    )

    # Perfect match across all categories
    bp = make_profile(
        skills=["Python"],
        experience_years=4.0,
        education_degree="Bachelor's Degree",
    )
    sp = make_search_profile(
        base_profile_id=bp.id,
        target_roles=["Backend Engineer"],
        locations=["Istanbul"],
        work_modes=["Hybrid"],
    )

    mr = engine.evaluate(job=job, base_profile=bp, search_profile=sp)

    assert mr.deterministic_score == Decimal("100.00")
    assert mr.final_score == Decimal("100.00")
    assert mr.category_scores["ROLE"] == Decimal("1.00")
    assert mr.category_scores["SKILLS"] == Decimal("1.00")
    assert mr.category_scores["EXPERIENCE"] == Decimal("1.00")
    assert mr.category_scores["LOCATION_WORK_MODE"] == Decimal("1.00")
    assert mr.category_scores["EDUCATION"] == Decimal("1.00")


def test_engine_blocker_capping() -> None:
    """Verify that an unmet BLOCKER requirement caps overall score at 40.0."""
    engine = DeterministicMatchEngine()

    # Blocker requirement that candidate fails
    req_blocker = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Mandatory PyTorch production experience",
        normalized_skill="PyTorch",
        criticality="BLOCKER",
    )
    req_exp = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EXPERIENCE,
        description="2+ years",
    )
    job = make_job(
        title="AI Engineer",
        location="Istanbul",
        work_mode="Hybrid",
        requirements=[req_blocker, req_exp],
    )

    # Candidate has everything EXCEPT PyTorch
    bp = make_profile(skills=["Python"], experience_years=5.0)
    sp = make_search_profile(bp.id, target_roles=["AI Engineer"])

    mr = engine.evaluate(job=job, base_profile=bp, search_profile=sp)

    assert mr.deterministic_score <= BLOCKER_SCORE_CAP
    assert mr.final_score <= BLOCKER_SCORE_CAP
    assert mr.explanation is not None
    assert len(mr.explanation.blockers) > 0
    assert any("PyTorch" in b for b in mr.explanation.blockers)


def test_engine_confidence_calculation() -> None:
    """Verify confidence reflects evidence completeness and drops with unknown data."""
    engine = DeterministicMatchEngine()

    # Case A: Complete data
    req_py = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Python",
        normalized_skill="Python",
    )
    req_exp = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EXPERIENCE,
        description="3+ years",
    )
    req_edu = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.EDUCATION,
        description="Bachelor's Degree",
    )
    job_complete = make_job(
        title="Backend Engineer",
        location="Istanbul",
        work_mode="Hybrid",
        requirements=[req_py, req_exp, req_edu],
    )
    bp_complete = make_profile(
        skills=["Python"],
        experience_years=3.0,
        education_degree="Bachelor's Degree",
    )
    sp_complete = make_search_profile(bp_complete.id, target_roles=["Backend Engineer"])

    mr_complete = engine.evaluate(job_complete, bp_complete, sp_complete)
    assert mr_complete.confidence >= Decimal("80.00")

    # Case B: Incomplete data (unknown role, location, education)
    job_incomplete = make_job(
        title="",
        location=None,
        work_mode=None,
        requirements=[req_py],
    )
    bp_empty = BaseProfile(user_id=uuid.uuid4(), name="Jane")
    sp_empty = SearchProfile(base_profile_id=bp_empty.id, name="Empty")

    mr_incomplete = engine.evaluate(job_incomplete, bp_empty, sp_empty)
    assert mr_incomplete.confidence < mr_complete.confidence


def test_engine_determinism_stability() -> None:
    """Verify running the engine multiple times produces identical output."""
    engine = DeterministicMatchEngine()

    req_py = JobRequirement(
        job_id=uuid.uuid4(),
        type=RequirementType.SKILL,
        description="Python",
        normalized_skill="Python",
    )
    job = make_job(
        title="Software Engineer",
        location="Istanbul",
        requirements=[req_py],
    )
    bp = make_profile(skills=["Python"], experience_years=3.0)
    sp = make_search_profile(bp.id, target_roles=["Software Engineer"])

    mr1 = engine.evaluate(job, bp, sp)
    mr2 = engine.evaluate(job, bp, sp)

    assert mr1.deterministic_score == mr2.deterministic_score
    assert mr1.final_score == mr2.final_score
    assert mr1.confidence == mr2.confidence
    assert mr1.category_scores == mr2.category_scores
    assert mr1.explanation.summary == mr2.explanation.summary
    assert len(mr1.requirement_matches) == len(mr2.requirement_matches)
    for rm1, rm2 in zip(mr1.requirement_matches, mr2.requirement_matches, strict=False):
        assert rm1.match_status == rm2.match_status
        assert rm1.score == rm2.score
        assert rm1.reason == rm2.reason
