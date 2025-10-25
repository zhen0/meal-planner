"""
Claude API integration for meal planning.
Handles dietary preference parsing and meal generation.
"""

import json
from typing import Optional

import logfire
from anthropic import Anthropic

from .config import get_config
from .models import DietaryPreferences, MealPlan


# Initialize Anthropic client
def _get_client() -> Anthropic:
    """Get configured Anthropic client."""
    config = get_config()
    return Anthropic(api_key=config.anthropic_api_key)


# System prompts
PREFERENCE_PARSER_PROMPT = """You are a dietary preference parser. Your job is to convert natural, everyday language dietary preferences into structured JSON format.

The user will provide dietary preferences in casual English. Your task is to extract and organize this information.

## EXTRACTION RULES
1. Identify dietary restrictions (vegetarian, vegan, gluten-free, dairy-free, nut-free, etc.)
2. Extract cuisine preferences if mentioned
3. Find specific ingredients to avoid
4. Identify preferred proteins or protein sources
5. Note cooking styles or meal type preferences
6. Extract any special notes or constraints

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown, no explanation):
{
  "dietary_restrictions": ["array of restrictions"],
  "cuisines": ["array of cuisines"],
  "avoid_ingredients": ["array of ingredients to avoid"],
  "protein_preferences": ["array of proteins"],
  "cooking_styles": ["array of cooking methods/meal types"],
  "max_cook_time_minutes": 20,
  "serves": 2,
  "special_notes": "any additional preferences or constraints"
}

## NOTES
- If a field is not mentioned, use empty array [] or reasonable default
- Be liberal in interpretation: "no mushrooms" and "mushroom-free" both map to avoid_ingredients
- Cooking styles: "quick salads", "stir-fries", "sheet pan meals", "one-pot", "no-cook", etc.
- Always include max_cook_time_minutes: 20 (this is the constraint for this agent)
- Always include serves: 2 (this is the constraint for this agent)
"""


MEAL_GENERATION_PROMPT = """You are a quick-cooking meal planner. Your role is to generate two healthy, delicious meals that take less than 20 minutes to cook, tailored to specific dietary preferences.

## CONSTRAINTS
- Each meal must take 15-20 minutes of active cooking time
- Recipes must use simple, accessible ingredients
- Minimize specialty equipment (knife, cutting board, 1-2 pots/pans max)
- Maximize ingredient overlap between the two meals to reduce shopping
- Each meal should serve 2 people
- Respect all dietary restrictions and preferences provided

## MEAL GENERATION RULES
1. Scan both meals and identify shared ingredients (garlic, oils, spices, vegetables)
2. Design meals so they naturally share 4-6 ingredients
3. Include shopping notes inline with ingredients (e.g., "organic", "pre-cut", "room temp")
4. Embed recipe tips directly in instructions (don't separate sections)
5. Ensure meals are different enough in flavor/texture (not just variations)
6. Prioritize vegetables and legumes; keep protein flexible based on preferences
7. If feedback is provided, regenerate with different cuisines/proteins while maintaining constraints

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown, no explanation):
{
  "meals": [
    {
      "name": "Meal Name",
      "description": "1-2 sentence description highlighting flavors and key ingredients",
      "serves": 2,
      "active_time_minutes": 18,
      "inactive_time_minutes": 2,
      "ingredients": [
        {
          "name": "ingredient",
          "quantity": "1",
          "unit": "medium",
          "shopping_notes": "organic, optional" or null
        }
      ],
      "instructions": [
        {
          "step": 1,
          "text": "Step text here. TIP: Additional context if helpful."
        }
      ]
    }
  ],
  "shared_ingredients": [
    {
      "name": "shared ingredient",
      "quantity": "total needed",
      "unit": "tsp",
      "shopping_notes": null
    }
  ]
}

## FEEDBACK HANDLING
If you receive feedback from the user (e.g., "don't like tomatoes", "make it spicier"), regenerate with:
- Different cuisines or flavor profiles
- Different proteins or ingredients (while respecting restrictions)
- Maintain simplicity and quick cook times
- Acknowledge feedback in the meal descriptions

## IMPORTANT
- Return ONLY JSON, no other text
- Ensure all JSON is valid and parseable
- Double-check ingredient quantities are realistic for 2 servings
- Make sure instructions are clear and numbered
"""


@logfire.instrument("parse_dietary_preferences")
async def parse_dietary_preferences(
    preferences_text: str,
) -> DietaryPreferences:
    """
    Parse natural language dietary preferences into structured format.

    Args:
        preferences_text: Natural language dietary preferences

    Returns:
        DietaryPreferences: Structured preferences object

    Raises:
        ValueError: If parsing fails or response is invalid
    """
    client = _get_client()

    logfire.info("Parsing dietary preferences", preferences_text=preferences_text)

    try:
        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=PREFERENCE_PARSER_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"USER PREFERENCES (raw text):\n{preferences_text}",
                }
            ],
        )

        # Extract response
        response_text = message.content[0].text
        logfire.debug("Claude response", response=response_text)

        # Parse JSON
        parsed_json = json.loads(response_text)

        # Validate and create DietaryPreferences object
        preferences = DietaryPreferences(**parsed_json)

        logfire.info(
            "Successfully parsed dietary preferences",
            dietary_restrictions=preferences.dietary_restrictions,
            cuisines=preferences.cuisines,
        )

        return preferences

    except json.JSONDecodeError as e:
        logfire.error("Failed to parse JSON from Claude response", error=str(e))
        raise ValueError(f"Failed to parse dietary preferences: Invalid JSON response") from e
    except Exception as e:
        logfire.error("Error parsing dietary preferences", error=str(e))
        raise ValueError(f"Failed to parse dietary preferences: {e}") from e


@logfire.instrument("generate_meal_plan")
async def generate_meal_plan(
    preferences: DietaryPreferences,
    feedback: Optional[str] = None,
) -> MealPlan:
    """
    Generate a meal plan based on dietary preferences.

    Args:
        preferences: Structured dietary preferences
        feedback: Optional feedback from previous rejection (for regeneration)

    Returns:
        MealPlan: Generated meal plan with 2 meals

    Raises:
        ValueError: If generation fails or response is invalid
    """
    client = _get_client()

    logfire.info(
        "Generating meal plan",
        preferences=preferences.model_dump(),
        feedback=feedback,
    )

    try:
        # Build user message
        user_message = f"USER PREFERENCES (parsed):\n{preferences.model_dump_json(indent=2)}"

        if feedback:
            user_message += f"\n\nUSER FEEDBACK (from previous rejection):\n{feedback}\n\nPlease regenerate the meal plan addressing this feedback."

        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=MEAL_GENERATION_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        )

        # Extract response
        response_text = message.content[0].text
        logfire.debug("Claude response", response=response_text)

        # Parse JSON
        parsed_json = json.loads(response_text)

        # Validate and create MealPlan object
        meal_plan = MealPlan(**parsed_json)

        logfire.info(
            "Successfully generated meal plan",
            num_meals=len(meal_plan.meals),
            meal_names=[m.name for m in meal_plan.meals],
            shared_ingredients_count=len(meal_plan.shared_ingredients),
        )

        return meal_plan

    except json.JSONDecodeError as e:
        logfire.error("Failed to parse JSON from Claude response", error=str(e))
        raise ValueError(f"Failed to generate meal plan: Invalid JSON response") from e
    except Exception as e:
        logfire.error("Error generating meal plan", error=str(e))
        raise ValueError(f"Failed to generate meal plan: {e}") from e
