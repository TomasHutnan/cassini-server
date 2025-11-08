"""
Test script for authentication endpoints.

Tests user registration, login, token refresh, and protected endpoints.
Run with: python test_auth.py
"""

import asyncio
import httpx
from uuid import uuid4


BASE_URL = "http://localhost:8000"


async def test_auth_flow():
    """Test the complete authentication flow."""
    print("🧪 Starting Authentication Tests\n")
    
    # Generate unique username for this test run
    test_username = f"testuser_{uuid4().hex[:8]}"
    test_password = "SecurePassword123!"
    
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        
        # Test 1: Register a new user
        print("1️⃣ Testing user registration...")
        try:
            register_response = await client.post(
                "/auth/register",
                json={
                    "username": test_username,
                    "password": test_password
                }
            )
            
            if register_response.status_code == 201:
                print("   ✅ User registered successfully")
                register_data = register_response.json()
                access_token = register_data["access_token"]
                refresh_token = register_data["refresh_token"]
                print(f"   📝 Access token: {access_token[:20]}...")
                print(f"   📝 Refresh token: {refresh_token[:20]}...")
            else:
                print(f"   ❌ Registration failed: {register_response.status_code}")
                print(f"   {register_response.text}")
                return
        except Exception as e:
            print(f"   ❌ Registration error: {e}")
            return
        
        print()
        
        # Test 2: Try to register with same username (should fail)
        print("2️⃣ Testing duplicate username registration...")
        try:
            duplicate_response = await client.post(
                "/auth/register",
                json={
                    "username": test_username,
                    "password": "DifferentPassword123!"
                }
            )
            
            if duplicate_response.status_code == 400:
                print("   ✅ Duplicate username correctly rejected")
            else:
                print(f"   ⚠️  Unexpected status: {duplicate_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 3: Login with correct credentials
        print("3️⃣ Testing login with correct credentials...")
        try:
            login_response = await client.post(
                "/auth/login",
                json={
                    "username": test_username,
                    "password": test_password
                }
            )
            
            if login_response.status_code == 200:
                print("   ✅ Login successful")
                login_data = login_response.json()
                new_access_token = login_data["access_token"]
                print(f"   📝 New access token: {new_access_token[:20]}...")
            else:
                print(f"   ❌ Login failed: {login_response.status_code}")
                print(f"   {login_response.text}")
        except Exception as e:
            print(f"   ❌ Login error: {e}")
        
        print()
        
        # Test 4: Login with wrong password
        print("4️⃣ Testing login with incorrect password...")
        try:
            wrong_login_response = await client.post(
                "/auth/login",
                json={
                    "username": test_username,
                    "password": "WrongPassword123!"
                }
            )
            
            if wrong_login_response.status_code == 401:
                print("   ✅ Incorrect password correctly rejected")
            else:
                print(f"   ⚠️  Unexpected status: {wrong_login_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 5: Access protected endpoint with valid token
        print("5️⃣ Testing protected endpoint with valid token...")
        try:
            me_response = await client.get(
                "/auth/info",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if me_response.status_code == 200:
                print("   ✅ Protected endpoint accessed successfully")
                user_data = me_response.json()
                print(f"   👤 User ID: {user_data['id']}")
                print(f"   👤 Username: {user_data['username']}")
            else:
                print(f"   ❌ Failed: {me_response.status_code}")
                print(f"   {me_response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 6: Access protected endpoint without token
        print("6️⃣ Testing protected endpoint without token...")
        try:
            no_token_response = await client.get("/auth/info")
            
            if no_token_response.status_code == 403:
                print("   ✅ Access correctly denied without token")
            else:
                print(f"   ⚠️  Unexpected status: {no_token_response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 7: Refresh token
        print("7️⃣ Testing token refresh...")
        try:
            refresh_response = await client.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            if refresh_response.status_code == 200:
                print("   ✅ Token refreshed successfully")
                refresh_data = refresh_response.json()
                print(f"   📝 New access token: {refresh_data['access_token'][:20]}...")
                print(f"   📝 New refresh token: {refresh_data['refresh_token'][:20]}...")
                
                # Use new token to access protected endpoint
                new_me_response = await client.get(
                    "/auth/info",
                    headers={"Authorization": f"Bearer {refresh_data['access_token']}"}
                )
                if new_me_response.status_code == 200:
                    print("   ✅ New token works correctly")
            else:
                print(f"   ❌ Refresh failed: {refresh_response.status_code}")
                print(f"   {refresh_response.text}")
        except Exception as e:
            print(f"   ❌ Refresh error: {e}")
        
        print()
        
        # Test 8: Change password
        print("8️⃣ Testing password change...")
        new_password = "NewSecurePassword456!"
        try:
            change_pw_response = await client.post(
                "/auth/change-password",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "old_password": test_password,
                    "new_password": new_password
                }
            )
            
            if change_pw_response.status_code == 204:
                print("   ✅ Password changed successfully")
                
                # Try to login with old password (should fail)
                old_pw_login = await client.post(
                    "/auth/login",
                    json={
                        "username": test_username,
                        "password": test_password
                    }
                )
                
                if old_pw_login.status_code == 401:
                    print("   ✅ Old password no longer works")
                
                # Try to login with new password (should work)
                new_pw_login = await client.post(
                    "/auth/login",
                    json={
                        "username": test_username,
                        "password": new_password
                    }
                )
                
                if new_pw_login.status_code == 200:
                    print("   ✅ New password works correctly")
            else:
                print(f"   ❌ Password change failed: {change_pw_response.status_code}")
                print(f"   {change_pw_response.text}")
        except Exception as e:
            print(f"   ❌ Password change error: {e}")
    
    print("\n" + "="*50)
    print("✅ All authentication tests completed!")
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
    print("🧪 Authentication API Test Suite")
    print("=" * 50)
    print()
    
    # Check if server is running
    if not await test_connection():
        return
    
    # Run auth tests
    await test_auth_flow()


if __name__ == "__main__":
    asyncio.run(main())
