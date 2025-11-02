"""Unit tests for slack_integration module."""


from src.models import Ingredient, Meal, MealPlan
from src.slack_integration import parse_slack_response
from src.utils.slack_formatting import format_meal_plan_message


def test_format_meal_plan_message():
    """Test meal plan message formatting."""
    # Create a simple meal plan
    meal = Meal(
        name="Test Meal",
        description="A delicious test meal",
        serves=2,
        active_time_minutes=15,
        inactive_time_minutes=5,
        ingredients=[
            Ingredient(name="Tomato", quantity="2", unit="medium", shopping_notes=None)
        ],
        instructions=[{"step": 1, "text": "Cook the thing"}],
    )

    meal_plan = MealPlan(
        meals=[meal],
        shared_ingredients=[
            Ingredient(name="Olive oil", quantity="2", unit="tbsp", shopping_notes=None)
        ],
    )

    message = format_meal_plan_message(meal_plan)

    # Check message contains key elements
    assert "Test Meal" in message
    assert "Active: 15 min" in message
    assert "Serves 2" in message
    assert "approve" in message.lower()
    assert "reject" in message.lower()
    assert "Shared Ingredients" in message


def test_parse_slack_response_approve():
    """Test parsing approval responses."""
    test_cases = ["approve", "APPROVE", "approved", "✓", "✅", "yes", "y"]

    for text in test_cases:
        approved, feedback, regenerate = parse_slack_response(text)
        assert approved is True
        assert feedback is None
        assert regenerate is False


def test_parse_slack_response_reject():
    """Test parsing rejection responses."""
    test_cases = ["reject", "REJECT", "rejected", "✗", "❌", "no", "n"]

    for text in test_cases:
        approved, feedback, regenerate = parse_slack_response(text)
        assert approved is False
        assert feedback is None
        assert regenerate is False


def test_parse_slack_response_feedback():
    """Test parsing feedback responses."""
    text = "feedback: make it spicier"

    approved, feedback, regenerate = parse_slack_response(text)

    assert approved is False
    assert feedback == "make it spicier"
    assert regenerate is True


def test_parse_slack_response_feedback_case_insensitive():
    """Test feedback parsing is case insensitive."""
    text = "FEEDBACK: No tomatoes please"

    approved, feedback, regenerate = parse_slack_response(text)

    assert approved is False
    assert "no tomatoes please" in feedback.lower()
    assert regenerate is True


def test_parse_slack_response_generic_feedback():
    """Test generic text is treated as feedback."""
    text = "I don't like this, make something else"

    approved, feedback, regenerate = parse_slack_response(text)

    assert approved is False
    assert feedback == text
    assert regenerate is True
