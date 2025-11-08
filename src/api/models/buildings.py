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


class ResourceAmount(BaseModel):
    """A resource type with an amount."""
    
    resource_type: str = Field(..., description="Resource type (WHEAT, WOOD, STONE)")
    amount: int = Field(..., ge=0, description="Amount of resource")


class BuildingTypeCosts(BaseModel):
    """Cost configuration for a specific building type."""
    
    base_building_cost: list[ResourceAmount] = Field(..., description="Base cost to create a building (level 1)")
    base_upgrade_cost: list[ResourceAmount] = Field(..., description="Base cost per level for upgrades")
    max_level: int = Field(..., description="Maximum building level")


class BuildingCostsResponse(BaseModel):
    """Response with building cost configuration for all building types."""
    
    WHEAT: BuildingTypeCosts = Field(..., description="Costs for Farm (produces WHEAT)")
    WOOD: BuildingTypeCosts = Field(..., description="Costs for Lumber Mill (produces WOOD)")
    STONE: BuildingTypeCosts = Field(..., description="Costs for Mine (produces STONE)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "WHEAT": {
                    "base_building_cost": [
                        {"resource_type": "WHEAT", "amount": 20},
                        {"resource_type": "WOOD", "amount": 100},
                        {"resource_type": "STONE", "amount": 50}
                    ],
                    "base_upgrade_cost": [
                        {"resource_type": "WHEAT", "amount": 10},
                        {"resource_type": "WOOD", "amount": 50},
                        {"resource_type": "STONE", "amount": 25}
                    ],
                    "max_level": 10
                },
                "WOOD": {
                    "base_building_cost": [
                        {"resource_type": "WHEAT", "amount": 80},
                        {"resource_type": "WOOD", "amount": 30},
                        {"resource_type": "STONE", "amount": 60}
                    ],
                    "base_upgrade_cost": [
                        {"resource_type": "WHEAT", "amount": 40},
                        {"resource_type": "WOOD", "amount": 15},
                        {"resource_type": "STONE", "amount": 30}
                    ],
                    "max_level": 10
                },
                "STONE": {
                    "base_building_cost": [
                        {"resource_type": "WHEAT", "amount": 70},
                        {"resource_type": "WOOD", "amount": 120},
                        {"resource_type": "STONE", "amount": 30}
                    ],
                    "base_upgrade_cost": [
                        {"resource_type": "WHEAT", "amount": 35},
                        {"resource_type": "WOOD", "amount": 60},
                        {"resource_type": "STONE", "amount": 15}
                    ],
                    "max_level": 10
                }
            }
        }
