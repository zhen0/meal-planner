"""
Main Prefect flow for weekly meal planning agent.
Orchestrates preference parsing, meal generation, approval, and grocery task creation.
"""

import asyncio
import os

import logfire
from prefect import flow, task
from prefect.flow_runs import pause_flow_run
from prefect.context import get_run_context
from prefect.artifacts import (
    create_markdown_artifact,
    create_table_artifact,
)
from prefect.deployments import run_deployment
from prefect.blocks.system import Secret
from prefect.variables import Variable

from .claude_integration import generate_meal_plan, parse_dietary_preferences
from .models import ApprovalInput, DietaryPreferences, MealPlan
from .slack_integration import (
    monitor_slack_thread_for_approval,
    poll_slack_and_resume_flow,
    post_final_meal_plan_to_slack,
    post_meal_plan_to_slack,
    post_simple_grocery_list_to_slack,
    resume_prefect_flow,
)
from .todoist_mcp_integration import create_grocery_tasks_from_meal_plan


# Configuration is loaded lazily inside the flow to work with Prefect managed execution
# Environment variables should be set via deployment job_variables

timeout_seconds = 86400
poll_interval_seconds = 30
max_regeneration_attempts = 3


# Artifact creation helpers
@task(name="create_meal_plan_artifact")
def create_meal_plan_artifact(meal_plan: MealPlan, feedback: str | None = None) -> None:
    """
    Create a Markdown artifact showing the meal plan in the Prefect UI.

    Args:
        meal_plan: The generated meal plan
        feedback: Optional feedback that was provided for regeneration
    """
    markdown = "# Weekly Meal Plan\n\n"

    if feedback:
        markdown += f"_Generated with feedback: {feedback}_\n\n"

    # Add meals
    for i, meal in enumerate(meal_plan.meals, 1):
        markdown += f"## Meal {i}: {meal.name}\n\n"
        markdown += f"**Description:** {meal.description}\n\n"
        markdown += f"**Details:**\n"
        markdown += f"- Serves: {meal.serves}\n"
        markdown += f"- Active time: {meal.active_time_minutes} minutes\n"
        if meal.inactive_time_minutes > 0:
            markdown += f"- Inactive time: {meal.inactive_time_minutes} minutes\n"
        markdown += f"- Ingredients: {len(meal.ingredients)} items\n\n"

        # Ingredients
        markdown += "**Ingredients:**\n"
        for ingredient in meal.ingredients:
            notes = f" ({ingredient.shopping_notes})" if ingredient.shopping_notes else ""
            markdown += f"- {ingredient.quantity} {ingredient.unit} {ingredient.name}{notes}\n"
        markdown += "\n"

        # Instructions
        markdown += "**Instructions:**\n"
        for instruction in meal.instructions:
            markdown += f"{instruction.step}. {instruction.text}\n"
        markdown += "\n---\n\n"

    # Shared ingredients
    if meal_plan.shared_ingredients:
        markdown += f"## Shared Ingredients ({len(meal_plan.shared_ingredients)} items)\n\n"
        for ingredient in meal_plan.shared_ingredients:
            notes = f" ({ingredient.shopping_notes})" if ingredient.shopping_notes else ""
            markdown += f"- {ingredient.quantity} {ingredient.unit} {ingredient.name}{notes}\n"

    create_markdown_artifact(
        key="weekly-meal-plan",
        markdown=markdown,
        description="Generated meal plan with recipes and ingredients",
    )


@task(name="create_grocery_list_artifact")
def create_grocery_list_artifact(meal_plan: MealPlan, created_tasks: list[dict]) -> None:
    """
    Create table and markdown artifacts showing the grocery list in the Prefect UI.

    Args:
        meal_plan: The approved meal plan
        created_tasks: List of created Todoist tasks
    """
    # Create a table artifact for quick scanning
    table_data = []

    # Add all ingredients from all meals
    for meal in meal_plan.meals:
        for ingredient in meal.ingredients:
            table_data.append({
                "Item": ingredient.name,
                "Quantity": ingredient.quantity,
                "Unit": ingredient.unit,
                "Notes": ingredient.shopping_notes or "",
                "Meal": meal.name,
            })

    # Add shared ingredients
    for ingredient in meal_plan.shared_ingredients:
        table_data.append({
            "Item": ingredient.name,
            "Quantity": ingredient.quantity,
            "Unit": ingredient.unit,
            "Notes": ingredient.shopping_notes or "",
            "Meal": "Shared",
        })

    create_table_artifact(
        key="grocery-shopping-list",
        table=table_data,
        description=f"Grocery list with {len(table_data)} items for {len(meal_plan.meals)} meals",
    )

    # Create a markdown artifact with task creation details
    markdown = f"# Grocery Tasks Created\n\n"
    markdown += f"**Total tasks created:** {len(created_tasks)}\n\n"
    markdown += f"**Meals:** {', '.join(meal.name for meal in meal_plan.meals)}\n\n"
    markdown += "## Task Details\n\n"

    for i, task in enumerate(created_tasks, 1):
        task_content = task.get("content", "Unknown task")
        markdown += f"{i}. {task_content}\n"

    create_markdown_artifact(
        key="grocery-tasks-created",
        markdown=markdown,
        description=f"Created {len(created_tasks)} grocery tasks in Todoist",
    )

    # Create a simple plain list artifact with unique items only
    unique_items = set()

    # Collect unique ingredient names from all meals
    for meal in meal_plan.meals:
        for ingredient in meal.ingredients:
            unique_items.add(ingredient.name)

    # Add unique shared ingredients
    for ingredient in meal_plan.shared_ingredients:
        unique_items.add(ingredient.name)

    # Create plain markdown list (sorted alphabetically)
    simple_list = "\n".join(sorted(unique_items))

    create_markdown_artifact(
        key="grocery-simple-list",
        markdown=simple_list,
        description=f"Simple list of {len(unique_items)} unique grocery items",
    )


@task(
    name="parse_preferences",
    retries=2,
    retry_delay_seconds=10,
    persist_result=True,
    result_storage_key="preferences-{flow_run.id}",
)
async def parse_preferences_task(preferences_text: str) -> DietaryPreferences:
    """
    Parse dietary preferences from natural language.

    Args:
        preferences_text: Natural language dietary preferences

    Returns:
        DietaryPreferences: Structured preferences
    """
    with logfire.span("task:parse_preferences"):
        return await parse_dietary_preferences(preferences_text)


@task(
    name="generate_meals",
    retries=2,
    retry_delay_seconds=10,
    persist_result=True,
    result_storage_key="meal-plan-{flow_run.id}-{task_run.id}",
)
async def generate_meals_task(
    preferences: DietaryPreferences,
    feedback: str | None = None,
) -> MealPlan:
    """
    Generate meal plan based on preferences.

    Args:
        preferences: Structured dietary preferences
        feedback: Optional feedback for regeneration

    Returns:
        MealPlan: Generated meal plan
    """
    with logfire.span("task:generate_meals", feedback=feedback):
        meal_plan = await generate_meal_plan(preferences, feedback)

        # Create meal plan artifact for UI visibility
        create_meal_plan_artifact(meal_plan, feedback)

        return meal_plan


@task(
    name="post_to_slack",
    retries=2,
    retry_delay_seconds=10,
    persist_result=True,
    result_storage_key="slack-message-{flow_run.id}-{task_run.id}",
)
async def post_to_slack_task(meal_plan: MealPlan, flow_run_id: str = None) -> str:
    """
    Post meal plan to Slack for approval.

    Args:
        meal_plan: Meal plan to post

    Returns:
        str: Slack message timestamp
    """
    with logfire.span("task:post_to_slack"):
        return await post_meal_plan_to_slack(meal_plan, flow_run_id)


@task(
    name="create_grocery_tasks",
    retries=2,
    retry_delay_seconds=10,
    persist_result=True,
    result_storage_key="grocery-tasks-{flow_run.id}",
)
async def create_grocery_tasks_task(meal_plan: MealPlan) -> list[dict]:
    """
    Create grocery tasks in Todoist via MCP.

    Args:
        meal_plan: Approved meal plan

    Returns:
        list: Created task responses
    """
    with logfire.span("task:create_grocery_tasks"):
        created_tasks = await create_grocery_tasks_from_meal_plan(meal_plan)

        # Create grocery list artifact for UI visibility
        create_grocery_list_artifact(meal_plan, created_tasks)

        return created_tasks


@task(
    name="post_final_plan",
    retries=2,
    retry_delay_seconds=10,
    persist_result=True,
    result_storage_key="final-confirmation-{flow_run.id}",
)
async def post_final_plan_task(meal_plan: MealPlan) -> None:
    """
    Post final approved meal plan to Slack.

    Args:
        meal_plan: Final approved meal plan
    """
    with logfire.span("task:post_final_plan"):
        await post_final_meal_plan_to_slack(meal_plan)


@task(
    name="post_simple_grocery_list",
    retries=2,
    retry_delay_seconds=10,
    persist_result=True,
    result_storage_key="simple-grocery-list-{flow_run.id}",
)
async def post_simple_grocery_list_task(meal_plan: MealPlan) -> None:
    """
    Post simple grocery list to Slack.

    Args:
        meal_plan: Final approved meal plan
    """
    with logfire.span("task:post_simple_grocery_list"):
        await post_simple_grocery_list_to_slack(meal_plan)


@flow(
    name="slack-approval-polling",
    log_prints=True,
)
async def slack_approval_polling_flow(
    channel_id: str,
    thread_ts: str,
    flow_run_id: str,
    pause_key: str,
    timeout_seconds: int = timeout_seconds,
    poll_interval_seconds: int = poll_interval_seconds,
):
    """
    Independent flow that polls Slack and resumes the paused meal planner flow.

    This runs as a separate deployment so it persists independently,
    even when the main flow is paused.

    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp to monitor
        flow_run_id: The paused flow run ID to resume
        pause_key: The key used when pausing (e.g., "approval-0")
        timeout_seconds: How long to poll before giving up
        poll_interval_seconds: How often to check Slack
    """
    with logfire.span("flow:slack_approval_polling"):
        logfire.info(
            "Starting independent Slack polling flow",
            flow_run_id=flow_run_id,
            pause_key=pause_key,
        )

        await poll_slack_and_resume_flow(
            channel_id=channel_id,
            thread_ts=thread_ts,
            flow_run_id=flow_run_id,
            pause_key=pause_key,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

        logfire.info("Slack polling flow completed")


@flow(
    name="weekly-meal-planner",
    log_prints=True,
    persist_result=True,
    result_storage='s3-bucket/meal-planner-results',  # S3 block for result storage
)
async def weekly_meal_planner_flow(
    dietary_preferences: str = "I like quick, healthy meals under 20 minutes for 3 people including one child."
):
    """
    Main flow for weekly meal planning.

    Args:
        dietary_preferences: Natural language dietary preferences

    This flow:
    1. Parses dietary preferences
    2. Generates meal plan
    3. Posts to Slack
    4. Pauses for approval (using pause_flow_run with wait_for_input)
    5. If approved: creates grocery tasks
    6. If feedback: regenerates meal plan
    7. Posts final confirmation
    """
    # Set environment variables required by Pydantic AI and Logfire
    anthropic_secret = await Secret.load("anthropic-api-key")
    anthropic_api_key = anthropic_secret.get()
    os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
    logfire_secret = await Secret.load("logfire-token")
    logfire_token = logfire_secret.get()
    os.environ["LOGFIRE_TOKEN"] = logfire_token

    # Configure Logfire observability
    logfire.configure()
    logfire.instrument_httpx()  # Auto-trace HTTP requests (Slack, MCP server)

    with logfire.span("flow:weekly_meal_planner"):
        logfire.info("Starting weekly meal planner flow")       

        # Task 1: Parse dietary preferences
        logfire.info("Parsing dietary preferences", dietary_preferences=dietary_preferences)
        preferences = await parse_preferences_task(dietary_preferences)

        regeneration_count = 0
        approval_received = False
        feedback_text = None

        # Meal generation and approval loop
        while not approval_received and regeneration_count <= 3:
            with logfire.span("meal_generation_iteration", iteration=regeneration_count):
                # Task 2: Generate meal plan
                logfire.info(
                    "Generating meal plan",
                    regeneration_count=regeneration_count,
                    has_feedback=feedback_text is not None,
                )
                meal_plan = await generate_meals_task(preferences, feedback_text)

                # Get flow run ID to include in Slack message
                flow_run_context = get_run_context()
                current_flow_run_id = str(flow_run_context.flow_run.id)

                # Task 3: Post to Slack with flow_run_id in metadata
                logfire.info("Posting meal plan to Slack with flow_run_id", flow_run_id=current_flow_run_id)
                message_ts = await post_to_slack_task(meal_plan, current_flow_run_id)

                # Task 4: Kick off independent polling deployment as fallback
                logfire.info("Kicking off independent Slack polling deployment as fallback")
                pause_key = f"approval-{regeneration_count}"
                channel_id = await variables.get("slack_channel_id", default=None)

                # Trigger polling flow as completely separate deployment run
                # This runs independently and persists even when this flow pauses
                await run_deployment(
                    name="slack-approval-polling/slack-polling",
                    parameters={
                        "channel_id": channel_id,
                        "thread_ts": message_ts,
                        "flow_run_id": current_flow_run_id,
                        "pause_key": pause_key,
                        "timeout_seconds": timeout_seconds,
                        "poll_interval_seconds": poll_interval_seconds,
                    },
                    timeout=0,  # Don't wait for it to complete
                )

                logfire.info("Polling deployment triggered successfully")

                # Task 5: Pause flow and wait for approval (webhook OR polling will resume)
                logfire.info(
                    "Pausing flow for approval (webhook or polling will resume)",
                    timeout_seconds=timeout_seconds,
                    pause_key=pause_key,
                )

                # Use Prefect's pause_flow_run with wait_for_input
                # This will pause the flow until it's resumed with ApprovalInput
                # Either the webhook OR the independent polling flow will resume it
                approval_input = await pause_flow_run(
                    wait_for_input=ApprovalInput,
                    timeout=timeout_seconds,
                    key=pause_key,
                )

                # Note: The polling flow runs independently and will continue
                # polling until timeout or until this flow resumes (whichever comes first)

                # Flow resumes here with approval_input
                logfire.info(
                    "Flow resumed with approval input",
                    approved=approval_input.approved,
                    has_feedback=approval_input.feedback is not None,
                    regenerate=approval_input.regenerate,
                )

                # Check approval status
                if approval_input.approved:
                    # Approved! Exit loop
                    approval_received = True
                    logfire.info("Meal plan approved")

                elif approval_input.regenerate and approval_input.feedback:
                    # User provided feedback, regenerate
                    feedback_text = approval_input.feedback
                    regeneration_count += 1

                    logfire.info(
                        "Regenerating meal plan with feedback",
                        feedback=feedback_text,
                        regeneration_count=regeneration_count,
                    )

                    if regeneration_count > max_regeneration_attempts:
                        logfire.warning(
                            "Max regeneration attempts reached",
                            max_attempts=max_regeneration_attempts,
                        )
                        # Use last meal plan even if not approved
                        approval_received = True

                else:
                    # Rejected without feedback, use last plan
                    logfire.warning("Meal plan rejected without feedback")
                    approval_received = True

        # Task 5: Create grocery tasks
        logfire.info("Creating grocery tasks in Todoist")
        created_tasks = await create_grocery_tasks_task(meal_plan)

        logfire.info(
            "Successfully created grocery tasks",
            num_tasks=len(created_tasks),
        )

        # Task 6: Post final confirmation
        logfire.info("Posting final meal plan to Slack")
        await post_final_plan_task(meal_plan)

        # Task 7: Post simple grocery list
        logfire.info("Posting simple grocery list to Slack")
        await post_simple_grocery_list_task(meal_plan)

        logfire.info(
            "Weekly meal planner flow completed",
            num_meals=len(meal_plan.meals),
            num_grocery_tasks=len(created_tasks),
            regeneration_count=regeneration_count,
        )

        return {
            "meal_plan": meal_plan.model_dump(),
            "num_grocery_tasks": len(created_tasks),
            "regeneration_count": regeneration_count,
        }


# Note: Slack approval is now handled via Prefect webhook
# When user responds in Slack, Slack Events API sends webhook to Prefect
# Prefect webhook triggers automation that calls resume_flow_run API
# See README for setup instructions


if __name__ == "__main__":
    # Run the flow
    asyncio.run(weekly_meal_planner_flow())
