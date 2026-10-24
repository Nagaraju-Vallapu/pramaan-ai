from app.api.routes.applications import router as applications_router
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.review import router as review_router

__all__ = ["applications_router", "auth_router", "documents_router", "review_router"]