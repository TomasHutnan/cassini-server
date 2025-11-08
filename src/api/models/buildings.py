"""Pydantic models for building-related API requests and responses."""

from pydantic import BaseModel

from src.game_objects.resources import Resource


class BuildingCreate(BaseModel):
    """Data for creating a new building."""

    hex_id: str
    name: str
    resource_type: Resource


class ClaimResourcesResponse(BaseModel):
    """Response from claiming building resources."""

    resources_claimed: int
    resource_type: str
    new_inventory_total: int
    seconds_elapsed: float
