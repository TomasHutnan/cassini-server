from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.map import router as map_router
from src.api.buildings import router as buildings_router
from src.config import get_settings
from src.database import init_db_pool, close_db_pool

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    await init_db_pool()
    yield
    # Shutdown
    await close_db_pool()


app = FastAPI(
    title="Geo-MMO City Builder API",
    description="A geospatially-aware MMO city builder powered by Copernicus data",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(map_router)
app.include_router(buildings_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "running",
        "message": "Geo-MMO City Builder API",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check() -> dict[str, str | bool]:
    """Detailed health check with service status."""
    return {
        "status": "healthy",
        "copernicus_configured": settings.has_copernicus_credentials,
        "database_configured": bool(settings.DATABASE_URL),
    }
