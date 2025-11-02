# """
# Security validation module for Todoist project access.
# Ensures ONLY the Grocery project can be written to.
# """

# import logfire

# from prefect.variables import Variable


# class ProjectAccessDenied(Exception):
#     """
#     Exception raised when attempting to access a project other than Grocery.
#     This is a security-critical exception that indicates a violation of
#     the strict project access policy.
#     """

#     pass


# @logfire.instrument("validate_project_id")
# def validate_project_id(project_id: str) -> None:
#     """
#     Validate that the provided project ID matches the configured Grocery project ID.

#     This is a CRITICAL security check. The agent MUST ONLY write to the Grocery
#     project. Any attempt to write to a different project will raise an exception
#     and be logged as a security incident.

#     Args:
#         project_id: The project ID to validate

#     Raises:
#         ProjectAccessDenied: If project_id does not match the Grocery project ID
#     """
#     # config = get_config()
#     grocery_project_id = Variable.get("todoist_grocery_project_id")

#     if project_id != grocery_project_id:
#         # Log security incident
#         logfire.error(
#             "SECURITY: Attempted task creation in wrong project",
#             attempted_project_id=project_id,
#             allowed_project_id=grocery_project_id,
#             security_incident=True,
#         )

#         # Raise exception to block the operation
#         raise ProjectAccessDenied(
#             f"Task creation restricted to Grocery project only. "
#             f"Attempted project: {project_id}, Allowed project: {grocery_project_id}"
#         )

#     # Log successful validation
#     logfire.debug(
#         "Project ID validation passed",
#         project_id=project_id,
#     )


# @logfire.instrument("validate_and_audit_task_creation")
# def validate_and_audit_task_creation(
#     project_id: str,
#     task_content: str,
# ) -> None:
#     """
#     Validate project ID and audit task creation attempt.

#     This function performs validation and creates an audit trail of all
#     task creation attempts for security monitoring.

#     Args:
#         project_id: The project ID for the task
#         task_content: The content/title of the task

#     Raises:
#         ProjectAccessDenied: If project_id does not match the Grocery project ID
#     """
#     # First validate the project ID
#     validate_project_id(project_id)

#     # Log successful audit
#     logfire.info(
#         "Task creation validated and audited",
#         project_id=project_id,
#         task_content=task_content,
#         audit_trail=True,
#     )
