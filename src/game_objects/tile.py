from dataclasses import dataclass
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
    center: Point
    biome: str
    settlement: Settlement | None = None

    def get_info(self):
        pass