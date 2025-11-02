"""Integration tests with mocked external services."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.claude_integration import generate_meal_plan, parse_dietary_preferences
from src.models import DietaryPreferences
from src.todoist_mcp_integration import create_grocery_tasks_from_meal_plan


@pytest.mark.asyncio
async def test_parse_dietary_preferences_integration():
    """Test dietary preference parsing with mocked Claude API."""
    mock_response = {
        "dietary_restrictions": ["vegetarian"],
        "cuisines": ["Mediterranean"],
        "avoid_ingredients": ["mushrooms"],
        "protein_preferences": ["chickpeas"],
        "cooking_styles": ["salads"],
        "max_cook_time_minutes": 20,
        "serves": 2,
        "special_notes": "Quick meals",
    }

    with patch("src.claude_integration.Anthropic") as mock_anthropic:
        # Mock the API response
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(mock_response))]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.return_value = mock_client

        # Call function
        preferences = await parse_dietary_preferences(
            "I'm vegetarian and like Mediterranean food"
        )

        # Verify
        assert isinstance(preferences, DietaryPreferences)
        assert preferences.dietary_restrictions == ["vegetarian"]
        assert preferences.cuisines == ["Mediterranean"]
        assert mock_client.messages.create.called


@pytest.mark.asyncio
async def test_generate_meal_plan_integration():
    """Test meal generation with mocked Claude API."""
    mock_response = {
        "meals": [
            {
                "name": "Test Meal",
                "description": "A test meal",
                "serves": 2,
                "active_time_minutes": 15,
                "inactive_time_minutes": 5,
                "ingredients": [
                    {
                        "name": "Tomato",
                        "quantity": "2",
                        "unit": "medium",
                        "shopping_notes": None,
                    }
                ],
                "instructions": [{"step": 1, "text": "Cook it"}],
            }
        ],
        "shared_ingredients": [],
    }

    with patch("src.claude_integration.Anthropic") as mock_anthropic:
        # Mock the API response
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(mock_response))]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.return_value = mock_client

        # Call function
        preferences = DietaryPreferences(dietary_restrictions=["vegetarian"])
        meal_plan = await generate_meal_plan(preferences)

        # Verify
        assert len(meal_plan.meals) == 1
        assert meal_plan.meals[0].name == "Test Meal"
        assert mock_client.messages.create.called


@pytest.mark.asyncio
async def test_create_grocery_tasks_integration(monkeypatch):
    """Test grocery task creation with mocked MCP server."""
    from src.models import Ingredient, Meal, MealPlan

    # Set up environment
    monkeypatch.setenv("TODOIST_GROCERY_PROJECT_ID", "12345")
    monkeypatch.setenv("TODOIST_MCP_SERVER_URL", "https://mock-mcp.com")

    # Create test meal plan
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Test Meal",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[
                    Ingredient(name="Tomato", quantity="2", unit="medium")
                ],
                instructions=[{"step": 1, "text": "Cook"}],
            )
        ],
        shared_ingredients=[
            Ingredient(name="Olive oil", quantity="1", unit="tbsp")
        ],
    )

    with patch("src.todoist_mcp_integration.httpx.AsyncClient") as mock_client:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "task-123", "content": "Test task"}
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        # Call function
        created_tasks = await create_grocery_tasks_from_meal_plan(meal_plan)

        # Verify
        assert len(created_tasks) == 2  # 1 ingredient + 1 shared
        assert mock_post.called


@pytest.mark.asyncio
async def test_security_validation_blocks_wrong_project(monkeypatch):
    """Test that security validation blocks wrong project."""
    from src.models import Ingredient, Meal, MealPlan
    from src.security_validation import ProjectAccessDenied

    # Set up environment with different project ID
    monkeypatch.setenv("TODOIST_GROCERY_PROJECT_ID", "12345")
    monkeypatch.setenv("TODOIST_MCP_SERVER_URL", "https://mock-mcp.com")

    # Create meal plan
    MealPlan(
        meals=[
            Meal(
                name="Test Meal",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[
                    Ingredient(name="Tomato", quantity="2", unit="medium")
                ],
                instructions=[{"step": 1, "text": "Cook"}],
            )
        ],
        shared_ingredients=[],
    )

    # Temporarily change the project ID in the task to wrong ID
    with patch("src.todoist_mcp_integration.get_config") as mock_config:
        mock_conf = MagicMock()
        mock_conf.todoist_grocery_project_id = "12345"
        mock_conf.todoist_mcp_server_url = "https://mock-mcp.com"
        mock_config.return_value = mock_conf

        # Patch the task creation to use wrong project ID
        with patch(
            "src.todoist_mcp_integration.TodoistTask"
        ) as mock_task_class:
            mock_task = MagicMock()
            mock_task.project_id = "99999"  # Wrong project!
            mock_task.content = "Test"
            mock_task_class.return_value = mock_task

            # This should raise ProjectAccessDenied
            with pytest.raises(ProjectAccessDenied):
                from src.todoist_mcp_integration import create_todoist_task

                await create_todoist_task(mock_task)
