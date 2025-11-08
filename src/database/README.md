# Database Layer

This folder contains all database-related code for the game server.

## Structure

```
database/
├── schema.sql              # PostgreSQL DDL - complete database schema
├── connection.py           # Connection pool management and utilities
├── queries/                # Organized query functions by domain
│   ├── users.py           # User account queries
│   ├── characters.py      # Character management queries
│   ├── buildings.py       # Building/settlement queries
│   └── inventory.py       # Inventory system queries
└── __init__.py            # Exports for clean imports
```

## Usage

### Connection Pool

The connection pool is automatically initialized on application startup and closed on shutdown (via FastAPI lifespan):

```python
# In src/main.py
from database import init_db_pool, close_db_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()  # Startup
    yield
    await close_db_pool()  # Shutdown
```

### Query Functions

Import query functions organized by domain:

```python
from database.queries import users, characters, buildings, inventory

# User operations
user = await users.get_user_by_name("player1")
new_user = await users.create_user("player2", hashed_pass, salt)

# Character operations
char = await characters.create_character(user_id, is_pvp=True)
chars = await characters.get_characters_by_user(user_id)

# Building operations
building = await buildings.get_building_by_h3("8928308280fffff")
my_buildings = await buildings.get_buildings_by_player(character_id)

# Inventory operations
inventory_items = await inventory.get_character_inventory(character_id)
await inventory.add_inventory_item(character_id, None, "WOOD", 100)
```

### Direct Database Access

For custom queries, use the connection utilities:

```python
from database import get_db_connection, fetch_one, fetch_all

# Context manager (recommended)
async with get_db_connection() as conn:
    result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

# Helper functions (simpler)
user = await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
users = await fetch_all("SELECT * FROM users WHERE created_at > $1", date)
```

## Connection Pool Configuration

Default settings in `connection.py`:
- **min_size**: 2 connections
- **max_size**: 10 connections
- **command_timeout**: 60 seconds

Adjust these in `init_db_pool()` based on your needs.

## Adding New Queries

1. Create a new file in `database/queries/` (e.g., `trades.py`)
2. Import connection utilities:
   ```python
   from ..connection import fetch_one, fetch_all, execute_query
   ```
3. Write query functions:
   ```python
   async def get_trade_by_id(trade_id: UUID) -> dict | None:
       return await fetch_one(
           "SELECT * FROM trades WHERE id = $1",
           trade_id
       )
   ```
4. Export in `database/queries/__init__.py`:
   ```python
   from . import users, characters, buildings, inventory, trades
   __all__ = ["users", "characters", "buildings", "inventory", "trades"]
   ```

## Error Handling

All query functions may raise `asyncpg` exceptions:
- `UniqueViolationError` - Duplicate key constraint violation
- `ForeignKeyViolationError` - Foreign key constraint violation
- `CheckViolationError` - Check constraint violation
- `ConnectionError` - Database connection issues

Handle these in your API endpoints:

```python
from asyncpg import UniqueViolationError
from fastapi import HTTPException, status

try:
    user = await users.create_user(username, hashed_pass, salt)
except UniqueViolationError:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Username already exists"
    )
```
