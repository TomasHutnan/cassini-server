"""Pydantic models for market API using boolean flags."""
from pydantic import BaseModel, Field, model_validator
from src.game_objects.resources import Resource
from uuid import UUID

class MarketOrderCreate(BaseModel):
    is_buy_order: bool = Field(..., description="True for BUY order, False for SELL")
    resource_type: Resource = Field(..., description="Material being traded (not MONEY)")
    amount: int = Field(..., gt=0, description="Amount of material units to trade")
    total_price: int = Field(..., ge=0, description="Total price in MONEY for the entire order")

    @model_validator(mode="after")
    def validate_resource_is_material(self):
        if self.resource_type == Resource.MONEY:
            raise ValueError("resource_type cannot be MONEY")
        return self

class MarketOrderUpdate(BaseModel):
    resource_type: Resource | None = Field(None, description="Material (not MONEY)")
    amount: int | None = Field(None, gt=0, description="Amount of material units")
    total_price: int | None = Field(None, ge=0, description="Total price in MONEY")

    @model_validator(mode="after")
    def validate_resource_is_material(self):
        if self.resource_type == Resource.MONEY:
            raise ValueError("Material cannot be MONEY")
        return self

class MarketOrderOut(BaseModel):
    id: UUID
    user_id: UUID
    is_buy_order: bool
    resource_type: Resource
    amount: int
    total_price: int
    is_open: bool
    created_at: str
    updated_at: str