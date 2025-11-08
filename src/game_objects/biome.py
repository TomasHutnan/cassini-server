"""Biome types and utilities."""

from enum import Enum


class BiomeType(str, Enum):
    """Available biome types in the game.
    
    Maps to the biome_type PostgreSQL ENUM.
    """
    TREE_COVER = "TREE_COVER"           # Tree cover (Copernicus code: 10)
    SHRUBLAND = "SHRUBLAND"             # Shrubland (20)
    GRASSLAND = "GRASSLAND"             # Grassland (30)
    CROPLAND = "CROPLAND"               # Cropland (40)
    WETLAND = "WETLAND"                 # Herbaceous wetland (50)
    MANGROVES = "MANGROVES"             # Mangroves (60)
    MOSS_LICHEN = "MOSS_LICHEN"         # Moss and lichen (70)
    BARE = "BARE"                       # Bare/sparse vegetation (80)
    BUILT_UP = "BUILT_UP"               # Built-up (90)
    WATER = "WATER"                     # Permanent water bodies (100)
    SNOW_ICE = "SNOW_ICE"               # Snow and ice (110)
    UNCLASSIFIABLE = "UNCLASSIFIABLE"   # Unclassifiable (254)


# Mapping from Copernicus land cover codes to BiomeType enum
COPERNICUS_CODE_TO_BIOME = {
    10: BiomeType.TREE_COVER,
    20: BiomeType.SHRUBLAND,
    30: BiomeType.GRASSLAND,
    40: BiomeType.CROPLAND,
    50: BiomeType.WETLAND,
    60: BiomeType.MANGROVES,
    70: BiomeType.MOSS_LICHEN,
    80: BiomeType.BARE,
    90: BiomeType.BUILT_UP,
    100: BiomeType.WATER,
    110: BiomeType.SNOW_ICE,
    254: BiomeType.UNCLASSIFIABLE,
}

# Reverse mapping for display purposes
BIOME_TO_COPERNICUS_CODE = {v: k for k, v in COPERNICUS_CODE_TO_BIOME.items()}


def code_to_biome(code: int) -> BiomeType:
    """Convert Copernicus land cover code to BiomeType.
    
    Args:
        code: Copernicus land cover classification code
        
    Returns:
        BiomeType enum value
        
    Raises:
        ValueError: If code is not recognized
    """
    if code not in COPERNICUS_CODE_TO_BIOME:
        raise ValueError(f"Unknown Copernicus land cover code: {code}")
    return COPERNICUS_CODE_TO_BIOME[code]


def biome_to_code(biome: BiomeType) -> int:
    """Convert BiomeType to Copernicus land cover code.
    
    Args:
        biome: BiomeType enum value
        
    Returns:
        Copernicus land cover classification code
    """
    return BIOME_TO_COPERNICUS_CODE[biome]
