"""Market management API endpoints using boolean flags (is_buy_order, is_open)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.game_objects.resources import Resource
from src.database.connection import get_db_connection
from src.database.queries.market import (
    get_market_order as db_get,
    list_market_orders as db_list,
    update_market_order as db_update,
    close_market_order as db_close,
)

from src.api.models.market import (
    MarketOrderCreate,
    MarketOrderOut,
    MarketOrderUpdate
)

from ..auth.dependencies import get_user_id

router = APIRouter(prefix="/market", tags=["market"])

@router.post("/orders", response_model=MarketOrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: MarketOrderCreate,
    user_id: Annotated[UUID, Depends(get_user_id)],
):
    async with get_db_connection() as conn:
        async with conn.transaction():
            if data.is_buy_order:
                money = await conn.fetchrow(
                    "SELECT id, quantity FROM inventory_item WHERE user_id = $1 AND resource_type = 'MONEY'::resource_type FOR UPDATE",
                    user_id,
                )
                if not money or money["quantity"] < data.total_price:
                    raise HTTPException(status_code=400, detail="Insufficient MONEY for buy order")
                await conn.execute(
                    "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    data.total_price,
                    money["id"],
                )
            else:
                resource = await conn.fetchrow(
                    "SELECT id, quantity FROM inventory_item WHERE user_id = $1 AND resource_type = $2::resource_type FOR UPDATE",
                    user_id,
                    data.resource_type.value,
                )
                if not resource or resource["quantity"] < data.amount:
                    raise HTTPException(status_code=400, detail="Insufficient resource for sell order")
                await conn.execute(
                    "UPDATE inventory_item SET quantity = quantity - $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    data.amount,
                    resource["id"],
                )
            row = await conn.fetchrow(
                """
                INSERT INTO market_order (user_id, is_buy_order, resource_type, amount, total_price)
                VALUES ($1, $2, $3::resource_type, $4, $5)
                RETURNING id, user_id, is_buy_order, resource_type, amount, total_price, is_open, created_at, updated_at
                """,
                user_id,
                data.is_buy_order,
                data.resource_type.value,
                data.amount,
                data.total_price,
            )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create order")
    return MarketOrderOut(
        id=row["id"],
        user_id=row["user_id"],
        is_buy_order=row["is_buy_order"],
        resource_type=Resource(row["resource_type"]),
        amount=row["amount"],
        total_price=row["total_price"],
        is_open=row["is_open"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.get("/orders", response_model=list[MarketOrderOut])
async def read_orders(
    is_buy_order: bool | None = None,
    resource_type: Resource | None = None,
    user_id: UUID | None = None,
    include_closed: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    rows = await db_list(
        is_buy_order=is_buy_order,
        resource_type=resource_type.value if resource_type else None,
        user_id=user_id,
        include_closed=include_closed,
        limit=max(limit, 1),
        offset=max(offset, 0),
    )
    return [
        MarketOrderOut(
            id=r["id"],
            user_id=r["user_id"],
            is_buy_order=r["is_buy_order"],
            resource_type=Resource(r["resource_type"]),
            amount=r["amount"],
            total_price=r["total_price"],
            is_open=r["is_open"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )
        for r in rows
    ]


@router.get("/orders/{order_id}", response_model=MarketOrderOut)
async def read_order(order_id: UUID):
    r = await db_get(order_id)
    if not r:
        raise HTTPException(status_code=404, detail="Order not found")
    return MarketOrderOut(
        id=r["id"],
        user_id=r["user_id"],
        is_buy_order=r["is_buy_order"],
        resource_type=Resource(r["resource_type"]),
        amount=r["amount"],
        total_price=r["total_price"],
        is_open=r["is_open"],
        created_at=str(r["created_at"]),
        updated_at=str(r["updated_at"]),
    )


@router.patch("/orders/{order_id}", response_model=MarketOrderOut)
async def update_order(
    order_id: UUID,
    data: MarketOrderUpdate,
    user_id: Annotated[UUID, Depends(get_user_id)],
):
    existing = await db_get(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this order")
    if not existing["is_open"]:
        raise HTTPException(status_code=400, detail="Only open orders can be modified")
    new_resource = data.resource_type.value if data.resource_type else existing["resource_type"]
    new_amount = data.amount if data.amount is not None else existing["amount"]
    new_price = data.total_price if data.total_price is not None else existing["total_price"]
    async with get_db_connection() as conn:
        async with conn.transaction():
            if not existing["is_buy_order"]:  # SELL
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
            else:  # BUY
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
            updated = await db_update(
                order_id=order_id,
                user_id=user_id,
                resource_type=new_resource if data.resource_type else None,
                amount=data.amount,
                total_price=data.total_price,
            )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update order")
    return MarketOrderOut(
        id=updated["id"],
        user_id=updated["user_id"],
        is_buy_order=updated["is_buy_order"],
        resource_type=Resource(updated["resource_type"]),
        amount=updated["amount"],
        total_price=updated["total_price"],
        is_open=updated["is_open"],
        created_at=str(updated["created_at"]),
        updated_at=str(updated["updated_at"]),
    )


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    user_id: Annotated[UUID, Depends(get_user_id)],
):
    existing = await db_get(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    if not existing["is_open"]:
        raise HTTPException(status_code=400, detail="Only open orders can be deleted")
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this order")

    async with get_db_connection() as conn:
        async with conn.transaction():
            order = await conn.fetchrow(
                "SELECT id, user_id, is_buy_order, resource_type, amount, total_price, is_open FROM market_order WHERE id = $1 FOR UPDATE",
                order_id,
            )
            if not order or order["user_id"] != user_id or not order["is_open"]:
                raise HTTPException(status_code=400, detail="Order cannot be deleted")
            if order["is_buy_order"]:
                await conn.execute(
                    "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, 'MONEY'::resource_type, $2)\n                     ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                    user_id,
                    order["total_price"],
                )
            else:
                await conn.execute(
                    "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, $2::resource_type, $3)\n                     ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                    user_id,
                    order["resource_type"],
                    order["amount"],
                )
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
    user_id: Annotated[UUID, Depends(get_user_id)],
):
    existing = await db_get(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    if not existing["is_open"]:
        raise HTTPException(status_code=400, detail="Order is not open")
    filler_user_id = user_id
    async with get_db_connection() as conn:
        async with conn.transaction():
            if existing["is_buy_order"]:
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
                await conn.execute(
                    "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, $2::resource_type, $3) ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                    existing["user_id"],
                    existing["resource_type"],
                    existing["amount"],
                )
            else:
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
                await conn.execute(
                    "INSERT INTO inventory_item (user_id, resource_type, quantity) VALUES ($1, $2::resource_type, $3) ON CONFLICT (user_id, resource_type) DO UPDATE SET quantity = inventory_item.quantity + EXCLUDED.quantity, updated_at = CURRENT_TIMESTAMP",
                    filler_user_id,
                    existing["resource_type"],
                    existing["amount"],
                )
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
            closed = await db_close(order_id)
    if not closed:
        raise HTTPException(status_code=400, detail="Unable to close order")
    return MarketOrderOut(
        id=closed["id"],
        user_id=closed["user_id"],
        is_buy_order=closed["is_buy_order"],
        resource_type=Resource(closed["resource_type"]),
        amount=closed["amount"],
        total_price=closed["total_price"],
        is_open=closed["is_open"],
        created_at=str(closed["created_at"]),
        updated_at=str(closed["updated_at"]),
    )
