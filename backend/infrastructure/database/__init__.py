"""Database infrastructure package.

Exposes declarative base, common mixins, engine, session factory,
and health inspection utilities.
"""

from backend.infrastructure.database.base import (
    Base,
    BaseModel,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from backend.infrastructure.database.engine import (
    create_database_engine,
    dispose_engine,
    get_engine,
)
from backend.infrastructure.database.health import check_database_health
from backend.infrastructure.database.models.application import (
    ApplicationModel,
    ApplicationStatusHistoryModel,
)
from backend.infrastructure.database.models.base_profile import (
    BaseProfileModel,
    ProfileEducationModel,
    ProfileExperienceModel,
    ProfileProjectModel,
    ProfileSkillModel,
)
from backend.infrastructure.database.models.crawl_run import (
    CrawlRunJobModel,
    CrawlRunModel,
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
from backend.infrastructure.database.models.search_profile import (
    SearchProfileModel,
)
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.session import (
    create_session_factory,
    get_db_context,
    get_db_session,
    get_session_factory,
)

__all__ = [
    "AIAnalysisModel",
    "AIEvidenceModel",
    "ApplicationModel",
    "ApplicationStatusHistoryModel",
    "Base",
    "BaseModel",
    "BaseProfileModel",
    "CrawlRunJobModel",
    "CrawlRunModel",
    "JobModel",
    "JobRequirementModel",
    "MatchResultModel",
    "ProfileEducationModel",
    "ProfileExperienceModel",
    "ProfileProjectModel",
    "ProfileSkillModel",
    "RawJobModel",
    "RequirementMatchModel",
    "SearchProfileModel",
    "SourceModel",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "UserModel",
    "check_database_health",
    "create_database_engine",
    "create_session_factory",
    "dispose_engine",
    "get_db_context",
    "get_db_session",
    "get_engine",
    "get_session_factory",
]
