"""
User Mode UI Components

This module contains UI components specific to the user mode,
including the history-based navigation system.
"""

import streamlit as st
from config import (
    LEVEL_TO_SCENARIO_MAPPING,
    MAX_AVAILABLE_LEVEL,
    EMAIL_MAX_CHARS,
    DEFAULT_SCENARIO,
    DEFAULT_MODEL
)
from utils import format_scenario_content, process_evaluation_text


def show_user_interface_with_history(available_scenarios, api_keys_available):
    """Show the user interface with history-based navigation"""
    
    # Set default model for user version (no sidebar configuration)
    model = DEFAULT_MODEL
    
    # Use the global level mapping
    level_to_scenario_mapping = LEVEL_TO_SCENARIO_MAPPING
    max_level = MAX_AVAILABLE_LEVEL
    
    # Determine current page from history
    current_page = st.session_state.page_history[st.session_state.current_history_index]
    current_level_from_history = current_page["level"]
    
    # Navigation header with history controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        # Back button (browser-like)
        can_go_back = st.session_state.current_history_index > 0
        if st.button("← Back", disabled=not can_go_back, help="Go back in history"):
            st.session_state.current_history_index -= 1
            st.rerun()
    
    with col2:
        # Current page indicator
        page_type = current_page["type"]
        page_title = f"Level {current_level_from_history} - {'Scenario' if page_type == 'scenario' else 'Results'}"
        st.markdown(f"**🎮 {page_title}**")
    
    with col3:
        # Forward button (browser-like)
        can_go_forward = st.session_state.current_history_index < len(st.session_state.page_history) - 1
        if st.button("Forward →", disabled=not can_go_forward, help="Go forward in history"):
            st.session_state.current_history_index += 1
            st.rerun()
    
    # Level progression info
    st.info("🎯 **Level Progression**: Navigate through your completed levels using Back/Forward buttons!")
    
    # Show overall progress
    completed_count = len(st.session_state.completed_levels)
    progress_percentage = (completed_count / max_level) * 100
    st.progress(progress_percentage / 100)
    st.caption(f"Progress: {completed_count}/{max_level} levels completed ({progress_percentage:.0f}%)")
    
    # Show different content based on current page type
    if current_page["type"] == "scenario":
        show_scenario_page(current_level_from_history, available_scenarios, level_to_scenario_mapping, api_keys_available, model)
    else:  # evaluation page
        show_evaluation_page_from_history(current_level_from_history)


def show_scenario_page(level, available_scenarios, level_to_scenario_mapping, api_keys_available, model):
    """Show the scenario page for a specific level"""
    
    # Get backend scenario ID from user level
    backend_scenario_id = level_to_scenario_mapping.get(level, 3)  # Default to scenario 3
    
    # Get scenario data based on backend scenario ID
    scenario_data = None
    scenario_content = ""
    
    if available_scenarios:
        # Look for the backend scenario ID
        target_scenario = f"scenario_{backend_scenario_id}"
        for scenario_name, scenario_info in available_scenarios.items():
            if target_scenario in scenario_info['filename'].lower() or str(backend_scenario_id) in scenario_name:
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
    
    # Scenario section
    st.subheader("📋 Scenario")
    
    # Display scenario content with proper line breaks
    formatted_content = format_scenario_content(scenario_content)
    st.markdown(
        f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff;">
        {formatted_content}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Set scenario for processing
    scenario = scenario_content
    
    # Email input section
    st.subheader("✍️ Your Email")
    
    # Pre-populate email if returning to a completed level
    initial_email_value = ""
    if level in st.session_state.level_emails:
        initial_email_value = st.session_state.level_emails[level]
    
    # Email text area - uses key to maintain state automatically
    email_content = st.text_area(
        "Write your email here",
        value=initial_email_value,
        height=400,
        max_chars=EMAIL_MAX_CHARS,
        placeholder="Type your email response to the scenario above...",
        help="Write the best email you can for the given scenario",
        key=f"email_input_level_{level}"  # Unique key per level
    )

    # Submit button
    st.markdown("---")
    if st.button(
        "📝 Send",
        type="primary",
        disabled=not api_keys_available or not email_content.strip(),
        help="Submit your email for AI evaluation"
    ):
        if not email_content.strip():
            st.error("Please write an email before submitting!")
        elif not api_keys_available:
            st.error("API keys not available")
        else:
            # Process email evaluation and update history
            from evaluation import process_email_evaluation_with_history
            process_email_evaluation_with_history(scenario, email_content, model, level)


def show_evaluation_page_from_history(level):
    """Show the stored evaluation results for a specific level"""
    
    if level in st.session_state.level_evaluations:
        result = st.session_state.level_evaluations[level]
        
        # Show the scenario
        st.subheader("📋 Scenario")
        st.text_area("", value=result["scenario"], height=200, disabled=True)
        
        # Show the email
        st.subheader("✍️ Your Email")
        st.text_area("", value=result["email"], height=300, disabled=True)
        
        # Show the recipient reply
        if "recipient_reply" in result:
            st.subheader("📨 Recipient's Reply")
            st.markdown(result["recipient_reply"])
        
        # Show goal achievement status
        if "goal_achieved" in result:
            if result["goal_achieved"]:
                st.success("🎉 **Success!** You persuaded the recipient and completed this level!")
            else:
                st.error("❌ **Goal Not Achieved** - You can try this level again to improve your result.")
        
        # Show the generated rubric (collapsible)
        if "rubric" in result:
            with st.expander("📏 Evaluation Rubric", expanded=False):
                st.markdown(result["rubric"])
        
        # Show the evaluation with improved formatting (collapsible)
        with st.expander("🤖 AI Evaluation", expanded=True):
            _show_evaluation_styles()
            processed_evaluation = process_evaluation_text(result["evaluation"])
            st.markdown(f'<div class="evaluation-content">{processed_evaluation}</div>', unsafe_allow_html=True)
        
        # Show additional navigation options
        st.markdown("---")
        
        # Show "Continue to Next Level" button if this was successful and there are more levels
        if result.get("goal_achieved") and level < MAX_AVAILABLE_LEVEL:
            next_level = level + 1
            if st.button(f"Continue to Level {next_level} →", type="primary"):
                # Add next level to history if not already there
                next_page = {"type": "scenario", "level": next_level}
                if next_page not in st.session_state.page_history:
                    st.session_state.page_history.append(next_page)
                # Navigate to next level
                st.session_state.current_history_index = len(st.session_state.page_history) - 1
                st.rerun()
        
        # Show "Try Again" button if this was unsuccessful
        elif not result.get("goal_achieved"):
            if st.button(f"Try Level {level} Again →", type="primary"):
                # Navigate back to the scenario page for this level
                scenario_page = {"type": "scenario", "level": level}
                # Find the scenario page in history or add it
                try:
                    scenario_index = st.session_state.page_history.index(scenario_page)
                    st.session_state.current_history_index = scenario_index
                except ValueError:
                    # Add scenario page to history if not found
                    st.session_state.page_history.append(scenario_page)
                    st.session_state.current_history_index = len(st.session_state.page_history) - 1
                st.rerun()
    else:
        st.error(f"No evaluation results found for Level {level}")


def _show_evaluation_styles():
    """Show CSS styles for evaluation display"""
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