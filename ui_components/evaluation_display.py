"""
Evaluation Display Components

Handles evaluation results and feedback display.
"""

import streamlit as st
from config import MAX_AVAILABLE_LEVEL, MULTI_TURN_LEVELS, MAX_TURNS
from utils import is_multi_recipient_scenario, process_evaluation_text
from .shared_components import show_evaluation_styles
from .shared_components import (
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
    
    # DEBUG: Show persistent majority reply analysis (TODO: Remove after debugging)
    _show_debug_reply_analysis(level)
    
    # DEBUG: Show consistency validation analysis for successful emails
    show_consistency_analysis(level)
    
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
            
            # Show strategy analysis for Level 3
            if level == 3 and "strategy_analysis" in result:
                _show_strategy_analysis(result["strategy_analysis"])
                
        else:
            st.error("❌ **Goal Not Achieved** - You can edit your email above and try again.")


def _show_strategy_analysis(strategy_analysis: dict):
    """Show strategy analysis for Level 3"""
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
        elif next_level == 3.5:
            next_level_display = "Challenge Level 3.5"
        else:
            next_level_display = f"Level {next_level}"
        
        button_text = f"Continue to {next_level_display} →"
        
        if st.button(button_text, type="primary", use_container_width=True):
            st.session_state.current_level = next_level
            # Clean up stale level data
            clean_stale_level_data(next_level, st.session_state)
            
            # Reset Gmail inbox state to show inbox view first (not opened email)
            st.session_state.gmail_view = 'inbox'  # Show inbox, not email view
            if 'selected_email_id' in st.session_state:
                del st.session_state.selected_email_id
            st.session_state.show_scenario_email = False  # Hide email input until user clicks email
            
            # Clear previous level's email content
            if 'level_emails' in st.session_state:
                del st.session_state.level_emails
            
            # Update URL parameters to match navigation
            session_id = st.session_state.get('game_session_id')
            if session_id:
                _clear_url_navigation_state_for_evaluation(next_level, session_id)
            
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


def _clear_url_navigation_state_for_evaluation(level: float, session_id: str):
    """Clear URL navigation state when navigating via evaluation completion"""
    try:
        import streamlit as st
        
        # Clear URL navigation processing flags
        if 'url_navigation_processed' in st.session_state:
            del st.session_state.url_navigation_processed
            
        # Update URL to show only session (no gang_level)
        st.query_params.update({"session": session_id})
        
    except Exception as e:
        # URL updates are not critical
        pass 


def _show_debug_reply_analysis(level: float):
    """Show persistent debug information from majority reply analysis"""
    # Check if debug data exists for this level
    debug_data = st.session_state.get('debug_reply_data', {}).get(level)
    
    if not debug_data:
        return
    
    # Check if this is multi-recipient data (Level 2) or single recipient
    if isinstance(debug_data, dict) and any(isinstance(v, dict) and 'all_replies' in v for v in debug_data.values()):
        # Multi-recipient scenario (Level 2)
        with st.expander(f"🔍 Debug: Multi-Recipient Majority Reply Analysis", expanded=False):
            for recipient_name, reply_data in debug_data.items():
                st.markdown(f"### {recipient_name.title()}'s Analysis")
                
                all_replies = reply_data.get('all_replies', [])
                outcomes = reply_data.get('outcome_analysis', {}).get('outcomes', [])
                evaluations = reply_data.get('outcome_analysis', {}).get('evaluations', [])
                majority_outcome = reply_data.get('majority_outcome', 'Unknown')
                outcome_counts = reply_data.get('outcome_counts', {})
                selected_reply = reply_data.get('reply', '')
                
                st.markdown(f"**Majority Outcome:** `{majority_outcome}`")
                st.markdown(f"**Distribution:** {dict(outcome_counts)}")
                
                # Show all replies with their outcomes
                st.markdown(f"**{recipient_name.title()}'s Generated Replies:**")
                for i, (reply, outcome) in enumerate(zip(all_replies, outcomes)):
                    is_selected = reply == selected_reply
                    status_icon = "👑" if is_selected else "📧"
                    outcome_color = {
                        'PASS': '✅',
                        'FAIL': '❌'
                    }.get(outcome, '⚪')
                    
                    selection_text = " (SELECTED)" if is_selected else ""
                    st.markdown(f"{status_icon} **Reply {i+1}** - {outcome_color} {outcome}{selection_text}")
                    
                    # Show reply content
                    st.markdown("**Reply Content:**")
                    st.code(reply, language=None)
                    
                    # Show evaluation for this reply
                    if i < len(evaluations):
                        st.markdown("**Evaluation:**")
                        evaluation_text = evaluations[i]
                        # Keep full evaluation text so decision isn't cut off
                        st.text_area(
                            f"{recipient_name.title()} Reply {i+1} Evaluation",
                            value=evaluation_text,
                            height=200,
                            key=f"eval_persist_{recipient_name}_{i}_{hash(reply[:20])}",
                            disabled=True
                        )
                    
                    if i < len(all_replies) - 1:  # Not the last reply
                        st.markdown("---")
                
                if recipient_name != list(debug_data.keys())[-1]:  # Not the last recipient
                    st.markdown("---")
    else:
        # Single recipient scenario
        all_replies = debug_data.get('all_replies', [])
        outcomes = debug_data.get('outcome_analysis', {}).get('outcomes', [])
        evaluations = debug_data.get('outcome_analysis', {}).get('evaluations', [])
        majority_outcome = debug_data.get('majority_outcome', 'Unknown')
        outcome_counts = debug_data.get('outcome_counts', {})
        selected_reply = debug_data.get('reply', '')
        
        if not all_replies:
            return
        
        with st.expander(f"🔍 Debug: Majority Reply Analysis ({len(all_replies)} samples)", expanded=False):
            st.markdown(f"**Majority Outcome:** `{majority_outcome}`")
            st.markdown(f"**Distribution:** {dict(outcome_counts)}")
            
            # Show all replies with their outcomes (without nested expanders)
            st.markdown("**All Generated Replies:**")
            for i, (reply, outcome) in enumerate(zip(all_replies, outcomes)):
                is_selected = reply == selected_reply
                status_icon = "👑" if is_selected else "📧"
                outcome_color = {
                    'PASS': '✅',
                    'FAIL': '❌'
                }.get(outcome, '⚪')
                
                selection_text = " (SELECTED)" if is_selected else ""
                st.markdown(f"{status_icon} **Reply {i+1}** - {outcome_color} {outcome}{selection_text}")
                
                # Show reply content
                st.markdown("**Reply Content:**")
                st.code(reply, language=None)
                
                # Show evaluation for this reply
                if i < len(evaluations):
                    st.markdown("**Evaluation:**")
                    evaluation_text = evaluations[i]
                    # Keep full evaluation text so decision isn't cut off
                    st.text_area(
                        f"Reply {i+1} Evaluation",
                        value=evaluation_text,
                        height=200,
                        key=f"eval_persist_single_{i}_{hash(reply[:20])}",
                        disabled=True
                    )
                
                if i < len(all_replies) - 1:  # Not the last reply
                    st.markdown("---")


def show_consistency_analysis(level: float):
    """Show consistency validation analysis for a level"""
    consistency_data = st.session_state.get('consistency_data', {}).get(level)
    
    if not consistency_data:
        return
    
    consistency_score = consistency_data.get('consistency_score', 0)
    is_consistent = consistency_data.get('is_consistent', False)
    analysis = consistency_data.get('analysis', '')
    
    # Determine expander color and icon based on consistency
    if is_consistent:
        expander_icon = "✅"
        expander_title = f"Email Consistency Validation - CONSISTENT ({consistency_score:.1%})"
    else:
        expander_icon = "⚠️"
        expander_title = f"Email Consistency Validation - POTENTIALLY ADVERSARIAL ({consistency_score:.1%})"
    
    with st.expander(f"{expander_icon} Debug: {expander_title}", expanded=False):
        st.markdown(f"**Consistency Score:** `{consistency_score:.1%}`")
        st.markdown(f"**Assessment:** {'CONSISTENT' if is_consistent else 'INCONSISTENT'}")
        
        if analysis:
            st.markdown("**Analysis Summary:**")
            st.text(analysis)
        
        if not is_consistent:
            st.warning("⚠️ This email may be using adversarial techniques that don't work when paraphrased.")
        else:
            st.success("✅ This email appears to achieve its goal through genuine effective communication.")
        
        st.markdown("---")
        
        # Check if this is multi-recipient results
        recipient_results = consistency_data.get('recipient_results')
        if recipient_results:
            # Multi-recipient scenario - show results for each recipient
            st.markdown("**Multi-Recipient Paraphrase Testing Results:**")
            for recipient_name, recipient_result in recipient_results.items():
                st.markdown(f"### {recipient_name.title()}'s Consistency Results")
                
                paraphrases = recipient_result.get('paraphrases', [])
                paraphrase_outcomes = recipient_result.get('paraphrase_outcomes', [])
                paraphrase_replies = recipient_result.get('paraphrase_replies', [])
                
                for i, (paraphrase, outcome, reply) in enumerate(zip(paraphrases, paraphrase_outcomes, paraphrase_replies)):
                    outcome_color = {
                        'PASS': '✅',
                        'FAIL': '❌'
                    }.get(outcome, '⚪')
                    
                    st.markdown(f"**Paraphrase {i+1}** - {outcome_color} {outcome}")
                    
                    # Show paraphrase content
                    st.markdown("**Paraphrased Email:**")
                    st.code(paraphrase, language=None)
                    
                    # Show recipient reply
                    if reply:
                        st.markdown(f"**{recipient_name.title()}'s Reply:**")
                        st.code(reply, language=None)
                    else:
                        st.markdown(f"**{recipient_name.title()}'s Reply:** *Failed to generate*")
                    
                    if i < len(paraphrases) - 1:  # Not the last paraphrase
                        st.markdown("---")
                
                if recipient_name != list(recipient_results.keys())[-1]:  # Not the last recipient
                    st.markdown("---")
        else:
            # Single recipient scenario - show paraphrase results
            paraphrases = consistency_data.get('paraphrases', [])
            paraphrase_outcomes = consistency_data.get('paraphrase_outcomes', [])
            paraphrase_replies = consistency_data.get('paraphrase_replies', [])
            
            st.markdown("**Paraphrase Testing Results:**")
            for i, (paraphrase, outcome, reply) in enumerate(zip(paraphrases, paraphrase_outcomes, paraphrase_replies)):
                outcome_color = {
                    'PASS': '✅',
                    'FAIL': '❌'
                }.get(outcome, '⚪')
                
                st.markdown(f"**Paraphrase {i+1}** - {outcome_color} {outcome}")
                
                # Show paraphrase content
                st.markdown("**Paraphrased Email:**")
                st.code(paraphrase, language=None)
                
                # Show recipient reply
                if reply:
                    st.markdown("**Recipient Reply:**")
                    st.code(reply, language=None)
                else:
                    st.markdown("**Recipient Reply:** *Failed to generate*")
                
                if i < len(paraphrases) - 1:  # Not the last paraphrase
                    st.markdown("---")