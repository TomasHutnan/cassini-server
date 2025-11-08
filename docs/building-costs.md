# Building Costs System

## Overview

The building costs system provides a flexible, real-time configurable way to manage resource costs for creating and upgrading buildings.

## Cost Formula

Costs scale linearly with building level:

```
cost_per_resource = base_cost × level
```

### Creating a Building
- **Level 1 Building**: `base_building_cost × 1`
- **Level 5 Building**: `base_building_cost × 5`

### Upgrading a Building
- **Upgrade from Level 1 → 2**: `base_upgrade_cost × 2` (target level)
- **Upgrade from Level 5 → 6**: `base_upgrade_cost × 6` (target level)

## Building Type Specific Costs

Each building type has different construction costs based on what it produces:

### Farm (Produces WHEAT)
Requires mostly wood and some stone to build farm structures.

```json
{
  "base_building_cost": [
    {"resource_type": "WHEAT", "amount": 20},
    {"resource_type": "WOOD", "amount": 100},
    {"resource_type": "STONE", "amount": 50}
  ],
  "base_upgrade_cost": [
    {"resource_type": "WHEAT", "amount": 10},
    {"resource_type": "WOOD", "amount": 50},
    {"resource_type": "STONE", "amount": 25}
  ],
  "max_level": 10
}
```

### Lumber Mill (Produces WOOD)
Requires mostly wheat (to feed workers) and stone for tools/buildings.

```json
{
  "base_building_cost": [
    {"resource_type": "WHEAT", "amount": 80},
    {"resource_type": "WOOD", "amount": 30},
    {"resource_type": "STONE", "amount": 60}
  ],
  "base_upgrade_cost": [
    {"resource_type": "WHEAT", "amount": 40},
    {"resource_type": "WOOD", "amount": 15},
    {"resource_type": "STONE", "amount": 30}
  ],
  "max_level": 10
}
```

### Mine (Produces STONE)
Requires mostly wood (for support structures) and wheat to sustain miners.

```json
{
  "base_building_cost": [
    {"resource_type": "WHEAT", "amount": 70},
    {"resource_type": "WOOD", "amount": 120},
    {"resource_type": "STONE", "amount": 30}
  ],
  "base_upgrade_cost": [
    {"resource_type": "WHEAT", "amount": 35},
    {"resource_type": "WOOD", "amount": 60},
    {"resource_type": "STONE", "amount": 15}
  ],
  "max_level": 10
}
```

## Backend Integration

To enforce costs in the create/upgrade endpoints:

```python
from src.game_objects.building_costs import (
    calculate_building_cost,
    calculate_upgrade_cost,
    can_afford,
    get_missing_resources
)

# Calculate cost for creating a building
cost = calculate_building_cost(resource_type="WHEAT", level=1)  # For a Farm

# Calculate cost for upgrading
upgrade_cost = calculate_upgrade_cost(resource_type="STONE", current_level=3)  # For a Mine
