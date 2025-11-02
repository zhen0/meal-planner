"""
Utility functions for working with ingredients.
Consolidates duplicated ingredient collection and processing logic.
"""

from typing import Iterator, Set

from ..models import Ingredient, MealPlan


def collect_all_ingredients(meal_plan: MealPlan) -> Iterator[Ingredient]:
    """
    Generator that yields all ingredients from a meal plan.

    Yields ingredients from all meals first, then shared ingredients.
    This is more memory-efficient than creating intermediate lists.

    Args:
        meal_plan: MealPlan object to extract ingredients from

    Yields:
        Ingredient: Each ingredient in the meal plan
    """
    for meal in meal_plan.meals:
        yield from meal.ingredients

    yield from meal_plan.shared_ingredients


def collect_unique_ingredient_names(meal_plan: MealPlan) -> Set[str]:
    """
    Collect unique ingredient names from a meal plan.

    This consolidates logic that was duplicated across multiple locations:
    - create_grocery_list_artifact
    - post_simple_grocery_list_to_slack

    Args:
        meal_plan: MealPlan object to extract ingredient names from

    Returns:
        Set[str]: Set of unique ingredient names
    """
    return {ingredient.name for ingredient in collect_all_ingredients(meal_plan)}


def count_total_ingredients(meal_plan: MealPlan) -> int:
    """
    Count total number of ingredients in a meal plan (including duplicates).

    Args:
        meal_plan: MealPlan object to count ingredients from

    Returns:
        int: Total count of ingredients
    """
    return sum(1 for _ in collect_all_ingredients(meal_plan))
