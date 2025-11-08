from dataclasses import dataclass, field
from .resources import Resource
from .inventory import InventoryItem


@dataclass
class Building:
    player_id: str
    name: str
    resource_type: Resource
    level: int
    inventory: list[InventoryItem] = field(default_factory=list)