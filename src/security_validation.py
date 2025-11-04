"""
Security validation module for Todoist project access control.
Ensures tasks are only created in the designated Grocery project.
"""

import os
from typing import Optional

import logfire
from prefect import variables


class ProjectAccessDenied(Exception):
    """
    Exception raised when attempting to access a non-Grocery project.
    
    This is a critical security control to prevent the agent from
    modifying or accessing projects other than the designated Grocery project.
    """
    
    pass


def validate_project_id(project_id: Optional[str]) -> None:
    """
    Validate that the project ID matches the configured Grocery project ID.
    
    This is a critical security check that MUST be called before any
    Todoist task creation operation. It ensures the agent can only
    write to the designated Grocery project.
    
    Args:
        project_id: The project ID to validate
        
    Raises:
        ProjectAccessDenied: If the project ID doesn't match the Grocery project ID
        TypeError: If project_id is None
        
    Example:
        >>> validate_project_id("12345")  # If TODOIST_GROCERY_PROJECT_ID=12345
        >>> validate_project_id("99999")  # Raises ProjectAccessDenied
    """
    # Get the allowed Grocery project ID from environment or Prefect variable
    allowed_project_id = os.getenv("TODOIST_GROCERY_PROJECT_ID")
    
    if not allowed_project_id:
        logfire.error("SECURITY: Grocery project ID not configured", security_incident=True)
        raise ValueError("TODOIST_GROCERY_PROJECT_ID environment variable is not set")
    
    # Check for None
    if project_id is None:
        logfire.error(
            "SECURITY: Attempted to validate None project ID",
            security_incident=True,
            allowed_project_id=allowed_project_id,
        )
        raise TypeError("project_id cannot be None")
    
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
    
    # Main validation: project_id must match the Grocery project ID
    if project_id != allowed_project_id:
        logfire.error(
            "SECURITY: Wrong project ID detected",
            security_incident=True,
            attempted_project_id=project_id,
            allowed_project_id=allowed_project_id,
        )
        raise ProjectAccessDenied(
            f"Access denied. Only the Grocery project (ID: {allowed_project_id}) is allowed. "
            f"Attempted project ID: {project_id}"
        )
    
    # Success - log for audit trail
    logfire.info(
        "Security validation passed",
        project_id=project_id,
        security_check="project_id_validation",
    )


async def validate_project_id_async(project_id: Optional[str]) -> None:
    """
    Async version of validate_project_id for use in async contexts.
    
    Loads the allowed project ID from Prefect variables (async).
    Falls back to environment variable if Prefect variable is not available.
    
    Args:
        project_id: The project ID to validate
        
    Raises:
        ProjectAccessDenied: If the project ID doesn't match the Grocery project ID
        TypeError: If project_id is None
    """
    # Try to get from Prefect variables first (for production)
    try:
        allowed_project_id = await variables.get("todoist-grocery-project-id", default=None)
    except Exception:
        allowed_project_id = None
    
    # Fallback to environment variable
    if not allowed_project_id:
        allowed_project_id = os.getenv("TODOIST_GROCERY_PROJECT_ID")
    
    if not allowed_project_id:
        logfire.error("SECURITY: Grocery project ID not configured", security_incident=True)
        raise ValueError(
            "Grocery project ID not configured. "
            "Set TODOIST_GROCERY_PROJECT_ID environment variable or todoist-grocery-project-id Prefect variable."
        )
    
    # Check for None
    if project_id is None:
        logfire.error(
            "SECURITY: Attempted to validate None project ID",
            security_incident=True,
            allowed_project_id=allowed_project_id,
        )
        raise TypeError("project_id cannot be None")
    
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
    
    # Main validation: project_id must match the Grocery project ID
    if project_id != allowed_project_id:
        logfire.error(
            "SECURITY: Wrong project ID detected",
            security_incident=True,
            attempted_project_id=project_id,
            allowed_project_id=allowed_project_id,
        )
        raise ProjectAccessDenied(
            f"Access denied. Only the Grocery project (ID: {allowed_project_id}) is allowed. "
            f"Attempted project ID: {project_id}"
        )
    
    # Success - log for audit trail
    logfire.info(
        "Security validation passed",
        project_id=project_id,
        security_check="project_id_validation",
    )
