"""
Main Prefect flow for weekly meal planning agent.
Orchestrates preference parsing, meal generation, approval, and grocery task creation.
"""

import asyncio

import logfire
from prefect import flow, task
from prefect.flow_runs import pause_flow_run
from prefect.context import get_run_context

from .claude_integration import generate_meal_plan, parse_dietary_preferences
from .config import get_config
from .models import ApprovalInput, DietaryPreferences, MealPlan
from .slack_integration import (
    monitor_slack_thread_for_approval,
    post_final_meal_plan_to_slack,
    post_meal_plan_to_slack,
    resume_prefect_flow,
)
from .todoist_mcp_integration import create_grocery_tasks_from_meal_plan


# Initialize Logfire
logfire.configure()
logfire.instrument_anthropic()


@task(name="parse_preferences", retries=2, retry_delay_seconds=10)
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


@task(name="generate_meals", retries=2, retry_delay_seconds=10)
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
        return await generate_meal_plan(preferences, feedback)


@task(name="post_to_slack", retries=2, retry_delay_seconds=10)
async def post_to_slack_task(meal_plan: MealPlan) -> str:
    """
    Post meal plan to Slack for approval.

    Args:
        meal_plan: Meal plan to post

    Returns:
        str: Slack message timestamp
    """
    with logfire.span("task:post_to_slack"):
        return await post_meal_plan_to_slack(meal_plan)


@task(name="create_grocery_tasks", retries=2, retry_delay_seconds=10)
async def create_grocery_tasks_task(meal_plan: MealPlan) -> list[dict]:
    """
    Create grocery tasks in Todoist via MCP.

    Args:
        meal_plan: Approved meal plan

    Returns:
        list: Created task responses
    """
    with logfire.span("task:create_grocery_tasks"):
        return await create_grocery_tasks_from_meal_plan(meal_plan)


@task(name="post_final_plan", retries=2, retry_delay_seconds=10)
async def post_final_plan_task(meal_plan: MealPlan) -> None:
    """
    Post final approved meal plan to Slack.

    Args:
        meal_plan: Final approved meal plan
    """
    with logfire.span("task:post_final_plan"):
        await post_final_meal_plan_to_slack(meal_plan)


@flow(name="weekly-meal-planner", log_prints=True)
async def weekly_meal_planner_flow():
    """
    Main flow for weekly meal planning.

    This flow:
    1. Parses dietary preferences
    2. Generates meal plan
    3. Posts to Slack
    4. Pauses for approval (using pause_flow_run with wait_for_input)
    5. If approved: creates grocery tasks
    6. If feedback: regenerates meal plan
    7. Posts final confirmation
    """
    config = get_config()

    with logfire.span("flow:weekly_meal_planner"):
        logfire.info("Starting weekly meal planner flow")

        # Task 1: Parse dietary preferences
        logfire.info("Parsing dietary preferences")
        preferences = await parse_preferences_task(config.dietary_preferences)

        regeneration_count = 0
        approval_received = False
        feedback_text = None

        # Meal generation and approval loop
        while not approval_received and regeneration_count <= config.max_regeneration_attempts:
            with logfire.span("meal_generation_iteration", iteration=regeneration_count):
                # Task 2: Generate meal plan
                logfire.info(
                    "Generating meal plan",
                    regeneration_count=regeneration_count,
                    has_feedback=feedback_text is not None,
                )
                meal_plan = await generate_meals_task(preferences, feedback_text)

                # Task 3: Post to Slack
                logfire.info("Posting meal plan to Slack")
                message_ts = await post_to_slack_task(meal_plan)

                # Task 4: Pause flow and wait for approval
                logfire.info(
                    "Pausing flow for approval",
                    timeout_seconds=config.approval_timeout_seconds,
                )

                # Use Prefect's pause_flow_run with wait_for_input
                # This will pause the flow until it's resumed with ApprovalInput
                approval_input = pause_flow_run(
                    wait_for_input=ApprovalInput,
                    timeout=config.approval_timeout_seconds,
                    key=f"approval_{regeneration_count}",
                )

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

                    if regeneration_count > config.max_regeneration_attempts:
                        logfire.warning(
                            "Max regeneration attempts reached",
                            max_attempts=config.max_regeneration_attempts,
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


# Background task to monitor Slack thread and resume flow
@flow(name="slack-approval-monitor", log_prints=True)
async def slack_approval_monitor_flow(
    flow_run_id: str,
    channel_id: str,
    thread_ts: str,
):
    """
    Background flow to monitor Slack thread and resume main flow.

    This flow runs alongside the main flow, monitoring the Slack thread
    for user responses and resuming the paused flow when a response is received.

    Args:
        flow_run_id: Main flow run ID to resume
        channel_id: Slack channel ID
        thread_ts: Slack message timestamp to monitor
    """
    config = get_config()

    with logfire.span("flow:slack_approval_monitor"):
        logfire.info(
            "Starting Slack approval monitor",
            flow_run_id=flow_run_id,
            thread_ts=thread_ts,
        )

        try:
            # Monitor thread for approval
            approval_input = await monitor_slack_thread_for_approval(
                channel_id=channel_id,
                thread_ts=thread_ts,
                timeout_seconds=config.approval_timeout_seconds,
                poll_interval_seconds=config.slack_poll_interval_seconds,
            )

            # Resume the paused flow
            await resume_prefect_flow(flow_run_id, approval_input)

            logfire.info(
                "Successfully resumed flow from Slack approval",
                approved=approval_input.approved,
            )

        except TimeoutError:
            logfire.error(
                "Timeout waiting for Slack approval",
                flow_run_id=flow_run_id,
            )
            raise

        except Exception as e:
            logfire.error(
                "Error in Slack approval monitor",
                error=str(e),
                flow_run_id=flow_run_id,
            )
            raise


if __name__ == "__main__":
    # Run the flow
    asyncio.run(weekly_meal_planner_flow())
