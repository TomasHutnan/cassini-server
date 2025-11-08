"""API request and response models."""

from src.api.models.map import MapResponse, MapCenter, TileResponse
from src.api.models.buildings import BuildingCreate, ClaimResourcesResponse
from src.api.models.auth import (
    LoginRequest,
    RegisterRequest,
    ChangePasswordRequest,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
)

__all__ = [
    # Map models
    "MapResponse",
    "MapCenter",
    "TileResponse",
    # Building models
    "BuildingCreate",
    "ClaimResourcesResponse",
    # Auth models
    "LoginRequest",
    "RegisterRequest",
    "ChangePasswordRequest",
    "TokenResponse",
    "UserResponse",
    "RefreshTokenRequest",
]
