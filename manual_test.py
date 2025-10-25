"""
Manual testing script for meal planner agent.
Run this to test individual components without deploying to Prefect Cloud.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.claude_integration import generate_meal_plan, parse_dietary_preferences
from src.config import get_config
from src.models import ApprovalInput, DietaryPreferences, Ingredient, Meal, MealPlan
from src.security_validation import ProjectAccessDenied, validate_project_id
from src.slack_integration import (
    format_meal_plan_message,
    parse_slack_response,
    post_meal_plan_to_slack,
)


async def test_config():
    """Test configuration loading."""
    print("\n" + "="*80)
    print("TEST: Configuration Loading")
    print("="*80)

    try:
        config = get_config()
        print("✓ Config loaded successfully")
        print(f"  - Slack channel: {config.slack_channel_id}")
        print(f"  - Todoist project: {config.todoist_grocery_project_id}")
        print(f"  - Prefect API URL: {config.prefect_api_url}")
        print(f"  - Logfire project: {config.logfire_project_name}")
        return True
    except Exception as e:
        print(f"✗ Config loading failed: {e}")
        return False


async def test_preference_parsing():
    """Test dietary preference parsing."""
    print("\n" + "="*80)
    print("TEST: Dietary Preference Parsing")
    print("="*80)

    test_input = "I'm vegetarian, no mushrooms. I like Mediterranean and Asian flavors."
    print(f"Input: {test_input}")

    try:
        preferences = await parse_dietary_preferences(test_input)
        print("✓ Preferences parsed successfully")
        print(f"  - Dietary restrictions: {preferences.dietary_restrictions}")
        print(f"  - Cuisines: {preferences.cuisines}")
        print(f"  - Avoid ingredients: {preferences.avoid_ingredients}")
        print(f"  - Max cook time: {preferences.max_cook_time_minutes} min")
        return True
    except Exception as e:
        print(f"✗ Preference parsing failed: {e}")
        return False


async def test_meal_generation():
    """Test meal plan generation."""
    print("\n" + "="*80)
    print("TEST: Meal Plan Generation")
    print("="*80)

    # Create test preferences
    preferences = DietaryPreferences(
        dietary_restrictions=["vegetarian"],
        cuisines=["Mediterranean"],
        avoid_ingredients=["mushrooms"],
        max_cook_time_minutes=20,
        serves=2,
    )
    print(f"Preferences: vegetarian, Mediterranean, no mushrooms")

    try:
        meal_plan = await generate_meal_plan(preferences)
        print("✓ Meal plan generated successfully")
        print(f"  - Number of meals: {len(meal_plan.meals)}")
        for i, meal in enumerate(meal_plan.meals, 1):
            print(f"  - Meal {i}: {meal.name}")
            print(f"    Active time: {meal.active_time_minutes} min")
            print(f"    Ingredients: {len(meal.ingredients)}")
        print(f"  - Shared ingredients: {len(meal_plan.shared_ingredients)}")
        return True
    except Exception as e:
        print(f"✗ Meal generation failed: {e}")
        return False


async def test_security_validation():
    """Test security validation."""
    print("\n" + "="*80)
    print("TEST: Security Validation")
    print("="*80)

    config = get_config()
    correct_id = config.todoist_grocery_project_id
    wrong_id = "99999"

    # Test correct project ID
    try:
        validate_project_id(correct_id)
        print(f"✓ Correct project ID validated: {correct_id}")
    except Exception as e:
        print(f"✗ Validation failed for correct ID: {e}")
        return False

    # Test wrong project ID
    try:
        validate_project_id(wrong_id)
        print(f"✗ Security breach! Wrong project ID was allowed: {wrong_id}")
        return False
    except ProjectAccessDenied:
        print(f"✓ Wrong project ID blocked: {wrong_id}")
        return True


def test_slack_response_parsing():
    """Test Slack response parsing."""
    print("\n" + "="*80)
    print("TEST: Slack Response Parsing")
    print("="*80)

    test_cases = [
        ("approve", True, None, False),
        ("reject", False, None, False),
        ("feedback: make it spicier", False, "make it spicier", True),
        ("✓", True, None, False),
        ("✗", False, None, False),
    ]

    all_passed = True
    for text, expected_approved, expected_feedback, expected_regenerate in test_cases:
        approved, feedback, regenerate = parse_slack_response(text)

        if approved == expected_approved and regenerate == expected_regenerate:
            print(f"✓ '{text}' -> approved={approved}, regenerate={regenerate}")
        else:
            print(f"✗ '{text}' -> Expected approved={expected_approved}, regenerate={expected_regenerate}")
            print(f"                Got approved={approved}, regenerate={regenerate}")
            all_passed = False

    return all_passed


def test_meal_plan_formatting():
    """Test meal plan message formatting."""
    print("\n" + "="*80)
    print("TEST: Meal Plan Message Formatting")
    print("="*80)

    # Create test meal plan
    meal = Meal(
        name="Mediterranean Chickpea Salad",
        description="Fresh and vibrant salad with chickpeas",
        serves=2,
        active_time_minutes=15,
        inactive_time_minutes=0,
        ingredients=[
            Ingredient(name="Chickpeas", quantity="2", unit="cans"),
            Ingredient(name="Cucumber", quantity="1", unit="medium"),
        ],
        instructions=[
            {"step": 1, "text": "Drain chickpeas"},
            {"step": 2, "text": "Chop vegetables"},
        ],
    )

    meal_plan = MealPlan(
        meals=[meal],
        shared_ingredients=[
            Ingredient(name="Olive oil", quantity="2", unit="tbsp")
        ],
    )

    message = format_meal_plan_message(meal_plan)
    print("✓ Message formatted successfully")
    print("\nFormatted message:")
    print("-" * 80)
    print(message)
    print("-" * 80)

    return True


async def run_all_tests():
    """Run all manual tests."""
    print("\n" + "#"*80)
    print("# MEAL PLANNER AGENT - MANUAL TESTS")
    print("#"*80)

    results = []

    # Run tests
    results.append(("Configuration", await test_config()))
    results.append(("Security Validation", await test_security_validation()))
    results.append(("Slack Response Parsing", test_slack_response_parsing()))
    results.append(("Meal Plan Formatting", test_meal_plan_formatting()))

    # Optional: Only run if API keys are configured
    config = get_config()
    if config.anthropic_api_key and config.anthropic_api_key.startswith("sk-ant-"):
        results.append(("Preference Parsing", await test_preference_parsing()))
        results.append(("Meal Generation", await test_meal_generation()))
    else:
        print("\n⚠ Skipping Claude API tests (ANTHROPIC_API_KEY not configured)")

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
