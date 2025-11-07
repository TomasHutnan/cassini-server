from dataclasses import dataclass, field
from .resources import Resource
from .inventory import InventoryItem


@dataclass
class Settlement:
    player_id: str
    name: str
    type: Resource
    level: int
    inventory: list[InventoryItem] = field(default_factory=list)