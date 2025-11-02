"""
MCP (Model Context Protocol) client wrapper.
Provides a cleaner abstraction for MCP server connections.
"""

import logfire
from prefect.blocks.system import Secret
from pydantic_ai.mcp import MCPServerStreamableHTTP

from ..config import get_config


class MCPClientManager:
    """
    Manages MCP server connections with centralized configuration.
    Provides a cleaner separation between connection management and business logic.
    """

    def __init__(self):
        """Initialize MCP client manager."""
        self._config = None
        self._todoist_client = None

    async def get_todoist_client(self) -> MCPServerStreamableHTTP:
        """
        Get or create Todoist MCP client (lazy initialization).

        Returns:
            MCPServerStreamableHTTP: Configured Todoist MCP client

        Raises:
            ValueError: If unable to load authentication token or connect to server
        """
        if self._todoist_client is not None:
            return self._todoist_client

        if self._config is None:
            self._config = get_config()

        # Load Todoist API token from Prefect secret block
        try:
            todoist_secret = await Secret.load("todoist-mcp-auth-token")
            todoist_token = todoist_secret.get()
            logfire.info("Loaded Todoist API token from secret block")
        except Exception as e:
            logfire.error("Failed to load todoist-mcp-auth-token secret", error=str(e))
            raise ValueError(f"Failed to load todoist-mcp-auth-token secret: {e}")

        try:
            # Connect to Todoist MCP server with authentication
            self._todoist_client = MCPServerStreamableHTTP(
                self._config.todoist_mcp_server_url,
                headers={"Authorization": f"Bearer {todoist_token}"},
            )
            logfire.info("Connected to Todoist MCP server", url=self._config.todoist_mcp_server_url)
            return self._todoist_client
        except Exception as e:
            logfire.error("Failed to connect to Todoist MCP server", error=str(e))
            raise ValueError(f"Failed to connect to Todoist MCP server: {e}")


# Global client manager instance (singleton pattern)
_mcp_manager = None


def get_mcp_manager() -> MCPClientManager:
    """
    Get the global MCP client manager instance (singleton pattern).

    Returns:
        MCPClientManager: The global MCP client manager instance
    """
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()
    return _mcp_manager
