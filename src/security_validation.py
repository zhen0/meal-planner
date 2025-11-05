"""
Security validation for Todoist project access.
Ensures tasks are only created in the designated Grocery project.
"""

import logfire

from .config import get_config


class ProjectAccessDenied(Exception):
    """
    Raised when attempting to access a project other than the Grocery project.
    This is a security exception that should never be caught and ignored.
    """

    pass


def validate_project_id(project_id: str) -> None:
    """
    Validate that the project ID matches the configured Grocery project ID.

    This is a critical security validation that ensures tasks are only created
    in the designated Grocery project. If validation fails, a ProjectAccessDenied
    exception is raised and logged as a security incident.

    Args:
        project_id: The project ID to validate

    Raises:
        ProjectAccessDenied: If project ID does not match the Grocery project ID
        TypeError: If project_id is None

    Example:
        >>> validate_project_id("12345")  # Passes if config has "12345"
        >>> validate_project_id("99999")  # Raises ProjectAccessDenied
    """
    config = get_config()
    allowed_project_id = config.todoist_grocery_project_id

    # Log validation attempt
    logfire.info(
        "Validating project ID",
        project_id=project_id,
        allowed_project_id=allowed_project_id,
    )

    if project_id != allowed_project_id:
        # Log security incident
        logfire.error(
            "SECURITY: Project ID validation failed - attempted access to wrong project",
            security_incident=True,
            attempted_project_id=project_id,
            allowed_project_id=allowed_project_id,
        )

        raise ProjectAccessDenied(
            f"Access denied: Tasks can only be created in Grocery project only. "
            f"Attempted: {project_id}, Allowed: {allowed_project_id}"
        )

    logfire.info("Project ID validation successful", project_id=project_id)
