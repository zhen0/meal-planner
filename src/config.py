"""
Configuration management for Meal Planner Agent.
Loads configuration from Prefect secrets/variables or environment variables.
"""

import os
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration model for Meal Planner Agent."""

    # Anthropic / Claude
    anthropic_api_key: str = Field(..., description="Anthropic API key")

    # Slack Integration
    slack_bot_token: str = Field(..., description="Slack bot OAuth token")
    slack_channel_id: str = Field(..., description="Slack channel ID")
    slack_signing_secret: Optional[str] = Field(
        default=None, description="Slack app signing secret for webhook validation"
    )

    # Todoist MCP Server
    todoist_grocery_project_id: str = Field(
        ..., description="Todoist Grocery project ID (only project allowed)"
    )
    todoist_mcp_server_url: str = Field(..., description="Hosted MCP server URL")
    todoist_mcp_auth_token: Optional[str] = Field(
        default=None, description="MCP authentication token"
    )

    # Prefect Cloud
    prefect_api_key: Optional[str] = Field(
        default=None, description="Prefect API key (optional for managed execution)"
    )
    prefect_api_url: Optional[str] = Field(
        default=None, description="Prefect API URL (optional for managed execution)"
    )
    prefect_flow_name: str = Field(
        default="weekly-meal-planner", description="Prefect flow name"
    )
    prefect_work_pool_name: str = Field(
        default="managed-execution", description="Prefect work pool name"
    )

    # Logfire Observability
    logfire_token: Optional[str] = Field(
        default=None, description="Logfire API token"
    )
    logfire_project_name: str = Field(
        default="meal-planner-agent", description="Logfire project name"
    )

    # Flow Configuration
    approval_timeout_seconds: int = Field(
        default=86400, description="Approval timeout in seconds (default 24 hours)"
    )
    slack_poll_interval_seconds: int = Field(
        default=30, description="Slack thread poll interval in seconds"
    )
    max_regeneration_attempts: int = Field(
        default=3, description="Maximum regeneration attempts"
    )

    # Dietary Preferences
    dietary_preferences: str = Field(
        default="I like quick, healthy meals under 20 minutes for 3 people including one child.",
        description="Default dietary preferences",
    )


def get_config() -> Config:
    """
    Load configuration from environment variables.

    In production, Prefect secrets and variables should be used.
    For local development, environment variables from .env file are used.

    Returns:
        Config: Configuration object

    Raises:
        ValueError: If required configuration is missing
    """
    return Config(
        # Anthropic / Claude
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        # Slack Integration
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        slack_channel_id=os.getenv("SLACK_CHANNEL_ID", ""),
        slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
        # Todoist MCP Server
        todoist_grocery_project_id=os.getenv("TODOIST_GROCERY_PROJECT_ID", ""),
        todoist_mcp_server_url=os.getenv("TODOIST_MCP_SERVER_URL", ""),
        todoist_mcp_auth_token=os.getenv("TODOIST_MCP_AUTH_TOKEN"),
        # Prefect Cloud
        prefect_api_key=os.getenv("PREFECT_API_KEY"),
        prefect_api_url=os.getenv("PREFECT_API_URL"),
        prefect_flow_name=os.getenv("PREFECT_FLOW_NAME", "weekly-meal-planner"),
        prefect_work_pool_name=os.getenv(
            "PREFECT_WORK_POOL_NAME", "managed-execution"
        ),
        # Logfire Observability
        logfire_token=os.getenv("LOGFIRE_TOKEN"),
        logfire_project_name=os.getenv("LOGFIRE_PROJECT_NAME", "meal-planner-agent"),
        # Flow Configuration
        approval_timeout_seconds=int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "86400")),
        slack_poll_interval_seconds=int(
            os.getenv("SLACK_POLL_INTERVAL_SECONDS", "30")
        ),
        max_regeneration_attempts=int(os.getenv("MAX_REGENERATION_ATTEMPTS", "3")),
        # Dietary Preferences
        dietary_preferences=os.getenv(
            "DIETARY_PREFERENCES",
            "I like quick, healthy meals under 20 minutes for 3 people including one child.",
        ),
    )
