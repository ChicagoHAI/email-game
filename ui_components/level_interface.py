"""
Level Interface Components

Handles level navigation, scenario display, and level progression logic.
Email-related functionality has been moved to gmail_inbox.py.
"""

import streamlit as st
from config import EMAIL_MAX_CHARS, LEVEL_TO_SCENARIO_MAPPING, MULTI_TURN_LEVELS, MAX_TURNS
from .html_helpers import create_scenario_display
from .shared_components import create_level_display


def show_level_navigation(session_id: str, current_level: float):
    """Show level navigation controls"""
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        _show_previous_level_button(session_id, current_level)
    
    with col2:
        level_display = create_level_display(current_level)
        st.markdown(f"<div style='text-align: center;'><strong>{level_display}</strong></div>", unsafe_allow_html=True)
        # st.markdown(f"<strong>{level_display}</strong>", unsafe_allow_html=True)
    
    with col3:
        # Create sub-columns to push the button to the right
        _, _, button_col = st.columns([1, 1, 2.5])
        with button_col:
            _show_next_level_button(session_id, current_level)
    
    # Level progression info
    # st.info("🎯 **Level Progression**: Complete this level to unlock the next!")


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
        # Clear Gmail inbox state to hide Brittany's email by default
        _clear_gmail_inbox_state()
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
        # Clear Gmail inbox state to hide Brittany's email by default
        _clear_gmail_inbox_state()
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


def _clear_gmail_inbox_state():
    """Clear Gmail inbox state to ensure proper navigation state on level changes"""
    # Clear the state that controls whether the scenario email is shown
    if 'show_scenario_email' in st.session_state:
        del st.session_state.show_scenario_email
    if 'selected_email' in st.session_state:
        del st.session_state.selected_email
    
    # Clear Gmail-specific navigation state
    if 'gmail_view' in st.session_state:
        del st.session_state.gmail_view
    if 'selected_email_id' in st.session_state:
        del st.session_state.selected_email_id


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


# def create_email_input_section(level: float, api_keys_available: bool):
#     """Create email input section for single-turn levels"""
#     # Import the shared component
#     from .shared_components import create_level_email_input
#     return create_level_email_input(level, api_keys_available)


# def create_submit_button(api_keys_available: bool, email_content: str):
#     """Create submit button for email submission"""
#     # Import the shared component
#     from .shared_components import create_submit_button as shared_submit_button
#     return shared_submit_button(api_keys_available, email_content)


# def show_level_progression_logic(level: float):
#     """Show level-specific progression logic"""
#     from .shared_components import create_level_info_message
#     create_level_info_message(level)


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