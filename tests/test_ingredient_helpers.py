"""Unit tests for ingredient helper utilities."""


from src.models import Ingredient, Meal, MealPlan
from src.utils.ingredient_helpers import (
    collect_all_ingredients,
    collect_unique_ingredient_names,
    count_total_ingredients,
)


def test_collect_all_ingredients():
    """Test collecting all ingredients from a meal plan."""
    meal1 = Meal(
        name="Meal 1",
        description="Test meal 1",
        serves=2,
        active_time_minutes=15,
        ingredients=[
            Ingredient(name="Tomato", quantity="2", unit="medium"),
            Ingredient(name="Onion", quantity="1", unit="large"),
        ],
        instructions=[{"step": 1, "text": "Cook"}],
    )

    meal2 = Meal(
        name="Meal 2",
        description="Test meal 2",
        serves=2,
        active_time_minutes=15,
        ingredients=[
            Ingredient(name="Garlic", quantity="2", unit="cloves"),
        ],
        instructions=[{"step": 1, "text": "Chop"}],
    )

    meal_plan = MealPlan(
        meals=[meal1, meal2],
        shared_ingredients=[
            Ingredient(name="Olive oil", quantity="2", unit="tbsp"),
        ],
    )

    # Collect all ingredients
    all_ingredients = list(collect_all_ingredients(meal_plan))

    # Should have 4 total ingredients (2 from meal1, 1 from meal2, 1 shared)
    assert len(all_ingredients) == 4
    assert all_ingredients[0].name == "Tomato"
    assert all_ingredients[1].name == "Onion"
    assert all_ingredients[2].name == "Garlic"
    assert all_ingredients[3].name == "Olive oil"


def test_collect_unique_ingredient_names():
    """Test collecting unique ingredient names from a meal plan."""
    meal1 = Meal(
        name="Meal 1",
        description="Test meal 1",
        serves=2,
        active_time_minutes=15,
        ingredients=[
            Ingredient(name="Tomato", quantity="2", unit="medium"),
            Ingredient(name="Garlic", quantity="2", unit="cloves"),
        ],
        instructions=[{"step": 1, "text": "Cook"}],
    )

    meal2 = Meal(
        name="Meal 2",
        description="Test meal 2",
        serves=2,
        active_time_minutes=15,
        ingredients=[
            Ingredient(name="Garlic", quantity="3", unit="cloves"),  # Duplicate
            Ingredient(name="Onion", quantity="1", unit="large"),
        ],
        instructions=[{"step": 1, "text": "Chop"}],
    )

    meal_plan = MealPlan(
        meals=[meal1, meal2],
        shared_ingredients=[
            Ingredient(name="Olive oil", quantity="2", unit="tbsp"),
        ],
    )

    # Collect unique names
    unique_names = collect_unique_ingredient_names(meal_plan)

    # Should have 4 unique names (Garlic appears twice but counted once)
    assert len(unique_names) == 4
    assert "Tomato" in unique_names
    assert "Garlic" in unique_names
    assert "Onion" in unique_names
    assert "Olive oil" in unique_names


def test_count_total_ingredients():
    """Test counting total ingredients including duplicates."""
    meal1 = Meal(
        name="Meal 1",
        description="Test meal 1",
        serves=2,
        active_time_minutes=15,
        ingredients=[
            Ingredient(name="Tomato", quantity="2", unit="medium"),
            Ingredient(name="Garlic", quantity="2", unit="cloves"),
        ],
        instructions=[{"step": 1, "text": "Cook"}],
    )

    meal2 = Meal(
        name="Meal 2",
        description="Test meal 2",
        serves=2,
        active_time_minutes=15,
        ingredients=[
            Ingredient(name="Garlic", quantity="3", unit="cloves"),  # Duplicate
            Ingredient(name="Onion", quantity="1", unit="large"),
        ],
        instructions=[{"step": 1, "text": "Chop"}],
    )

    meal_plan = MealPlan(
        meals=[meal1, meal2],
        shared_ingredients=[
            Ingredient(name="Olive oil", quantity="2", unit="tbsp"),
        ],
    )

    # Count total (including duplicates)
    total = count_total_ingredients(meal_plan)

    # Should be 5 total (2 + 2 + 1 shared)
    assert total == 5


def test_empty_meal_plan():
    """Test utility functions with empty meal plan."""
    meal_plan = MealPlan(meals=[], shared_ingredients=[])

    # Test all functions with empty meal plan
    assert list(collect_all_ingredients(meal_plan)) == []
    assert collect_unique_ingredient_names(meal_plan) == set()
    assert count_total_ingredients(meal_plan) == 0
