"""Pydantic models for building-related API requests and responses."""

from datetime import datetime
from pydantic import BaseModel, Field

from src.game_objects.resources import Resource
from src.game_objects.biome import BiomeType


class BuildingCreate(BaseModel):
    """Data for creating a new building."""

    h3_index: str = Field(..., description="H3 hexagonal index where building is placed")
    name: str = Field(..., min_length=1, max_length=255, description="Building name")
    biome_type: BiomeType = Field(..., description="Biome type of the location")
    resource_type: Resource = Field(..., description="Resource type produced by building")


class BuildingResponse(BaseModel):
    """Building information response."""

    h3_index: str
    user_id: str
    name: str
    biome_type: str
    resource_type: str
    level: int
    last_claim_at: datetime
    created_at: datetime
    updated_at: datetime


class BuildingListResponse(BaseModel):
    """Response for listing buildings."""

    buildings: list[BuildingResponse]
    total: int


class ClaimResourcesResponse(BaseModel):
    """Response from claiming building resources."""

    resources_claimed: int
    resource_type: str
    new_inventory_total: int
    seconds_elapsed: float
