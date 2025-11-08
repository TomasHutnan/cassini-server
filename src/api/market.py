"""Market management API endpoints."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from src.game_objects.resources import Resource
from src.database.connection import get_db_connection
from src.database.queries.market import (
    delete_market_order,
    get_market_order,
    list_market_orders,
    update_market_order,
    close_market_order,
)

from src.api.models.market import (
    MarketOrderCreate,
    MarketOrderOut,
    MarketOrderUpdate,
)

from ..auth.dependencies import get_user_id

router = APIRouter(prefix="/market", tags=["market"])

@router.post("/orders", response_model=MarketOrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: MarketOrderCreate,
    user_id: Annotated[UUID, Depends(get_user_id)],
):
    """Create a new market order (buy or sell) and reserve required assets in inventory."""
    async with get_db_connection() as conn:
        async with conn.transaction():
            if data.order_type == "BUY":
                money = await conn.fetchrow(
                    "SELECT id, quantity FROM inventory_item WHERE user_id = $1 AND resource_type = 'MONEY'::resource_type FOR UPDATE",
                    user_id,
                )
                if not money or money["quantity"] < data.total_price:
                    raise HTTPException(status_code=400, detail="Insufficient MONEY for BUY order")
                await conn.execute(
                    "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    data.total_price,
                    money["id"],
                )
            else:  # SELL
                resource = await conn.fetchrow(
                    "SELECT id, quantity FROM inventory_item WHERE user_id = $1 AND resource_type = $2::resource_type FOR UPDATE",
                    user_id,
                    data.resource_type.value,
                )
                if not resource or resource["quantity"] < data.amount:
                    raise HTTPException(status_code=400, detail="Insufficient resource for SELL order")
                await conn.execute(
                    "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    data.amount,
                    resource["id"],
                )
            row = await conn.fetchrow(
                """
                INSERT INTO market_order (user_id, order_type, resource_type, amount, total_price)
                VALUES ($1, $2, $3::resource_type, $4, $5)
                RETURNING id, user_id, order_type, resource_type, amount, total_price, status, created_at, updated_at
                """,
                user_id,
                data.order_type,
                data.resource_type.value,
                data.amount,
                data.total_price,
            )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create order")
    row["resource_type"] = Resource(row["resource_type"])  # type: ignore[index]
    return row  # type: ignore[return-value]


@router.get("/orders", response_model=list[MarketOrderOut])
async def read_orders(
    order_type: Literal["BUY", "SELL"] | None = None,
    resource_type: Resource | None = None,
    user_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Read market orders.

    If order_type is provided, returns only BUY or SELL orders. Otherwise, returns both.
    By default, returns only OPEN orders unless include_closed is True.
    Supports pagination with limit and offset.
    """
    rows = await list_market_orders(
        order_type=order_type,
        resource_type=resource_type.value if resource_type else None,
        user_id=user_id,
        limit=max(limit, 1),
        offset=max(offset, 0),
    )
    # Cast resource_type to Resource
    for r in rows:
        r["resource_type"] = Resource(r["resource_type"])  # type: ignore[index]
    return rows  # type: ignore[return-value]


@router.get("/orders/{order_id}", response_model=MarketOrderOut)
async def read_order(order_id: UUID):
    row = await get_market_order(order_id)
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    row["resource_type"] = Resource(row["resource_type"])  # type: ignore[index]
    return row  # type: ignore[return-value]


@router.patch("/orders/{order_id}", response_model=MarketOrderOut)
async def update_order(
    order_id: UUID,
    data: MarketOrderUpdate,
    user_id: Annotated[UUID, Depends(get_user_id)],
):
    existing = await get_market_order(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this order")
    if existing["status"] != "OPEN":
        raise HTTPException(status_code=400, detail="Only OPEN orders can be modified")
    new_resource = data.resource_type.value if data.resource_type else existing["resource_type"]
    new_amount = data.amount if data.amount is not None else existing["amount"]
    new_price = data.total_price if data.total_price is not None else existing["total_price"]
    async with get_db_connection() as conn:
        async with conn.transaction():
            if existing["order_type"] == "SELL":
                # Adjust resource reservation
                resource_row = await conn.fetchrow(
                    "SELECT id, quantity FROM inventory_item WHERE user_id = $1 AND resource_type = $2::resource_type FOR UPDATE",
                    user_id,
                    new_resource,
                )
                # If resource type changed, refund old first
                if new_resource != existing["resource_type"]:
                    # Refund old amount
                    await conn.execute(
                        "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, $2::resource_type, $3) ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                        user_id,
                        existing["resource_type"],
                        existing["amount"],
                    )
                    if not resource_row or resource_row["quantity"] < new_amount:
                        raise HTTPException(status_code=400, detail="Insufficient resource after change")
                    # Reserve new
                    await conn.execute(
                        "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                        new_amount,
                        resource_row["id"],
                    )
                else:
                    delta = new_amount - existing["amount"]
                    if delta != 0:
                        if delta > 0:
                            if not resource_row or resource_row["quantity"] < delta:
                                raise HTTPException(status_code=400, detail="Insufficient resource to increase amount")
                            await conn.execute(
                                "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                                delta,
                                resource_row["id"],
                            )
                        else:
                            await conn.execute(
                                "UPDATE inventory_item SET quantity = quantity + $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                                -delta,
                                resource_row["id"],
                            )
            else:  # BUY order
                money_row = await conn.fetchrow(
                    "SELECT id, quantity FROM inventory_item WHERE user_id = $1 AND resource_type = 'MONEY'::resource_type FOR UPDATE",
                    user_id,
                )
                price_delta = new_price - existing["total_price"]
                if price_delta != 0:
                    if price_delta > 0:
                        if not money_row or money_row["quantity"] < price_delta:
                            raise HTTPException(status_code=400, detail="Insufficient MONEY to raise price")
                        await conn.execute(
                            "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                            price_delta,
                            money_row["id"],
                        )
                    else:
                        await conn.execute(
                            "UPDATE inventory_item SET quantity = quantity + $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                            -price_delta,
                            money_row["id"],
                        )
            updated = await update_market_order(
                order_id=order_id,
                user_id=user_id,
                resource_type=new_resource if data.resource_type else None,
                amount=data.amount,
                total_price=data.total_price,
            )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update order")
    updated["resource_type"] = Resource(updated["resource_type"])  # type: ignore[index]
    return updated  # type: ignore[return-value]


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    user_id: Annotated[UUID, Depends(get_user_id)],
):
    existing = await get_market_order(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    if existing["status"] != "OPEN":
        raise HTTPException(status_code=400, detail="Only OPEN orders can be deleted")
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this order")

    # Refund reservation and delete within a single transaction
    async with get_db_connection() as conn:
        async with conn.transaction():
            # Lock and re-validate
            order = await conn.fetchrow(
                "SELECT id, user_id, order_type, resource_type, amount, total_price, status FROM market_order WHERE id = $1 FOR UPDATE",
                order_id,
            )
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            if order["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this order")
            if order["status"] != "OPEN":
                raise HTTPException(status_code=400, detail="Only OPEN orders can be deleted")

            if order["order_type"] == "BUY":
                # Refund MONEY to creator
                await conn.execute(
                    "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, 'MONEY'::resource_type, $2)\n"
                    "ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                    user_id,
                    order["total_price"],
                )
            else:
                # Refund resource to creator
                await conn.execute(
                    "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, $2::resource_type, $3)\n"
                    "ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                    user_id,
                    order["resource_type"],
                    order["amount"],
                )

            # Delete the order
            res = await conn.execute(
                "DELETE FROM market_order WHERE id = $1 AND user_id = $2",
                order_id,
                user_id,
            )
            if not res.endswith(" 1"):
                raise HTTPException(status_code=500, detail="Failed to delete order")
    return None

@router.post("/orders/{order_id}/fill", response_model=MarketOrderOut)
async def fill_order(
    order_id: UUID,
    filler_user_id: Annotated[UUID, Depends(get_user_id)],
):
    existing = await get_market_order(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    if existing["status"] != "OPEN":
        raise HTTPException(status_code=400, detail="Order is not open")
    async with get_db_connection() as conn:
        async with conn.transaction():
            if existing["order_type"] == "BUY":
                # filler sells resource
                resource_row = await conn.fetchrow(
                    "SELECT id, quantity FROM inventory_item WHERE user_id = $1 AND resource_type = $2::resource_type FOR UPDATE",
                    filler_user_id,
                    existing["resource_type"],
                )
                if not resource_row or resource_row["quantity"] < existing["amount"]:
                    raise HTTPException(status_code=400, detail="Seller lacks resource")
                await conn.execute(
                    "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    existing["amount"],
                    resource_row["id"],
                )
                # Pay seller money
                seller_money = await conn.fetchrow(
                    "SELECT id FROM inventory_item WHERE user_id = $1 AND resource_type = 'MONEY'::resource_type FOR UPDATE",
                    filler_user_id,
                )
                if seller_money:
                    await conn.execute(
                        "UPDATE inventory_item SET quantity = quantity + $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                        existing["total_price"],
                        seller_money["id"],
                    )
                else:
                    await conn.execute(
                        "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, 'MONEY'::resource_type, $2)",
                        filler_user_id,
                        existing["total_price"],
                    )
                # Give buyer resource
                await conn.execute(
                    "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, $2::resource_type, $3) ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                    existing["user_id"],
                    existing["resource_type"],
                    existing["amount"],
                )
            else:  # SELL order
                buyer_money = await conn.fetchrow(
                    "SELECT id, quantity FROM inventory_item WHERE user_id = $1 AND resource_type = 'MONEY'::resource_type FOR UPDATE",
                    filler_user_id,
                )
                if not buyer_money or buyer_money["quantity"] < existing["total_price"]:
                    raise HTTPException(status_code=400, detail="Buyer lacks MONEY")
                await conn.execute(
                    "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    existing["total_price"],
                    buyer_money["id"],
                )
                # Transfer resource to buyer (already reserved by creator)
                await conn.execute(
                    "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, $2::resource_type, $3) ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                    filler_user_id,
                    existing["resource_type"],
                    existing["amount"],
                )
                # Pay seller
                seller_money = await conn.fetchrow(
                    "SELECT id FROM inventory_item WHERE user_id = $1 AND resource_type = 'MONEY'::resource_type FOR UPDATE",
                    existing["user_id"],
                )
                if seller_money:
                    await conn.execute(
                        "UPDATE inventory_item SET quantity = quantity + $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                        existing["total_price"],
                        seller_money["id"],
                    )
                else:
                    await conn.execute(
                        "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, 'MONEY'::resource_type, $2)",
                        existing["user_id"],
                        existing["total_price"],
                    )
            closed = await close_market_order(order_id)
    if not closed:
        raise HTTPException(status_code=400, detail="Unable to close order")
    closed["resource_type"] = Resource(closed["resource_type"])  # type: ignore[index]
    return closed  # type: ignore[return-value]
