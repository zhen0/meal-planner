"""
Slack integration for meal plan approval.
Posts meal proposals, monitors threads for approval, and resumes paused flows.
"""

import asyncio
import os
import re
from typing import Optional, Tuple

import logfire
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .models import ApprovalInput, MealPlan


def _get_slack_client() -> WebClient:
    """Get configured Slack client from environment variable."""
    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_bot_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable not set")
    return WebClient(token=slack_bot_token)


@logfire.instrument("format_meal_plan_message")
def format_meal_plan_message(meal_plan: MealPlan) -> str:
    """
    Format meal plan as Slack message.

    Args:
        meal_plan: MealPlan object to format

    Returns:
        str: Formatted Slack message
    """
    lines = ["🍽️ *YOUR WEEKLY MEAL PLAN* (for approval)\n"]

    # Add each meal
    for i, meal in enumerate(meal_plan.meals, 1):
        lines.append(f"*Meal {i}: {meal.name}*")
        lines.append(
            f"Active: {meal.active_time_minutes} min | "
            f"Serves {meal.serves} | "
            f"Ingredients: {len(meal.ingredients)} items"
        )
        lines.append(f"_{meal.description}_\n")

    # Add shared ingredients info
    if meal_plan.shared_ingredients:
        lines.append(f"📊 *Shared Ingredients:* {len(meal_plan.shared_ingredients)} items")
        shared_names = [ing.name for ing in meal_plan.shared_ingredients[:3]]
        lines.append(f"_{', '.join(shared_names)}{'...' if len(meal_plan.shared_ingredients) > 3 else ''}_\n")

    # Add approval instructions
    lines.append("---")
    lines.append("*How to respond:*")
    lines.append("• Reply `approve` or `✓` to accept this plan")
    lines.append("• Reply `reject` or `✗` to reject")
    lines.append("• Reply `feedback: <your feedback>` to regenerate with changes")
    lines.append("  Example: `feedback: make it spicier` or `feedback: no tomatoes`")

    return "\n".join(lines)


@logfire.instrument("post_meal_plan_to_slack")
def post_meal_plan_to_slack(meal_plan: MealPlan, flow_run_id: str = None) -> str:
    """
    Post meal plan to Slack channel.

    Args:
        meal_plan: MealPlan to post
        flow_run_id: Optional flow run ID to include in metadata for webhook

    Returns:
        str: Slack message timestamp (for thread monitoring)

    Raises:
        SlackApiError: If posting fails
    """
    channel_id = os.environ.get("SLACK_CHANNEL_ID")

    message_text = format_meal_plan_message(meal_plan)
    logfire.info("Posting meal plan to Slack", channel_id=channel_id, flow_run_id=flow_run_id)

    try:
        # Include flow_run_id in metadata so webhook can resume the flow
        post_kwargs = {
            "channel": channel_id,
            "text": message_text,
            "mrkdwn": True,
        }

        if flow_run_id:
            post_kwargs["metadata"] = {
                "event_type": "meal_plan_approval",
                "event_payload": {
                    "flow_run_id": flow_run_id,
                }
            }

        client = _get_slack_client()

        response = client.chat_postMessage(**post_kwargs)

        message_ts = response["ts"]

        logfire.info(
            "Successfully posted meal plan to Slack",
            message_ts=message_ts,
            channel_id=channel_id,
            flow_run_id=flow_run_id,
        )

        return message_ts

    except SlackApiError as e:
        logfire.error("Failed to post to Slack", error=str(e))
        raise


@logfire.instrument("parse_slack_response")
def parse_slack_response(text: str) -> Tuple[bool, Optional[str], bool]:
    """
    Parse Slack message text to determine approval status.

    Args:
        text: Message text from Slack

    Returns:
        Tuple of (approved, feedback, regenerate):
            - approved: True if approved, False if rejected/feedback
            - feedback: Feedback text if provided, None otherwise
            - regenerate: True if feedback provided (needs regeneration)
    """
    text_lower = text.lower().strip()

    # Check for approval
    if text_lower in ["approve", "approved", "✓", "✅", "yes", "y"]:
        return (True, None, False)

    # Check for rejection
    if text_lower in ["reject", "rejected", "✗", "❌", "no", "n"]:
        return (False, None, False)

    # Check for feedback pattern: "feedback: <text>"
    feedback_match = re.match(r"feedback:\s*(.+)", text_lower, re.IGNORECASE)
    if feedback_match:
        feedback_text = feedback_match.group(1).strip()
        return (False, feedback_text, True)

    # If no recognized pattern, treat as feedback
    # This is generous: any reply that's not approve/reject is treated as feedback
    return (False, text, True)


@logfire.instrument("monitor_slack_thread_for_approval")
async def monitor_slack_thread_for_approval(
    channel_id: str,
    thread_ts: str,
    timeout_seconds: int = 86400,
    poll_interval_seconds: int = 30,
) -> ApprovalInput:
    """
    Monitor Slack thread for user approval response.

    This function polls the Slack API for replies in a thread until:
    1. A response is received
    2. The timeout is reached

    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp to monitor
        timeout_seconds: Maximum time to wait (default 24 hours)
        poll_interval_seconds: How often to poll (default 30 seconds)

    Returns:
        ApprovalInput: Parsed approval input from user response

    Raises:
        TimeoutError: If no response received within timeout
        SlackApiError: If Slack API calls fail
    """
    client = _get_slack_client()

    logfire.info(
        "Starting Slack thread monitoring",
        thread_ts=thread_ts,
        timeout_seconds=timeout_seconds,
    )

    elapsed_time = 0
    last_checked_ts = thread_ts

    while elapsed_time < timeout_seconds:
        try:
            # Get thread replies
            response = client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                oldest=last_checked_ts,
                limit=10,
            )

            messages = response.get("messages", [])

            # Skip the first message if it's the original post
            if messages and messages[0]["ts"] == thread_ts:
                messages = messages[1:]

            # Check for new replies
            if messages:
                # Get the first reply (most recent)
                latest_message = messages[0]
                message_text = latest_message.get("text", "")

                logfire.info(
                    "Received Slack response",
                    message_text=message_text,
                    message_ts=latest_message["ts"],
                )

                # Parse response
                approved, feedback, regenerate = parse_slack_response(message_text)

                # Create ApprovalInput
                approval_input = ApprovalInput(
                    approved=approved,
                    feedback=feedback,
                    regenerate=regenerate,
                )

                logfire.info(
                    "Parsed approval input",
                    approved=approved,
                    has_feedback=feedback is not None,
                    regenerate=regenerate,
                )

                return approval_input

        except SlackApiError as e:
            logfire.error("Error checking Slack thread", error=str(e))
            # Continue monitoring despite errors

        # Wait before next poll
        await asyncio.sleep(poll_interval_seconds)
        elapsed_time += poll_interval_seconds

        logfire.debug(
            "Still waiting for Slack response",
            elapsed_seconds=elapsed_time,
            timeout_seconds=timeout_seconds,
        )

    # Timeout reached
    logfire.error(
        "Timeout waiting for Slack approval",
        elapsed_seconds=elapsed_time,
        timeout_seconds=timeout_seconds,
    )

    raise TimeoutError(
        f"No response received in Slack thread within {timeout_seconds} seconds"
    )


@logfire.instrument("resume_prefect_flow")
async def resume_prefect_flow(
    flow_run_id: str,
    approval_input: ApprovalInput,
    key: str = "approval-0",
) -> dict:
    """
    Resume a paused Prefect flow with approval input.

    Uses Prefect's built-in client which automatically handles authentication
    when running on Prefect Cloud.

    Args:
        flow_run_id: Prefect flow run ID (UUID)
        approval_input: ApprovalInput object with user decision
        key: The pause key (e.g., "approval-0", "approval-1")

    Returns:
        dict: Response from Prefect API

    Raises:
        httpx.HTTPError: If API request fails
    """
    from prefect.client.orchestration import get_client

    logfire.info(
        "Resuming Prefect flow",
        flow_run_id=flow_run_id,
        key=key,
        approved=approval_input.approved,
        has_feedback=approval_input.feedback is not None,
    )

    try:
        # Use Prefect's built-in client (automatically authenticated on Prefect Cloud)
        async with get_client() as client:
            # Resume the paused flow run with the approval input
            # The run_input should be a plain dict with the approval fields
            await client.resume_flow_run(
                flow_run_id=flow_run_id,
                run_input=approval_input.model_dump(),
            )

            logfire.info(
                "Successfully resumed flow with input",
                flow_run_id=flow_run_id,
                key=key,
            )

            return {"success": True, "flow_run_id": flow_run_id}

    except Exception as e:
        logfire.error(
            "Failed to resume Prefect flow",
            error=str(e),
            flow_run_id=flow_run_id,
            key=key,
        )
        raise


@logfire.instrument("poll_slack_and_resume_flow")
async def poll_slack_and_resume_flow(
    channel_id: str,
    thread_ts: str,
    flow_run_id: str,
    pause_key: str = "approval-0",
    timeout_seconds: int = 86400,
    poll_interval_seconds: int = 30,
) -> None:
    """
    Poll Slack for approval response and automatically resume the Prefect flow.

    This runs as a background task - it monitors Slack for a response,
    parses it, and resumes the paused flow when a response is received.

    This is a fallback mechanism for when webhooks aren't available.

    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp to monitor
        flow_run_id: Prefect flow run ID to resume
        pause_key: The key used when pausing the flow (e.g., "approval-0")
        timeout_seconds: Maximum time to wait (default 24 hours)
        poll_interval_seconds: How often to poll (default 30 seconds)

    Raises:
        TimeoutError: If no response received within timeout
    """
    logfire.info(
        "Starting background Slack polling task",
        thread_ts=thread_ts,
        flow_run_id=flow_run_id,
        pause_key=pause_key,
    )

    try:
        # Poll Slack for approval
        approval_input = await monitor_slack_thread_for_approval(
            channel_id=channel_id,
            thread_ts=thread_ts,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

        # Resume the flow with the approval input
        await resume_prefect_flow(
            flow_run_id=flow_run_id,
            approval_input=approval_input,
            key=pause_key,
        )

        logfire.info(
            "Background polling task completed successfully",
            flow_run_id=flow_run_id,
        )

    except TimeoutError as e:
        logfire.error(
            "Background polling task timed out",
            error=str(e),
            flow_run_id=flow_run_id,
        )
        # Don't raise - let the flow timeout naturally

    except Exception as e:
        logfire.error(
            "Background polling task failed",
            error=str(e),
            flow_run_id=flow_run_id,
        )
        # Don't raise - this is a background task


@logfire.instrument("post_simple_grocery_list_to_slack")
async def post_simple_grocery_list_to_slack(meal_plan: MealPlan) -> None:
    """
    Post a simple grocery list to Slack with unique items only.

    Args:
        meal_plan: Approved MealPlan to extract grocery list from

    Raises:
        SlackApiError: If posting fails
    """
    channel_id = os.environ.get("SLACK_CHANNEL_ID")
    client = _get_slack_client()

    # Collect unique ingredient names
    unique_items = set()

    for meal in meal_plan.meals:
        for ingredient in meal.ingredients:
            unique_items.add(ingredient.name)

    for ingredient in meal_plan.shared_ingredients:
        unique_items.add(ingredient.name)

    # Build simple list message
    lines = ["🛒 *GROCERY LIST*\n"]

    # Add items alphabetically
    for item in sorted(unique_items):
        lines.append(f"• {item}")

    lines.append(f"\n_Total: {len(unique_items)} items_")

    message_text = "\n".join(lines)

    logfire.info("Posting simple grocery list to Slack")

    try:
        client.chat_postMessage(
            channel=channel_id,
            text=message_text,
            mrkdwn=True,
        )

        logfire.info("Successfully posted simple grocery list")

    except SlackApiError as e:
        logfire.error("Failed to post simple grocery list", error=str(e))
        raise


@logfire.instrument("post_final_meal_plan_to_slack")
async def post_final_meal_plan_to_slack(meal_plan: MealPlan) -> None:
    """
    Post final approved meal plan to Slack with full details.

    Args:
        meal_plan: Approved MealPlan to post

    Raises:
        SlackApiError: If posting fails
    """
    channel_id = os.environ.get("SLACK_CHANNEL_ID")
    client = _get_slack_client()

    # Build detailed message
    lines = ["✅ *MEAL PLAN APPROVED*\n", "🍽️ *MEALS THIS WEEK*\n"]

    # Add each meal with full details
    for i, meal in enumerate(meal_plan.meals, 1):
        lines.append(f"*Meal {i}: {meal.name}*")
        lines.append(
            f"Serves {meal.serves} | "
            f"Active Time: {meal.active_time_minutes} min | "
            f"Inactive Time: {meal.inactive_time_minutes} min"
        )
        lines.append(f"{meal.description}\n")

        # Ingredients
        lines.append("*Ingredients:*")
        for ing in meal.ingredients:
            line = f"• {ing.name} - {ing.quantity} {ing.unit}"
            if ing.shopping_notes:
                line += f" ({ing.shopping_notes})"
            lines.append(line)

        # Instructions
        lines.append("\n*Instructions:*")
        for inst in meal.instructions:
            lines.append(f"{inst.step}. {inst.text}")

        lines.append("\n---\n")

    # Shared ingredients
    if meal_plan.shared_ingredients:
        lines.append(f"📋 *Shared Ingredients* ({len(meal_plan.shared_ingredients)} items)")
        for ing in meal_plan.shared_ingredients:
            line = f"• {ing.name} - {ing.quantity} {ing.unit}"
            if ing.shopping_notes:
                line += f" ({ing.shopping_notes})"
            lines.append(line)
        lines.append("")

    lines.append("✅ Ingredients added to Todoist Grocery project!")

    message_text = "\n".join(lines)

    logfire.info("Posting final meal plan to Slack")

    try:
        client.chat_postMessage(
            channel=channel_id,
            text=message_text,
            mrkdwn=True,
        )

        logfire.info("Successfully posted final meal plan")

    except SlackApiError as e:
        logfire.error("Failed to post final meal plan", error=str(e))
        raise
