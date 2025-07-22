"""
Utility Functions

This module contains helper functions for file operations, text processing,
and other utility functions used throughout the Email Writing Game.
"""

import streamlit as st
import os
import glob
import re
from typing import Dict
from config import (
    SCENARIOS_FOLDER,
    RECIPIENTS_FOLDER,
    RUBRICS_FOLDER,
    DEFAULT_RECIPIENT_PROMPT,
    DEFAULT_USE_RUBRIC
)


def get_script_directory() -> str:
    """Get the directory where the current script is located."""
    return os.path.dirname(os.path.abspath(__file__))


def load_file_content(relative_path: str, fallback_content: str = "") -> str:
    """
    Load content from a file relative to the script directory.
    
    Args:
        relative_path: Path relative to the script directory
        fallback_content: Content to return if file cannot be loaded
        
    Returns:
        File content or fallback content
    """
    try:
        script_dir = get_script_directory()
        file_path = os.path.join(script_dir, relative_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError) as e:
        if fallback_content:
            return fallback_content
        else:
            st.error(f"Error loading file {relative_path}: {str(e)}")
            return ""


def load_scenarios_from_folder(folder_path: str = SCENARIOS_FOLDER) -> Dict[str, Dict[str, str]]:
    """Load all scenario files from the specified folder"""
    scenarios = {}
    
    # Adjust path relative to current working directory
    if not os.path.isabs(folder_path):
        script_dir = get_script_directory()
        folder_path = os.path.join(script_dir, folder_path)
    
    if os.path.exists(folder_path):
        scenario_files = glob.glob(os.path.join(folder_path, "scenario_*.txt"))
        
        for file_path in sorted(scenario_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    
                # Extract scenario number from filename
                filename = os.path.basename(file_path)
                scenario_num = filename.replace('scenario_', '').replace('.txt', '')
                
                # Create display name
                display_name = f"Scenario {scenario_num}"
                
                # Try to extract a summary from the first line or paragraph
                first_line = content.split('\n')[0][:100]
                if len(first_line) == 100:
                    first_line += "..."
                
                display_name += f" - {first_line}"
                
                scenarios[display_name] = {
                    'content': content,
                    'filename': filename
                }
                
            except Exception as e:
                st.error(f"Error loading scenario from {file_path}: {str(e)}")
    
    return scenarios


def load_recipient_prompt(scenario_filename: str) -> str:
    """Load recipient prompt for a given scenario filename"""
    # Handle None scenario_filename (custom scenarios)
    if scenario_filename is None:
        return DEFAULT_RECIPIENT_PROMPT
        
    script_dir = get_script_directory()
    recipient_path = os.path.join(script_dir, RECIPIENTS_FOLDER, scenario_filename)
    
    if os.path.exists(recipient_path):
        try:
            with open(recipient_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            st.error(f"Error loading recipient prompt: {str(e)}")
            return DEFAULT_RECIPIENT_PROMPT
    else:
        return DEFAULT_RECIPIENT_PROMPT


def load_rubric_from_file(scenario_filename: str) -> str:
    """Load rubric from rubrics folder for a given scenario filename"""
    # Handle None scenario_filename (custom scenarios)
    if scenario_filename is None:
        return None
        
    script_dir = get_script_directory()
    rubric_path = os.path.join(script_dir, RUBRICS_FOLDER, scenario_filename)
    
    if os.path.exists(rubric_path):
        try:
            with open(rubric_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            st.error(f"Error loading rubric: {str(e)}")
            return None
    else:
        return None


def save_rubric_to_file(scenario_filename: str, rubric: str) -> bool:
    """Save generated rubric to rubrics folder"""
    # Handle None scenario_filename (custom scenarios) - cannot save without filename
    if scenario_filename is None:
        return False
        
    script_dir = get_script_directory()
    rubrics_dir = os.path.join(script_dir, RUBRICS_FOLDER)
    
    # Create rubrics directory if it doesn't exist
    if not os.path.exists(rubrics_dir):
        try:
            os.makedirs(rubrics_dir)
        except Exception as e:
            st.error(f"Error creating rubrics directory: {str(e)}")
            return False
    
    rubric_path = os.path.join(rubrics_dir, scenario_filename)
    
    try:
        with open(rubric_path, 'w', encoding='utf-8') as f:
            f.write(rubric)
        return True
    except Exception as e:
        st.error(f"Error saving rubric: {str(e)}")
        return False


def extract_goal_achievement_score(evaluation_text: str) -> bool:
    """
    Extract the goal achievement from the evaluation text by checking the final word.
    
    Expects the evaluation to end with "Yes" or "No" as the final word.
    
    Args:
        evaluation_text: The AI evaluation text that should end with Yes/No
        
    Returns:
        bool: True if final word is "Yes", False if "No"
        
    Raises:
        ValueError: If the final word is not "Yes" or "No"
    """
    
    # Get the final word from the evaluation text
    words = evaluation_text.strip().split()
    if not words:
        raise ValueError("Evaluation text is empty")
    
    final_word = words[-1].lower().strip('.,!?;:')
    
    if final_word == "yes":
        return True
    else:
        return False


def format_scenario_content(scenario_content: str) -> str:
    """
    Format scenario content for HTML display by converting line breaks to <br> tags.
    
    Args:
        scenario_content: Raw scenario text with line breaks
        
    Returns:
        HTML-formatted text with <br> tags
    """
    return scenario_content.replace('\n', '<br>')


def process_evaluation_text(evaluation_text: str) -> str:
    """
    Process evaluation text to add proper formatting for quotes and rationales.
    
    Args:
        evaluation_text: Raw evaluation text from AI
        
    Returns:
        HTML-formatted evaluation text with styling
    """
    # Remove bullet points first
    processed_evaluation = re.sub(r'^\s*[-•*]\s*', '', evaluation_text, flags=re.MULTILINE)
    
    # Process evaluation to add yellow boxes for quotes and rationales
    def process_quotes_and_rationales(text):
        lines = text.split('\n')
        # Remove empty lines
        lines = [line for line in lines if line.strip()]
        processed_lines = []

        i = 0
        while i < len(lines):
            line = lines[i].strip() 

            if line.startswith('Quote:') or line.startswith('Rationale:'):
                # Check if there's a next line and if it's a Rationale
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith('Rationale:'):
                        line = f'{line}\n\n{next_line.strip()}'
                        i += 1  # Skip the next line since we've processed it
                
                processed_lines.append(f'<div class="quote-box">{line.strip()}</div>')
            elif line:  # Only add non-empty lines
                processed_lines.append(f'<div class="evaluation-item">{line}</div>')
            
            i += 1  # Move to next line
        
        return '\n'.join(processed_lines)
    
    return process_quotes_and_rationales(processed_evaluation)


def initialize_session_state():
    """Initialize all required session state variables."""
    session_defaults = {
        'leaderboard': [],
        'current_score': None,
        'show_breakdown': False,
        'evaluating': False,
        'selected_scenario': None,
        'current_page': "mode_selection",
        'evaluation_result': None,
        'recipient_reply': None,
        'selected_scenario_file': None,
        'cached_rubrics': {},
        'app_mode': None,
        'current_level': 0,  # Start from level 0 (tutorial)
        'completed_levels': set(),
        'level_emails': {},
        'level_evaluations': {},
        'use_rubric': DEFAULT_USE_RUBRIC,  # Will be updated based on mode
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def check_api_keys():
    """Check if any API keys are available"""
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY_CLAB"))


def get_api_client():
    """Get the appropriate API client based on available keys"""
    import openai
    
    # Try OpenAI first
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return openai.OpenAI(api_key=openai_key)
    
    # Fallback to legacy key
    legacy_key = os.getenv("OPENAI_API_KEY_CLAB")
    if legacy_key:
        return openai.OpenAI(api_key=legacy_key)
    
    raise ValueError("No API key found. Set OPENAI_API_KEY or OPENAI_API_KEY_CLAB environment variable.")


def load_scenarios():
    """Load scenarios using the new function name"""
    return load_scenarios_from_folder() 


def get_scenario_recipients(scenario_filename: str) -> Dict[str, str]:
    """
    Detect and load all recipients for a scenario.
    
    For multi-recipient scenarios like Level 3, this will find files like:
    - scenario_5.3_emily.txt (in both scenarios/ and recipients/ folders)
    - scenario_5.3_mark.txt (in both scenarios/ and recipients/ folders)
    
    Args:
        scenario_filename: Base scenario filename (e.g., "scenario_5.3.txt")
        
    Returns:
        Dict mapping recipient names to their recipient prompts
        If no additional recipients found, returns single recipient with base scenario
    """
    if scenario_filename is None:
        return {"": DEFAULT_RECIPIENT_PROMPT}
    
    # Extract base name without extension
    base_name = scenario_filename.replace('.txt', '')  # e.g., "scenario_5.3"
    
    script_dir = get_script_directory()
    recipients_dir = os.path.join(script_dir, RECIPIENTS_FOLDER)
    
    recipients = {}
    
    # Look for recipient-specific files
    if os.path.exists(recipients_dir):
        recipient_files = glob.glob(os.path.join(recipients_dir, f"{base_name}_*.txt"))
        
        for recipient_file in sorted(recipient_files):
            filename = os.path.basename(recipient_file)
            # Skip GM files
            if filename.endswith('_gm.txt'):
                continue
            
            # Extract recipient name from filename like "scenario_5.3_emily.txt"
            recipient_name = filename.replace(f"{base_name}_", "").replace('.txt', '')
            
            try:
                with open(recipient_file, 'r', encoding='utf-8') as f:
                    recipients[recipient_name] = f.read().strip()
            except Exception as e:
                st.error(f"Error loading recipient {recipient_name}: {str(e)}")
    
    # If no specific recipients found, use the default single recipient
    if not recipients:
        recipients[""] = load_recipient_prompt(scenario_filename)
    
    return recipients


def get_scenario_prompts(scenario_filename: str) -> Dict[str, str]:
    """
    Get scenario prompts for all recipients.
    
    For multi-recipient scenarios, this loads files like:
    - scenario_5.3_emily.txt (from scenarios/ folder - contains Emily's complaint email)
    - scenario_5.3_mark.txt (from scenarios/ folder - contains Mark's complaint email)
    
    Args:
        scenario_filename: Base scenario filename (e.g., "scenario_5.3.txt")
        
    Returns:
        Dict mapping recipient names to their scenario prompts (the emails they sent)
        Returns empty dict if no additional prompts found
    """
    if scenario_filename is None:
        return {}
    
    # Extract base name without extension
    base_name = scenario_filename.replace('.txt', '')  # e.g., "scenario_5.3"
    
    script_dir = get_script_directory()
    scenarios_dir = os.path.join(script_dir, SCENARIOS_FOLDER)
    
    prompts = {}
    
    # Look for recipient-specific scenario files
    if os.path.exists(scenarios_dir):
        prompt_files = glob.glob(os.path.join(scenarios_dir, f"{base_name}_*.txt"))
        
        for prompt_file in sorted(prompt_files):
            filename = os.path.basename(prompt_file)
            # Extract recipient name from filename like "scenario_5.3_emily.txt"
            recipient_name = filename.replace(f"{base_name}_", "").replace('.txt', '')
            
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompts[recipient_name] = f.read().strip()
            except Exception as e:
                st.error(f"Error loading scenario prompt for {recipient_name}: {str(e)}")
    
    return prompts


def is_multi_recipient_scenario(scenario_filename: str) -> bool:
    """
    Check if a scenario has multiple recipients.
    
    Args:
        scenario_filename: Base scenario filename (e.g., "scenario_5.3.txt")
        
    Returns:
        bool: True if multiple recipients found
    """
    recipients = get_scenario_recipients(scenario_filename)
    return len(recipients) > 1 or (len(recipients) == 1 and "" not in recipients)


def load_communication_goal(scenario_filename: str) -> str:
    """
    Load communication goal for a given scenario filename.
    
    Args:
        scenario_filename: Base scenario filename (e.g., "scenario_5.3.txt")
        
    Returns:
        str: Communication goal text, or default message if not found
    """
    if scenario_filename is None:
        return "Achieve effective communication with the recipient."
    
    script_dir = get_script_directory()
    goal_path = os.path.join(script_dir, "prompts", "comm_goals", scenario_filename)
    
    if os.path.exists(goal_path):
        try:
            with open(goal_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            st.error(f"Error loading communication goal: {str(e)}")
            return "Achieve effective communication with the recipient."
    else:
        # Fallback goal if no specific goal file exists
        return "Achieve effective communication with the recipient."


def get_forwarded_emails(scenario_filename: str) -> Dict[str, str]:
    """
    Load forwarded emails for a given scenario filename.
    
    Args:
        scenario_filename: Base scenario filename (e.g., "scenario_5.5.txt")
        
    Returns:
        Dict[str, str]: Dictionary mapping email identifiers to email content
    """
    if scenario_filename is None:
        return {}
    
    # Extract scenario base name (e.g., "scenario_5.5" from "scenario_5.5.txt")
    base_name = scenario_filename.replace('.txt', '')
    
    script_dir = get_script_directory()
    scenarios_dir = os.path.join(script_dir, SCENARIOS_FOLDER)
    
    forwarded_emails = {}
    
    # Look for files with pattern: scenario_X.Y_emailN.txt
    if os.path.exists(scenarios_dir):
        for filename in os.listdir(scenarios_dir):
            if filename.startswith(f"{base_name}_email") and filename.endswith('.txt'):
                # Extract email identifier (e.g., "email1", "email2", etc.)
                email_id = filename.replace(f"{base_name}_", "").replace('.txt', '')
                
                email_path = os.path.join(scenarios_dir, filename)
                try:
                    with open(email_path, 'r', encoding='utf-8') as f:
                        forwarded_emails[email_id] = f.read().strip()
                except Exception as e:
                    st.error(f"Error loading forwarded email {filename}: {str(e)}")
                    continue
    
    return forwarded_emails


def has_forwarded_emails(scenario_filename: str) -> bool:
    """
    Check if a scenario has forwarded emails.
    
    Args:
        scenario_filename: Base scenario filename (e.g., "scenario_5.5.txt")
        
    Returns:
        bool: True if the scenario has forwarded emails, False otherwise
    """
    forwarded_emails = get_forwarded_emails(scenario_filename)
    return len(forwarded_emails) > 0


def get_all_additional_emails(scenario_filename: str) -> Dict[str, any]:
    """
    Get all additional emails for a scenario (forwarded emails for context).
    This is separate from multi-recipient functionality.
    
    Args:
        scenario_filename: The scenario filename to check for additional emails
        
    Returns:
        Dictionary containing:
        {
            'has_emails': bool,
            'title': str,
            'description': str,
            'emails': [(title, content), ...]  # List of tuples for ordered display
        }
    """
    result = {
        'has_emails': False,
        'title': '',
        'description': '',
        'emails': []
    }
    
    # Check for forwarded emails (context emails)
    if has_forwarded_emails(scenario_filename):
        forwarded_emails = get_forwarded_emails(scenario_filename)
        
        if forwarded_emails:
            # Sort emails by their identifier (email1, email2, etc.)
            sorted_emails = sorted(forwarded_emails.items(), key=lambda x: x[0])
            
            email_list = []
            for email_id, email_content in sorted_emails:
                email_title = f"Forwarded Email {email_id.replace('email', '')}"
                email_list.append((email_title, email_content))
            
            result.update({
                'has_emails': True,
                'title': '📧 Forwarded Emails',
                'description': '💼 The following email correspondence has been forwarded to provide context for your response.',
                'emails': email_list
            })
    
    return result 


def load_game_master_prompt(scenario_filename: str) -> str:
    """
    Load Game Master prompt for a given scenario filename.
    
    Args:
        scenario_filename: Base scenario filename (e.g., "scenario_5.5.txt")
        
    Returns:
        str: Game Master prompt content, or empty string if not found
    """
    if scenario_filename is None:
        return ""
    
    # Extract scenario base name (e.g., "scenario_5.5" from "scenario_5.5.txt")
    base_name = scenario_filename.replace('.txt', '')
    
    script_dir = get_script_directory()
    gm_prompt_path = os.path.join(script_dir, RECIPIENTS_FOLDER, f"{base_name}_gm.txt")
    
    if os.path.exists(gm_prompt_path):
        try:
            with open(gm_prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            st.error(f"Error loading Game Master prompt: {str(e)}")
            return ""
    else:
        return ""


def has_game_master(scenario_filename: str) -> bool:
    """
    Check if a scenario has a Game Master prompt.
    
    Args:
        scenario_filename: Base scenario filename (e.g., "scenario_5.5.txt")
        
    Returns:
        bool: True if the scenario has a Game Master prompt, False otherwise
    """
    gm_prompt = load_game_master_prompt(scenario_filename)
    return bool(gm_prompt.strip())