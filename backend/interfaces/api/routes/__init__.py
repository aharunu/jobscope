from backend.interfaces.api.routes.crawl import router as crawl_router
from backend.interfaces.api.routes.health import router as health_router
from backend.interfaces.api.routes.sources import router as sources_router

__all__ = ["crawl_router", "health_router", "sources_router"]
