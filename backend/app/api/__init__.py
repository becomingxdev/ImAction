# ImAction CKA API Endpoints Package
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.api.analysis import router as analysis_router

__all__ = ["health_router", "search_router", "analysis_router"]



