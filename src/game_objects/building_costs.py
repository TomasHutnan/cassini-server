"""Building cost configuration and calculation.

Building costs scale with level using the formula:
cost_per_resource = base_cost * level

This allows easy balancing and real-time adjustments.
"""

from typing import Dict, List
from pydantic import BaseModel

from src.game_objects.resources import Resource


class ResourceAmount(BaseModel):
    """A resource type with an amount."""
    
    resource_type: str  # Resource enum value (e.g., "WHEAT", "WOOD", "STONE")
    amount: int


class BuildingCostsConfig(BaseModel):
    """Configuration for all building costs."""
    
    # Base costs for creating a new building (level 1)
    base_building_cost: List[ResourceAmount]
    
    # Base costs for upgrading (multiplied by target level)
    base_upgrade_cost: List[ResourceAmount]
    
    # Maximum building level
    max_level: int


# Default building costs configuration per building type (resource produced)
# Each building type has different construction costs
DEFAULT_BUILDING_COSTS_BY_TYPE = {
    # Farm (produces WHEAT) - requires mostly wood and some stone
    Resource.WHEAT.value: BuildingCostsConfig(
        base_building_cost=[
            ResourceAmount(resource_type=Resource.WHEAT.value, amount=20),
            ResourceAmount(resource_type=Resource.WOOD.value, amount=100),
            ResourceAmount(resource_type=Resource.STONE.value, amount=50),
        ],
        base_upgrade_cost=[
            ResourceAmount(resource_type=Resource.WHEAT.value, amount=10),
            ResourceAmount(resource_type=Resource.WOOD.value, amount=50),
            ResourceAmount(resource_type=Resource.STONE.value, amount=25),
        ],
        max_level=10
    ),
    
    # Lumber Mill (produces WOOD) - requires mostly wheat and some stone
    Resource.WOOD.value: BuildingCostsConfig(
        base_building_cost=[
            ResourceAmount(resource_type=Resource.WHEAT.value, amount=80),
            ResourceAmount(resource_type=Resource.WOOD.value, amount=30),
            ResourceAmount(resource_type=Resource.STONE.value, amount=60),
        ],
        base_upgrade_cost=[
            ResourceAmount(resource_type=Resource.WHEAT.value, amount=40),
            ResourceAmount(resource_type=Resource.WOOD.value, amount=15),
            ResourceAmount(resource_type=Resource.STONE.value, amount=30),
        ],
        max_level=10
    ),
    
    # Mine (produces STONE) - requires mostly wood and wheat
    Resource.STONE.value: BuildingCostsConfig(
        base_building_cost=[
            ResourceAmount(resource_type=Resource.WHEAT.value, amount=70),
            ResourceAmount(resource_type=Resource.WOOD.value, amount=120),
            ResourceAmount(resource_type=Resource.STONE.value, amount=30),
        ],
        base_upgrade_cost=[
            ResourceAmount(resource_type=Resource.WHEAT.value, amount=35),
            ResourceAmount(resource_type=Resource.WOOD.value, amount=60),
            ResourceAmount(resource_type=Resource.STONE.value, amount=15),
        ],
        max_level=10
    ),
}

# Global mutable config that can be updated at runtime
_current_costs_config = {
    resource_type: config.model_copy(deep=True)
    for resource_type, config in DEFAULT_BUILDING_COSTS_BY_TYPE.items()
}


def get_building_costs(resource_type: str) -> BuildingCostsConfig:
    """Get current building costs configuration for a specific building type.
    
    Args:
        resource_type: The resource type the building produces (WHEAT, WOOD, STONE)
        
    Returns:
        BuildingCostsConfig for that building type
        
    Raises:
        ValueError: If resource_type is not valid
    """
    if resource_type not in _current_costs_config:
        raise ValueError(f"Invalid resource type: {resource_type}. Must be one of {list(_current_costs_config.keys())}")
    return _current_costs_config[resource_type]


def get_all_building_costs() -> Dict[str, BuildingCostsConfig]:
    """Get building costs configuration for all building types.
    
    Returns:
        Dictionary mapping resource_type to BuildingCostsConfig
    """
    return _current_costs_config.copy()


def set_building_costs(resource_type: str, config: BuildingCostsConfig) -> None:
    """Update building costs configuration for a specific building type at runtime.
    
    Args:
        resource_type: The resource type the building produces (WHEAT, WOOD, STONE)
        config: New cost configuration
        
    Raises:
        ValueError: If resource_type is not valid
    """
    global _current_costs_config
    if resource_type not in _current_costs_config:
        raise ValueError(f"Invalid resource type: {resource_type}. Must be one of {list(_current_costs_config.keys())}")
    _current_costs_config[resource_type] = config.model_copy(deep=True)


def calculate_building_cost(resource_type: str, level: int = 1) -> Dict[str, int]:
    """Calculate the cost to create a building.
    
    Args:
        resource_type: The resource type the building produces (WHEAT, WOOD, STONE)
        level: Building level (default: 1 for new buildings)
        
    Returns:
        Dictionary with resource costs {resource_type: quantity}
    """
    config = get_building_costs(resource_type)
    
    return {
        cost.resource_type: cost.amount * level
        for cost in config.base_building_cost
    }


def calculate_upgrade_cost(resource_type: str, current_level: int) -> Dict[str, int]:
    """Calculate the cost to upgrade a building to the next level.
    
    Args:
        resource_type: The resource type the building produces (WHEAT, WOOD, STONE)
        current_level: Current building level
        
    Returns:
        Dictionary with resource costs for upgrade {resource_type: quantity}
    """
    config = get_building_costs(resource_type)
    target_level = current_level + 1
    
    if target_level > config.max_level:
        raise ValueError(f"Building is already at max level ({config.max_level})")
    
    return {
        cost.resource_type: cost.amount * target_level
        for cost in config.base_upgrade_cost
    }


def can_afford(inventory: Dict[str, int], costs: Dict[str, int]) -> bool:
    """Check if player has enough resources.
    
    Args:
        inventory: Player's current resources {resource_type: quantity}
        costs: Required resources {resource_type: quantity}
        
    Returns:
        True if player can afford the costs
    """
    for resource, cost in costs.items():
        if inventory.get(resource.upper(), 0) < cost:
            return False
    return True


def get_missing_resources(inventory: Dict[str, int], costs: Dict[str, int]) -> Dict[str, int]:
    """Calculate missing resources needed to afford costs.
    
    Args:
        inventory: Player's current resources {resource_type: quantity}
        costs: Required resources {resource_type: quantity}
        
    Returns:
        Dictionary of missing resources {resource_type: shortage}
    """
    missing = {}
    for resource, cost in costs.items():
        current = inventory.get(resource.upper(), 0)
        if current < cost:
            missing[resource] = cost - current
    return missing
