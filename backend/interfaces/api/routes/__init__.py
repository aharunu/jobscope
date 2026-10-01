from backend.interfaces.api.routes.applications import (
    router as applications_router,
)
from backend.interfaces.api.routes.crawl import router as crawl_router
from backend.interfaces.api.routes.health import router as health_router
from backend.interfaces.api.routes.jobs import router as jobs_router
from backend.interfaces.api.routes.matching import router as matching_router
from backend.interfaces.api.routes.profile import router as profile_router
from backend.interfaces.api.routes.search_profile import (
    router as search_profile_router,
)
from backend.interfaces.api.routes.sources import router as sources_router

__all__ = [
    "applications_router",
    "crawl_router",
    "health_router",
    "jobs_router",
    "matching_router",
    "profile_router",
    "search_profile_router",
    "sources_router",
]
