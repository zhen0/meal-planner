"""
Security validation module for Todoist project access control.

This module provides strict security controls to ensure the agent only
writes to the designated Grocery project.
"""

import os
from typing import Optional

import logfire


class ProjectAccessDenied(Exception):
    """Exception raised when attempting to access a non-allowed project."""

    pass


def validate_project_id(project_id: Optional[str]) -> None:
    """
    Validate that the project ID matches the allowed Grocery project.

    This function implements strict security controls:
    1. Loads the allowed project ID from environment variable
    2. Compares the requested project ID against the allowed one
    3. Raises ProjectAccessDenied if validation fails
    4. Logs all validation attempts to Logfire with security flags

    Args:
        project_id: The project ID to validate

    Raises:
        ProjectAccessDenied: If project_id doesn't match the allowed Grocery project,
                           or if project_id is None or empty, or if the allowed
                           project ID is not configured

    Example:
        >>> validate_project_id("12345")  # Passes if TODOIST_GROCERY_PROJECT_ID=12345
        >>> validate_project_id("99999")  # Raises ProjectAccessDenied
    """
    # Get the allowed grocery project ID from environment
    allowed_project_id = os.getenv("TODOIST_GROCERY_PROJECT_ID")

    # Validate that the allowed project ID is configured
    if not allowed_project_id or not allowed_project_id.strip():
        logfire.error(
            "SECURITY: TODOIST_GROCERY_PROJECT_ID not configured",
            security_incident=True,
        )
        raise ProjectAccessDenied(
            "Grocery project ID not configured. "
            "Please set TODOIST_GROCERY_PROJECT_ID environment variable."
        )

    # Log the validation attempt
    logfire.info(
        "Validating project ID",
        requested_project_id=project_id,
        allowed_project_id=allowed_project_id,
    )

    # Handle None project ID
    if project_id is None:
        logfire.error(
            "SECURITY: Project ID is None",
            security_incident=True,
            allowed_project_id=allowed_project_id,
        )
        raise ProjectAccessDenied(
            f"Grocery project only. Project ID cannot be None. "
            f"Expected: {allowed_project_id}"
        )

    # Handle empty project ID
    if not project_id or not project_id.strip():
        logfire.error(
            "SECURITY: Empty project ID",
            security_incident=True,
            allowed_project_id=allowed_project_id,
        )
        raise ProjectAccessDenied(
            f"Grocery project only. Project ID cannot be empty. "
            f"Expected: {allowed_project_id}"
        )

    # Validate project ID matches allowed one
    if project_id != allowed_project_id:
        logfire.error(
            "SECURITY: Wrong project ID",
            security_incident=True,
            requested_project_id=project_id,
            allowed_project_id=allowed_project_id,
        )
        raise ProjectAccessDenied(
            f"Grocery project only. Access denied to project '{project_id}'. "
            f"Only allowed project: {allowed_project_id}"
        )

    # Success - log and return
    logfire.info(
        "Project ID validation successful",
        project_id=project_id,
    )
