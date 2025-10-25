"""
Data models for Meal Planner Agent.
Includes ApprovalInput (RunInput subclass) for pause/resume flow.
"""

from typing import List, Optional

from prefect.input import RunInput
from pydantic import BaseModel, Field


class ApprovalInput(RunInput):
    """
    Input model for meal plan approval flow.
    Used with pause_flow_run(wait_for_input=ApprovalInput).

    When a user responds in Slack, the bot will resume the paused flow
    with an instance of this model containing the approval decision.
    """

    approved: bool = Field(
        ...,
        description="Whether the meal plan was approved (True) or rejected (False)",
    )

    feedback: Optional[str] = Field(
        default=None,
        description="Optional feedback from user for meal regeneration (e.g., 'make it spicier', 'no tomatoes')",
    )

    regenerate: bool = Field(
        default=False,
        description="Whether to regenerate the meal plan with feedback",
    )


class DietaryPreferences(BaseModel):
    """
    Structured dietary preferences parsed from natural language.
    """

    dietary_restrictions: List[str] = Field(
        default_factory=list,
        description="List of dietary restrictions (vegetarian, vegan, gluten-free, etc.)",
    )

    cuisines: List[str] = Field(
        default_factory=list,
        description="Preferred cuisine types (Mediterranean, Asian, etc.)",
    )

    avoid_ingredients: List[str] = Field(
        default_factory=list,
        description="Specific ingredients to avoid",
    )

    protein_preferences: List[str] = Field(
        default_factory=list,
        description="Preferred protein sources",
    )

    cooking_styles: List[str] = Field(
        default_factory=list,
        description="Preferred cooking methods or meal types",
    )

    max_cook_time_minutes: int = Field(
        default=20,
        description="Maximum cook time in minutes",
    )

    serves: int = Field(
        default=2,
        description="Number of servings per meal",
    )

    special_notes: str = Field(
        default="",
        description="Any additional preferences or constraints",
    )


class Ingredient(BaseModel):
    """Single ingredient with quantity and shopping notes."""

    name: str = Field(..., description="Ingredient name")
    quantity: str = Field(..., description="Quantity as string (e.g., '2', '1/2 cup')")
    unit: str = Field(..., description="Unit of measurement")
    shopping_notes: Optional[str] = Field(
        default=None,
        description="Optional shopping notes (e.g., 'organic', 'pre-cut')",
    )


class InstructionStep(BaseModel):
    """Single cooking instruction step."""

    step: int = Field(..., description="Step number")
    text: str = Field(..., description="Step instruction text")


class Meal(BaseModel):
    """Single meal with ingredients and instructions."""

    name: str = Field(..., description="Meal name")
    description: str = Field(..., description="Brief meal description")
    serves: int = Field(..., description="Number of servings")
    active_time_minutes: int = Field(..., description="Active cooking time in minutes")
    inactive_time_minutes: int = Field(
        default=0, description="Inactive time (resting, baking, etc.)"
    )
    ingredients: List[Ingredient] = Field(..., description="List of ingredients")
    instructions: List[InstructionStep] = Field(..., description="Cooking instructions")


class MealPlan(BaseModel):
    """Complete meal plan with multiple meals and shared ingredients."""

    meals: List[Meal] = Field(..., description="List of meals in the plan")
    shared_ingredients: List[Ingredient] = Field(
        default_factory=list,
        description="Ingredients shared across multiple meals",
    )


class TodoistTask(BaseModel):
    """Todoist task to be created via MCP."""

    content: str = Field(..., description="Task content/title")
    project_id: str = Field(..., description="Todoist project ID (must be Grocery project)")
    labels: List[str] = Field(default_factory=list, description="Task labels")
    due_string: Optional[str] = Field(
        default=None,
        description="Natural language due date (e.g., 'tomorrow', 'Sunday')",
    )
