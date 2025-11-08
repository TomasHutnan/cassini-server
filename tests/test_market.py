"""
Comprehensive tests for market endpoints and inventory interactions using is_buy_order/is_open.

Run with: python tests/test_market.py
"""

import asyncio
import httpx
from uuid import uuid4

BASE_URL = "http://localhost:8000"


async def ensure_server():
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
            r = await client.get("/health")
            return r.status_code == 200
    except Exception:
        return False


async def register_user():
    username = f"market_tester_{uuid4().hex[:8]}"
    password = "StrongPassw0rd!"
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20) as client:
        resp = await client.post(
            "/auth/register", json={"username": username, "password": password}
        )
        if resp.status_code != 201:
            raise RuntimeError(f"Register failed: {resp.status_code} {resp.text}")
        data = resp.json()
        return username, password, data["access_token"], data["refresh_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def set_up_user_with(
    access_token: str,
    money: int = 0,
    wood: int = 0,
    stone: int = 0,
    wheat: int = 0,
):
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20, headers=auth_headers(access_token)) as client:
        if money:
            r = await client.post("/inventory/adjust", json={"resource_type": "MONEY", "quantity_delta": money})
            assert r.status_code == 200, r.text
        if wood:
            r = await client.post("/inventory/adjust", json={"resource_type": "WOOD", "quantity_delta": wood})
            assert r.status_code == 200, r.text
        if stone:
            r = await client.post("/inventory/adjust", json={"resource_type": "STONE", "quantity_delta": stone})
            assert r.status_code == 200, r.text
        if wheat:
            r = await client.post("/inventory/adjust", json={"resource_type": "WHEAT", "quantity_delta": wheat})
            assert r.status_code == 200, r.text


async def get_money(token: str) -> int:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20, headers=auth_headers(token)) as client:
        r = await client.get("/inventory/money")
        if r.status_code == 200:
            return r.json()["quantity"]
        return 0


async def get_qty(token: str, resource_type: str) -> int:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20, headers=auth_headers(token)) as client:
        r = await client.get("/inventory/")
        assert r.status_code == 200
        for item in r.json():
            if item["resource_type"] == resource_type:
                return item["quantity"]
        return 0


async def test_market_flow():
    print("🧪 Market endpoints comprehensive tests (booleans)\n")

    if not await ensure_server():
        print("❌ Server not running at", BASE_URL)
        print("   Start it with: uvicorn src.main:app --reload")
        return

    # Create two users: buyer and seller
    _, _, buyer_token, _ = await register_user()
    _, _, seller_token, _ = await register_user()

    # Provision initial balances
    await set_up_user_with(buyer_token, money=200)
    await set_up_user_with(seller_token, wood=50)

    # Track expected values
    buyer_money = 200
    buyer_wood = 0
    seller_money = 0
    seller_wood = 50

    # 1) BUY order creation success
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(buyer_token)) as client:
        print("1) Creating BUY order (buyer reserves MONEY)...")
        resp = await client.post(
            "/market/orders",
            json={"is_buy_order": True, "resource_type": "WOOD", "amount": 10, "total_price": 100},
        )
        assert resp.status_code == 201, resp.text
        buy_order = resp.json()
        buy_order_id = buy_order["id"]
        assert buy_order["is_buy_order"] is True
        assert buy_order["is_open"] is True
        print("   ✅ BUY order created:", buy_order)

        # Buyer money decreased by 100
        buyer_money -= 100
        assert await get_money(buyer_token) == buyer_money

        # Verify listing (OPEN only)
        list_resp = await client.get("/market/orders", params={"is_buy_order": True, "resource_type": "WOOD"})
        assert list_resp.status_code == 200
        assert any(o["id"] == buy_order_id for o in list_resp.json())

        # 2) BUY order update: increase price (enough funds)
        print("2) Updating BUY order price +50 (buyer reserves more MONEY)...")
        await set_up_user_with(buyer_token, money=50)
        buyer_money += 50
        upd = await client.patch(f"/market/orders/{buy_order_id}", json={"total_price": 150})
        assert upd.status_code == 200, upd.text
        assert upd.json()["total_price"] == 150
        # Reservation increases by 50
        buyer_money -= 50
        assert await get_money(buyer_token) == buyer_money

        # 3) BUY order update: increase price beyond funds (should fail)
        print("3) Updating BUY order price +1000 (should fail due to insufficient MONEY)...")
        upd_fail = await client.patch(f"/market/orders/{buy_order_id}", json={"total_price": 1150})
        assert upd_fail.status_code in (400, 500), upd_fail.text
        # No change
        assert await get_money(buyer_token) == buyer_money

    # 4) SELL order creation success (seller reserves resource)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(seller_token)) as s_client:
        print("4) Creating SELL order (seller reserves WOOD)...")
        sell_resp = await s_client.post(
            "/market/orders",
            json={"is_buy_order": False, "resource_type": "WOOD", "amount": 20, "total_price": 60},
        )
        assert sell_resp.status_code == 201, sell_resp.text
        sell_order = sell_resp.json()
        sell_order_id = sell_order["id"]
        assert sell_order["is_buy_order"] is False
        assert sell_order["is_open"] is True
        print("   ✅ SELL order created:", sell_order)
        # Seller wood decreased by 20
        seller_wood -= 20
        assert await get_qty(seller_token, "WOOD") == seller_wood

        # 5) SELL order update: increase amount within available (should succeed)
        print("5) Updating SELL order amount +10 within reserve (should succeed)...")
        await set_up_user_with(seller_token, wood=10)
        seller_wood += 10
        upd_s = await s_client.patch(f"/market/orders/{sell_order_id}", json={"amount": 30})
        assert upd_s.status_code == 200, upd_s.text
        assert upd_s.json()["amount"] == 30
        # Additional reservation -10 wood
        seller_wood -= 10
        assert await get_qty(seller_token, "WOOD") == seller_wood

        # 6) SELL order update: increase amount beyond available (should fail)
        print("6) Updating SELL order amount to 1000 (should fail insufficient resource)...")
        upd_s_fail = await s_client.patch(f"/market/orders/{sell_order_id}", json={"amount": 1000})
        assert upd_s_fail.status_code in (400, 500), upd_s_fail.text
        assert await get_qty(seller_token, "WOOD") == seller_wood

    # 7) Fill BUY order by seller (seller must have enough resource)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(seller_token)) as s_client:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(buyer_token)) as b_client:
            print("7) Filling BUY order by seller...")
            fill_buy = await s_client.post(f"/market/orders/{buy_order_id}/fill")
            assert fill_buy.status_code == 200, fill_buy.text
            assert fill_buy.json()["is_open"] is False
            # Listing excludes closed by default
            buy_list_after = await b_client.get("/market/orders", params={"is_buy_order": True, "resource_type": "WOOD"})
            assert buy_list_after.status_code == 200
            assert all(o["id"] != buy_order_id for o in buy_list_after.json())
            # Verify balances after BUY fill
            seller_money += 150
            seller_wood -= 10
            buyer_wood += 10
            assert await get_money(seller_token) == seller_money
            assert await get_qty(seller_token, "WOOD") == seller_wood
            assert await get_qty(buyer_token, "WOOD") == buyer_wood
            assert await get_money(buyer_token) == buyer_money

    # 8) Fill SELL order by buyer (buyer must have enough money)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(buyer_token)) as b_client:
        print("8) Ensuring buyer has enough MONEY to fill SELL order...")
        await set_up_user_with(buyer_token, money=100)
        buyer_money += 100
        print("   Filling SELL order by buyer...")
        fill_sell = await b_client.post(f"/market/orders/{sell_order_id}/fill")
        assert fill_sell.status_code == 200, fill_sell.text
        assert fill_sell.json()["is_open"] is False
        # Verify balances after SELL fill
        buyer_money -= 60
        buyer_wood += 30
        seller_money += 60
        assert await get_money(buyer_token) == buyer_money  # expected 140
        assert await get_qty(buyer_token, "WOOD") == buyer_wood  # expected 40
        assert await get_money(seller_token) == seller_money  # expected 210
        assert await get_qty(seller_token, "WOOD") == seller_wood  # expected 20

    # 9) Attempt to fill already closed order (should fail)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(buyer_token)) as client:
        print("9) Attempting to fill CLOSED order (should fail)...")
        closed_fill = await client.post(f"/market/orders/{sell_order_id}/fill")
        assert closed_fill.status_code == 400

    # 10) Create failing orders and unauthorized update
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(buyer_token)) as b_client:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(seller_token)) as s_client:
            print("10) Creating BUY without enough MONEY (should fail)...")
            bad_buy = await b_client.post(
                "/market/orders",
                json={"is_buy_order": True, "resource_type": "WOOD", "amount": 1, "total_price": 1_000_000},
            )
            assert bad_buy.status_code in (400, 500), bad_buy.text

            print("    Creating SELL without enough resource (should fail)...")
            bad_sell = await s_client.post(
                "/market/orders",
                json={"is_buy_order": False, "resource_type": "STONE", "amount": 9999, "total_price": 1},
            )
            assert bad_sell.status_code in (400, 500), bad_sell.text

            print("    Unauthorized update attempt on other's order (should be 403)...")
            unauth_upd = await s_client.patch(f"/market/orders/{buy_order_id}", json={"total_price": 999})
            assert unauth_upd.status_code == 403

    # 11) Deletion refunds (OPEN orders)
    # SELL delete refund
    _, _, temp_seller_token, _ = await register_user()
    await set_up_user_with(temp_seller_token, wood=5)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(temp_seller_token)) as t_client:
        print("11a) Deleting OPEN SELL order refunds resources...")
        before = await get_qty(temp_seller_token, "WOOD")  # expect 5
        tmp = await t_client.post(
            "/market/orders",
            json={"is_buy_order": False, "resource_type": "WOOD", "amount": 5, "total_price": 10},
        )
        assert tmp.status_code == 201
        mid = await get_qty(temp_seller_token, "WOOD")
        assert mid == before - 5 == 0
        tmp_id = tmp.json()["id"]
        del_resp = await t_client.delete(f"/market/orders/{tmp_id}")
        assert del_resp.status_code == 204, del_resp.text
        after = await get_qty(temp_seller_token, "WOOD")
        assert after == before  # refunded back to 5

    # BUY delete refund
    _, _, temp_buyer_token, _ = await register_user()
    await set_up_user_with(temp_buyer_token, money=100)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=auth_headers(temp_buyer_token)) as tb_client:
        print("11b) Deleting OPEN BUY order refunds MONEY...")
        m_before = await get_money(temp_buyer_token)  # expect 100
        tmpb = await tb_client.post(
            "/market/orders",
            json={"is_buy_order": True, "resource_type": "WOOD", "amount": 3, "total_price": 70},
        )
        assert tmpb.status_code == 201
        m_mid = await get_money(temp_buyer_token)
        assert m_mid == m_before - 70 == 30
        tmpb_id = tmpb.json()["id"]
        delb = await tb_client.delete(f"/market/orders/{tmpb_id}")
        assert delb.status_code == 204, delb.text
        m_after = await get_money(temp_buyer_token)
        assert m_after == m_before  # refunded back to 100

    print("\n✅ Market tests completed!")


if __name__ == "__main__":
    asyncio.run(test_market_flow())
