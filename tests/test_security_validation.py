"""Unit tests for security_validation module."""

import pytest

from src.security_validation import ProjectAccessDenied, validate_project_id


def test_validate_project_id_success(monkeypatch):
    """Test successful project ID validation."""
    # Mock config to return specific project ID
    monkeypatch.setenv("TODOIST_GROCERY_PROJECT_ID", "12345")

    # Should not raise exception
    validate_project_id("12345")


def test_validate_project_id_failure(monkeypatch):
    """Test project ID validation failure."""
    # Mock config to return specific project ID
    monkeypatch.setenv("TODOIST_GROCERY_PROJECT_ID", "12345")

    # Should raise ProjectAccessDenied
    with pytest.raises(ProjectAccessDenied) as exc_info:
        validate_project_id("99999")

    assert "Grocery project only" in str(exc_info.value)
    assert "12345" in str(exc_info.value)


def test_validate_project_id_empty(monkeypatch):
    """Test validation with empty project ID."""
    monkeypatch.setenv("TODOIST_GROCERY_PROJECT_ID", "12345")

    with pytest.raises(ProjectAccessDenied):
        validate_project_id("")


def test_validate_project_id_none(monkeypatch):
    """Test validation with None project ID."""
    monkeypatch.setenv("TODOIST_GROCERY_PROJECT_ID", "12345")

    with pytest.raises((ProjectAccessDenied, TypeError)):
        validate_project_id(None)
