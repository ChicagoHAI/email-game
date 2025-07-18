"""
Evaluation Display Components

Handles evaluation results and feedback display.
"""

import streamlit as st
from config import MAX_AVAILABLE_LEVEL, MULTI_TURN_LEVELS, MAX_TURNS
from utils import is_multi_recipient_scenario, process_evaluation_text
from .html_helpers import (
    show_evaluation_styles,
    create_success_message,
    create_strategy_warning,
    create_strategy_success
)


def show_level_results(level: float):
    """Show the evaluation results for a level inline"""
    
    result = st.session_state.level_evaluations[level]
    
    # Check if game was just completed and trigger leaderboard
    if st.session_state.get('game_completed', False):
        _show_game_completion()
        return
    
    # Success indicator first
    st.markdown("---")
    st.subheader("📊 Results")
    
    # Show goal achievement status prominently
    _show_goal_achievement_status(result, level)
    
    # Show the recipient reply(ies)
    _show_recipient_replies(result)
    
    # Show the generated rubric (collapsible) - only if rubric toggle is enabled
    _show_rubric_section(result)
    
    # Show the evaluation with improved formatting (collapsible)
    _show_evaluation_section(result)
    
    # Navigation options
    _show_navigation_options(level, result)


def _show_game_completion():
    """Show game completion celebration"""
    st.success("🎊 **GAME COMPLETE!** 🎊")
    st.balloons()  # Celebration animation!
    st.success("🏆 **You are now a Communication Master!** 🏆")
    
    # Wait a moment then redirect to leaderboard
    import time
    time.sleep(1)
    st.session_state.show_leaderboard = True
    st.session_state.game_completed = False  # Clear the flag
    st.rerun()


def _show_goal_achievement_status(result: dict, level: float):
    """Show goal achievement status"""
    if "goal_achieved" in result:
        if result["goal_achieved"]:
            success_message = create_success_message(level)
            st.success(success_message)
            
            # Show strategy analysis for Level 2
            if level == 2 and "strategy_analysis" in result:
                _show_strategy_analysis(result["strategy_analysis"])
                
        else:
            st.error("❌ **Goal Not Achieved** - You can edit your email above and try again.")


def _show_strategy_analysis(strategy_analysis: dict):
    """Show strategy analysis for Level 2"""
    if strategy_analysis.get("used_forbidden_strategies"):
        create_strategy_warning()
        
        # Show details
        with st.expander("📊 Strategy Details", expanded=False):
            if strategy_analysis.get("used_layoff"):
                st.write("❌ **Layoff threats detected** in your email")
            if strategy_analysis.get("used_salary_increase"):
                st.write("❌ **Salary increase offers detected** in your email")
            st.write(f"**Analysis**: {strategy_analysis.get('explanation', 'No explanation available')}")
    else:
        create_strategy_success()


def _show_recipient_replies(result: dict):
    """Show recipient replies"""
    if "recipient_reply" in result:
        # Check if this is a multi-recipient scenario for display formatting
        scenario_filename = st.session_state.get('selected_scenario_file', '')
        is_multi_recipient = is_multi_recipient_scenario(scenario_filename)
        
        if is_multi_recipient:
            st.subheader("📨 Recipients' Replies")
        else:
            st.subheader("📨 Recipient's Reply")
        st.markdown(result["recipient_reply"])


def _show_rubric_section(result: dict):
    """Show rubric section if enabled"""
    use_rubric = st.session_state.get('use_rubric', True)
    if use_rubric and "rubric" in result and result["rubric"]:
        with st.expander("📏 Evaluation Rubric", expanded=False):
            st.markdown(result["rubric"])


def _show_evaluation_section(result: dict):
    """Show evaluation section"""
    with st.expander("🤖 AI Evaluation", expanded=True):
        show_evaluation_styles()
        processed_evaluation = process_evaluation_text(result["evaluation"])
        st.markdown(f'<div class="evaluation-content">{processed_evaluation}</div>', unsafe_allow_html=True)


def _show_navigation_options(level: float, result: dict):
    """Show navigation options after evaluation"""
    st.markdown("---")
    
    # Show "Continue to Next Level" button if successful and next level exists
    if result.get("goal_achieved"):
        _show_success_navigation(level)
    
    # Show "Try Again" hint if unsuccessful
    elif not result.get("goal_achieved"):
        _show_failure_navigation(level, result)


def _show_success_navigation(level: float):
    """Show navigation options for successful completion"""
    from session_manager import is_game_complete
    from ui_user import determine_next_level
    
    # Check if this is the final level completion
    if level == MAX_AVAILABLE_LEVEL and is_game_complete(st.session_state.get('game_session_id')):
        _show_final_completion_options()
    else:
        _show_regular_progression_options(level)


def _show_final_completion_options():
    """Show options for final game completion"""
    st.success("🎊 Congratulations! You have cleared all the levels!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 View Leaderboard", type="primary", use_container_width=True):
            st.session_state.show_leaderboard = True
            st.rerun()
    
    with col2:
        if st.button("🎮 Play Again", use_container_width=True):
            # Clear current session and return to selection screen
            if 'game_session_id' in st.session_state:
                del st.session_state.game_session_id
            st.rerun()


def _show_regular_progression_options(level: float):
    """Show regular level progression options"""
    from config import LEVEL_TO_SCENARIO_MAPPING
    from ui_user import determine_next_level, clean_stale_level_data
    
    next_level = determine_next_level(level, st.session_state)
    
    if next_level is not None and next_level in LEVEL_TO_SCENARIO_MAPPING:
        # Determine button text based on level
        if next_level == 0:
            next_level_display = "Tutorial"
        elif next_level == 2.5:
            next_level_display = "Challenge Level 2.5"
        else:
            next_level_display = f"Level {next_level}"
        
        button_text = f"Continue to {next_level_display} →"
        
        if st.button(button_text, type="primary", use_container_width=True):
            st.session_state.current_level = next_level
            # Clean up stale level data
            clean_stale_level_data(next_level, st.session_state)
            st.rerun()
    else:
        # All levels completed!
        st.success("🎊 **Congratulations!** You've completed all available levels!")


def _show_failure_navigation(level: float, result: dict):
    """Show navigation options for failed attempts"""
    # Special handling for Level 4 when max turns reached
    if level in MULTI_TURN_LEVELS and result.get("max_turns_reached"):
        _show_multi_turn_restart_option(level)
    else:
        st.info("💡 **Tip:** Edit your email above and click Send again to improve your result!")


def _show_multi_turn_restart_option(level: float):
    """Show restart option for multi-turn levels"""
    st.info("💡 **Level 4 ended after maximum turns.** You can restart the level to try a different approach.")
    
    if st.button("🔄 Restart Level 4", type="secondary", use_container_width=True):
        from ui_components.turn_management import handle_turn_restart
        
        session_id = st.session_state.get('game_session_id')
        if session_id and handle_turn_restart(session_id, level):
            st.rerun()


def show_evaluation_error(error_message: str):
    """Show evaluation error message"""
    st.error(f"❌ **Evaluation Error:** {error_message}")
    st.info("💡 **Please try again** - this was likely a temporary issue.")


def show_email_submission_validation(email_content: str, api_keys_available: bool):
    """Show validation messages for email submission"""
    if not email_content.strip():
        st.error("Please write an email before submitting!")
        return False
    elif not api_keys_available:
        st.error("API keys not available")
        return False
    return True


def show_turn_evaluation_result(level: float, turn_number: int, goal_achieved: bool, 
                               recipient_reply: str, max_turns_reached: bool = False):
    """Show evaluation result for a single turn in multi-turn levels"""
    if goal_achieved:
        st.success(f"🎯 **Goal achieved in Turn {turn_number}!**")
    elif max_turns_reached:
        st.info(f"📧 **Turn {turn_number} completed.** Maximum turns reached.")
    else:
        st.info(f"📧 **Turn {turn_number} completed.** Continue the conversation to achieve your goal.")
    
    # Show Adam's response
    if recipient_reply:
        st.markdown("**Adam's Response:**")
        from .html_helpers import create_recipient_reply_display
        reply_html = create_recipient_reply_display(recipient_reply)
        st.markdown(reply_html, unsafe_allow_html=True) 