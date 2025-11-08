"""Market order database queries (boolean flags)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.database.connection import fetch_one, fetch_all, execute_query


async def create_market_order(
    *,
    user_id: UUID,
    is_buy_order: bool,
    resource_type: str,
    amount: int,
    total_price: int,
) -> dict | None:
    """Create a market order and return the created row (no side effects)."""
    return await fetch_one(
        """
        INSERT INTO market_order (user_id, is_buy_order, resource_type, amount, total_price)
        VALUES ($1, $2, $3::resource_type, $4, $5)
        RETURNING id, user_id, is_buy_order, resource_type, amount, total_price, is_open, created_at, updated_at
        """,
        user_id, is_buy_order, resource_type, amount, total_price,
    )


async def get_market_order(order_id: UUID) -> dict | None:
    row = await fetch_one(
        """
        SELECT id, user_id, is_buy_order, resource_type, amount, total_price, is_open, created_at, updated_at
        FROM market_order
        WHERE id = $1
        """,
        order_id,
    )
    return row


async def list_market_orders(
    *,
    user_id: UUID | None = None,
    is_buy_order: bool | None = None,
    resource_type: str | None = None,
    include_closed: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List market orders with optional filters and pagination."""
    conditions: list[str] = []
    args: list[Any] = []
    idx = 1

    if is_buy_order is not None:
        conditions.append(f"is_buy_order = ${idx}")
        args.append(is_buy_order)
        idx += 1
    if resource_type is not None:
        conditions.append(f"resource_type = ${idx}::resource_type")
        args.append(resource_type)
        idx += 1
    if user_id is not None:
        conditions.append(f"user_id = ${idx}")
        args.append(user_id)
        idx += 1
    if not include_closed:
        conditions.append("is_open = TRUE")

    where_clause = ""
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    p_limit = idx
    p_offset = idx + 1
    args.extend([limit, offset])

    query = (
        "SELECT id, user_id, is_buy_order, resource_type, amount, total_price, is_open, created_at, updated_at\n"
        "FROM market_order" + where_clause + "\n"
        f"ORDER BY created_at DESC LIMIT ${p_limit} OFFSET ${p_offset}"
    )
    rows = await fetch_all(query, *args)
    return rows


async def update_market_order(
    *,
    order_id: UUID,
    user_id: UUID,
    resource_type: str | None = None,
    amount: int | None = None,
    total_price: int | None = None,
) -> dict | None:
    """Update fields of an OPEN market order owned by the user and return the updated row."""
    set_parts: list[str] = []
    args: list[Any] = []
    idx = 1

    if resource_type is not None:
        set_parts.append(f"resource_type = ${idx}::resource_type")
        args.append(resource_type)
        idx += 1
    if amount is not None:
        set_parts.append(f"amount = ${idx}")
        args.append(amount)
        idx += 1
    if total_price is not None:
        set_parts.append(f"total_price = ${idx}")
        args.append(total_price)
        idx += 1

    if not set_parts:
        return await get_market_order(order_id)

    set_parts.append("updated_at = CURRENT_TIMESTAMP")

    args.extend([order_id, user_id])

    query = (
        "UPDATE market_order\n"
        f"SET {', '.join(set_parts)}\n"
        f"WHERE id = ${idx} AND user_id = ${idx + 1} AND is_open = TRUE\n"
        "RETURNING id, user_id, is_buy_order, resource_type, amount, total_price, is_open, created_at, updated_at"
    )
    row = await fetch_one(query, *args)
    return row


async def close_market_order(order_id: UUID) -> dict | None:
    """Mark an OPEN order as CLOSED (filled)."""
    row = await fetch_one(
        """
        UPDATE market_order
        SET is_open = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1 AND is_open = TRUE
        RETURNING id, user_id, is_buy_order, resource_type, amount, total_price, is_open, created_at, updated_at
        """,
        order_id,
    )
    return row


async def delete_market_order(order_id: UUID, user_id: UUID) -> bool:
    """Delete a market order owned by the user."""
    result = await execute_query(
        """
        DELETE FROM market_order
        WHERE id = $1 AND user_id = $2
        """,
        order_id, user_id,
    )
    return result == "DELETE 1"
