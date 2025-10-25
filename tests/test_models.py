"""Unit tests for data models."""

import pytest
from pydantic import ValidationError

from src.models import ApprovalInput, DietaryPreferences, Ingredient, Meal


def test_approval_input_approved():
    """Test ApprovalInput for approval case."""
    input_data = ApprovalInput(
        approved=True,
        feedback=None,
        regenerate=False,
    )

    assert input_data.approved is True
    assert input_data.feedback is None
    assert input_data.regenerate is False


def test_approval_input_with_feedback():
    """Test ApprovalInput with feedback."""
    input_data = ApprovalInput(
        approved=False,
        feedback="make it spicier",
        regenerate=True,
    )

    assert input_data.approved is False
    assert input_data.feedback == "make it spicier"
    assert input_data.regenerate is True


def test_dietary_preferences_defaults():
    """Test DietaryPreferences with defaults."""
    prefs = DietaryPreferences()

    assert prefs.dietary_restrictions == []
    assert prefs.cuisines == []
    assert prefs.avoid_ingredients == []
    assert prefs.protein_preferences == []
    assert prefs.cooking_styles == []
    assert prefs.max_cook_time_minutes == 20
    assert prefs.serves == 2
    assert prefs.special_notes == ""


def test_dietary_preferences_with_values():
    """Test DietaryPreferences with values."""
    prefs = DietaryPreferences(
        dietary_restrictions=["vegetarian"],
        cuisines=["Mediterranean"],
        avoid_ingredients=["mushrooms"],
        protein_preferences=["chickpeas"],
        cooking_styles=["salads"],
        max_cook_time_minutes=15,
        serves=2,
        special_notes="Quick and easy",
    )

    assert prefs.dietary_restrictions == ["vegetarian"]
    assert prefs.cuisines == ["Mediterranean"]
    assert prefs.avoid_ingredients == ["mushrooms"]
    assert prefs.protein_preferences == ["chickpeas"]
    assert prefs.cooking_styles == ["salads"]
    assert prefs.max_cook_time_minutes == 15
    assert prefs.serves == 2
    assert prefs.special_notes == "Quick and easy"


def test_ingredient_required_fields():
    """Test Ingredient requires name, quantity, unit."""
    # Should work with all required fields
    ing = Ingredient(
        name="Tomato",
        quantity="2",
        unit="medium",
    )

    assert ing.name == "Tomato"
    assert ing.quantity == "2"
    assert ing.unit == "medium"
    assert ing.shopping_notes is None


def test_ingredient_with_shopping_notes():
    """Test Ingredient with shopping notes."""
    ing = Ingredient(
        name="Tomato",
        quantity="2",
        unit="medium",
        shopping_notes="organic",
    )

    assert ing.shopping_notes == "organic"


def test_meal_required_fields():
    """Test Meal requires all fields."""
    meal = Meal(
        name="Test Meal",
        description="A test meal",
        serves=2,
        active_time_minutes=15,
        inactive_time_minutes=5,
        ingredients=[
            Ingredient(name="Tomato", quantity="2", unit="medium")
        ],
        instructions=[{"step": 1, "text": "Do something"}],
    )

    assert meal.name == "Test Meal"
    assert meal.serves == 2
    assert meal.active_time_minutes == 15
    assert len(meal.ingredients) == 1
    assert len(meal.instructions) == 1
