"""
Configuration module for Meal Planner Agent.
Loads configuration from Prefect secrets and variables for production,
with fallback to environment variables for local development.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

try:
    from prefect.blocks.system import Secret, String
    PREFECT_AVAILABLE = True
except ImportError:
    PREFECT_AVAILABLE = False


# Load environment variables from .env file (for local development)
load_dotenv()


def get_secret(name: str, default: str = "") -> str:
    """
    Get value from Prefect Secret block or fallback to environment variable.

    Prefect Secrets are used for sensitive data (API keys, tokens).
    In production (Prefect Cloud), use: prefect block register
    For local dev, uses environment variables.

    Args:
        name: Secret/env var name (lowercase with hyphens for Prefect, uppercase with underscores for env)
        default: Default value if not found

    Returns:
        Secret value
    """
    if PREFECT_AVAILABLE:
        try:
            # Try to load from Prefect Secret block
            # Convert ANTHROPIC_API_KEY -> anthropic-api-key
            block_name = name.lower().replace("_", "-")
            secret = Secret.load(block_name)
            return secret.get()
        except Exception:
            # Fall back to environment variable
            pass

    return os.getenv(name, default)


def get_variable(name: str, default: str = "") -> str:
    """
    Get value from Prefect Variable or fallback to environment variable.

    Prefect Variables are used for non-sensitive configuration (IDs, URLs).
    In production (Prefect Cloud), use: prefect variable set NAME value
    For local dev, uses environment variables.

    Args:
        name: Variable/env var name (lowercase with hyphens for Prefect, uppercase with underscores for env)
        default: Default value if not found

    Returns:
        Variable value
    """
    if PREFECT_AVAILABLE:
        try:
            from prefect import variables
            # Convert SLACK_CHANNEL_ID -> slack-channel-id
            var_name = name.lower().replace("_", "-")
            value = variables.get(var_name)
            if value is not None:
                return value
        except Exception:
            # Fall back to environment variable
            pass

    return os.getenv(name, default)


class Config(BaseModel):
    """
    Application configuration loaded from environment variables.
    All sensitive data and configuration is managed through env vars.
    """

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
    # Note: API key and URL are automatically handled by Prefect when running on Prefect Cloud
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
    Load and validate configuration from Prefect secrets/variables or environment variables.

    Configuration priority:
    1. Prefect Secrets (for API keys/tokens) - in production
    2. Prefect Variables (for IDs/URLs) - in production
    3. Environment variables - for local development

    Returns:
        Config: Validated configuration object

    Raises:
        ValueError: If required configuration is missing or invalid
    """
    try:
        config = Config(
            # Secrets (sensitive data)
            anthropic_api_key=get_secret("ANTHROPIC_API_KEY", ""),
            slack_bot_token=get_secret("SLACK_BOT_TOKEN", ""),
            slack_signing_secret=get_secret("SLACK_SIGNING_SECRET") or None,
            todoist_mcp_auth_token=get_secret("TODOIST_MCP_AUTH_TOKEN") or None,
            logfire_token=get_secret("LOGFIRE_TOKEN", ""),

            # Variables (non-sensitive configuration)
            slack_channel_id=get_variable("SLACK_CHANNEL_ID", ""),
            todoist_grocery_project_id=get_variable("TODOIST_GROCERY_PROJECT_ID", ""),
            todoist_mcp_server_url=get_variable("TODOIST_MCP_SERVER_URL", ""),
            prefect_flow_name=get_variable("PREFECT_FLOW_NAME", "weekly-meal-planner"),
            prefect_work_pool_name=get_variable("PREFECT_WORK_POOL_NAME", "managed-execution"),
            logfire_project_name=get_variable("LOGFIRE_PROJECT_NAME", "meal-planner-agent"),
            approval_timeout_seconds=int(get_variable("APPROVAL_TIMEOUT_SECONDS", "86400")),
            slack_poll_interval_seconds=int(get_variable("SLACK_POLL_INTERVAL_SECONDS", "30")),
            max_regeneration_attempts=int(get_variable("MAX_REGENERATION_ATTEMPTS", "3")),
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
