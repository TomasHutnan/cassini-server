# Authentication System Guide

## Overview

This server implements JWT-based authentication with access and refresh tokens. All sensitive endpoints can be protected using FastAPI's dependency injection.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# JWT Configuration
JWT_SECRET_KEY=your--secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=300
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://user:password@host:port/database
```

**Important:** Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Database Setup

Ensure your PostgreSQL database has the schema from `database/schema.sql`.

## API Endpoints

### Public Endpoints (No Authentication Required)

#### Register
```http
POST /auth/register
Content-Type: application/json

{
  "username": "player1",
  "password": "securepassword123"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "player1",
  "password": "securepassword123"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Protected Endpoints (Require Authentication)

All protected endpoints require the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

#### Get Current User Info
```http
GET /auth/me
Authorization: Bearer eyJ...
```

Response:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "player1",
  "created_at": "2025-01-01T12:00:00"
}
```

#### Change Password
```http
POST /auth/change-password
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "old_password": "securepassword123",
  "new_password": "newsecurepassword456"
}
```

Response: `204 No Content`

## Protecting Your Endpoints

### Basic Protection

To require authentication on any endpoint, add the `get_current_user` dependency:

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from src.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/protected")
async def protected_route(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    """This endpoint requires authentication."""
    return {
        "message": f"Hello, {current_user['name']}!",
        "user_id": current_user["id"]
    }
```

### Extract Just User ID

If you only need the user ID:

```python
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
from src.auth.dependencies import get_user_id

router = APIRouter()

@router.post("/buildings")
async def create_building(
    user_id: Annotated[UUID, Depends(get_user_id)],
    building_name: str
):
    """Create a building for the authenticated user."""
    return {
        "owner_id": user_id,
        "name": building_name
    }
```

### Manual Token Verification

For more control (e.g., optional authentication):

```python
from fastapi import APIRouter, Header
from src.auth.jwt import get_user_id_from_token

router = APIRouter()

@router.get("/optional-auth")
async def optional_auth_route(authorization: str | None = Header(None)):
    """Endpoint that works with or without auth."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        user_id = get_user_id_from_token(token)
        if user_id:
            return {"message": "Authenticated", "user_id": str(user_id)}
    
    return {"message": "Anonymous access"}
```

## Example: Protected Buildings API

```python
"""Building management with authentication."""

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.auth.dependencies import get_user_id

router = APIRouter(prefix="/buildings", tags=["buildings"])


class BuildingCreate(BaseModel):
    hex_id: str
    name: str
    building_type: str


@router.post("/")
async def create_building(
    data: BuildingCreate,
    user_id: Annotated[UUID, Depends(get_user_id)]
):
    """Create a building (requires authentication)."""
    # TODO: Implement database insert
    return {
        "hex_id": data.hex_id,
        "name": data.name,
        "type": data.building_type,
        "owner_id": str(user_id),
        "message": "Building created successfully"
    }


@router.get("/my-buildings")
async def list_my_buildings(
    user_id: Annotated[UUID, Depends(get_user_id)]
):
    """List all buildings owned by the authenticated user."""
    # TODO: Implement database query
    return {
        "owner_id": str(user_id),
        "buildings": []
    }


@router.delete("/{building_id}")
async def delete_building(
    building_id: str,
    user_id: Annotated[UUID, Depends(get_user_id)]
):
    """Delete a building (requires ownership)."""
    # TODO: Verify ownership and delete from database
    return {"message": "Building deleted successfully"}
```

## Testing with curl

### 1. Register
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"player1","password":"password123"}'
```

Save the `access_token` from the response.

### 2. Access Protected Endpoint
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 3. Create Building (Protected)
```bash
curl -X POST http://localhost:8000/buildings/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"hex_id":"8928308280fffff","name":"My Farm","building_type":"farm"}'
```

## Security Best Practices

1. **Secret Key**: Use a strong, random secret key in production
2. **HTTPS**: Always use HTTPS in production to protect tokens in transit
3. **Token Storage**: Store tokens securely on the client (httpOnly cookies or secure storage)
4. **Token Expiration**: Keep access tokens short-lived (15-30 minutes)
5. **Refresh Tokens**: Store refresh tokens securely, invalidate on logout
6. **Password Requirements**: Enforce strong passwords (minimum 8 characters in this implementation)
7. **Rate Limiting**: Add rate limiting to auth endpoints to prevent brute force attacks
8. **CORS**: Configure CORS properly for your frontend domain

## Error Handling

All auth endpoints return standard HTTP status codes:

- `200 OK` - Success
- `201 Created` - User registered successfully
- `204 No Content` - Password changed successfully
- `400 Bad Request` - Invalid request data or username already exists
- `401 Unauthorized` - Invalid credentials or token
- `500 Internal Server Error` - Server error

Error response format:
```json
{
  "detail": "Error message here"
}
```

## Token Lifecycle

1. **User registers/logs in** → Receive access_token + refresh_token
2. **Use access_token** → Make authenticated requests (valid for 30 minutes)
3. **Access token expires** → Use refresh_token to get new tokens
4. **Refresh token expires** → User must log in again (valid for 7 days)

