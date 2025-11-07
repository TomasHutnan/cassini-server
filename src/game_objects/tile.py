from dataclasses import dataclass, field
from .settlement import Settlement


@dataclass
class Point:
    lat: float
    lon: float

    def to_list(self) -> list[float]:
        return [self.lat, self.lon]


@dataclass
class Tile:
    hex_id: str
    boundary: list[Point] = field(default_factory=list)
    biome: str
    settlement: Settlement | None = None

    def get_info(self):
        pass