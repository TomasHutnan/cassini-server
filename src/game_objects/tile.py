from dataclasses import dataclass
from .building import Building
from .biome import BiomeType


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
    biome: BiomeType
    building: Building | None = None

    def get_info(self):
        pass
