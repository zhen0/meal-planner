"""
Todoist MCP integration with strict Grocery project restriction.
Uses Pydantic AI agent with Todoist MCP tools to create grocery tasks.
"""

from typing import List

import logfire
from pydantic_ai import Agent
from pydantic_ai.durable_exec.prefect import PrefectAgent, TaskConfig
from pydantic_ai.mcp import MCPServerStreamableHTTP

from .config import get_config
from .models import MealPlan
from .security_validation import validate_and_audit_task_creation


# System prompt for Todoist task creation agent
TODOIST_AGENT_PROMPT = """You are a grocery task creation assistant. Your job is to create tasks in Todoist based on meal plans.

CRITICAL RULES:
1. You MUST use the Todoist MCP tools available to you
2. All tasks MUST be created in the Grocery project (project_id will be provided)
3. Each ingredient from the meal plan becomes a separate Todoist task
4. Format task content as: "[Meal Name] ingredient - quantity unit (shopping notes if any)"
5. Add labels: ["grocery", "meal-prep", "this-week"]
6. For shared ingredients, use "[Shared]" as the meal name prefix
7. Set due date to "tomorrow" for all tasks
8. Confirm each task was created successfully

You will receive a meal plan with meals and ingredients. Create a Todoist task for each ingredient using the available MCP tools.

IMPORTANT: Use the Todoist MCP tools to create tasks. Do NOT try to make HTTP requests or use any other method."""


@logfire.instrument("create_grocery_tasks_from_meal_plan")
async def create_grocery_tasks_from_meal_plan(meal_plan: MealPlan) -> List[dict]:
    """
    Create Todoist grocery tasks from a meal plan using Pydantic AI agent with MCP tools.

    This function:
    1. Validates the grocery project ID (security check)
    2. Creates a Pydantic AI agent with access to Todoist MCP tools
    3. Sends the meal plan to the agent
    4. Agent creates tasks in Todoist using MCP tools

    Args:
        meal_plan: MealPlan object with meals and ingredients

    Returns:
        List[dict]: Summary of created tasks

    Raises:
        ProjectAccessDenied: If project ID validation fails
    """
    config = get_config()

    # CRITICAL: Validate project ID before making ANY calls
    validate_and_audit_task_creation(
        project_id=config.todoist_grocery_project_id,
        task_content="Validation check",
    )

    logfire.info(
        "Creating grocery tasks from meal plan via Pydantic AI agent",
        num_meals=len(meal_plan.meals),
        num_shared_ingredients=len(meal_plan.shared_ingredients),
    )

    # Count total tasks to create
    total_ingredients = sum(len(meal.ingredients) for meal in meal_plan.meals)
    total_ingredients += len(meal_plan.shared_ingredients)

    # Connect to Todoist MCP server with authentication
    # FastMCP Todoist server expects the Todoist API token in a specific header
    # Typically X-API-Key or Authorization Bearer format
    headers = {}
    if config.todoist_api_token:
        # Try the standard FastMCP auth pattern first
        headers["X-API-Key"] = config.todoist_api_token

    todoist_mcp = MCPServerStreamableHTTP(
        config.todoist_mcp_server_url,
        headers=headers
    )

    # Create Pydantic AI agent with Todoist MCP tools
    agent = Agent(
        'anthropic:claude-3-5-sonnet-20241022',
        system_prompt=TODOIST_AGENT_PROMPT,
        toolsets=[todoist_mcp],
        name='todoist-grocery-task-creator',
    )

    # Wrap with PrefectAgent for durable execution
    prefect_agent = PrefectAgent(
        agent,
        model_task_config=TaskConfig(
            retries=2,
            retry_delay_seconds=[10.0, 20.0],
            timeout_seconds=120.0,  # Allow time for creating multiple tasks
        ),
    )

    # Build the prompt with meal plan details
    prompt = f"""Create Todoist grocery tasks for the following meal plan.

**CRITICAL: Use project_id: {config.todoist_grocery_project_id}**

**Meal Plan:**

"""

    # Add each meal with ingredients
    for meal in meal_plan.meals:
        prompt += f"\n**{meal.name}**\n"
        for ingredient in meal.ingredients:
            notes = f" ({ingredient.shopping_notes})" if ingredient.shopping_notes else ""
            prompt += f"- {ingredient.name} - {ingredient.quantity} {ingredient.unit}{notes}\n"

    # Add shared ingredients
    if meal_plan.shared_ingredients:
        prompt += f"\n**Shared Ingredients (used across multiple meals):**\n"
        for ingredient in meal_plan.shared_ingredients:
            notes = f" ({ingredient.shopping_notes})" if ingredient.shopping_notes else ""
            prompt += f"- {ingredient.name} - {ingredient.quantity} {ingredient.unit}{notes}\n"

    prompt += f"""

**Instructions:**
1. Create a separate Todoist task for EACH ingredient listed above
2. Use project_id: {config.todoist_grocery_project_id}
3. Format: "[Meal Name] ingredient - quantity unit (notes if any)"
4. For shared ingredients, use "[Shared]" as the prefix
5. Add labels: ["grocery", "meal-prep", "this-week"]
6. Set due date: "tomorrow"
7. Confirm each task was created successfully

Total tasks to create: {total_ingredients}

Please create all {total_ingredients} grocery tasks now using the Todoist MCP tools."""

    try:
        # Run agent with Prefect durability
        result = await prefect_agent.run(prompt)

        logfire.info(
            "Successfully created grocery tasks via agent",
            agent_output=str(result.output),
        )

        # Return summary
        return [
            {
                "success": True,
                "total_tasks": total_ingredients,
                "project_id": config.todoist_grocery_project_id,
                "agent_response": str(result.output),
            }
        ]

    except Exception as e:
        logfire.error("Error creating grocery tasks via agent", error=str(e))
        raise ValueError(f"Failed to create grocery tasks: {e}") from e
