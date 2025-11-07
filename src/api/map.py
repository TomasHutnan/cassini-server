"""Map-related API endpoints."""

from fastapi import APIRouter, Query
from examples.hexwater_prototype import generate_map
router = APIRouter(prefix="/map", tags=["map"])


@router.get("/")
async def get_map(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate"),
    range: int = Query(200, description="Range in meters", ge=50, le=5000),
):
    """Fetch the map with all buildings and resource information.

    Example usage: http://localhost:8000/map/?lat=48.1486&lon=17.1077&range=200

    Args:
        lat: Latitude of the center point
        lon: Longitude of the center point
        range: Range in meters (default: 200m)

    Returns:
        Dictionary containing tile information with biomes, buildings, and resources
    """
    # TODO: Implement actual map generation using Copernicus data
    return {
        "center": {"lat": lat, "lon": lon},
        "range_m": range,
        "tiles": generate_map(lat,lon,range),
        "message": "Map generation not yet implemented",
    }
