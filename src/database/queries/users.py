"""User-related database queries."""

from uuid import UUID

from src.database.connection import fetch_one, execute_query


async def get_user_by_name(username: str) -> dict | None:
    """Fetch user by username.
    
    Args:
        username: User's username
        
    Returns:
        User record as dict or None if not found
    """
    return await fetch_one(
        'SELECT id, name, hash_pass, hash_salt, created_at, updated_at FROM "user" WHERE name = $1',
        username
    )


async def get_user_by_id(user_id: UUID) -> dict | None:
    """Fetch user by ID.
    
    Args:
        user_id: User's UUID
        
    Returns:
        User record as dict or None if not found
    """
    return await fetch_one(
        'SELECT id, name, hash_pass, hash_salt, created_at, updated_at FROM "user" WHERE id = $1',
        user_id
    )


async def create_user(username: str, hashed_password: str, salt: str) -> dict:
    """Create a new user.
    
    Args:
        username: Desired username
        hashed_password: Hashed password
        salt: Password salt
        
    Returns:
        Created user record as dict
        
    Raises:
        asyncpg.UniqueViolationError: If username already exists
    """
    row = await fetch_one(
        '''
        INSERT INTO "user" (name, hash_pass, hash_salt)
        VALUES ($1, $2, $3)
        RETURNING id, name, created_at, updated_at
        ''',
        username, hashed_password, salt
    )
    if not row:
        raise RuntimeError("Failed to create user")
    return row


async def update_user_password(user_id: UUID, hashed_password: str, salt: str) -> bool:
    """Update user's password.
    
    Args:
        user_id: User's UUID
        hashed_password: New hashed password
        salt: New password salt
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        '''
        UPDATE "user"
        SET hash_pass = $1, hash_salt = $2, updated_at = CURRENT_TIMESTAMP
        WHERE id = $3
        ''',
        hashed_password, salt, user_id
    )
    return result == "UPDATE 1"


async def delete_user(user_id: UUID) -> bool:
    """Delete a user.
    
    Args:
        user_id: User's UUID
        
    Returns:
        True if successful, False otherwise
    """
    result = await execute_query(
        'DELETE FROM "user" WHERE id = $1',
        user_id
    )
    return result == "DELETE 1"
