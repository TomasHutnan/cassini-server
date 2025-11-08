from pydantic import BaseModel, Field, model_validator
from src.game_objects.resources import Resource
from typing import Literal
from uuid import UUID

class MarketOrderBase(BaseModel):
    order_type: Literal["BUY", "SELL"] = Field(..., description="Type of order: BUY or SELL")
    resource_type: Resource = Field(..., description="Material being traded (not MONEY)")
    amount: int = Field(..., gt=0, description="Amount of material units to trade")
    total_price: int = Field(..., ge=0, description="Total price in MONEY for the entire order")

    @model_validator(mode="after")
    def validate_resource_is_material(self):
        # Do not allow MONEY as a material to trade; price is already in MONEY
        if self.resource_type == Resource.MONEY:
            raise ValueError("resource_type cannot be MONEY")
        return self


class MarketOrderCreate(MarketOrderBase):
    pass


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
    order_type: Literal["BUY", "SELL"]
    resource_type: Resource
    amount: int
    total_price: int
    status: Literal["OPEN", "CLOSED"]
    created_at: str
    updated_at: str