"""
Prefect artifact creation service.
Handles creation of UI artifacts for meal plans and grocery lists.
"""

from prefect.artifacts import create_markdown_artifact, create_table_artifact

from ..models import MealPlan
from ..utils.ingredient_helpers import collect_unique_ingredient_names


def create_meal_plan_artifact(meal_plan: MealPlan, feedback: str | None = None) -> None:
    """
    Create a Markdown artifact showing the meal plan in the Prefect UI.

    Args:
        meal_plan: The generated meal plan
        feedback: Optional feedback that was provided for regeneration
    """
    markdown = "# Weekly Meal Plan\n\n"

    if feedback:
        markdown += f"_Generated with feedback: {feedback}_\n\n"

    # Add meals
    for i, meal in enumerate(meal_plan.meals, 1):
        markdown += f"## Meal {i}: {meal.name}\n\n"
        markdown += f"**Description:** {meal.description}\n\n"
        markdown += "**Details:**\n"
        markdown += f"- Serves: {meal.serves}\n"
        markdown += f"- Active time: {meal.active_time_minutes} minutes\n"
        if meal.inactive_time_minutes > 0:
            markdown += f"- Inactive time: {meal.inactive_time_minutes} minutes\n"
        markdown += f"- Ingredients: {len(meal.ingredients)} items\n\n"

        # Ingredients
        markdown += "**Ingredients:**\n"
        for ingredient in meal.ingredients:
            notes = f" ({ingredient.shopping_notes})" if ingredient.shopping_notes else ""
            markdown += f"- {ingredient.quantity} {ingredient.unit} {ingredient.name}{notes}\n"
        markdown += "\n"

        # Instructions
        markdown += "**Instructions:**\n"
        for instruction in meal.instructions:
            markdown += f"{instruction.step}. {instruction.text}\n"
        markdown += "\n---\n\n"

    # Shared ingredients
    if meal_plan.shared_ingredients:
        markdown += f"## Shared Ingredients ({len(meal_plan.shared_ingredients)} items)\n\n"
        for ingredient in meal_plan.shared_ingredients:
            notes = f" ({ingredient.shopping_notes})" if ingredient.shopping_notes else ""
            markdown += f"- {ingredient.quantity} {ingredient.unit} {ingredient.name}{notes}\n"

    create_markdown_artifact(
        key="weekly-meal-plan",
        markdown=markdown,
        description="Generated meal plan with recipes and ingredients",
    )


def create_grocery_list_artifact(meal_plan: MealPlan, created_tasks: list[dict]) -> None:
    """
    Create table and markdown artifacts showing the grocery list in the Prefect UI.

    Args:
        meal_plan: The approved meal plan
        created_tasks: List of created Todoist tasks
    """
    # Create a table artifact for quick scanning
    table_data = []

    # Add all ingredients from all meals
    for meal in meal_plan.meals:
        for ingredient in meal.ingredients:
            table_data.append({
                "Item": ingredient.name,
                "Quantity": ingredient.quantity,
                "Unit": ingredient.unit,
                "Notes": ingredient.shopping_notes or "",
                "Meal": meal.name,
            })

    # Add shared ingredients
    for ingredient in meal_plan.shared_ingredients:
        table_data.append({
            "Item": ingredient.name,
            "Quantity": ingredient.quantity,
            "Unit": ingredient.unit,
            "Notes": ingredient.shopping_notes or "",
            "Meal": "Shared",
        })

    create_table_artifact(
        key="grocery-shopping-list",
        table=table_data,
        description=f"Grocery list with {len(table_data)} items for {len(meal_plan.meals)} meals",
    )

    # Create a markdown artifact with task creation details
    markdown = "# Grocery Tasks Created\n\n"
    markdown += f"**Total tasks created:** {len(created_tasks)}\n\n"
    markdown += f"**Meals:** {', '.join(meal.name for meal in meal_plan.meals)}\n\n"
    markdown += "## Task Details\n\n"

    for i, task in enumerate(created_tasks, 1):
        task_content = task.get("content", "Unknown task")
        markdown += f"{i}. {task_content}\n"

    create_markdown_artifact(
        key="grocery-tasks-created",
        markdown=markdown,
        description=f"Created {len(created_tasks)} grocery tasks in Todoist",
    )

    # Create a simple plain list artifact with unique items only
    unique_items = collect_unique_ingredient_names(meal_plan)

    # Create plain markdown list (sorted alphabetically)
    simple_list = "\n".join(sorted(unique_items))

    create_markdown_artifact(
        key="grocery-simple-list",
        markdown=simple_list,
        description=f"Simple list of {len(unique_items)} unique grocery items",
    )
