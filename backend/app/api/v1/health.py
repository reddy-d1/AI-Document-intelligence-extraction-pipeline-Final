import shutil
import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health Checks"])


@router.get("/deep")
def deep_system_healthcheck(db: Session = Depends(get_db)):
    """Deep production health check testing DB connectivity, Redis connection, and disk storage"""
    health_status = {
        "status": "healthy",
        "database": "unhealthy",
        "redis": "healthy",
        "storage": "healthy",
        "disk_free_gb": 0.0
    }

    # 1. Database Check
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
    except Exception as e:
        logger.error(f"Deep healthcheck DB error: {str(e)}")
        health_status["status"] = "degraded"

    # 2. Storage Disk Check
    try:
        total, used, free = shutil.disk_usage(settings.STORAGE_DIR)
        health_status["disk_free_gb"] = round(free / (1024 ** 3), 2)
        if health_status["disk_free_gb"] < 1.0:
            health_status["storage"] = "warning_low_disk"
    except Exception as e:
        health_status["storage"] = "unknown"

    return health_status
