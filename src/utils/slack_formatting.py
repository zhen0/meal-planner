"""
Slack message formatting utilities.
Separates message formatting logic from Slack API communication.
"""

from ..models import MealPlan
from ..utils.ingredient_helpers import collect_unique_ingredient_names


def format_meal_plan_message(meal_plan: MealPlan) -> str:
    """
    Format meal plan as Slack message.

    Args:
        meal_plan: MealPlan object to format

    Returns:
        str: Formatted Slack message
    """
    lines = ["🍽️ *YOUR WEEKLY MEAL PLAN* (for approval)\n"]

    # Add each meal
    for i, meal in enumerate(meal_plan.meals, 1):
        lines.append(f"*Meal {i}: {meal.name}*")
        lines.append(
            f"Active: {meal.active_time_minutes} min | "
            f"Serves {meal.serves} | "
            f"Ingredients: {len(meal.ingredients)} items"
        )
        lines.append(f"_{meal.description}_\n")

    # Add shared ingredients info
    if meal_plan.shared_ingredients:
        lines.append(f"📊 *Shared Ingredients:* {len(meal_plan.shared_ingredients)} items")
        shared_names = [ing.name for ing in meal_plan.shared_ingredients[:3]]
        lines.append(f"_{', '.join(shared_names)}{'...' if len(meal_plan.shared_ingredients) > 3 else ''}_\n")

    # Add approval instructions
    lines.append("---")
    lines.append("*How to respond:*")
    lines.append("• Reply `approve` or `✓` to accept this plan")
    lines.append("• Reply `reject` or `✗` to reject")
    lines.append("• Reply `feedback: <your feedback>` to regenerate with changes")
    lines.append("  Example: `feedback: make it spicier` or `feedback: no tomatoes`")

    return "\n".join(lines)


def format_simple_grocery_list(meal_plan: MealPlan) -> str:
    """
    Format a simple grocery list for Slack with unique items only.

    Args:
        meal_plan: Approved MealPlan to extract grocery list from

    Returns:
        str: Formatted Slack message with grocery list
    """
    unique_items = collect_unique_ingredient_names(meal_plan)

    # Build simple list message
    lines = ["🛒 *GROCERY LIST*\n"]

    # Add items alphabetically
    for item in sorted(unique_items):
        lines.append(f"• {item}")

    lines.append(f"\n_Total: {len(unique_items)} items_")

    return "\n".join(lines)


def format_final_meal_plan(meal_plan: MealPlan) -> str:
    """
    Format final approved meal plan for Slack with full details.

    Args:
        meal_plan: Approved MealPlan to format

    Returns:
        str: Formatted Slack message with full meal plan details
    """
    lines = ["✅ *MEAL PLAN APPROVED*\n", "🍽️ *MEALS THIS WEEK*\n"]

    # Add each meal with full details
    for i, meal in enumerate(meal_plan.meals, 1):
        lines.append(f"*Meal {i}: {meal.name}*")
        lines.append(
            f"Serves {meal.serves} | "
            f"Active Time: {meal.active_time_minutes} min | "
            f"Inactive Time: {meal.inactive_time_minutes} min"
        )
        lines.append(f"{meal.description}\n")

        # Ingredients
        lines.append("*Ingredients:*")
        for ing in meal.ingredients:
            line = f"• {ing.name} - {ing.quantity} {ing.unit}"
            if ing.shopping_notes:
                line += f" ({ing.shopping_notes})"
            lines.append(line)

        # Instructions
        lines.append("\n*Instructions:*")
        for inst in meal.instructions:
            lines.append(f"{inst.step}. {inst.text}")

        lines.append("\n---\n")

    # Shared ingredients
    if meal_plan.shared_ingredients:
        lines.append(f"📋 *Shared Ingredients* ({len(meal_plan.shared_ingredients)} items)")
        for ing in meal_plan.shared_ingredients:
            line = f"• {ing.name} - {ing.quantity} {ing.unit}"
            if ing.shopping_notes:
                line += f" ({ing.shopping_notes})"
            lines.append(line)
        lines.append("")

    lines.append("✅ Ingredients added to Todoist Grocery project!")

    return "\n".join(lines)
