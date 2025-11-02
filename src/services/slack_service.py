"""
Slack service layer.
Provides high-level Slack operations with centralized client management.
"""

import logfire
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..config import get_config
from ..models import MealPlan
from ..utils.slack_formatting import (
    format_final_meal_plan,
    format_meal_plan_message,
    format_simple_grocery_list,
)


class SlackService:
    """
    Centralized Slack service for managing Slack API interactions.
    Provides a single point of client initialization and configuration.
    """

    def __init__(self):
        """Initialize Slack service with configuration."""
        self._client = None
        self._config = None

    @property
    def client(self) -> WebClient:
        """
        Get or create Slack client (lazy initialization).

        Returns:
            WebClient: Configured Slack client
        """
        if self._client is None:
            if self._config is None:
                self._config = get_config()
            self._client = WebClient(token=self._config.slack_bot_token)
        return self._client

    @logfire.instrument("slack_service.post_meal_plan")
    async def post_meal_plan(self, meal_plan: MealPlan, flow_run_id: str = None) -> str:
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
        config = self._config or get_config()
        message_text = format_meal_plan_message(meal_plan)

        logfire.info("Posting meal plan to Slack", channel_id=config.slack_channel_id, flow_run_id=flow_run_id)

        try:
            # Include flow_run_id in metadata so webhook can resume the flow
            post_kwargs = {
                "channel": config.slack_channel_id,
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

            response = self.client.chat_postMessage(**post_kwargs)
            message_ts = response["ts"]

            logfire.info(
                "Successfully posted meal plan to Slack",
                message_ts=message_ts,
                channel_id=config.slack_channel_id,
                flow_run_id=flow_run_id,
            )

            return message_ts

        except SlackApiError as e:
            logfire.error("Failed to post to Slack", error=str(e))
            raise

    @logfire.instrument("slack_service.post_simple_grocery_list")
    async def post_simple_grocery_list(self, meal_plan: MealPlan) -> None:
        """
        Post a simple grocery list to Slack with unique items only.

        Args:
            meal_plan: Approved MealPlan to extract grocery list from

        Raises:
            SlackApiError: If posting fails
        """
        config = self._config or get_config()
        message_text = format_simple_grocery_list(meal_plan)

        logfire.info("Posting simple grocery list to Slack")

        try:
            self.client.chat_postMessage(
                channel=config.slack_channel_id,
                text=message_text,
                mrkdwn=True,
            )

            logfire.info("Successfully posted simple grocery list")

        except SlackApiError as e:
            logfire.error("Failed to post simple grocery list", error=str(e))
            raise

    @logfire.instrument("slack_service.post_final_meal_plan")
    async def post_final_meal_plan(self, meal_plan: MealPlan) -> None:
        """
        Post final approved meal plan to Slack with full details.

        Args:
            meal_plan: Approved MealPlan to post

        Raises:
            SlackApiError: If posting fails
        """
        config = self._config or get_config()
        message_text = format_final_meal_plan(meal_plan)

        logfire.info("Posting final meal plan to Slack")

        try:
            self.client.chat_postMessage(
                channel=config.slack_channel_id,
                text=message_text,
                mrkdwn=True,
            )

            logfire.info("Successfully posted final meal plan")

        except SlackApiError as e:
            logfire.error("Failed to post final meal plan", error=str(e))
            raise


# Global service instance (singleton pattern)
_slack_service = None


def get_slack_service() -> SlackService:
    """
    Get the global Slack service instance (singleton pattern).

    Returns:
        SlackService: The global Slack service instance
    """
    global _slack_service
    if _slack_service is None:
        _slack_service = SlackService()
    return _slack_service
