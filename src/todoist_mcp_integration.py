"""
Todoist MCP integration with strict Grocery project restriction.
All task creation is validated before being sent to the MCP server.
Uses MCP (Model Context Protocol) JSON-RPC format.
"""

from typing import List

import httpx
import logfire
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from .config import get_config
from .models import Ingredient, MealPlan, TodoistTask
from .security_validation import ProjectAccessDenied, validate_and_audit_task_creation


@logfire.instrument("create_todoist_task")
async def create_todoist_task(task: TodoistTask) -> dict:
    """
    Create a single task in Todoist via MCP server using prompt-based approach.

    This function includes strict validation to ensure ONLY the Grocery
    project can be written to.

    Args:
        task: TodoistTask object with task details

    Returns:
        dict: Response from MCP server

    Raises:
        ProjectAccessDenied: If task is for wrong project
    """
    config = get_config()

    # CRITICAL: Validate project ID before making ANY MCP call
    validate_and_audit_task_creation(
        project_id=task.project_id,
        task_content=task.content,
    )

    logfire.info(
        "Creating Todoist task via MCP",
        project_id=task.project_id,
        task_content=task.content,
    )

    # Build the prompt for the MCP server
    labels_str = ", ".join(task.labels) if task.labels else "none"
    due_str = f" with due date '{task.due_string}'" if task.due_string else ""

    prompt = f"""Create a Todoist task with the following details:
- Content: {task.content}
- Project ID: {task.project_id}
- Labels: {labels_str}{due_str}

Please create this task and confirm it was created successfully."""

    try:
        # Use MCP client to send prompt to Todoist server
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-todoist"],
            env={"TODOIST_API_TOKEN": config.todoist_api_token} if config.todoist_api_token else None,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Send the prompt to create the task
                result = await session.send_prompt(prompt)

                logfire.info(
                    "Successfully created Todoist task",
                    task_content=task.content,
                    result=str(result),
                )

                return {"success": True, "content": task.content, "result": str(result)}

    except Exception as e:
        logfire.error(
            "Failed to create Todoist task via MCP",
            error=str(e),
            task_content=task.content,
        )
        raise


@logfire.instrument("create_grocery_tasks_from_meal_plan")
async def create_grocery_tasks_from_meal_plan(meal_plan: MealPlan) -> List[dict]:
    """
    Create Todoist grocery tasks from a meal plan.

    This function:
    1. Extracts all ingredients from the meal plan
    2. Formats them as grocery tasks with meal prefixes
    3. Validates project ID for EACH task (security check)
    4. Creates tasks in the Grocery project via MCP

    Args:
        meal_plan: MealPlan object with meals and ingredients

    Returns:
        List[dict]: List of created task responses from MCP server

    Raises:
        ProjectAccessDenied: If any task is for wrong project
    """
    config = get_config()
    created_tasks = []

    logfire.info(
        "Creating grocery tasks from meal plan",
        num_meals=len(meal_plan.meals),
        num_shared_ingredients=len(meal_plan.shared_ingredients),
    )

    # Process ingredients for each meal
    for meal in meal_plan.meals:
        for ingredient in meal.ingredients:
            # Format task content with meal prefix
            task_content = f"[{meal.name}] {ingredient.name} - {ingredient.quantity} {ingredient.unit}"

            if ingredient.shopping_notes:
                task_content += f" ({ingredient.shopping_notes})"

            # Create TodoistTask object
            task = TodoistTask(
                content=task_content,
                project_id=config.todoist_grocery_project_id,
                labels=["grocery", "meal-prep", "this-week"],
                due_string="tomorrow",
            )

            # Create task (includes validation)
            result = await create_todoist_task(task)
            created_tasks.append(result)

    # Process shared ingredients
    for ingredient in meal_plan.shared_ingredients:
        # Format task content for shared ingredients
        task_content = f"[Shared] {ingredient.name} - {ingredient.quantity} {ingredient.unit}"

        if ingredient.shopping_notes:
            task_content += f" ({ingredient.shopping_notes})"

        # Create TodoistTask object
        task = TodoistTask(
            content=task_content,
            project_id=config.todoist_grocery_project_id,
            labels=["grocery", "meal-prep", "this-week", "shared"],
            due_string="tomorrow",
        )

        # Create task (includes validation)
        result = await create_todoist_task(task)
        created_tasks.append(result)

    logfire.info(
        "Successfully created all grocery tasks",
        total_tasks_created=len(created_tasks),
    )

    return created_tasks
