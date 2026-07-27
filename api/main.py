"""FastAPI backend for ColdMail AI Pro"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.logging import logger
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""

    logger.info(
        "Starting %s v%s",
        settings.APP_NAME,
        settings.APP_VERSION,
    )

    # Initialize services here if needed
    # Example:
    # Database connection
    # Redis connection
    # ChromaDB check

    yield

    logger.info("Shutting down application.")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered autonomous cold email generation platform.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with allowed frontend origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""

    logger.exception(
        "Unhandled exception on %s: %s",
        request.url.path,
        exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal Server Error",
        },
    )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint."""

    return {
        "success": True,
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""

    return {
        "success": True,
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
    }


@app.get("/ready", tags=["System"])
async def readiness_check():
    """Readiness check endpoint."""

    return {
        "success": True,
        "ready": True,
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }