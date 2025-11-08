"""
Unit tests for building costs system.

Tests the building cost calculation functions and configuration management.
Run with: python -m tests.test_building_costs
"""

from src.game_objects.building_costs import (
    get_building_costs,
    get_all_building_costs,
    calculate_building_cost,
    calculate_upgrade_cost,
    can_afford,
    get_missing_resources,
)
from src.game_objects.resources import Resource


def test_get_building_costs():
    """Test retrieving costs for specific building types."""
    print("1️⃣ Testing get_building_costs()...")
    
    # Test for each building type
    for resource_type in [Resource.WHEAT.value, Resource.WOOD.value, Resource.STONE.value]:
        config = get_building_costs(resource_type)
        
        assert config is not None, f"Config for {resource_type} should not be None"
        assert len(config.base_building_cost) == 3, "Should have costs for 3 resource types"
        assert len(config.base_upgrade_cost) == 3, "Should have upgrade costs for 3 resource types"
        assert config.max_level == 10, "Max level should be 10"
        
        print(f"   ✅ {resource_type} building costs retrieved successfully")
    
    # Test invalid resource type
    try:
        get_building_costs("INVALID")
        assert False, "Should raise ValueError for invalid resource type"
    except ValueError as e:
        print(f"   ✅ Invalid resource type correctly rejected: {e}")
    
    print()


def test_get_all_building_costs():
    """Test retrieving costs for all building types."""
    print("2️⃣ Testing get_all_building_costs()...")
    
    all_costs = get_all_building_costs()
    
    assert len(all_costs) == 3, "Should have costs for 3 building types"
    assert Resource.WHEAT.value in all_costs, "Should include WHEAT costs"
    assert Resource.WOOD.value in all_costs, "Should include WOOD costs"
    assert Resource.STONE.value in all_costs, "Should include STONE costs"
    
    print("   ✅ All building costs retrieved successfully")
    print(f"   Building types: {list(all_costs.keys())}")
    print()


def test_building_types_have_different_costs():
    """Test that each building type has unique costs."""
    print("3️⃣ Testing building type cost differences...")
    
    wheat_config = get_building_costs(Resource.WHEAT.value)
    wood_config = get_building_costs(Resource.WOOD.value)
    stone_config = get_building_costs(Resource.STONE.value)
    
    # Convert to comparable format
    wheat_costs = {cost.resource_type: cost.amount for cost in wheat_config.base_building_cost}
    wood_costs = {cost.resource_type: cost.amount for cost in wood_config.base_building_cost}
    stone_costs = {cost.resource_type: cost.amount for cost in stone_config.base_building_cost}
    
    # Check that they're different
    assert wheat_costs != wood_costs, "WHEAT and WOOD buildings should have different costs"
    assert wood_costs != stone_costs, "WOOD and STONE buildings should have different costs"
    assert wheat_costs != stone_costs, "WHEAT and STONE buildings should have different costs"
    
    print("   ✅ Each building type has unique construction costs")
    print(f"   WHEAT (Farm): {wheat_costs}")
    print(f"   WOOD (Lumber Mill): {wood_costs}")
    print(f"   STONE (Mine): {stone_costs}")
    print()


def test_calculate_building_cost():
    """Test building cost calculations."""
    print("4️⃣ Testing calculate_building_cost()...")
    
    # Test level 1 Farm (WHEAT building)
    level1_costs = calculate_building_cost(Resource.WHEAT.value, level=1)
    
    assert level1_costs[Resource.WHEAT.value] == 20, "Level 1 Farm should cost 20 WHEAT"
    assert level1_costs[Resource.WOOD.value] == 100, "Level 1 Farm should cost 100 WOOD"
    assert level1_costs[Resource.STONE.value] == 50, "Level 1 Farm should cost 50 STONE"
    
    print("   ✅ Level 1 Farm costs: WHEAT=20, WOOD=100, STONE=50")
    
    # Test level 5 Farm (costs should scale linearly)
    level5_costs = calculate_building_cost(Resource.WHEAT.value, level=5)
    
    assert level5_costs[Resource.WHEAT.value] == 100, "Level 5 Farm should cost 100 WHEAT (20×5)"
    assert level5_costs[Resource.WOOD.value] == 500, "Level 5 Farm should cost 500 WOOD (100×5)"
    assert level5_costs[Resource.STONE.value] == 250, "Level 5 Farm should cost 250 STONE (50×5)"
    
    print("   ✅ Level 5 Farm costs scale correctly: WHEAT=100, WOOD=500, STONE=250")
    
    # Test Mine (STONE building)
    mine_costs = calculate_building_cost(Resource.STONE.value, level=1)
    
    assert mine_costs[Resource.WHEAT.value] == 70, "Level 1 Mine should cost 70 WHEAT"
    assert mine_costs[Resource.WOOD.value] == 120, "Level 1 Mine should cost 120 WOOD"
    assert mine_costs[Resource.STONE.value] == 30, "Level 1 Mine should cost 30 STONE"
    
    print("   ✅ Level 1 Mine costs: WHEAT=70, WOOD=120, STONE=30")
    print()


def test_calculate_upgrade_cost():
    """Test upgrade cost calculations."""
    print("5️⃣ Testing calculate_upgrade_cost()...")
    
    # Test upgrading Farm from level 1 to 2
    upgrade_1_to_2 = calculate_upgrade_cost(Resource.WHEAT.value, current_level=1)
    
    # Upgrade cost = base_upgrade_cost × target_level (2)
    assert upgrade_1_to_2[Resource.WHEAT.value] == 20, "Upgrade 1→2 should cost 20 WHEAT (10×2)"
    assert upgrade_1_to_2[Resource.WOOD.value] == 100, "Upgrade 1→2 should cost 100 WOOD (50×2)"
    assert upgrade_1_to_2[Resource.STONE.value] == 50, "Upgrade 1→2 should cost 50 STONE (25×2)"
    
    print("   ✅ Farm upgrade 1→2: WHEAT=20, WOOD=100, STONE=50")
    
    # Test upgrading from level 5 to 6
    upgrade_5_to_6 = calculate_upgrade_cost(Resource.WHEAT.value, current_level=5)
    
    assert upgrade_5_to_6[Resource.WHEAT.value] == 60, "Upgrade 5→6 should cost 60 WHEAT (10×6)"
    assert upgrade_5_to_6[Resource.WOOD.value] == 300, "Upgrade 5→6 should cost 300 WOOD (50×6)"
    assert upgrade_5_to_6[Resource.STONE.value] == 150, "Upgrade 5→6 should cost 150 STONE (25×6)"
    
    print("   ✅ Farm upgrade 5→6: WHEAT=60, WOOD=300, STONE=150")
    
    # Test max level restriction
    try:
        calculate_upgrade_cost(Resource.WHEAT.value, current_level=10)
        assert False, "Should raise ValueError when at max level"
    except ValueError as e:
        print(f"   ✅ Max level restriction works: {e}")
    
    print()


def test_can_afford():
    """Test affordability checking."""
    print("6️⃣ Testing can_afford()...")
    
    # Test sufficient resources
    inventory = {
        Resource.WHEAT.value: 100,
        Resource.WOOD.value: 200,
        Resource.STONE.value: 100,
    }
    
    costs = {
        Resource.WHEAT.value: 50,
        Resource.WOOD.value: 100,
        Resource.STONE.value: 75,
    }
    
    assert can_afford(inventory, costs), "Should be able to afford with sufficient resources"
    print("   ✅ Correctly identifies sufficient resources")
    
    # Test insufficient resources
    insufficient_inventory = {
        Resource.WHEAT.value: 10,
        Resource.WOOD.value: 20,
        Resource.STONE.value: 30,
    }
    
    assert not can_afford(insufficient_inventory, costs), "Should not afford with insufficient resources"
    print("   ✅ Correctly identifies insufficient resources")
    print()


def test_get_missing_resources():
    """Test missing resource calculation."""
    print("7️⃣ Testing get_missing_resources()...")
    
    inventory = {
        Resource.WHEAT.value: 30,
        Resource.WOOD.value: 150,
        Resource.STONE.value: 40,
    }
    
    costs = {
        Resource.WHEAT.value: 50,
        Resource.WOOD.value: 100,
        Resource.STONE.value: 75,
    }
    
    missing = get_missing_resources(inventory, costs)
    
    assert missing[Resource.WHEAT.value] == 20, "Should need 20 more WHEAT"
    assert Resource.WOOD.value not in missing, "Should have enough WOOD"
    assert missing[Resource.STONE.value] == 35, "Should need 35 more STONE"
    
    print(f"   ✅ Missing resources calculated correctly: {missing}")
    print()


def test_building_cost_ratios():
    """Test that building costs reflect their resource production."""
    print("8️⃣ Testing building cost ratios (should require less of what they produce)...")
    
    # Farm produces WHEAT - should require less WHEAT to build
    wheat_config = get_building_costs(Resource.WHEAT.value)
    wheat_costs = {cost.resource_type: cost.amount for cost in wheat_config.base_building_cost}
    
    # Wood produces WOOD - should require less WOOD to build  
    wood_config = get_building_costs(Resource.WOOD.value)
    wood_costs = {cost.resource_type: cost.amount for cost in wood_config.base_building_cost}
    
    # Mine produces STONE - should require less STONE to build
    stone_config = get_building_costs(Resource.STONE.value)
    stone_costs = {cost.resource_type: cost.amount for cost in stone_config.base_building_cost}
    
    # Farm should require less WHEAT than other buildings
    assert wheat_costs[Resource.WHEAT.value] < wood_costs[Resource.WHEAT.value], \
        "Farm should require less WHEAT than Lumber Mill"
    assert wheat_costs[Resource.WHEAT.value] < stone_costs[Resource.WHEAT.value], \
        "Farm should require less WHEAT than Mine"
    
    print(f"   ✅ Farm requires least WHEAT: {wheat_costs[Resource.WHEAT.value]}")
    
    # Lumber Mill should require less WOOD than other buildings
    assert wood_costs[Resource.WOOD.value] < wheat_costs[Resource.WOOD.value], \
        "Lumber Mill should require less WOOD than Farm"
    assert wood_costs[Resource.WOOD.value] < stone_costs[Resource.WOOD.value], \
        "Lumber Mill should require less WOOD than Mine"
    
    print(f"   ✅ Lumber Mill requires least WOOD: {wood_costs[Resource.WOOD.value]}")
    
    # Mine should require less STONE than other buildings
    assert stone_costs[Resource.STONE.value] < wheat_costs[Resource.STONE.value], \
        "Mine should require less STONE than Farm"
    assert stone_costs[Resource.STONE.value] < wood_costs[Resource.STONE.value], \
        "Mine should require less STONE than Lumber Mill"
    
    print(f"   ✅ Mine requires least STONE: {stone_costs[Resource.STONE.value]}")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Building Costs Unit Tests")
    print("=" * 60)
    print()
    
    try:
        test_get_building_costs()
        test_get_all_building_costs()
        test_building_types_have_different_costs()
        test_calculate_building_cost()
        test_calculate_upgrade_cost()
        test_can_afford()
        test_get_missing_resources()
        test_building_cost_ratios()
        
        print("=" * 60)
        print("✅ All building costs tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
