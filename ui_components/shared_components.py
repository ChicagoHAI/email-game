"""
Shared UI Components

This module contains reusable UI components that are used across 
different parts of the email game interface to eliminate duplication.
"""

import streamlit as st
from typing import Optional, Dict, Any
from config import EMAIL_MAX_CHARS, EMAIL_TEXT_AREA_HEIGHT
from utils import is_multi_recipient_scenario


# =============================================================================
# INPUT COMPONENTS - Text areas, buttons, form elements
# =============================================================================

def create_email_textarea(
    label: str = "Write your email here",
    key: str = "email_input",
    height: int = EMAIL_TEXT_AREA_HEIGHT,
    max_chars: int = EMAIL_MAX_CHARS,
    placeholder: str = "Type your email response...",
    help_text: str = "Write your email response",
    value: str = "",
    auto_populate_from_session: bool = False,
    session_key: Optional[str] = None
) -> str:
    """
    Create a standardized email text area component.
    
    This replaces the multiple email input implementations across:
    - ui.py (developer mode)
    - ui_components/level_interface.py 
    - ui_components/turn_management.py
    
    Args:
        label: The label for the text area
        key: Streamlit widget key for state management
        height: Height of the text area in pixels
        max_chars: Maximum character limit
        placeholder: Placeholder text
        help_text: Help text shown on hover
        value: Initial value for the text area
        auto_populate_from_session: Whether to auto-populate from session state
        session_key: Session state key to use for auto-population
    
    Returns:
        The text content from the text area
    """
    # Auto-populate from session state if requested
    initial_value = value
    if auto_populate_from_session and session_key:
        session_data = st.session_state.get(session_key, {})
        if isinstance(session_data, str):
            initial_value = session_data
        elif isinstance(session_data, dict) and session_data:
            # Get the specific level's email if it exists, otherwise use empty
            level_from_key = None
            if 'email_input_level_' in key:
                try:
                    level_from_key = float(key.split('email_input_level_')[1].split('_turn_')[0])
                except (ValueError, IndexError):
                    pass
            
            if level_from_key is not None and level_from_key in session_data:
                initial_value = session_data[level_from_key]
            else:
                initial_value = value  # Use empty value if no data for this specific level
    
    return st.text_area(
        label=label,
        value=initial_value,
        height=height,
        max_chars=max_chars,
        placeholder=placeholder,
        help=help_text,
        key=key
    )


def create_level_email_input(
    level: float, 
    api_keys_available: bool = True
) -> str:
    """
    Create email input specifically for level-based gameplay.
    Replaces create_email_input_section from level_interface.py
    """
    # Standard single-turn level
    placeholder = "Type your email response to the scenario above..."
    help_text = "Write the best email you can for the given scenario"
    label = "Write your email here"
    height = EMAIL_TEXT_AREA_HEIGHT
    
    return create_email_textarea(
        label=label,
        key=f"email_input_level_{level}",
        height=height,
        placeholder=placeholder,
        help_text=help_text,
        auto_populate_from_session=True,
        session_key='level_emails'
    )


def create_turn_email_input(
    level: float, 
    current_turn: int, 
    max_turns: int
) -> str:
    """
    Create email input for multi-turn levels.
    Replaces create_turn_email_input from turn_management.py
    """
    return create_email_textarea(
        label=f"Write your email to Adam (Turn {current_turn}):",
        key=f"email_input_level_{level}_turn_{current_turn}",
        placeholder="Continue the conversation with Adam. Try to understand what's really bothering him...",
        help_text="Write an email that helps Adam open up about his true concerns",
        value=""  # Always start with empty value for new turns
    )


def create_developer_email_input(
    key: str = "email_input",
    with_ai_generation: bool = False,
    scenario: str = "",
    model: str = "gpt-4o",
    api_keys_available: bool = True
) -> str:
    """
    Create email input for developer mode with optional AI generation.
    Replaces the email input implementation in ui.py
    """
    if with_ai_generation:
        # AI generation header and button
        col_email_header, col_ai_button = st.columns([3, 1])
        with col_email_header:
            st.subheader("✍️ Your Email")
        with col_ai_button:
            if st.button("🤖 Generate email with AI", help="Generate an email using AI for the current scenario"):
                if api_keys_available and scenario.strip():
                    with st.spinner("🤖 AI is writing an email..."):
                        try:
                            from models import EmailGenerator
                            generator = EmailGenerator()
                            generated_email = generator.generate_email(scenario, model)
                            if generated_email:
                                st.session_state[key] = generated_email
                                st.success("✅ Email generated!")
                                st.rerun()
                            else:
                                st.error("Failed to generate email")
                        except Exception as e:
                            st.error(f"Error initializing generator: {str(e)}")
                elif not api_keys_available:
                    st.error("API keys not available")
                else:
                    st.error("Please select a scenario first")
    
    return create_email_textarea(
        label="Write your email here",
        key=key,
        max_chars=3000,  # Developer mode uses slightly different max chars
        placeholder="Type your email response to the scenario above, or use the AI generation button...",
        help_text="Write the best email you can for the given scenario, or generate one with AI"
    )


def create_submit_button(
    api_keys_available: bool, 
    email_content: str,
    button_text: str = "📝 Send",
    button_type: str = "primary"
) -> bool:
    """
    Create a standardized submit button for email submission.
    Replaces create_submit_button from level_interface.py
    """
    return st.button(
        button_text,
        type=button_type,
        disabled=not api_keys_available or not email_content.strip(),
        help="Submit your email for evaluation" if api_keys_available else "API keys required to submit"
    )


def create_scenario_textarea(
    scenario_content: str,
    key: str = "scenario_input",
    editable: bool = True
) -> str:
    """
    Create a standardized scenario text area.
    """
    # Use constants from config, with fallbacks
    SCENARIO_HEIGHT = 350  # matches the existing usage in ui.py
    SCENARIO_MAX_CHARS = 5000  # matches the existing usage in ui.py
    
    if editable:
        return st.text_area(
            "Current Scenario",
            value=scenario_content,
            height=SCENARIO_HEIGHT,
            max_chars=SCENARIO_MAX_CHARS,
            help="The scenario for which participants will write emails",
            key=key
        )
    else:
        # Read-only display
        st.text_area(
            "Scenario",
            value=scenario_content,
            height=SCENARIO_HEIGHT,
            disabled=True,
            help="The current scenario"
        )
        return scenario_content 


def create_mode_change_button() -> bool:
    """Create standardized mode change button"""
    return st.button("Change Mode", help="Go back to mode selection")


def create_primary_action_button(text: str, disabled: bool = False, help_text: str = "") -> bool:
    """Create standardized primary action button"""
    return st.button(
        text, 
        type="primary", 
        disabled=disabled, 
        help=help_text,
        use_container_width=False
    )


def create_secondary_action_button(text: str, disabled: bool = False, help_text: str = "") -> bool:
    """Create standardized secondary action button"""
    return st.button(
        text, 
        type="secondary", 
        disabled=disabled, 
        help=help_text,
        use_container_width=False
    )


# =============================================================================
# STATUS & NOTIFICATION FUNCTIONS - Messages, errors, success notifications
# =============================================================================

def show_api_key_status(api_keys_available: bool) -> None:
    """Standardized API key status display"""
    if api_keys_available:
        st.success("✅ API keys loaded from environment")
    else:
        st.error("❌ Missing API keys")
        st.info("Set OPENAI_API_KEY_CLAB environment variable")


def show_scenario_loading_status(num_scenarios: int) -> None:
    """Standardized scenario loading status display"""
    if num_scenarios > 0:
        st.success(f"Loaded {num_scenarios} scenario(s)")
    else:
        st.warning("No scenarios found in manual folder")


def show_session_info(session_id: str, message_type: str = "active") -> None:
    """Standardized session info messages"""
    session_short = session_id[:8] + "..." if len(session_id) > 8 else session_id
    
    if message_type == "active":
        st.info(f"🔗 **Auto-using active session:** {session_short} (you can override with `?session=OTHER_ID&gang_level=X`)")
    elif message_type == "created":
        st.info(f"🆕 **Created new session:** {session_short}")
    elif message_type == "existing":
        st.info(f"🔄 **Using existing session:** {session_short}")
    elif message_type == "not_found":
        st.error(f"❌ **Session not found:** {session_short} does not exist")


def show_goal_achieved(turn_number: int) -> None:
    """Standardized goal achievement message"""
    st.success(f"🎯 **Goal achieved in Turn {turn_number}!**")


def show_submission_error(error_type: str = "empty") -> None:
    """Standardized submission error messages"""
    if error_type == "empty":
        st.error("Please write an email before submitting!")
    elif error_type == "api_keys":
        st.error("API keys not available")
    else:
        st.error(f"❌ {error_type}")


def show_level_progression_hint() -> None:
    """Show level progression hint (currently commented out in original code)"""
    # st.info("🎯 **Level Progression**: Complete this level to unlock the next!")
    pass


def show_turn_update_success(turn_number: int) -> None:
    """Standardized turn update success message"""
    st.success("🔄 Turn updated successfully! The page will refresh to show the new response.")


def show_turn_evaluation_info(turn_number: int) -> None:
    """Standardized turn evaluation info message"""
    st.info(f"📧 **Turn {turn_number} updated.** Continue the conversation to achieve your goal.")


def show_level_restart_success(level: float) -> None:
    """Standardized level restart success message"""
    st.success(f"🔄 Level {level} restarted! You can now try again.")


def show_level_restart_error() -> None:
    """Standardized level restart error message"""
    st.error("❌ Failed to restart level. Please try again.")


# =============================================================================
# DISPLAY FUNCTIONS - Content display, formatting, level-specific messages
# =============================================================================

def create_session_info_display(session_id: str) -> None:
    """Create session info display"""
    st.info(f"📋 **Session ID:** `{session_id}` (copy this to resume the game later)")


def create_level_display(level: float) -> str:
    """Create level display string"""
    if level == 0:
        return "Tutorial"
    elif level == 2.5:
        return "Challenge Level 2.5"
    else:
        return f"Level {level}"


def create_success_message(level: float) -> str:
    """Create success message for level completion"""
    if level == 2.5:
        return "🎉 **Success!** You completed the challenge level!"
    else:
        return "🎉 **Success!** You persuaded the recipient and completed this level!"


def create_strategy_warning() -> None:
    """Create strategy analysis warning display"""
    st.warning("⚠️ **Strategy Analysis**: You used forbidden strategies (layoffs or salary increases)!")
    st.info("🎯 **Next Challenge**: You'll be directed to Level 2.5 where these strategies are prohibited.")


def create_strategy_success() -> None:
    """Create strategy analysis success display"""
    st.info("✅ **Strategy Analysis**: Great! You didn't use any forbidden strategies. You can proceed directly to Level 3.")


def create_turn_counter_display(current_turn: int, max_turns: int) -> None:
    """Create turn counter display for multi-turn levels"""
    st.info(f"📧 **Turn {current_turn} of {max_turns}** - Continue the conversation with Adam")


def create_level_complete_display(level: float) -> None:
    """Create level complete display"""
    st.success(f"🎉 **Level {level} Complete!** You successfully helped Adam express his concerns.")


def create_turn_limit_display(max_turns: int) -> None:
    """Create turn limit reached display"""
    st.warning(f"⏱️ **Turn limit reached** ({max_turns} turns)")
    st.info("💼 Adam has decided to just bring noise canceling headphones and a blanket to work.")


def create_level_info_message(level: float) -> None:
    """Create standardized level info messages"""
    if level == 2:
        st.info("💼 **Level 2**: Send an email to multiple recipients.")
    elif level == 3:
        st.info("🎯 **Level 3**: Choose your strategy wisely - some approaches may lead to additional challenges!")
    elif level == 3.5:
        st.warning("⚠️ **Challenge Level 3.5**: Forbidden strategies (layoffs, salary increases) are not allowed here!")
    elif level == 4:
        from config import MAX_TURNS
        st.info(f"📧 **Multi-turn Level**: Figure out Adam's true concerns within {MAX_TURNS} turns.")
    # elif level == 5:
    #     st.info("🏆 **Final Level**: Demonstrate mastery of all communication skills.")


# =============================================================================
# LAYOUT & STYLING FUNCTIONS - Spacing, separators, visual formatting
# =============================================================================

def add_padding(pixels: int = 20) -> None:
    """Add vertical padding using CSS"""
    st.markdown(f"<div style='padding-top: {pixels}px;'></div>", unsafe_allow_html=True)


def add_separator() -> None:
    """Add a visual separator line"""
    st.markdown("---")


def show_evaluation_styles():
    """Inject CSS styles for evaluation display"""
    st.markdown("""
    <style>
    .quote-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 12px;
        margin: 4px 0 24px 0;
        font-style: italic;
        white-space: pre-line;
    }
    .evaluation-content {
        font-size: 0.9rem !important;
        line-height: 1.5 !important;
    }
    .evaluation-content p {
        font-size: 0.9rem !important;
        line-height: 1.5 !important;
        margin-bottom: 1rem !important;
    }
    .evaluation-content ul {
        list-style: none !important;
        padding-left: 0 !important;
    }
    .evaluation-content li {
        margin-bottom: 1rem !important;
        font-size: 0.9rem !important;
    }
    .evaluation-item {
        margin-bottom: 4px;
    }
    .evaluation-item:first-child {
        margin-top: 0;
    }
    </style>
    """, unsafe_allow_html=True) 