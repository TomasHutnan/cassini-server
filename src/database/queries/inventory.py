"""Inventory-related database queries."""

from uuid import UUID

from src.database.connection import fetch_one, fetch_all, execute_query


RESOURCES_PER_HOUR: int = 10

def resources_per_hour_on_level(level: int) -> int:
    return RESOURCES_PER_HOUR * level


def calculate_resource_production(level: int, seconds_elapsed: float) -> tuple[int, int]:
    """Calculate resources produced based on building level and time elapsed.
    
    Production rate: base_rate * level resources per hour
    Base rate: 10 resources per hour per level
    
    Args:
        level: Building level (1-10)
        seconds_elapsed: Seconds since last claim
        
    Returns:
        Total resources produced (integer), Seconds this production took (integer).
    """
    resources_per_hour = resources_per_hour_on_level(level)

    resources_produced = seconds_elapsed * resources_per_hour // 3600

    return resources_produced, resources_produced // resources_per_hour * 3600


async def get_user_inventory(user_id: UUID) -> list[dict]:
    """Fetch all inventory items for a user.
    
    Args:
        user_id: User's UUID
        
    Returns:
        List of inventory items with resource details
    """
    return await fetch_all(
        '''
        SELECT 
            i.id,
            i.user_id,
            i.resource_type,
            i.quantity,
            i.updated_at
        FROM inventory_item i
        WHERE i.user_id = $1
        ORDER BY i.resource_type
        ''',
        user_id
    )





async def get_inventory_item(user_id: UUID, resource_type: str) -> dict | None:
    """Fetch a specific inventory item for a user.
    
    Args:
        user_id: User's UUID
        resource_type: Resource type enum value
    
    Returns:
        Inventory item record as dict if found, or None if the item does not exist (empty result normalization).
    """
    row = await fetch_one(
        '''
        SELECT id, user_id, resource_type, quantity, created_at, updated_at
        FROM inventory_item
        WHERE user_id = $1 AND resource_type = $2
        ''',
        user_id, resource_type
    )
    if not row:
        return None
    return row


async def add_inventory_item(
    user_id: UUID,
    resource_type: str,
    quantity: int
) -> dict:
    """Add or update an inventory item for a user.
    
    Uses INSERT ... ON CONFLICT to add new items or update existing quantities.
    
    Args:
        user_id: User's UUID
        resource_type: Resource type enum value
        quantity: Quantity to add
        
    Returns:
        Inventory item record as dict
    """
    row = await fetch_one(
        '''
        INSERT INTO inventory_item (user_id, resource_type, quantity)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, resource_type)
        DO UPDATE SET
            quantity = inventory_item.quantity + EXCLUDED.quantity,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id, user_id, resource_type, quantity, created_at, updated_at
        ''',
        user_id, resource_type, quantity
    )
    if not row:
        raise RuntimeError("Failed to add inventory item")
    return row


async def update_inventory_quantity(
    user_id: UUID,
    resource_type: str,
    new_quantity: int
) -> bool:
    """Set an inventory item's quantity to a specific value.
    
    Args:
        user_id: User's UUID
        resource_type: Resource type enum value
        new_quantity: New quantity value
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        '''
        UPDATE inventory_item
        SET quantity = $1, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = $2 AND resource_type = $3
        ''',
        new_quantity, user_id, resource_type
    )
    return result == "UPDATE 1"


async def remove_inventory_item(user_id: UUID, resource_type: str) -> bool:
    """Remove an inventory item entirely.
    
    Args:
        user_id: User's UUID
        resource_type: Resource type enum value
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        '''
        DELETE FROM inventory_item
        WHERE user_id = $1 AND resource_type = $2
        ''',
        user_id, resource_type
    )
    return result == "DELETE 1"
