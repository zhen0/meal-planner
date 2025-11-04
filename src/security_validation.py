"""
Security validation for Todoist project access.
Ensures ONLY the Grocery project can be written to.
"""

import os

import logfire


class ProjectAccessDenied(Exception):
    """
    Exception raised when attempting to access a project other than the Grocery project.
    This is a security control to ensure the agent only writes to the designated project.
    """

    pass


def validate_project_id(project_id: str | None) -> None:
    """
    Validate that the project ID matches the configured Grocery project.

    This is a CRITICAL security control. The agent must ONLY write to the
    designated Grocery project. Any attempt to write to a different project
    should be blocked immediately.

    Args:
        project_id: The project ID to validate

    Raises:
        ProjectAccessDenied: If project_id does not match the Grocery project ID,
            is None, or is empty
        ValueError: If TODOIST_GROCERY_PROJECT_ID is not configured

    Example:
        >>> validate_project_id("12345")  # OK if TODOIST_GROCERY_PROJECT_ID=12345
        >>> validate_project_id("99999")  # Raises ProjectAccessDenied
    """
    # Get the allowed Grocery project ID from environment
    allowed_project_id = os.environ.get("TODOIST_GROCERY_PROJECT_ID")

    if not allowed_project_id:
        logfire.error(
            "SECURITY: Grocery project ID not configured",
            security_incident=True,
        )
        raise ValueError(
            "TODOIST_GROCERY_PROJECT_ID environment variable is not set. "
            "Cannot validate project access without configured Grocery project ID."
        )

    # Check for None
    if project_id is None:
        logfire.error(
            "SECURITY: Attempted to validate None project ID",
            security_incident=True,
            allowed_project_id=allowed_project_id,
        )
        raise ProjectAccessDenied(
            f"Project ID cannot be None. Grocery project only (ID: {allowed_project_id})"
        )

    # Check for empty string
    if not project_id or not project_id.strip():
        logfire.error(
            "SECURITY: Attempted to validate empty project ID",
            security_incident=True,
            allowed_project_id=allowed_project_id,
        )
        raise ProjectAccessDenied(
            f"Project ID cannot be empty. Grocery project only (ID: {allowed_project_id})"
        )

    # Check if project ID matches the Grocery project
    if project_id != allowed_project_id:
        logfire.error(
            "SECURITY: Wrong project ID attempted",
            security_incident=True,
            attempted_project_id=project_id,
            allowed_project_id=allowed_project_id,
        )
        raise ProjectAccessDenied(
            f"Grocery project only. Access denied. "
            f"Attempted: {project_id}, Allowed: {allowed_project_id}"
        )

    # Validation passed
    logfire.info(
        "Project ID validation successful",
        project_id=project_id,
    )
