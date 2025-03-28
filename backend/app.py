# app.py - Main FastAPI application for ZealX Backend

import os
import sys
import time
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from logging.config import dictConfig
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
import asyncio

# Add project root to path
sys.path.append(os.path.abspath("/Users/momo/Desktop/x"))

# Import ZealX components
from zealx import ZealX
from storagex.storagex import StorageX
from autox_ai.autox_core import AutoX
from autox_ai.autox_ai import AutoXAI
from autox_ai.adx_enhanced import ADXEnhanced

# Import backend components
from backend.core.config import Settings
from backend.core.logging_manager import logging_manager
from backend.core.firelayers import fire_layers
from backend.middleware.api_account_manager import APIAccountManager
from backend.middleware.error_handlers import setup_error_handlers
from backend.middleware.security import setup_security_middleware
from backend.routers import api_router

# Configure logging
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": True
        },
        "uvicorn.error": {
            "level": "INFO",
        },
        "uvicorn.access": {
            "level": "INFO",
        },
    },
}
dictConfig(logging_config)
logger = logging.getLogger(__name__)

# Initialize components on startup and shutdown on app termination
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load settings
    settings = Settings()
    app.state.settings = settings
    
    # Initialize Redis
    logger.info("Connecting to Redis...")
    redis_client = redis.from_url(settings.redis_url)
    app.state.redis = redis_client
    
    # Initialize API Account Manager
    logger.info("Initializing API Account Manager...")
    api_manager = APIAccountManager(redis_client, settings)
    await api_manager.initialize()
    app.state.api_manager = api_manager
    
    # Initialize StorageX
    logger.info("Initializing StorageX...")
    storage = StorageX()
    app.state.storage = storage
    
    # Initialize FireLayers X++
    logger.info("Initializing FireLayers X++...")
    app.state.fire_layers = fire_layers
    
    # Initialize other components
    logger.info("Initializing ZealX Backend components...")
    app.state.zealx_instances = {}
    
    # Start background tasks
    logger.info("Starting background tasks...")
    app.state.background_tasks = set()
    api_health_task = asyncio.create_task(api_manager.run_health_checks())
    app.state.background_tasks.add(api_health_task)
    api_health_task.add_done_callback(lambda t: app.state.background_tasks.remove(t))
    
    logger.info("ZealX Backend initialized and ready!")
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down ZealX Backend...")
    
    # Cancel all background tasks
    for task in app.state.background_tasks:
        task.cancel()
    
    # Wait for tasks to complete
    await asyncio.gather(*app.state.background_tasks, return_exceptions=True)
    
    # Close API Account Manager
    await api_manager.close()
    
    # Close Redis connection
    await redis_client.close()
    
    # Close logging manager
    logging_manager.close()
    
    # Shutdown all active ZealX instances
    for user_id, zealx in app.state.zealx_instances.items():
        zealx.stop()
    
    logger.info("ZealX Backend shutdown complete")

# Create FastAPI app with lifespan management
app = FastAPI(
    title="ZealX API",
    description="AI-powered digital twin and automation system API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if Settings().debug else None,
    redoc_url="/redoc" if Settings().debug else None,
    openapi_url="/openapi.json" if Settings().debug else None,
)

# Add middleware to inject API manager into request state
@app.middleware("http")
async def add_api_manager_middleware(request: Request, call_next):
    request.state.api_manager = request.app.state.api_manager
    response = await call_next(request)
    return response

# Add request processing time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Setup middleware
settings = Settings()
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# Setup security middleware (CORS, rate limiting, API key auth)
setup_security_middleware(app, settings, redis_client)

# Setup error handlers
setup_error_handlers(app)

# Include routers
app.include_router(api_router.router)

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to ZealX API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs" if settings.debug else "Documentation disabled in production"
    }

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": "production" if not settings.debug else "development"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)