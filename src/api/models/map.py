"""Pydantic models for map API endpoints."""

from pydantic import BaseModel, Field


class TileResponse(BaseModel):
    """Response model for a single map tile.
    
    Each tile represents a hexagonal area with biome information.
    Water features (rivers/lakes) are represented by biome type 'WATER'.
    """
    
    hex_id: str = Field(..., description="H3 hexagonal index identifier")
    lat: float = Field(..., description="Tile center latitude")
    lon: float = Field(..., description="Tile center longitude")
    biome: str = Field(
        ..., 
        description="Biome type enum value (e.g., 'GRASSLAND', 'TREE_COVER', 'WATER')"
    )
    boundary: list[list[float]] = Field(
        ..., 
        description="Hexagon boundary coordinates as [[lat, lon], ...]"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "hex_id": "8c2a1072b3b1dff",
                "lat": 48.1486,
                "lon": 17.1077,
                "biome": "GRASSLAND",
                "boundary": [
                    [48.14865, 17.10765],
                    [48.14870, 17.10770],
                    [48.14865, 17.10775],
                    [48.14855, 17.10775],
                    [48.14850, 17.10770],
                    [48.14855, 17.10765]
                ]
            }
        }


class MapCenter(BaseModel):
    """Map center coordinates."""
    
    lat: float = Field(..., description="Center latitude")
    lon: float = Field(..., description="Center longitude")


class MapResponse(BaseModel):
    """Response model for map data.
    
    Contains hexagonal tiles with biome information from Copernicus land cover data
    and EU-Hydro water features. Rivers and lakes are represented by biome type 'WATER'.
    """
    
    center: MapCenter = Field(..., description="Map center coordinates")
    range_m: int = Field(..., description="Map range in meters")
    tile_count: int = Field(..., description="Number of tiles returned")
    tiles: list[TileResponse] = Field(..., description="List of map tiles with biome data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "center": {"lat": 48.1486, "lon": 17.1077},
                "range_m": 200,
                "tile_count": 127,
                "tiles": [
                    {
                        "hex_id": "8c2a1072b3b1dff",
                        "lat": 48.1486,
                        "lon": 17.1077,
                        "biome": "GRASSLAND",
                        "boundary": [
                            [48.14865, 17.10765],
                            [48.14870, 17.10770]
                        ]
                    }
                ]
            }
        }
