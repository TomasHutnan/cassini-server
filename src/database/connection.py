"""Shared database connection management.

This module provides connection pooling and database access utilities
for the entire application.
"""

import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from src.config import get_settings

# Global connection pool
_pool: asyncpg.Pool | None = None


async def init_db_pool() -> None:
    """Initialize the database connection pool.
    
    Should be called on application startup.
    """
    global _pool
    settings = get_settings()
    
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    
    _pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=60,
    )


async def close_db_pool() -> None:
    """Close the database connection pool.
    
    Should be called on application shutdown.
    """
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Get the database connection pool.
    
    Returns:
        Connection pool instance
        
    Raises:
        RuntimeError: If pool is not initialized
    """
    if _pool is None:
        raise RuntimeError(
            "Database pool not initialized. Call init_db_pool() first."
        )
    return _pool


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a database connection from the pool.
    
    Usage:
        async with get_db_connection() as conn:
            result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    
    Yields:
        Database connection
    """
    pool = get_pool()
    async with pool.acquire() as connection:
        yield connection


async def execute_query(query: str, *args) -> str:
    """Execute a query that modifies data (INSERT, UPDATE, DELETE).
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        Result status string (e.g., "INSERT 0 1", "UPDATE 1")
    """
    async with get_db_connection() as conn:
        return await conn.execute(query, *args)


async def fetch_one(query: str, *args) -> dict | None:
    """Fetch a single row from the database.
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        Row as dict or None if not found
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> list[dict]:
    """Fetch multiple rows from the database.
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        List of rows as dicts
    """
    async with get_db_connection() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def fetch_val(query: str, *args):
    """Fetch a single value from the database.
    
    Args:
        query: SQL query string
        *args: Query parameters
        
    Returns:
        Single value or None
    """
    async with get_db_connection() as conn:
        return await conn.fetchval(query, *args)
