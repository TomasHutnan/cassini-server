"""Building management API endpoints."""

from datetime import datetime, timezone, timedelta

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
import h3

from src.api.models.buildings import (
    BuildingCreate,
    BuildingResponse,
    BuildingListResponse,
    ClaimResourcesResponse,
)
from src.database.queries.buildings import (
    get_building_by_h3,
    get_buildings_by_user,
    get_buildings_in_area,
    create_building as db_create_building,
    delete_building as db_delete_building,
)
from src.database.queries.inventory import (
    add_inventory_item,
    calculate_resource_production,
)
from src.database.connection import execute_query
from src.auth.dependencies import get_user_id

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("/my", response_model=BuildingListResponse)
async def list_my_buildings(user_id: Annotated[UUID, Depends(get_user_id)]):
    """List all buildings owned by the authenticated user.

    Args:
        user_id: Authenticated user ID from JWT token

    Returns:
        BuildingListResponse with list of buildings and total count
    """
    buildings = await get_buildings_by_user(user_id)
    
    # Convert UUID to string for each building
    buildings_list = []
    for building in buildings:
        building_dict = dict(building)
        building_dict["user_id"] = str(building_dict["user_id"])
        buildings_list.append(BuildingResponse(**building_dict))
    
    return BuildingListResponse(
        buildings=buildings_list,
        total=len(buildings_list),
    )


@router.get("/area", response_model=BuildingListResponse)
async def list_buildings_in_area(
    lat: float = Query(..., description="Center latitude coordinate", ge=-90, le=90),
    lon: float = Query(..., description="Center longitude coordinate", ge=-180, le=180),
    range_m: int = Query(200, description="Search radius in meters", ge=50, le=5000),
):
    """List all buildings within a geographic area.

    Returns all buildings within the specified radius from the center point,
    using H3 hexagonal grid. Similar to the map endpoint.

    Example usage:
    - `GET /buildings/area?lat=48.1486&lon=17.1077&range_m=200`

    Args:
        lat: Center point latitude (-90 to 90)
        lon: Center point longitude (-180 to 180)
        range_m: Search radius in meters (50 to 5000m, default: 200m)

    Returns:
        BuildingListResponse with all buildings in the area
    """
    resolution = 12
    
    # Get center hex
    center_hex = h3.latlng_to_cell(lat, lon, resolution)
    
    # Calculate number of rings needed to cover the range
    avg_hex_size = 9
    rings = max(1, int(range_m / avg_hex_size))
    
    # Get all hexagons in the area
    hexagons = list(h3.grid_disk(center_hex, rings))
    
    # Query buildings in these hexagons
    buildings = await get_buildings_in_area(hexagons)
    
    # Convert UUID to string for each building
    buildings_list = []
    for building in buildings:
        building_dict = dict(building)
        building_dict["user_id"] = str(building_dict["user_id"])
        buildings_list.append(BuildingResponse(**building_dict))
    
    return BuildingListResponse(
        buildings=buildings_list,
        total=len(buildings_list),
    )


@router.post("/", response_model=BuildingResponse, status_code=201)
async def create_building(
    data: BuildingCreate, user_id: Annotated[UUID, Depends(get_user_id)]
):
    """Create a new building on a hex tile.

    Args:
        data: BuildingCreate containing h3_index, name, biome_type, and resource_type
        user_id: Authenticated user ID from JWT token

    Returns:
        BuildingResponse with created building details

    Raises:
        HTTPException: 409 if a building already exists at that h3_index
    """
    # Check if building already exists at this location
    existing = await get_building_by_h3(data.h3_index)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A building already exists at this location",
        )
    
    # Create the building
    building = await db_create_building(
        h3_index=data.h3_index,
        user_id=user_id,
        name=data.name,
        biome_type=data.biome_type.value,
        resource_type=data.resource_type.value,
    )
    
    # Convert UUID to string for Pydantic model
    building_dict = dict(building)
    building_dict["user_id"] = str(building_dict["user_id"])
    
    return BuildingResponse(**building_dict)


@router.get("/{h3_index}", response_model=BuildingResponse)
async def get_building(h3_index: str):
    """Get details of a specific building by its H3 index.

    Args:
        h3_index: H3 hex index of the building

    Returns:
        BuildingResponse with building details

    Raises:
        HTTPException: 404 if building not found
    """
    building = await get_building_by_h3(h3_index)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    # Convert UUID to string for Pydantic model
    building_dict = dict(building)
    building_dict["user_id"] = str(building_dict["user_id"])
    
    return BuildingResponse(**building_dict)


@router.delete("/{h3_index}")
async def delete_building(
    h3_index: str, user_id: Annotated[UUID, Depends(get_user_id)]
):
    """Delete a building (requires ownership).

    Only the owner can delete their building.

    Args:
        h3_index: H3 hex index of the building to delete
        user_id: Authenticated user ID from JWT token

    Returns:
        Confirmation message

    Raises:
        HTTPException: 404 if building not found, 403 if not owned by user
    """
    # Get the building to verify ownership
    building = await get_building_by_h3(h3_index)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    # Verify ownership
    if building["user_id"] != user_id:
        raise HTTPException(
            status_code=403, detail="You don't own this building"
        )
    
    # Delete the building
    await db_delete_building(h3_index)
    
    return {"message": "Building deleted successfully", "h3_index": h3_index}


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
    # Ensure last_claim is timezone-aware
    if last_claim.tzinfo is None:
        last_claim = last_claim.replace(tzinfo=timezone.utc)
    
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
    # Remove timezone info for database storage (PostgreSQL stores as UTC by default)
    if new_last_claim.tzinfo is not None:
        new_last_claim = new_last_claim.replace(tzinfo=None)
    
    await execute_query(
        "UPDATE building SET last_claim_at = $1, updated_at = CURRENT_TIMESTAMP WHERE h3_index = $2",
        new_last_claim,
        h3_index,
    )

    return ClaimResourcesResponse(
        resources_claimed=resources_produced,
        resource_type=building["resource_type"],
        new_inventory_total=inventory_item["quantity"],
        seconds_elapsed=round(seconds_spent, 2),
    )
