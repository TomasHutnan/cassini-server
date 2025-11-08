"""
Test script for building management endpoints.

PREREQUISITES:
- Server must be running at http://localhost:8000
- Database must have the following test users created:
  * Username: test_user_1, Password: ae_pass123#
  * Username: test_user_2, Password: ae_pass123#
  * Username: test_user_3, Password: ae_pass123#

Tests building creation, listing, retrieval, claiming resources, and deletion.
Run with: python tests/test_buildings.py
"""

import asyncio
import httpx


BASE_URL = "http://localhost:8000"

# Test user credentials (must exist in database)
TEST_USERS = [
    {"username": "test_user_1", "password": "ae_pass123#"},
    {"username": "test_user_2", "password": "ae_pass123#"},
    {"username": "test_user_3", "password": "ae_pass123#"},
]


async def login_user(client: httpx.AsyncClient, username: str, password: str) -> str:
    """Login and return access token."""
    response = await client.post(
        "/auth/login",
        json={"username": username, "password": password}
    )
    
    if response.status_code != 200:
        raise Exception(f"Login failed for {username}: {response.text}")
    
    return response.json()["access_token"]


async def test_create_building(client: httpx.AsyncClient, token: str, h3_index: str, name: str) -> dict:
    """Test creating a new building."""
    response = await client.post(
        "/buildings/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "h3_index": h3_index,
            "name": name,
            "biome_type": "GRASSLAND",
            "resource_type": "WOOD"
        }
    )
    
    return response


async def test_buildings_flow():
    """Test the complete buildings flow."""
    print("🏗️  Starting Building Management Tests\n")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        
        # Login all test users
        print("1️⃣ Logging in test users...")
        tokens = {}
        try:
            for user in TEST_USERS:
                token = await login_user(client, user["username"], user["password"])
                tokens[user["username"]] = token
                print(f"   ✅ {user['username']} logged in")
        except Exception as e:
            print(f"   ❌ Login failed: {e}")
            print("   Make sure test users exist in the database!")
            return
        
        print()
        
        # Test 2: Create buildings for each user
        print("2️⃣ Testing building creation...")
        user1_token = tokens["test_user_1"]
        user2_token = tokens["test_user_2"]
        
        # User 1 creates a building
        try:
            building1_response = await test_create_building(
                client, user1_token,
                "8c2a1072b3b1dff",
                "User 1's Farm"
            )
            
            if building1_response.status_code == 201:
                building1 = building1_response.json()
                print(f"   ✅ User 1 created building: {building1['name']}")
                print(f"      H3 Index: {building1['h3_index']}")
                print(f"      Biome: {building1['biome_type']}")
                print(f"      Resource: {building1['resource_type']}")
            else:
                print(f"   ❌ Building creation failed: {building1_response.status_code}")
                print(f"      {building1_response.text}")
        except Exception as e:
            print(f"   ❌ Error creating building: {e}")
        
        # User 2 creates a building
        try:
            building2_response = await test_create_building(
                client, user2_token,
                "8c2a1072b3b1fff",
                "User 2's Mine"
            )
            
            if building2_response.status_code == 201:
                building2 = building2_response.json()
                print(f"   ✅ User 2 created building: {building2['name']}")
            else:
                print(f"   ⚠️  User 2 building creation: {building2_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 3: Try to create building at same location (should fail)
        print("3️⃣ Testing duplicate location rejection...")
        try:
            duplicate_response = await test_create_building(
                client, user2_token,
                "8c2a1072b3b1dff",  # Same as building1
                "User 2's Duplicate"
            )
            
            if duplicate_response.status_code == 409:
                print("   ✅ Duplicate location correctly rejected")
            else:
                print(f"   ⚠️  Unexpected status: {duplicate_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 4: List user's buildings
        print("4️⃣ Testing list my buildings...")
        try:
            my_buildings_response = await client.get(
                "/buildings/my",
                headers={"Authorization": f"Bearer {user1_token}"}
            )
            
            if my_buildings_response.status_code == 200:
                my_buildings = my_buildings_response.json()
                print(f"   ✅ User 1 has {my_buildings['total']} building(s)")
                for building in my_buildings['buildings']:
                    print(f"      - {building['name']} (Level {building['level']})")
            else:
                print(f"   ❌ Failed: {my_buildings_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 5: Get specific building (public endpoint)
        print("5️⃣ Testing get building by H3 index...")
        try:
            get_building_response = await client.get(
                "/buildings/8c2a1072b3b1dff"
            )
            
            if get_building_response.status_code == 200:
                building = get_building_response.json()
                print(f"   ✅ Retrieved building: {building['name']}")
                print(f"      Owner: {building['user_id']}")
                print(f"      Level: {building['level']}")
                print(f"      Last claimed: {building['last_claim_at']}")
            else:
                print(f"   ❌ Failed: {get_building_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 6: Get non-existent building
        print("6️⃣ Testing get non-existent building...")
        try:
            not_found_response = await client.get(
                "/buildings/8c0000000000000"
            )
            
            if not_found_response.status_code == 404:
                print("   ✅ Non-existent building correctly returns 404")
            else:
                print(f"   ⚠️  Unexpected status: {not_found_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 7: List buildings in area
        print("7️⃣ Testing list buildings in area...")
        try:
            area_response = await client.get(
                "/buildings/area",
                params={
                    "lat": 48.1486,
                    "lon": 17.1077,
                    "range_m": 500
                }
            )
            
            if area_response.status_code == 200:
                area_buildings = area_response.json()
                print(f"   ✅ Found {area_buildings['total']} building(s) in area")
                for building in area_buildings['buildings']:
                    print(f"      - {building['name']} at {building['h3_index'][:15]}...")
            else:
                print(f"   ❌ Failed: {area_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 8: Claim resources from building
        print("8️⃣ Testing claim building resources...")
        
        # Wait a second to allow some resources to accumulate
        print("   ⏳ Waiting 2 seconds for resources to accumulate...")
        await asyncio.sleep(2)
        
        try:
            claim_response = await client.post(
                "/buildings/8c2a1072b3b1dff/claim",
                headers={"Authorization": f"Bearer {user1_token}"}
            )
            
            if claim_response.status_code == 200:
                claim_data = claim_response.json()
                print(f"   ✅ Claimed {claim_data['resources_claimed']} {claim_data['resource_type']}")
                print(f"      New inventory total: {claim_data['new_inventory_total']}")
                print(f"      Seconds elapsed: {claim_data['seconds_elapsed']:.2f}")
            else:
                print(f"   ❌ Failed: {claim_response.status_code}")
                print(f"      {claim_response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 9: Try to claim resources from another user's building
        print("9️⃣ Testing claim from another user's building...")
        try:
            unauthorized_claim = await client.post(
                "/buildings/8c2a1072b3b1dff/claim",  # User 1's building
                headers={"Authorization": f"Bearer {user2_token}"}  # User 2's token
            )
            
            if unauthorized_claim.status_code == 403:
                print("   ✅ Unauthorized claim correctly rejected")
            else:
                print(f"   ⚠️  Unexpected status: {unauthorized_claim.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 10: Try to delete another user's building
        print("🔟 Testing delete another user's building...")
        try:
            unauthorized_delete = await client.delete(
                "/buildings/8c2a1072b3b1dff",  # User 1's building
                headers={"Authorization": f"Bearer {user2_token}"}  # User 2's token
            )
            
            if unauthorized_delete.status_code == 403:
                print("   ✅ Unauthorized deletion correctly rejected")
            else:
                print(f"   ⚠️  Unexpected status: {unauthorized_delete.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 11: Delete own building
        print("1️⃣1️⃣ Testing delete own building...")
        try:
            delete_response = await client.delete(
                "/buildings/8c2a1072b3b1dff",
                headers={"Authorization": f"Bearer {user1_token}"}
            )
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                print("   ✅ Building deleted successfully")
                print(f"      Message: {delete_data['message']}")
                
                # Verify building is gone
                verify_response = await client.get("/buildings/8c2a1072b3b1dff")
                if verify_response.status_code == 404:
                    print("   ✅ Building confirmed deleted")
            else:
                print(f"   ❌ Failed: {delete_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 12: Try to delete non-existent building
        print("1️⃣2️⃣ Testing delete non-existent building...")
        try:
            not_found_delete = await client.delete(
                "/buildings/8c0000000000000",
                headers={"Authorization": f"Bearer {user1_token}"}
            )
            
            if not_found_delete.status_code == 404:
                print("   ✅ Non-existent building deletion returns 404")
            else:
                print(f"   ⚠️  Unexpected status: {not_found_delete.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Cleanup: Delete User 2's building if it exists
        print("🧹 Cleaning up test buildings...")
        try:
            await client.delete(
                "/buildings/8c2a1072b3b1fff",
                headers={"Authorization": f"Bearer {user2_token}"}
            )
            print("   ✅ Cleanup complete")
        except Exception:
            pass
    
    print("\n" + "="*50)
    print("✅ All building management tests completed!")
    print("="*50)


async def test_connection():
    """Test if the server is running."""
    print("🔌 Testing server connection...\n")
    try:
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            response = await client.get("/health")
            if response.status_code == 200:
                print("✅ Server is running and healthy")
                health_data = response.json()
                print(f"   Status: {health_data.get('status')}")
                print(f"   Database configured: {health_data.get('database_configured')}")
                print()
                return True
            else:
                print(f"⚠️  Server responded with status {response.status_code}")
                return False
    except httpx.ConnectError:
        print("❌ Cannot connect to server. Make sure it's running at", BASE_URL)
        print("   Run: uvicorn src.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return False


async def main():
    """Main test runner."""
    print("=" * 50)
    print("🏗️  Building Management API Test Suite")
    print("=" * 50)
    print()
    
    # Check if server is running
    if not await test_connection():
        return
    
    # Run building tests
    await test_buildings_flow()


if __name__ == "__main__":
    asyncio.run(main())
