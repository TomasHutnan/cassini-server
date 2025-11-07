"""Building-related database queries."""

from uuid import UUID

from src.database.connection import fetch_one, fetch_all, execute_query


async def get_building_by_h3(h3_index: str) -> dict | None:
    """Fetch building by H3 index.
    
    Args:
        h3_index: H3 hexagonal index
        
    Returns:
        Building record as dict or None if not found
    """
    return await fetch_one(
        '''
        SELECT h3_index, player_id, name, biome_type, type, level, created_at, updated_at
        FROM building WHERE h3_index = $1
        ''',
        h3_index
    )


async def get_buildings_by_player(player_id: UUID) -> list[dict]:
    """Fetch all buildings owned by a player.
    
    Args:
        player_id: Player's character UUID
        
    Returns:
        List of building records
    """
    return await fetch_all(
        '''
        SELECT h3_index, player_id, name, biome_type, type, level, created_at, updated_at
        FROM building WHERE player_id = $1
        ORDER BY created_at DESC
        ''',
        player_id
    )


async def get_buildings_in_area(h3_indexes: list[str]) -> list[dict]:
    """Fetch all buildings in a specific area.
    
    Args:
        h3_indexes: List of H3 hexagonal indexes
        
    Returns:
        List of building records
    """
    return await fetch_all(
        '''
        SELECT h3_index, player_id, name, biome_type, type, level, created_at, updated_at
        FROM building WHERE h3_index = ANY($1)
        ''',
        h3_indexes
    )


async def create_building(
    h3_index: str,
    player_id: UUID,
    name: str,
    biome_type: str,
    building_type: str,
    level: int = 1
) -> dict:
    """Create a new building.
    
    Args:
        h3_index: H3 hexagonal index where building is placed
        player_id: Owner's character UUID
        name: Building name
        biome_type: Biome classification
        building_type: Building function type
        level: Building level (default: 1)
        
    Returns:
        Created building record as dict
        
    Raises:
        asyncpg.UniqueViolationError: If h3_index already has a building
    """
    row = await fetch_one(
        '''
        INSERT INTO building (h3_index, player_id, name, biome_type, type, level)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING h3_index, player_id, name, biome_type, type, level, created_at, updated_at
        ''',
        h3_index, player_id, name, biome_type, building_type, level
    )
    if not row:
        raise RuntimeError("Failed to create building")
    return row


async def update_building_level(h3_index: str, new_level: int) -> bool:
    """Update a building's level.
    
    Args:
        h3_index: Building's H3 index
        new_level: New level (1-10)
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        '''
        UPDATE building
        SET level = $1, updated_at = CURRENT_TIMESTAMP
        WHERE h3_index = $2
        ''',
        new_level, h3_index
    )
    return result == "UPDATE 1"


async def delete_building(h3_index: str) -> bool:
    """Delete a building.
    
    Args:
        h3_index: Building's H3 index
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        'DELETE FROM building WHERE h3_index = $1',
        h3_index
    )
    return result == "DELETE 1"
