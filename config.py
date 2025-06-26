"""
Email Game Configuration

This module contains all configuration settings, constants, and mappings
for the Email Writing Game application.
"""

# Game Configuration
LEVEL_TO_SCENARIO_MAPPING = {
    1: 3,  # User Level 1 maps to Backend Scenario 3
    2: 4,  # User Level 2 maps to Backend Scenario 4
    # 3: 2,  # User Level 3 maps to Backend Scenario 2
    # Add more levels here: 4: 1, 5: 5, etc.
}
MAX_AVAILABLE_LEVEL = max(LEVEL_TO_SCENARIO_MAPPING.keys())

# File Paths
SCENARIOS_FOLDER = "prompts/scenarios"
RECIPIENTS_FOLDER = "prompts/recipients"
RUBRICS_FOLDER = "rubrics"
EVALUATION_PROMPT_PATH = "prompts/evaluation/default.txt"
RUBRIC_GENERATION_PROMPT_PATH = "prompts/rubric_generation/default.txt"

# API Configuration
API_KEY_ENV_VAR = "OPENAI_API_KEY_CLAB"
DEFAULT_MODEL = "gpt-4o"
MODELS = ["gpt-4o", "gpt-4", "gpt-3.5-turbo"]

# UI Configuration
EMAIL_MAX_CHARS = 3000
SCENARIO_MAX_CHARS = 5000
SCENARIO_TEXT_AREA_HEIGHT = 350
EMAIL_TEXT_AREA_HEIGHT = 400
EVALUATION_TEXT_AREA_HEIGHT = 300

# Default Content
DEFAULT_SCENARIO = """You are coordinating a weekend trip to a national park with 5 friends. You need to organize transportation, accommodation, and activities. Some friends prefer camping while others want a hotel. The trip is in 3 weeks and you need everyone to confirm their participation and preferences by Friday."""

DEFAULT_RECIPIENT_PROMPT = "You are the recipient of an email. Please respond naturally and appropriately to the email you receive."

DEFAULT_EVALUATION_TEMPLATE = """
Please evaluate the email based on the rubric provided:

Scenario: {scenario}
Rubric: {rubric}
Email: {email}

Your evaluation:
"""

DEFAULT_RUBRIC_TEMPLATE = """I'm creating an AI-driven game where the player attempts to write emails to negotiate an outcome in a scenario. Can you look at the scenario and come up with a rubric to grade the email? The last item, on whether the email successfully achieves the goal, must always be included and worth 10 points.

Ready? Here's the scenario:

{scenario}

Rubric:""" 