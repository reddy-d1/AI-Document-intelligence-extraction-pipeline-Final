from fastapi import APIRouter
from app.api.v1.documents import router as documents_router
from app.api.v1.auth import router as auth_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.health import router as health_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(analytics_router)
api_router.include_router(health_router)
api_router.include_router(documents_router)


@api_router.get("/health", tags=["Health"])
async def api_health():
    """Health check endpoint for API v1"""
    return {
        "status": "healthy",
        "api_version": "v1",
        "service": "document-intelligence-api"
    }
