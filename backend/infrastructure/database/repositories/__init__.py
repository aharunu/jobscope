"""Database repositories package."""

from backend.infrastructure.database.repositories.application_repository import (
    SQLAlchemyApplicationRepository,
)
from backend.infrastructure.database.repositories.base_profile_repository import (
    SQLAlchemyBaseProfileRepository,
)
from backend.infrastructure.database.repositories.crawl_run_repository import (
    SQLAlchemyCrawlRunRepository,
)
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
    SQLAlchemyRawJobRepository,
)
from backend.infrastructure.database.repositories.job_requirement_repository import (
    SQLAlchemyJobRequirementRepository,
)
from backend.infrastructure.database.repositories.matching_repository import (
    SQLAlchemyMatchResultRepository,
)
from backend.infrastructure.database.repositories.profile_child_repositories import (
    SQLAlchemyProfileEducationRepository,
    SQLAlchemyProfileExperienceRepository,
    SQLAlchemyProfileProjectRepository,
    SQLAlchemyProfileSkillRepository,
)
from backend.infrastructure.database.repositories.search_profile_repository import (
    SQLAlchemySearchProfileRepository,
)
from backend.infrastructure.database.repositories.source_repository import (
    SQLAlchemySourceRepository,
)

__all__ = [
    "SQLAlchemyApplicationRepository",
    "SQLAlchemyBaseProfileRepository",
    "SQLAlchemyCrawlRunRepository",
    "SQLAlchemyJobRepository",
    "SQLAlchemyJobRequirementRepository",
    "SQLAlchemyMatchResultRepository",
    "SQLAlchemyProfileEducationRepository",
    "SQLAlchemyProfileExperienceRepository",
    "SQLAlchemyProfileProjectRepository",
    "SQLAlchemyProfileSkillRepository",
    "SQLAlchemyRawJobRepository",
    "SQLAlchemySearchProfileRepository",
    "SQLAlchemySourceRepository",
]
