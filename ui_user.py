"""
User Mode UI Components

This module contains UI components specific to the user mode,
including the level-based navigation system with inline results.
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
from evaluation import process_email_evaluation_user_mode_inline


def show_user_interface_with_levels(available_scenarios, api_keys_available):
    """Show the user interface with level-based navigation"""
    
    # Set default model for user version (no sidebar configuration)
    model = DEFAULT_MODEL
    
    # Use the global level mapping
    level_to_scenario_mapping = LEVEL_TO_SCENARIO_MAPPING
    max_level = MAX_AVAILABLE_LEVEL
    total_levels = len(level_to_scenario_mapping)  # Total number of levels available
    
    # Get current level (default to 0 if not set)
    current_level = st.session_state.get('current_level', 0)
    
    # Navigation header with level controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        # Previous level button
        can_go_back = current_level > 0
        if st.button("← Previous Level", disabled=not can_go_back, help="Go to previous level"):
            st.session_state.current_level = current_level - 1
            st.rerun()
    
    with col2:
        # Current level indicator
        level_display = "Tutorial" if current_level == 0 else f"Level {current_level}"
        st.markdown(f"**🎮 {level_display}**")
    
    with col3:
        # Next level button (only if level is completed and next level exists)
        next_level = current_level + 1
        can_go_forward = (next_level in level_to_scenario_mapping and 
                         current_level in st.session_state.get('completed_levels', set()))
        if st.button("Next Level →", disabled=not can_go_forward, help="Go to next level"):
            st.session_state.current_level = next_level
            st.rerun()
    
    # Level progression info
    st.info("🎯 **Level Progression**: Complete levels to unlock the next ones!")
    
    # Show overall progress
    completed_count = len(st.session_state.get('completed_levels', set()))
    # Cap progress at 100% to prevent crashes
    progress_percentage = min((completed_count / total_levels) * 100, 100) if total_levels > 0 else 0
    st.progress(progress_percentage / 100)
    st.caption(f"Progress: {min(completed_count, total_levels)}/{total_levels} levels completed ({progress_percentage:.0f}%)")
    
    # Show the current level page
    show_level_page(current_level, available_scenarios, level_to_scenario_mapping, api_keys_available, model)


def show_level_page(level, available_scenarios, level_to_scenario_mapping, api_keys_available, model):
    """Show a complete level page with scenario, email input, and results"""
    
    # Get backend scenario ID from user level
    backend_scenario_id = level_to_scenario_mapping.get(level, "5.0")
    
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
    
    # Email input section
    st.subheader("✍️ Your Email")
    
    # Pre-populate email if returning to a completed level
    initial_email_value = ""
    if level in st.session_state.get('level_emails', {}):
        initial_email_value = st.session_state.level_emails[level]
    
    # Email text area - uses unique key per level
    email_content = st.text_area(
        "Write your email here",
        value=initial_email_value,
        height=400,
        max_chars=EMAIL_MAX_CHARS,
        placeholder="Type your email response to the scenario above...",
        help="Write the best email you can for the given scenario",
        key=f"email_input_level_{level}"
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
            # Process email evaluation inline (like developer mode)
            process_email_evaluation_user_mode_inline(scenario_content, email_content, model, level)
    
    # Show results if available for this level
    if level in st.session_state.get('level_evaluations', {}):
        show_level_results(level)


def show_level_results(level):
    """Show the evaluation results for a level inline"""
    
    result = st.session_state.level_evaluations[level]
    
    # Success indicator first
    st.markdown("---")
    st.subheader("📊 Results")
    
    # Show goal achievement status prominently
    if "goal_achieved" in result:
        if result["goal_achieved"]:
            st.success("🎉 **Success!** You persuaded the recipient and completed this level!")
        else:
            st.error("❌ **Goal Not Achieved** - You can edit your email above and try again.")

    # Show the recipient reply
    if "recipient_reply" in result:
        st.subheader("📨 Recipient's Reply")
        st.markdown(result["recipient_reply"])
    
    # Show the generated rubric (collapsible) - only if rubric toggle is enabled
    use_rubric = st.session_state.get('use_rubric', True)
    if use_rubric and "rubric" in result and result["rubric"]:
        with st.expander("📏 Evaluation Rubric", expanded=False):
            st.markdown(result["rubric"])
    
    # Show the evaluation with improved formatting (collapsible)
    with st.expander("🤖 AI Evaluation", expanded=True):
        _show_evaluation_styles()
        processed_evaluation = process_evaluation_text(result["evaluation"])
        st.markdown(f'<div class="evaluation-content">{processed_evaluation}</div>', unsafe_allow_html=True)
    
    # Navigation options
    st.markdown("---")
    
    # Show "Continue to Next Level" button if successful and next level exists
    next_level = level + 1
    if result.get("goal_achieved") and next_level in LEVEL_TO_SCENARIO_MAPPING:
        next_level_display = "Tutorial" if next_level == 0 else f"Level {next_level}"
        
        if st.button(f"Continue to {next_level_display} →", type="primary", use_container_width=True):
            st.session_state.current_level = next_level
            st.rerun()
    elif result.get("goal_achieved"):
        # All levels completed!
        st.success("🎊 **Congratulations!** You've completed all available levels!")
    
    # Show "Try Again" hint if unsuccessful
    elif not result.get("goal_achieved"):
        st.info("💡 **Tip:** Edit your email above and click Send again to improve your result!")


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