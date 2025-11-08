"""Map-related API endpoints."""

from fastapi import APIRouter, Query
from src.copernicus.main import get_map_data
from src.api.models.map import MapResponse, MapCenter, TileResponse

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/", response_model=MapResponse)
async def get_map(
    lat: float = Query(..., description="Latitude coordinate", ge=-90, le=90),
    lon: float = Query(..., description="Longitude coordinate", ge=-180, le=180),
    range_m: int = Query(200, description="Range in meters", ge=50, le=5000),
):
    """Fetch the map with biome and water feature information.

    This endpoint generates a hexagonal tile map centered at the given coordinates,
    including Copernicus biome data and EU-Hydro river/lake information.

    Example usage: 
    - `GET /map/?lat=48.1486&lon=17.1077&range_m=200`
    - `GET /map/?lat=50.0755&lon=14.4378&range_m=500` (Prague)

    Args:
        lat: Latitude of the center point (-90 to 90)
        lon: Longitude of the center point (-180 to 180)
        range_m: Map range in meters (50 to 5000m, default: 200m)

    Returns:
        MapResponse containing:
        - center: Map center coordinates
        - range_m: Requested range in meters
        - tile_count: Number of tiles in the response
        - tiles: List of hexagonal tiles with biome and water data
    """
    # Fetch map data from Copernicus
    tiles_data = get_map_data(lat, lon, range_m)
    
    # Convert to response model
    tiles = [TileResponse(**tile) for tile in tiles_data]
    
    return MapResponse(
        center=MapCenter(lat=lat, lon=lon),
        range_m=range_m,
        tile_count=len(tiles),
        tiles=tiles
    )
