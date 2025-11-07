from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import map, buildings
from src.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Geo-MMO City Builder API",
    description="A geospatially-aware MMO city builder powered by Copernicus data",
    version="0.1.0",
    debug=settings.DEBUG,
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
app.include_router(map.router)
app.include_router(buildings.router)


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
