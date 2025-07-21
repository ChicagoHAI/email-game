"""
Level Interface Components

Handles level navigation, display, and scenario presentation.
"""

import streamlit as st
from config import EMAIL_MAX_CHARS, LEVEL_TO_SCENARIO_MAPPING, MULTI_TURN_LEVELS, MAX_TURNS
from utils import is_multi_recipient_scenario
from .html_helpers import (
    create_scenario_display, 
    create_level_display,
    create_forwarded_email_display,
    create_emily_email_display,
    create_mark_email_display
)


def show_level_navigation(session_id: str, current_level: float):
    """Show level navigation controls"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        _show_previous_level_button(session_id, current_level)
    
    with col2:
        level_display = create_level_display(current_level)
        st.markdown(f"**🎮 {level_display}**")
    
    with col3:
        _show_next_level_button(session_id, current_level)
    
    # Level progression info
    st.info("🎯 **Level Progression**: Complete this level to unlock the next!")


def _show_previous_level_button(session_id: str, current_level: float):
    """Show previous level button"""
    from ui_user import determine_previous_level, clean_stale_level_data
    from session_manager import save_session_progress
    
    previous_level = determine_previous_level(current_level, st.session_state)
    can_go_back = previous_level is not None
    
    if st.button("← Previous Level", disabled=not can_go_back, help="Go to previous level"):
        st.session_state.current_level = previous_level
        # Clean up stale level data
        clean_stale_level_data(previous_level, st.session_state)
        # Auto-save progress
        save_session_progress(session_id, st.session_state.current_level, st.session_state.get('completed_levels', set()))
        
        # Clear any URL navigation flags and update URL
        _clear_url_navigation_state(previous_level, session_id)
        
        st.rerun()


def _show_next_level_button(session_id: str, current_level: float):
    """Show next level button"""
    from ui_user import determine_next_level, clean_stale_level_data
    from session_manager import save_session_progress
    
    next_level = determine_next_level(current_level, st.session_state)
    can_go_forward = (next_level is not None and 
                     next_level in LEVEL_TO_SCENARIO_MAPPING and 
                     current_level in st.session_state.get('completed_levels', set()))
    
    next_level_text = "Next Level →"
    help_text = "Go to next level"
    
    # Special messaging for Level 3 progression (formerly Level 2)
    if current_level == 3 and can_go_forward:
        strategy_analysis = st.session_state.get('strategy_analysis', {}).get(3)
        completed_levels = st.session_state.get('completed_levels', set())
        
        # Check if forbidden strategies were used
        used_forbidden_strategies = (strategy_analysis and strategy_analysis.get('used_forbidden_strategies')) or (3.5 in completed_levels)
        
        if used_forbidden_strategies and next_level == 3.5:
            next_level_text = "Challenge Level 3.5 →"
            help_text = "You used forbidden strategies! Try the harder challenge."
                
    if st.button(next_level_text, disabled=not can_go_forward, help=help_text):
        st.session_state.current_level = next_level
        # Clean up stale level data
        clean_stale_level_data(next_level, st.session_state)
        # Auto-save progress
        save_session_progress(session_id, st.session_state.current_level, st.session_state.get('completed_levels', set()))
        
        # Clear any URL navigation flags and update URL
        _clear_url_navigation_state(next_level, session_id)
        
        st.rerun()


def _clear_url_navigation_state(level: float, session_id: str):
    """Clear URL navigation state and update URL for normal navigation"""
    try:
        # Clear URL navigation processing flags
        if 'url_navigation_processed' in st.session_state:
            del st.session_state.url_navigation_processed
            
        # Update URL to show only session (no gang_level)
        st.query_params.update({"session": session_id})
        
    except Exception as e:
        # URL updates are not critical
        pass


def _update_url_for_navigation(level: float, session_id: str):
    """Update URL parameters when navigating via buttons"""
    # This function is kept for backward compatibility but now calls the clearer version
    _clear_url_navigation_state(level, session_id)


def show_scenario_section(scenario_content: str):
    """Show the scenario section"""
    st.subheader("📋 Scenario")
    
    # Display scenario content with proper formatting
    scenario_html = create_scenario_display(scenario_content)
    st.markdown(scenario_html, unsafe_allow_html=True)


def show_gmail_inbox_section(scenario_content: str, level: float):
    """Show the Gmail-like inbox interface instead of the traditional scenario section"""
    from .gmail_inbox import create_gmail_inbox
    
    st.subheader("📧 Your Inbox")
    create_gmail_inbox(scenario_content, level)


def show_additional_emails(scenario_filename: str):
    """Show additional emails for a scenario"""
    from utils import get_all_additional_emails
    
    # First check for forwarded emails (context emails)
    forwarded_emails = get_all_additional_emails(scenario_filename)
    
    if forwarded_emails['has_emails']:
        st.markdown(f"**{forwarded_emails['title']}**")
        st.info(forwarded_emails['description'])
        
        for email_title, email_content in forwarded_emails['emails']:
            with st.expander(email_title, expanded=False):
                email_html = create_forwarded_email_display(email_content)
                st.markdown(email_html, unsafe_allow_html=True)
    
    # Then check for multi-recipient context emails (Emily/Mark)
    if is_multi_recipient_scenario(scenario_filename):
        _show_multi_recipient_emails(scenario_filename)


def _show_multi_recipient_emails(scenario_filename: str):
    """Show multi-recipient context emails"""
    from utils import get_scenario_prompts
    recipient_prompts = get_scenario_prompts(scenario_filename)
    
    if 'emily' in recipient_prompts and 'mark' in recipient_prompts:
        st.markdown("**📨 Email Context**")
        st.info("💼 Below are the emails from Emily and Mark that prompted this request.")
        
        # Emily's email
        with st.expander("Emily's Email", expanded=False):
            emily_html = create_emily_email_display(recipient_prompts['emily'])
            st.markdown(emily_html, unsafe_allow_html=True)
        
        # Mark's email
        with st.expander("Mark's Email", expanded=False):
            mark_html = create_mark_email_display(recipient_prompts['mark'])
            st.markdown(mark_html, unsafe_allow_html=True)


def create_email_input_section(level: float, api_keys_available: bool):
    """Create email input section for single-turn levels"""
    st.subheader("✍️ Your Email")
    
    # Determine input type based on level
    if level == 2:
        return _create_level_2_email_input(level)
    else:
        return _create_standard_email_input(level)


def _create_level_2_email_input(level: float):
    """Create email input for Level 2 (multi-recipient)"""
    scenario_filename = st.session_state.get('selected_scenario_file', '')
    is_multi_recipient = is_multi_recipient_scenario(scenario_filename)
    
    if is_multi_recipient:
        st.info("📝 **Level 2**: Write a single email that will be sent to both Emily and Mark.")
        placeholder_text = "Type your email response that addresses both Emily's and Mark's concerns..."
        help_text = "Write an email that will resolve the conflict between Emily and Mark"
    else:
        st.info("📝 **Level 2**: Write an email that addresses the situation described in the scenario.")
        placeholder_text = "Type your email response that addresses the situation..."
        help_text = "Write an email that addresses the situation described in the scenario"
    
    return _create_email_textarea(level, placeholder_text, help_text)


def _create_standard_email_input(level: float):
    """Create standard email input for single-turn levels"""
    placeholder_text = "Type your email response to the scenario above..."
    help_text = "Write the best email you can for the given scenario"
    
    return _create_email_textarea(level, placeholder_text, help_text)


def _create_email_textarea(level: float, placeholder_text: str, help_text: str):
    """Create email textarea with pre-populated content if available"""
    # Pre-populate email if returning to a completed level
    initial_email_value = ""
    if level in st.session_state.get('level_emails', {}):
        level_emails = st.session_state.level_emails[level]
        if isinstance(level_emails, str):
            initial_email_value = level_emails
        elif isinstance(level_emails, dict) and level_emails:
            # If somehow stored as dict, use the first value
            initial_email_value = list(level_emails.values())[0]
    
    return st.text_area(
        "Write your email here" if level != 2 else "Write your email response:",
        value=initial_email_value,
        height=400 if level != 2 else 350,
        max_chars=EMAIL_MAX_CHARS,
        placeholder=placeholder_text,
        help=help_text,
        key=f"email_input_level_{level}"
    )


def create_submit_button(api_keys_available: bool, email_content: str):
    """Create submit button for email submission"""
    st.markdown("---")
    return st.button(
        "📝 Send",
        type="primary",
        disabled=not api_keys_available or not email_content.strip(),
        help="Submit your email for AI evaluation"
    )


def show_level_progression_logic(level: float):
    """Show level-specific progression logic"""
    if level in MULTI_TURN_LEVELS:
        st.info(f"📧 **Multi-turn Level**: This level supports up to {MAX_TURNS} conversation turns with Adam.")
    elif level == 2:
        st.info("💼 **Level 2**: Navigate complex multi-stakeholder communication.")
    elif level == 3:
        st.info("🎯 **Level 3**: Choose your strategy wisely - some approaches may lead to additional challenges!")
    elif level == 3.5:
        st.warning("⚠️ **Challenge Level 3.5**: Forbidden strategies (layoffs, salary increases) are not allowed here!")
    elif level == 5:
        st.info("🏆 **Final Level**: Demonstrate mastery of all communication skills.")


def get_scenario_data(level: float, available_scenarios: dict):
    """Get scenario data for a given level"""
    from config import DEFAULT_SCENARIO
    
    # Get backend scenario ID from user level
    backend_scenario_id = LEVEL_TO_SCENARIO_MAPPING.get(level, "5.0")
    
    # Get scenario data based on backend scenario ID
    scenario_data = None
    scenario_content = ""
    
    if available_scenarios:
        # Look for the backend scenario ID with exact matching
        target_scenario = f"scenario_{backend_scenario_id}.txt"
        for scenario_name, scenario_info in available_scenarios.items():
            # Use exact filename matching to avoid partial matches
            if scenario_info['filename'].lower() == target_scenario.lower():
                scenario_data = scenario_info
                scenario_content = scenario_info['content']
                st.session_state.selected_scenario = scenario_content
                st.session_state.selected_scenario_file = scenario_info['filename']
                break
        
        if not scenario_data:
            st.warning(f"Level {level} scenario not found. Using default scenario.")
            scenario_content = DEFAULT_SCENARIO
    else:
        # Fallback to default scenario if no scenarios found
        scenario_content = DEFAULT_SCENARIO
        st.warning("No scenarios found in manual folder. Using default scenario.")
    
    return scenario_content 