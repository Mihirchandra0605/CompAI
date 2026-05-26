"""API v1 routes."""

from fastapi import APIRouter

from .pipelines import router as pipelines_router
from .health import router as health_router

router = APIRouter()
router.include_router(pipelines_router, prefix="/pipelines", tags=["pipelines"])
router.include_router(health_router, prefix="/health", tags=["health"])
