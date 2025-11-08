"""Building management API endpoints."""

from datetime import datetime, timezone, timedelta

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.models.buildings import BuildingCreate, ClaimResourcesResponse
from src.database.queries.buildings import get_building_by_h3
from src.database.queries.inventory import (
    add_inventory_item,
    calculate_resource_production,
)
from src.database.connection import execute_query
from src.auth.dependencies import get_user_id

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("/")
async def list_buildings(player_id: str | None = None):
    """List all buildings, optionally filtered by player.

    Args:
        player_id: Optional player ID to filter buildings

    Returns:
        List of buildings
    """
    # TODO: Implement building retrieval from database
    return {
        "buildings": [],
        "message": "Building listing not yet implemented",
    }


@router.post("/")
async def create_building(
    data: BuildingCreate, user_id: Annotated[UUID, Depends(get_user_id)]
):
    """Create a new building on a hex tile.

    Args:
        data: BuildingCreate

    Returns:
        Created building data
    """
    # TODO: Implement building creation logic
    # - Validate hex_id exists and is available
    # - Save to database with user_id as owner
    return {
        "building": {
            "hex_id": data.hex_id,
            "player_id": str(user_id),
            "name": data.name,
            # resource_type is an Enum; return its string value for JSON/DB
            "resource_type": data.resource_type.value,
            "level": 1,
        },
        "message": "Building creation not yet implemented",
    }


@router.get("/{building_id}")
async def get_building(
    building_id: str, user_id: Annotated[UUID, Depends(get_user_id)]
):
    """Get details of a specific building.

    Args:
        building_id: Unique building identifier

    Returns:
        Building details including inventory and production
    """
    # TODO: Implement building detail retrieval
    raise HTTPException(status_code=404, detail="Building not found")


@router.delete("/{building_id}")
async def delete_building(
    building_id: str, user_id: Annotated[UUID, Depends(get_user_id)]
):
    """Delete a building (requires ownership).

    Requires authentication - Only the owner can delete their building.

    Args:
        building_id: Building to delete
        player_id: Player requesting deletion (must be owner)

    Returns:
        Confirmation message
    """
    # TODO: Implement building deletion with ownership validation
    raise HTTPException(status_code=404, detail="Building not found")


@router.post("/{h3_index}/claim")
async def claim_building_resources(
    h3_index: str, user_id: Annotated[UUID, Depends(get_user_id)]
):
    """Claim accumulated resources from a building.

    Calculates resources based on building level and time since last claim.
    Production rate: 10 * level resources per hour.

    Args:
        h3_index: Building's H3 hex index
        user_id: Authenticated user ID

    Returns:
        ClaimResourcesResponse with claimed resources and updated inventory

    Raises:
        HTTPException: 404 if building not found, 403 if not owned by user
    """

    # Get the building
    building = await get_building_by_h3(h3_index)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    # Verify ownership
    if building["user_id"] != user_id:
        raise HTTPException(
            status_code=403, detail="You don't own this building"
        )

    # Calculate time elapsed since last claim
    last_claim = building["last_claim_at"]
    now = datetime.now(timezone.utc)
    time_delta = now - last_claim

    # Calculate resources produced (whole units only)
    resources_produced, seconds_spent = calculate_resource_production(
        building["level"], time_delta.total_seconds()
    )

    # Add resources to user inventory
    inventory_item = await add_inventory_item(
        user_id=user_id,
        resource_type=building["resource_type"],
        quantity=resources_produced,
    )

    # Update building's last_claim_at by only the time that was "consumed" for whole resources
    # This preserves fractional progress (e.g., if 15 min elapsed, 2 resources claimed at 6 min each, 3 min remains)
    new_last_claim = last_claim + timedelta(seconds=seconds_spent)
    await execute_query(
        "UPDATE building SET last_claim_at = $1, updated_at = CURRENT_TIMESTAMP WHERE h3_index = $2",
        new_last_claim,
        h3_index,
    )

    return ClaimResourcesResponse(
        resources_claimed=resources_produced,
        resource_type=building["resource_type"],
        new_inventory_total=inventory_item["quantity"],
        hours_elapsed=round(seconds_spent, 2),
    )
