"""Pydantic models for inventory API."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from src.game_objects.resources import Resource

class InventoryItemResponse(BaseModel):
    id: Optional[UUID] = Field(None, description="Inventory item ID (may be None if deleted)")
    user_id: Optional[UUID] = Field(None, description="Owner user ID")
    resource_type: Resource
    quantity: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class InventoryAdjustRequest(BaseModel):
    resource_type: Resource = Field(..., description="Resource to adjust")
    quantity_delta: int = Field(..., description="Positive to add, negative to subtract; cannot be 0")

    @model_validator(mode="after")
    def validate_delta(self):
        if self.quantity_delta == 0:
            raise ValueError("quantity_delta cannot be 0")
        return self
