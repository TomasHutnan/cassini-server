"""Pydantic models for authentication API requests and responses."""

from pydantic import BaseModel, Field


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


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str
