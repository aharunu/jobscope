"""Matching ORM persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.matching.entities import (
    AIAnalysis,
    AIEvidence,
    MatchResult,
    RequirementMatch,
)
from backend.domain.matching.enums import MatchStatus
from backend.infrastructure.database.base import (
    Base,
    BaseModel,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from backend.infrastructure.database.models.base_profile import (
        BaseProfileModel,
    )
    from backend.infrastructure.database.models.job import (
        JobModel,
        JobRequirementModel,
    )
    from backend.infrastructure.database.models.search_profile import (
        SearchProfileModel,
    )


class MatchResultModel(BaseModel):
    """SQLAlchemy ORM model for the match_results table."""

    __tablename__ = "match_results"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    base_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("base_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    search_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("search_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deterministic_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    ai_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    ai_adjustment: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2),
        default=Decimal("0.0"),
        server_default=sa.text("0.0"),
        nullable=True,
    )
    final_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "base_profile_id",
            "search_profile_id",
            name="uq_match_results_job_base_search",
        ),
    )

    # Relationships
    job: Mapped[JobModel] = relationship(
        "JobModel",
        back_populates="match_results",
    )
    base_profile: Mapped[BaseProfileModel] = relationship(
        "BaseProfileModel",
        back_populates="match_results",
    )
    search_profile: Mapped[SearchProfileModel] = relationship(
        "SearchProfileModel",
        back_populates="match_results",
    )
    requirement_matches: Mapped[list[RequirementMatchModel]] = relationship(
        "RequirementMatchModel",
        back_populates="match_result",
        cascade="all, delete-orphan",
    )
    ai_analysis: Mapped[AIAnalysisModel | None] = relationship(
        "AIAnalysisModel",
        back_populates="match_result",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> MatchResult:
        """Convert ORM model to domain entity."""
        return MatchResult(
            id=self.id,
            job_id=self.job_id,
            base_profile_id=self.base_profile_id,
            search_profile_id=self.search_profile_id,
            deterministic_score=self.deterministic_score,
            ai_score=self.ai_score,
            ai_adjustment=self.ai_adjustment,
            final_score=self.final_score,
            confidence=self.confidence,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, res: MatchResult) -> MatchResultModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": res.id,
            "job_id": res.job_id,
            "base_profile_id": res.base_profile_id,
            "search_profile_id": res.search_profile_id,
            "deterministic_score": res.deterministic_score,
            "ai_score": res.ai_score,
            "ai_adjustment": res.ai_adjustment,
            "final_score": res.final_score,
            "confidence": res.confidence,
        }
        if res.created_at is not None:
            kwargs["created_at"] = res.created_at
        if res.updated_at is not None:
            kwargs["updated_at"] = res.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<MatchResultModel id={self.id} final_score={self.final_score} "
            f"confidence={self.confidence}>"
        )


class RequirementMatchModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy ORM model for the requirement_matches table."""

    __tablename__ = "requirement_matches"

    match_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("match_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_status: Mapped[MatchStatus] = mapped_column(
        SQLEnum(MatchStatus, native_enum=False, length=50),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    is_blocker: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=sa.text("false"),
        nullable=False,
    )

    # Relationships
    match_result: Mapped[MatchResultModel] = relationship(
        "MatchResultModel",
        back_populates="requirement_matches",
    )
    requirement: Mapped[JobRequirementModel] = relationship(
        "JobRequirementModel",
        back_populates="matches",
    )

    def to_domain(self) -> RequirementMatch:
        """Convert ORM model to domain entity."""
        return RequirementMatch(
            id=self.id,
            match_result_id=self.match_result_id,
            requirement_id=self.requirement_id,
            match_status=self.match_status,
            score=self.score,
            evidence=self.evidence,
            reason=self.reason,
            is_blocker=self.is_blocker,
        )

    @classmethod
    def from_domain(cls, match: RequirementMatch) -> RequirementMatchModel:
        """Construct ORM model from domain entity."""
        return cls(
            id=match.id,
            match_result_id=match.match_result_id,
            requirement_id=match.requirement_id,
            match_status=match.match_status,
            score=match.score,
            evidence=match.evidence,
            reason=match.reason,
            is_blocker=match.is_blocker,
        )

    def __repr__(self) -> str:
        status_val = getattr(self.match_status, "value", self.match_status)
        return (
            f"<RequirementMatchModel id={self.id} match_status={status_val!r} "
            f"score={self.score}>"
        )


class AIAnalysisModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy ORM model for the ai_analyses table."""

    __tablename__ = "ai_analyses"

    match_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("match_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    assessment: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    match_result: Mapped[MatchResultModel] = relationship(
        "MatchResultModel",
        back_populates="ai_analysis",
    )
    evidence_list: Mapped[list[AIEvidenceModel]] = relationship(
        "AIEvidenceModel",
        back_populates="ai_analysis",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> AIAnalysis:
        """Convert ORM model to domain entity."""
        return AIAnalysis(
            id=self.id,
            match_result_id=self.match_result_id,
            model=self.model,
            provider=self.provider,
            ai_score=self.ai_score,
            assessment=self.assessment,
            summary=self.summary,
            fingerprint=self.fingerprint,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, analysis: AIAnalysis) -> AIAnalysisModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": analysis.id,
            "match_result_id": analysis.match_result_id,
            "model": analysis.model,
            "provider": analysis.provider,
            "ai_score": analysis.ai_score,
            "assessment": analysis.assessment,
            "summary": analysis.summary,
            "fingerprint": analysis.fingerprint,
        }
        if analysis.created_at is not None:
            kwargs["created_at"] = analysis.created_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<AIAnalysisModel id={self.id} model={self.model!r} "
            f"ai_score={self.ai_score}>"
        )


class AIEvidenceModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy ORM model for the ai_evidence table."""

    __tablename__ = "ai_evidence"

    ai_analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    ai_analysis: Mapped[AIAnalysisModel] = relationship(
        "AIAnalysisModel",
        back_populates="evidence_list",
    )

    def to_domain(self) -> AIEvidence:
        """Convert ORM model to domain entity."""
        return AIEvidence(
            id=self.id,
            ai_analysis_id=self.ai_analysis_id,
            claim=self.claim,
            evidence_type=self.evidence_type,
            source_reference=self.source_reference,
            reason=self.reason,
        )

    @classmethod
    def from_domain(cls, ev: AIEvidence) -> AIEvidenceModel:
        """Construct ORM model from domain entity."""
        return cls(
            id=ev.id,
            ai_analysis_id=ev.ai_analysis_id,
            claim=ev.claim,
            evidence_type=ev.evidence_type,
            source_reference=ev.source_reference,
            reason=ev.reason,
        )

    def __repr__(self) -> str:
        return f"<AIEvidenceModel id={self.id} evidence_type={self.evidence_type!r}>"
