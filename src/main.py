import logging
import os

from fastapi import FastAPI

from src.api.deprecation import DeprecationManager
from src.api.routes import router
from src.database.connection_pool_config import ConnectionPoolConfig
from src.cache.redis_cache import RedisCache
from src.security.cors_config import setup_cors
from src.logging.request_id import RequestIDManager
from src.monitoring.latency_monitor import LatencyMonitor
from src.core.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AdvancedAIAssistant",
    description="Production-ready AI Assistant API",
    version="1.0.0",
)

setup_cors(app)
RequestIDManager.add_request_id_middleware(app)
LatencyMonitor.add_latency_middleware(app)
DeprecationManager.add_deprecation_middleware(app)
ErrorHandler.register(app)
app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    """Initialize database and cache on startup."""
    if os.getenv("APP_SKIP_STARTUP_RESOURCES", "").lower() in {"1", "true", "yes"}:
        app.state.db_pool = None
        app.state.cache = RedisCache(None)
        logger.info("Skipping startup resource initialization.")
        return

    db_cfg = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
        "database": os.getenv("DB_NAME", "advanced_ai"),
        "min_size": int(os.getenv("DB_POOL_MIN", "10")),
        "max_size": int(os.getenv("DB_POOL_MAX", "50")),
    }
    db_config = ConnectionPoolConfig(**db_cfg)

    try:
        app.state.db_pool = await db_config.initialize()
        logger.info("Database pool initialized")
    except Exception as exc:
        logger.warning("Failed to initialize database, continuing without pool: %s", exc)
        app.state.db_pool = None

    # Initialize Redis cache
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_pw = os.getenv("REDIS_PASSWORD", "redis_password")
    try:
        from aioredis import from_url as redis_from_url

        redis = await redis_from_url(f"redis://:{redis_pw}@{redis_host}:{redis_port}")
        app.state.cache = RedisCache(redis)
        logger.info("Redis cache initialized")
    except Exception as exc:
        logger.warning("Redis not available, using fallback: %s", exc)
        app.state.cache = RedisCache(None)


@app.on_event("shutdown")
async def shutdown() -> None:
    """Cleanup resources on shutdown."""
    pool = getattr(app.state, "db_pool", None)
    if pool is not None:
        try:
            await pool.close()
            logger.info("Database pool closed")
        except Exception as exc:
            logger.error("Error closing database pool: %s", exc)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AdvancedAIAssistant",
        "version": "1.0.0",
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "AdvancedAIAssistant API",
        "docs": "/docs",
        "version": "1.0.0",
    }
