"""Loads geospatial data from Copernicus.

Public interface for fetching map data with biomes and water features.
"""

from src.copernicus.hexwater_prototype import generate_map
import json


def get_map_data(lat: float, lon: float, range_m: int) -> list[dict]:
    return generate_map(lat, lon, range_m)