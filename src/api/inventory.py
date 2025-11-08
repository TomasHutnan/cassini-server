"""Inventory management API endpoints."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.models.inventory import InventoryItemResponse, InventoryAdjustRequest
from src.game_objects.resources import Resource
from src.database.queries.inventory import (
    get_user_inventory,
    get_inventory_item,
    add_inventory_item,
    update_inventory_quantity,
    remove_inventory_item,
)
from src.auth.dependencies import get_user_id

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/", response_model=list[InventoryItemResponse])
async def list_user_inventory(user_id: Annotated[UUID, Depends(get_user_id)]):
    items = await get_user_inventory(user_id)
    # Cast resource types
    return [
        InventoryItemResponse(
            id=i.get("id"),
            user_id=i.get("user_id"),
            resource_type=Resource(i["resource_type"]),
            quantity=i["quantity"],
            created_at=str(i.get("created_at")) if i.get("created_at") else None,
            updated_at=str(i.get("updated_at")) if i.get("updated_at") else None,
        )
        for i in items
    ]


@router.get("/money", response_model=InventoryItemResponse)
async def get_user_money(user_id: Annotated[UUID, Depends(get_user_id)]):
    item = await get_inventory_item(user_id, Resource.MONEY.value)
    if not item:
        # Represent zero balance if absent
        return InventoryItemResponse(
            id=None,
            user_id=user_id,
            resource_type=Resource.MONEY,
            quantity=0,
        )
    return InventoryItemResponse(
        id=item.get("id"),
        user_id=item.get("user_id"),
        resource_type=Resource(item["resource_type"]),
        quantity=item["quantity"],
        created_at=str(item.get("created_at")) if item.get("created_at") else None,
        updated_at=str(item.get("updated_at")) if item.get("updated_at") else None,
    )


@router.post("/adjust", response_model=InventoryItemResponse, status_code=status.HTTP_200_OK)
async def adjust_inventory(
    data: InventoryAdjustRequest,
    user_id: Annotated[UUID, Depends(get_user_id)],
):
    """Add or remove resources from current user's inventory using primitive query functions.

    Rules:
    - If item does not exist and quantity_delta > 0: create via add_inventory_item.
    - If item does not exist and quantity_delta < 0: error (cannot go below zero).
    - If existing and new quantity > 0: use update_inventory_quantity.
    - If existing and new quantity == 0:
        * If resource != MONEY: remove row via remove_inventory_item
        * If resource == MONEY: keep row by setting quantity to 0 (update)
    - Never allow new quantity < 0.
    """
    resource = data.resource_type
    delta = data.quantity_delta

    existing = await get_inventory_item(user_id, resource.value)

    if not existing:
        if delta < 0:
            raise HTTPException(status_code=400, detail="Cannot subtract from non-existing inventory item")
        # Create new
        created = await add_inventory_item(user_id, resource.value, delta)
        return InventoryItemResponse(
            id=created.get("id"),
            user_id=created.get("user_id"),
            resource_type=resource,
            quantity=created["quantity"],
            created_at=str(created.get("created_at")) if created.get("created_at") else None,
            updated_at=str(created.get("updated_at")) if created.get("updated_at") else None,
        )

    current_qty = existing["quantity"]
    new_qty = current_qty + delta
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Resulting quantity would be negative")

    if new_qty > 0:
        success = await update_inventory_quantity(user_id, resource.value, new_qty)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update inventory item")
        updated = await get_inventory_item(user_id, resource.value)
        return InventoryItemResponse(
            id=updated.get("id"),  # type: ignore[union-attr]
            user_id=updated.get("user_id"),
            resource_type=resource,
            quantity=updated["quantity"],  # type: ignore[index]
            created_at=str(updated.get("created_at")) if updated.get("created_at") else None,  # type: ignore[union-attr]
            updated_at=str(updated.get("updated_at")) if updated.get("updated_at") else None,  # type: ignore[union-attr]
        )

    # new_qty == 0
    if resource == Resource.MONEY:
        # Keep row, set to 0
        success = await update_inventory_quantity(user_id, resource.value, 0)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to zero money balance")
        zeroed = await get_inventory_item(user_id, resource.value)
        return InventoryItemResponse(
            id=zeroed.get("id"),  # type: ignore[union-attr]
            user_id=zeroed.get("user_id"),
            resource_type=resource,
            quantity=0,
            created_at=str(zeroed.get("created_at")) if zeroed.get("created_at") else None,  # type: ignore[union-attr]
            updated_at=str(zeroed.get("updated_at")) if zeroed.get("updated_at") else None,  # type: ignore[union-attr]
        )

    # Delete non-money resource
    deleted = await remove_inventory_item(user_id, resource.value)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete inventory item")
    return InventoryItemResponse(
        id=None,
        user_id=user_id,
        resource_type=resource,
        quantity=0,
    )
