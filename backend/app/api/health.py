import logging
import time
from typing import Any, Dict
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings

# Setup logger for health monitoring
logger = logging.getLogger("imaction.health")
router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Perform a system health check",
    response_description="Detailed system health metadata"
)
def check_health(response: Response, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Performs a high-fidelity system health check:
    1. Verifies the FastAPI application is alive and responding.
    2. Runs a lightweight `SELECT 1` ping query against PostgreSQL.
    3. Measures and reports database round-trip response latency.
    4. Dynamically updates the HTTP status code to 503 if database connectivity is broken.
    """
    health_status = "healthy"
    database_status = "connected"
    latency_ms = 0.0

    start_time = time.time()
    try:
        if db is None:
            raise RuntimeError("Database session provider is not available.")
        
        # Lightweight ping query to PostgreSQL
        db.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start_time) * 1000, 2)
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        health_status = "unhealthy"
        database_status = "disconnected"
        # Set response status code to Service Unavailable
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": health_status,
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": {
            "status": database_status,
            "latency_ms": latency_ms if database_status == "connected" else None
        },
        "debug_mode": settings.DEBUG,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
