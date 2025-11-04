"""
Tests for Prefect MCP integration.
Tests the integration of Pydantic AI with Prefect and MCP for Todoist task creation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import Ingredient, Meal, MealPlan
from src.todoist_mcp_integration import (
    create_grocery_tasks_from_meal_plan,
    TODOIST_AGENT_PROMPT,
)


def create_async_secret_mock(token_value):
    """Helper to create an async mock for Secret.load."""
    mock_secret = MagicMock()
    mock_secret.get.return_value = token_value
    
    async def async_load(name):
        return mock_secret
    
    return async_load


def create_async_variables_get(config_dict):
    """Helper to create an async mock for variables.get."""
    async def async_get(key, default=None):
        return config_dict.get(key, default)
    
    return async_get


@pytest.mark.asyncio
async def test_todoist_agent_prompt_contains_mcp_instructions():
    """Test that the agent prompt contains MCP-specific instructions."""
    assert "MCP" in TODOIST_AGENT_PROMPT
    assert "Todoist MCP tools" in TODOIST_AGENT_PROMPT
    assert "project_id" in TODOIST_AGENT_PROMPT


@pytest.mark.asyncio
async def test_create_grocery_tasks_loads_prefect_secrets():
    """Test that the function loads Todoist token from Prefect Secret block."""
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Test Meal",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[Ingredient(name="Tomato", quantity="2", unit="medium")],
                instructions=[{"step": 1, "text": "Cook"}],
            )
        ],
        shared_ingredients=[],
    )

    # Mock Secret.load
    with patch("src.todoist_mcp_integration.Secret.load") as mock_load:
        mock_load.side_effect = create_async_secret_mock("test-token-123")

        # Mock variables.get
        with patch("src.todoist_mcp_integration.variables.get") as mock_vars:
            mock_vars.side_effect = create_async_variables_get({
                "todoist-mcp-server-url": "https://test-mcp.com",
                "todoist-grocery-project-id": "12345",
            })

            # Mock MCPServerStreamableHTTP and Agent
            with patch("src.todoist_mcp_integration.MCPServerStreamableHTTP"):
                # Mock Agent
                with patch("src.todoist_mcp_integration.Agent") as mock_agent_cls:
                    mock_base_agent = MagicMock()
                    mock_agent_cls.return_value = mock_base_agent

                # Mock Agent
                with patch("src.todoist_mcp_integration.Agent") as mock_agent_cls:
                    mock_base_agent = MagicMock()
                    mock_agent_cls.return_value = mock_base_agent

                    # Mock PrefectAgent
                    with patch("src.todoist_mcp_integration.PrefectAgent") as mock_prefect_agent_cls:
                        mock_agent = MagicMock()
                        mock_result = MagicMock()
                        mock_result.output = "Successfully created 1 tasks"
                        mock_agent.run = AsyncMock(return_value=mock_result)
                        mock_prefect_agent_cls.return_value = mock_agent

                        # Call the function
                        result = await create_grocery_tasks_from_meal_plan(meal_plan)

                        # Verify Secret.load was called with correct name
                        mock_load.assert_called_once_with("todoist-mcp-auth-token")

                    # Verify the secret.get() was called
                    mock_secret.get.assert_called_once()

                    # Verify result
                    assert result[0]["success"] is True


@pytest.mark.asyncio
async def test_create_grocery_tasks_loads_prefect_variables():
    """Test that the function loads configuration from Prefect Variables."""
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Test Meal",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[Ingredient(name="Tomato", quantity="2", unit="medium")],
                instructions=[{"step": 1, "text": "Cook"}],
            )
        ],
        shared_ingredients=[],
    )

    # Mock Secret.load
    with patch("src.todoist_mcp_integration.Secret.load") as mock_load:
        mock_load.side_effect = create_async_secret_mock("test-token-123")

        # Mock variables.get to track calls
        with patch("src.todoist_mcp_integration.variables.get") as mock_vars:
            mock_vars.side_effect = create_async_variables_get({
                "todoist-mcp-server-url": "https://test-mcp.com",
                "todoist-grocery-project-id": "12345",
            })

            # Mock MCPServerStreamableHTTP and Agent
            with patch("src.todoist_mcp_integration.MCPServerStreamableHTTP"):
                # Mock Agent
                with patch("src.todoist_mcp_integration.Agent") as mock_agent_cls:
                    mock_base_agent = MagicMock()
                    mock_agent_cls.return_value = mock_base_agent

                # Mock PrefectAgent
                with patch("src.todoist_mcp_integration.PrefectAgent") as mock_agent_class:
                    mock_agent = MagicMock()
                    mock_result = MagicMock()
                    mock_result.output = "Successfully created 1 tasks"
                    mock_agent.run = AsyncMock(return_value=mock_result)
                    mock_agent_class.return_value = mock_agent

                    # Call the function
                    await create_grocery_tasks_from_meal_plan(meal_plan)

                    # Verify variables.get was called for both URL and project ID
                    assert mock_vars.call_count >= 2
                    calls = [call[0][0] for call in mock_vars.call_args_list]
                    assert "todoist-mcp-server-url" in calls
                    assert "todoist-grocery-project-id" in calls


@pytest.mark.asyncio
async def test_create_grocery_tasks_initializes_mcp_client():
    """Test that MCPServerStreamableHTTP is initialized correctly."""
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Test Meal",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[Ingredient(name="Tomato", quantity="2", unit="medium")],
                instructions=[{"step": 1, "text": "Cook"}],
            )
        ],
        shared_ingredients=[],
    )

    # Mock Secret.load
    with patch("src.todoist_mcp_integration.Secret.load") as mock_load:
        mock_load.side_effect = create_async_secret_mock("test-token-xyz")

        # Mock variables.get
        with patch("src.todoist_mcp_integration.variables.get") as mock_vars:
            mock_vars.side_effect = create_async_variables_get({
                "todoist-mcp-server-url": "https://mcp.example.com",
                "todoist-grocery-project-id": "67890",
            })

            # Mock MCPServerStreamableHTTP to track initialization
            with patch("src.todoist_mcp_integration.MCPServerStreamableHTTP") as mock_mcp:
                # Mock PrefectAgent
                with patch("src.todoist_mcp_integration.PrefectAgent") as mock_agent_class:
                    mock_agent = MagicMock()
                    mock_result = MagicMock()
                    mock_result.output = "Success"
                    mock_agent.run = AsyncMock(return_value=mock_result)
                    mock_agent_class.return_value = mock_agent

                    # Call the function
                    await create_grocery_tasks_from_meal_plan(meal_plan)

                    # Verify MCPServerStreamableHTTP was called with URL and auth headers
                    mock_mcp.assert_called_once()
                    call_args = mock_mcp.call_args
                    assert call_args[0][0] == "https://mcp.example.com"
                    assert "headers" in call_args[1]
                    assert "Authorization" in call_args[1]["headers"]
                    assert "Bearer test-token-xyz" in call_args[1]["headers"]["Authorization"]


@pytest.mark.asyncio
async def test_create_grocery_tasks_wraps_agent_with_prefect():
    """Test that the Pydantic AI agent is wrapped with PrefectAgent for durability."""
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Test Meal",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[Ingredient(name="Tomato", quantity="2", unit="medium")],
                instructions=[{"step": 1, "text": "Cook"}],
            )
        ],
        shared_ingredients=[],
    )

    # Mock Secret.load
    with patch("src.todoist_mcp_integration.Secret.load") as mock_load:
        mock_load.side_effect = create_async_secret_mock("test-token")
        

        # Mock variables.get
        with patch("src.todoist_mcp_integration.variables.get") as mock_vars:
            mock_vars.side_effect = create_async_variables_get({
                "todoist-mcp-server-url": "https://test-mcp.com",
                "todoist-grocery-project-id": "12345",
            })

            # Mock MCPServerStreamableHTTP and Agent
            with patch("src.todoist_mcp_integration.MCPServerStreamableHTTP"):
                # Mock Agent
                with patch("src.todoist_mcp_integration.Agent") as mock_agent_cls:
                    mock_base_agent = MagicMock()
                    mock_agent_cls.return_value = mock_base_agent

                # Mock Agent
                with patch("src.todoist_mcp_integration.Agent") as mock_agent_cls:
                    mock_base_agent = MagicMock()
                    mock_agent_cls.return_value = mock_base_agent

                    # Mock PrefectAgent to track wrapping
                    with patch("src.todoist_mcp_integration.PrefectAgent") as mock_prefect_agent_cls:
                        mock_prefect_agent = MagicMock()
                        mock_result = MagicMock()
                        mock_result.output = "Success"
                        mock_prefect_agent.run = AsyncMock(return_value=mock_result)
                        mock_prefect_agent_cls.return_value = mock_prefect_agent

                        # Call the function
                        await create_grocery_tasks_from_meal_plan(meal_plan)

                        # Verify PrefectAgent was initialized with the base agent
                        mock_prefect_agent_cls.assert_called_once()
                        call_args = mock_prefect_agent_cls.call_args
                        assert call_args[0][0] == mock_base_agent

                        # Verify TaskConfig was passed
                        assert "model_task_config" in call_args[1]
                        task_config = call_args[1]["model_task_config"]
                        assert hasattr(task_config, "retries")


@pytest.mark.asyncio
async def test_create_grocery_tasks_includes_project_id_in_prompt():
    """Test that the project ID is included in the agent prompt."""
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Pasta",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[Ingredient(name="Pasta", quantity="200", unit="g")],
                instructions=[{"step": 1, "text": "Boil pasta"}],
            )
        ],
        shared_ingredients=[],
    )

    project_id = "PROJECT-123"

    # Mock Secret.load
    with patch("src.todoist_mcp_integration.Secret.load") as mock_load:
        mock_load.side_effect = create_async_secret_mock("test-token")
        

        # Mock variables.get
        with patch("src.todoist_mcp_integration.variables.get") as mock_vars:
            mock_vars.side_effect = create_async_variables_get({
                "todoist-mcp-server-url": "https://test-mcp.com",
                "todoist-grocery-project-id": project_id,
            })

            # Mock MCPServerStreamableHTTP and Agent
            with patch("src.todoist_mcp_integration.MCPServerStreamableHTTP"):
                # Mock Agent
                with patch("src.todoist_mcp_integration.Agent") as mock_agent_cls:
                    mock_base_agent = MagicMock()
                    mock_agent_cls.return_value = mock_base_agent

                # Mock PrefectAgent
                with patch("src.todoist_mcp_integration.PrefectAgent") as mock_agent_class:
                    mock_agent = MagicMock()
                    mock_result = MagicMock()
                    mock_result.output = "Success"
                    mock_agent.run = AsyncMock(return_value=mock_result)
                    mock_agent_class.return_value = mock_agent

                    # Call the function
                    await create_grocery_tasks_from_meal_plan(meal_plan)

                    # Verify the agent.run was called with a prompt containing the project ID
                    mock_agent.run.assert_called_once()
                    prompt = mock_agent.run.call_args[0][0]
                    assert project_id in prompt
                    assert "project_id" in prompt


@pytest.mark.asyncio
async def test_create_grocery_tasks_fails_without_mcp_server_url():
    """Test that the function raises an error if MCP server URL is not configured."""
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Test Meal",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[Ingredient(name="Tomato", quantity="2", unit="medium")],
                instructions=[{"step": 1, "text": "Cook"}],
            )
        ],
        shared_ingredients=[],
    )

    # Mock Secret.load
    with patch("src.todoist_mcp_integration.Secret.load") as mock_load:
        mock_load.side_effect = create_async_secret_mock("test-token")
        

        # Mock variables.get to return None for MCP server URL
        with patch("src.todoist_mcp_integration.variables.get") as mock_vars:
            mock_vars.side_effect = create_async_variables_get({
                "todoist-grocery-project-id": "12345",
            })

            # Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                await create_grocery_tasks_from_meal_plan(meal_plan)

            assert "MCP server URL" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_grocery_tasks_fails_without_token():
    """Test that the function raises an error if Todoist token is not available."""
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Test Meal",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[Ingredient(name="Tomato", quantity="2", unit="medium")],
                instructions=[{"step": 1, "text": "Cook"}],
            )
        ],
        shared_ingredients=[],
    )

    # Mock Secret.load to raise an exception
    with patch("src.todoist_mcp_integration.Secret.load") as mock_load:
        mock_load.side_effect = Exception("Secret not found")

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await create_grocery_tasks_from_meal_plan(meal_plan)

        assert "todoist-mcp-auth-token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_grocery_tasks_counts_ingredients_correctly():
    """Test that the function correctly counts total ingredients from meals and shared ingredients."""
    meal_plan = MealPlan(
        meals=[
            Meal(
                name="Meal 1",
                description="Test",
                serves=2,
                active_time_minutes=15,
                inactive_time_minutes=0,
                ingredients=[
                    Ingredient(name="Tomato", quantity="2", unit="medium"),
                    Ingredient(name="Onion", quantity="1", unit="large"),
                ],
                instructions=[{"step": 1, "text": "Cook"}],
            ),
            Meal(
                name="Meal 2",
                description="Test",
                serves=2,
                active_time_minutes=10,
                inactive_time_minutes=0,
                ingredients=[
                    Ingredient(name="Pasta", quantity="200", unit="g"),
                ],
                instructions=[{"step": 1, "text": "Boil"}],
            ),
        ],
        shared_ingredients=[
            Ingredient(name="Olive Oil", quantity="1", unit="tbsp"),
            Ingredient(name="Salt", quantity="1", unit="tsp"),
        ],
    )

    # Mock Secret.load
    with patch("src.todoist_mcp_integration.Secret.load") as mock_load:
        mock_load.side_effect = create_async_secret_mock("test-token")
        

        # Mock variables.get
        with patch("src.todoist_mcp_integration.variables.get") as mock_vars:
            mock_vars.side_effect = create_async_variables_get({
                "todoist-mcp-server-url": "https://test-mcp.com",
                "todoist-grocery-project-id": "12345",
            })

            # Mock MCPServerStreamableHTTP and Agent
            with patch("src.todoist_mcp_integration.MCPServerStreamableHTTP"):
                # Mock Agent
                with patch("src.todoist_mcp_integration.Agent") as mock_agent_cls:
                    mock_base_agent = MagicMock()
                    mock_agent_cls.return_value = mock_base_agent

                # Mock PrefectAgent
                with patch("src.todoist_mcp_integration.PrefectAgent") as mock_agent_class:
                    mock_agent = MagicMock()
                    mock_result = MagicMock()
                    mock_result.output = "Success"
                    mock_agent.run = AsyncMock(return_value=mock_result)
                    mock_agent_class.return_value = mock_agent

                    # Call the function
                    result = await create_grocery_tasks_from_meal_plan(meal_plan)

                    # Verify the total tasks count (2 + 1 + 2 shared = 5)
                    assert result[0]["total_tasks"] == 5
                    assert result[0]["project_id"] == "12345"
