"""Character-related database queries."""

from uuid import UUID

from src.database.connection import fetch_one, fetch_all, execute_query


async def get_character_by_id(character_id: UUID) -> dict | None:
    """Fetch character by ID.
    
    Args:
        character_id: Character's UUID
        
    Returns:
        Character record as dict or None if not found
    """
    return await fetch_one(
        'SELECT id, user_id, is_pvp, created_at, updated_at FROM character WHERE id = $1',
        character_id
    )


async def get_characters_by_user(user_id: UUID) -> list[dict]:
    """Fetch all characters belonging to a user.
    
    Args:
        user_id: User's UUID
        
    Returns:
        List of character records
    """
    return await fetch_all(
        'SELECT id, user_id, is_pvp, created_at, updated_at FROM character WHERE user_id = $1',
        user_id
    )


async def get_user_character(user_id: UUID, is_pvp: bool) -> dict | None:
    """Fetch a specific character type for a user.
    
    Args:
        user_id: User's UUID
        is_pvp: True for PVP character, False for PVE
        
    Returns:
        Character record as dict or None if not found
    """
    return await fetch_one(
        'SELECT id, user_id, is_pvp, created_at, updated_at FROM character WHERE user_id = $1 AND is_pvp = $2',
        user_id, is_pvp
    )


async def create_character(user_id: UUID, is_pvp: bool) -> dict:
    """Create a new character for a user.
    
    Args:
        user_id: User's UUID
        is_pvp: True for PVP character, False for PVE
        
    Returns:
        Created character record as dict
        
    Raises:
        asyncpg.UniqueViolationError: If character type already exists for user
    """
    row = await fetch_one(
        '''
        INSERT INTO character (user_id, is_pvp)
        VALUES ($1, $2)
        RETURNING id, user_id, is_pvp, created_at, updated_at
        ''',
        user_id, is_pvp
    )
    if not row:
        raise RuntimeError("Failed to create character")
    return row


async def delete_character(character_id: UUID) -> bool:
    """Delete a character.
    
    Args:
        character_id: Character's UUID
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        'DELETE FROM character WHERE id = $1',
        character_id
    )
    return result == "DELETE 1"
