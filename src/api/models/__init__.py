"""API request and response models."""

from src.api.models.map import MapResponse, MapCenter, TileResponse
from src.api.models.buildings import (
    BuildingCreate,
    BuildingResponse,
    BuildingListResponse,
    ClaimResourcesResponse,
    BuildingCostsResponse,
)
from src.api.models.auth import (
    LoginRequest,
    RegisterRequest,
    ChangePasswordRequest,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
)
from src.api.models.inventory import InventoryItemResponse, InventoryAdjustRequest
from src.api.models.market import (
    MarketOrderCreate,
    MarketOrderUpdate,
    MarketOrderOut
)

__all__ = [
    # Map models
    "MapResponse",
    "MapCenter",
    "TileResponse",
    # Building models
    "BuildingCreate",
    "BuildingResponse",
    "BuildingListResponse",
    "ClaimResourcesResponse",
    "BuildingCostsResponse",
    # Auth models
    "LoginRequest",
    "RegisterRequest",
    "ChangePasswordRequest",
    "TokenResponse",
    "UserResponse",
    "RefreshTokenRequest",
    # Market models
    "MarketOrderCreate",
    "MarketOrderUpdate",
    "MarketOrderOut",
    # Inventory models
    "InventoryItemResponse",
    "InventoryAdjustRequest",
]
