"""Inventory-related database queries."""

from uuid import UUID

from src.database.connection import fetch_one, fetch_all, execute_query


async def get_character_inventory(character_id: UUID) -> list[dict]:
    """Fetch all inventory items for a character.
    
    Args:
        character_id: Character's UUID
        
    Returns:
        List of inventory items with resource details
    """
    return await fetch_all(
        '''
        SELECT 
            i.id,
            i.character_id,
            i.resource_type,
            i.quantity,
            i.updated_at
        FROM inventory_item i
        WHERE i.character_id = $1
        ORDER BY i.resource_type
        ''',
        character_id
    )


async def get_building_inventory(h3_index: str) -> list[dict]:
    """Fetch all inventory items for a building.
    
    Args:
        h3_index: Building's H3 index
        
    Returns:
        List of inventory items with resource details
    """
    return await fetch_all(
        '''
        SELECT 
            i.id,
            i.building_h3_index,
            i.resource_type,
            i.quantity,
            i.updated_at
        FROM inventory_item i
        WHERE i.building_h3_index = $1
        ORDER BY i.resource_type
        ''',
        h3_index
    )


async def get_inventory_item(
    character_id: UUID | None,
    building_h3_index: str | None,
    resource_type: str
) -> dict | None:
    """Fetch a specific inventory item.
    
    Args:
        character_id: Character's UUID (for character inventory)
        building_h3_index: Building's H3 index (for building inventory)
        resource_type: Resource type enum value
        
    Returns:
        Inventory item as dict or None if not found
    """
    return await fetch_one(
        '''
        SELECT id, character_id, building_h3_index, resource_type, quantity, created_at, updated_at
        FROM inventory_item
        WHERE 
            (character_id = $1 OR ($1 IS NULL AND character_id IS NULL))
            AND (building_h3_index = $2 OR ($2 IS NULL AND building_h3_index IS NULL))
            AND resource_type = $3
        ''',
        character_id, building_h3_index, resource_type
    )


async def add_inventory_item(
    character_id: UUID | None,
    building_h3_index: str | None,
    resource_type: str,
    quantity: int
) -> dict:
    """Add or update an inventory item.
    
    Uses INSERT ... ON CONFLICT to add new items or update existing quantities.
    
    Args:
        character_id: Character's UUID (for character inventory)
        building_h3_index: Building's H3 index (for building inventory)
        resource_type: Resource type enum value
        quantity: Quantity to add
        
    Returns:
        Inventory item record as dict
    """
    row = await fetch_one(
        '''
        INSERT INTO inventory_item (character_id, building_h3_index, resource_type, quantity)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (character_id, building_h3_index, resource_type)
        DO UPDATE SET
            quantity = inventory_item.quantity + EXCLUDED.quantity,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id, character_id, building_h3_index, resource_type, quantity, created_at, updated_at
        ''',
        character_id, building_h3_index, resource_type, quantity
    )
    if not row:
        raise RuntimeError("Failed to add inventory item")
    return row


async def update_inventory_quantity(
    character_id: UUID | None,
    building_h3_index: str | None,
    resource_type: str,
    new_quantity: int
) -> bool:
    """Set an inventory item's quantity to a specific value.
    
    Args:
        character_id: Character's UUID (for character inventory)
        building_h3_index: Building's H3 index (for building inventory)
        resource_type: Resource type enum value
        new_quantity: New quantity value
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        '''
        UPDATE inventory_item
        SET quantity = $1, updated_at = CURRENT_TIMESTAMP
        WHERE 
            (character_id = $2 OR ($2 IS NULL AND character_id IS NULL))
            AND (building_h3_index = $3 OR ($3 IS NULL AND building_h3_index IS NULL))
            AND resource_type = $4
        ''',
        new_quantity, character_id, building_h3_index, resource_type
    )
    return result == "UPDATE 1"


async def remove_inventory_item(
    character_id: UUID | None,
    building_h3_index: str | None,
    resource_type: str
) -> bool:
    """Remove an inventory item entirely.
    
    Args:
        character_id: Character's UUID (for character inventory)
        building_h3_index: Building's H3 index (for building inventory)
        resource_type: Resource type enum value
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        '''
        DELETE FROM inventory_item
        WHERE 
            (character_id = $1 OR ($1 IS NULL AND character_id IS NULL))
            AND (building_h3_index = $2 OR ($2 IS NULL AND building_h3_index IS NULL))
            AND resource_type = $3
        ''',
        character_id, building_h3_index, resource_type
    )
    return result == "DELETE 1"
