"""User authentication and management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..database.queries.users import create_user, get_user_by_name, update_user_password
from ..auth.dependencies import get_current_user
from ..auth.jwt import create_access_token, create_refresh_token, verify_token
from ..auth.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Models


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """Registration data."""

    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    """Password change data."""

    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User information response."""

    id: str
    username: str
    created_at: str


# Endpoints


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(data: RegisterRequest):
    """Register a new user account.

    Creates a new user with hashed password and returns JWT tokens.

    Args:
        data: Registration request with username and password

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException 400: If username already exists
    """
    # Check if username already exists
    existing_user = await get_user_by_name(data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Hash password with salt
    hashed_password, salt = hash_password(data.password)

    # Create user
    user = await create_user(data.username, hashed_password, salt)

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user["id"])})
    refresh_token = create_refresh_token(data={"sub": str(user["id"])})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """Login with username and password.

    Validates credentials and returns JWT tokens.

    Args:
        data: Login request with username and password

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException 401: If credentials are invalid
    """
    # Fetch user
    user = await get_user_by_name(data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(
        data.password, user["hash_salt"], user["hash_pass"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user["id"])})
    refresh_token = create_refresh_token(data={"sub": str(user["id"])})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token using a valid refresh token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException 401: If refresh token is invalid
    """
    # Verify refresh token
    payload = verify_token(refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate new tokens
    access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(data={"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Change the current user's password.

    Requires authentication. Validates old password before updating.

    Args:
        data: Password change request with old and new passwords
        current_user: Current authenticated user (from JWT)

    Raises:
        HTTPException 401: If old password is incorrect
        HTTPException 500: If password update fails
    """
    # Verify old password
    if not verify_password(
        data.old_password, current_user["hash_salt"], current_user["hash_pass"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    # Hash new password
    hashed_password, salt = hash_password(data.new_password)

    # Update password
    success = await update_user_password(
        current_user["id"], hashed_password, salt
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )


@router.get("/info", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get current authenticated user's information.

    Requires authentication.

    Args:
        current_user: Current authenticated user (from JWT)

    Returns:
        User information
    """
    return UserResponse(
        id=str(current_user["id"]),
        username=current_user["name"],
        created_at=str(current_user["created_at"]),
    )
