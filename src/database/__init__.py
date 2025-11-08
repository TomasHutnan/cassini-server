"""Database access layer.

This module provides:
- Connection pooling (connection.py)
- Organized query functions by domain (queries/)
- Transaction management utilities
"""

from .connection import (
    init_db_pool,
    close_db_pool,
    get_pool,
    get_db_connection,
    execute_query,
    fetch_one,
    fetch_all,
    fetch_val,
)

__all__ = [
    # Connection management
    "init_db_pool",
    "close_db_pool",
    "get_pool",
    "get_db_connection",
    # Query helpers
    "execute_query",
    "fetch_one",
    "fetch_all",
    "fetch_val",
    # Query modules
]
