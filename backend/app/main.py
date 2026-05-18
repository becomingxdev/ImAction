import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.core.config import settings
from app.core.database import sync_engine
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.search import router as search_router
from app.api.analysis import router as analysis_router
from app.api.challenge import router as challenge_router




# ==============================================================================
# Unified Application Logging Setup
# ==============================================================================
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("imaction.main")


# ==============================================================================
# FastAPI Lifespan Context Manager (Startup & Shutdown hooks)
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle events of the CKA FastAPI application.
    Performs startup verification checks and releases resources on shutdown.
    """
    # Startup Hook
    logger.info("==============================================================")
    logger.info(f"Initializing {settings.APP_NAME}...")
    logger.info(f"Target Environment : {settings.APP_ENV}")
    logger.info(f"Debug Mode Enabled : {settings.DEBUG}")
    
    # Only probe DB if a DATABASE_URL is explicitly configured.
    # On Cloud Run (MVP phase), the database is not yet wired — skip gracefully.
    db_url_configured = bool(settings.DATABASE_URL)
    if sync_engine is not None and db_url_configured:
        try:
            logger.info("Validating database connection pool...")
            with sync_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL database connection: SUCCESSFUL")
        except Exception as e:
            logger.warning(
                f"PostgreSQL connection check failed (non-fatal): {e}"
            )
    else:
        logger.info("Database not configured — skipping connection probe (MVP mode).")

    # Precompute and cache knowledge base document embeddings on startup
    try:
        from app.services.retrieval_service import retrieval_service
        logger.info("Precomputing knowledge base document embeddings...")
        retrieval_service.initialize_cache()
        logger.info("Semantic retrieval cache precomputation: SUCCESSFUL")
    except Exception as e:
        # Non-fatal: server still starts and handles requests.
        # Cache will be lazily rebuilt on the first search request once the API is available.
        logger.warning(
            f"Semantic retrieval cache precomputation DEFERRED — will retry on first request. "
            f"Reason: {type(e).__name__}: {e}"
        )

    logger.info(f"{settings.APP_NAME} is fully initialized and accepting requests.")
    logger.info("==============================================================")

    
    yield
    
    # Shutdown Hook
    logger.info("==============================================================")
    logger.info(f"Initiating shutdown sequence for {settings.APP_NAME}...")
    # Cleanups (e.g. closing connection pools, sync buffers) can be added here
    if sync_engine is not None:
        sync_engine.dispose()
        logger.info("PostgreSQL connection pools disposed successfully.")
    logger.info(f"Shutdown sequence complete. {settings.APP_NAME} terminated.")
    logger.info("==============================================================")


# ==============================================================================
# FastAPI App Instance
# ==============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    description="Contextual Knowledge Agent (CKA) enterprise AI backend analyzer.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None
)


# ==============================================================================
# CORS Middleware Configurations
# ==============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Global Exception Resiliency Handlers
# ==============================================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Catches client payload validation errors (Pydantic schema mismatches)
    and formats a structured, descriptive JSON error envelope.
    """
    logger.warning(
        f"Validation failure detected on '{request.method} {request.url.path}': "
        f"{exc.errors()}"
    )
    
    # Process location lists and message strings for user consumption
    formatted_details = []
    for err in exc.errors():
        formatted_details.append({
            "field": ".".join(map(str, err.get("loc", []))),
            "message": err.get("msg", ""),
            "type": err.get("type", "")
        })
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request payload failed field validation checks.",
                "details": formatted_details
            }
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Intercepts database-level exceptions (connection drops, lock conflicts, etc.).
    Masks raw SQL parameters to prevent security leakage while logging details locally.
    """
    logger.error(
        f"Database transaction failure on '{request.method} {request.url.path}': "
        f"{exc}", 
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_ERROR",
                "message": "A secure transaction error occurred on the database cluster.",
                "details": None
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Default catch-all handler for unexpected system runtime exceptions.
    Prevents raw stack trace leakage to external users while ensuring telemetry logging.
    """
    logger.error(
        f"Unhandled system exception on '{request.method} {request.url.path}': "
        f"{exc}", 
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected system runtime error occurred.",
                "details": None
            }
        }
    )


# ==============================================================================
# Router Integrations
# ==============================================================================
# Health route mounted directly to base path as requested
app.include_router(health_router)
app.include_router(knowledge_router)
app.include_router(search_router)
app.include_router(analysis_router)
app.include_router(challenge_router)


