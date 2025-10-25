"""
Configuration module for Meal Planner Agent.
Loads and validates all environment variables.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


# Load environment variables from .env file
load_dotenv()


class Config(BaseModel):
    """
    Application configuration loaded from environment variables.
    All sensitive data and configuration is managed through env vars.
    """

    # Dietary Preferences
    dietary_preferences: str = Field(
        default="I like quick, healthy meals under 20 minutes.",
        description="Natural language dietary preferences",
    )

    # Anthropic / Claude
    anthropic_api_key: str = Field(..., description="Anthropic API key")

    # Slack
    slack_bot_token: str = Field(..., description="Slack bot token (xoxb-...)")
    slack_channel_id: str = Field(..., description="Slack channel ID for posting meals")
    slack_signing_secret: Optional[str] = Field(
        default=None, description="Slack app signing secret (optional)"
    )

    # Todoist MCP - GROCERY PROJECT ONLY
    todoist_grocery_project_id: str = Field(
        ..., description="Todoist Grocery project ID (ONLY this project will be written to)"
    )
    todoist_mcp_server_url: str = Field(..., description="Hosted MCP server URL")
    todoist_mcp_auth_token: Optional[str] = Field(
        default=None, description="MCP authentication token (if required)"
    )

    # Prefect Cloud
    prefect_api_key: str = Field(..., description="Prefect Cloud API key")
    prefect_api_url: str = Field(..., description="Prefect Cloud API URL")
    prefect_flow_name: str = Field(
        default="weekly-meal-planner", description="Prefect flow name"
    )
    prefect_work_pool_name: str = Field(
        default="managed-execution", description="Prefect work pool name"
    )

    # Logfire
    logfire_token: str = Field(..., description="Logfire authentication token")
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
        default=3, description="Maximum meal regeneration attempts"
    )

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_anthropic_key(cls, v: str) -> str:
        """Validate Anthropic API key format."""
        if not v.startswith("sk-ant-"):
            raise ValueError("Anthropic API key must start with 'sk-ant-'")
        return v

    @field_validator("slack_bot_token")
    @classmethod
    def validate_slack_token(cls, v: str) -> str:
        """Validate Slack bot token format."""
        if not v.startswith("xoxb-"):
            raise ValueError("Slack bot token must start with 'xoxb-'")
        return v

    @field_validator("slack_channel_id")
    @classmethod
    def validate_slack_channel(cls, v: str) -> str:
        """Validate Slack channel ID format."""
        if not v.startswith("C"):
            raise ValueError("Slack channel ID must start with 'C'")
        return v

    @field_validator("prefect_api_key")
    @classmethod
    def validate_prefect_key(cls, v: str) -> str:
        """Validate Prefect API key format."""
        if not v.startswith("pnu_"):
            raise ValueError("Prefect API key must start with 'pnu_'")
        return v

    @field_validator("todoist_grocery_project_id")
    @classmethod
    def validate_todoist_project_id(cls, v: str) -> str:
        """Validate Todoist project ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Todoist Grocery project ID cannot be empty")
        return v.strip()

    @field_validator("approval_timeout_seconds", "slack_poll_interval_seconds", "max_regeneration_attempts")
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate positive integer values."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    class Config:
        """Pydantic configuration."""

        env_prefix = ""
        case_sensitive = False


def load_config() -> Config:
    """
    Load and validate configuration from environment variables.

    Returns:
        Config: Validated configuration object

    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    try:
        config = Config(
            dietary_preferences=os.getenv("DIETARY_PREFERENCES", "I like quick, healthy meals under 20 minutes."),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
            slack_channel_id=os.getenv("SLACK_CHANNEL_ID", ""),
            slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
            todoist_grocery_project_id=os.getenv("TODOIST_GROCERY_PROJECT_ID", ""),
            todoist_mcp_server_url=os.getenv("TODOIST_MCP_SERVER_URL", ""),
            todoist_mcp_auth_token=os.getenv("TODOIST_MCP_AUTH_TOKEN"),
            prefect_api_key=os.getenv("PREFECT_API_KEY", ""),
            prefect_api_url=os.getenv("PREFECT_API_URL", ""),
            prefect_flow_name=os.getenv("PREFECT_FLOW_NAME", "weekly-meal-planner"),
            prefect_work_pool_name=os.getenv("PREFECT_WORK_POOL_NAME", "managed-execution"),
            logfire_token=os.getenv("LOGFIRE_TOKEN", ""),
            logfire_project_name=os.getenv("LOGFIRE_PROJECT_NAME", "meal-planner-agent"),
            approval_timeout_seconds=int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "86400")),
            slack_poll_interval_seconds=int(os.getenv("SLACK_POLL_INTERVAL_SECONDS", "30")),
            max_regeneration_attempts=int(os.getenv("MAX_REGENERATION_ATTEMPTS", "3")),
        )
        return config
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}") from e


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance (singleton pattern).

    Returns:
        Config: The global configuration object
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config
