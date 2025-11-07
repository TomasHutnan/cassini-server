from dataclasses import dataclass
from .resources import Resource


@dataclass
class InventoryItem:
    type: Resource
    quantity: int