"""
User Mode UI - Refactored Version

Refactored user interface using modular components.
This replaces the original ui_user.py with a cleaner, more maintainable structure.
"""

import streamlit as st
from config import (
    LEVEL_TO_SCENARIO_MAPPING,
    MAX_AVAILABLE_LEVEL,
    DEFAULT_MODEL,
    MAX_TURNS,
    MULTI_TURN_LEVELS
)
from session_manager import (
    session_exists,
    save_session_progress,
    get_conversation_history,
    get_next_turn_number,
    is_level_complete_multi_turn,
    handle_level_success,
    update_turn_and_clear_future,
    get_database_session,
    SessionEmailSubmission,
    EvaluationResult
)
from evaluation import (
    process_email_evaluation_user_mode_inline,
    process_email_evaluation_user_mode_multi_turn
)

# Import new modular components
from ui_components.session_interface import (
    show_session_selection_screen,
    show_session_header
)
from ui_components.level_interface import (
    show_level_navigation,
    show_scenario_section,
    show_gmail_inbox_section,
    show_additional_emails,
    create_email_input_section,
    create_submit_button,
    show_level_progression_logic,
    get_scenario_data
)
from ui_components.turn_management import (
    show_conversation_history,
    show_turn_status,
    get_current_turn_info,
    create_turn_email_input
)
from ui_components.evaluation_display import (
    show_level_results,
    show_email_submission_validation
)
from ui_components.leaderboard_interface import (
    check_and_show_leaderboard_trigger
)


def show_user_interface_with_levels(available_scenarios, api_keys_available):
    """Main entry point for user mode - handles session selection and game interface"""
    
    # Check if user has a valid session
    game_session_id = st.session_state.get('game_session_id')
    
    if not game_session_id or not session_exists(game_session_id):
        # Show session selection screen
        show_session_selection_screen()
    else:
        # Show the game interface with session ID
        show_game_interface_with_session(available_scenarios, api_keys_available, game_session_id)


def show_game_interface_with_session(available_scenarios, api_keys_available, session_id):
    """Show the main game interface with session information"""
    
    # Check if we should show the leaderboard
    if check_and_show_leaderboard_trigger(session_id):
        return
    
    # Display session header
    show_session_header(session_id)
    
    # Show the level-based game interface
    show_level_based_game_interface(available_scenarios, api_keys_available, session_id)


def show_level_based_game_interface(available_scenarios, api_keys_available, session_id):
    """Show the level-based game interface"""
    
    # Set default model for user version
    model = DEFAULT_MODEL
    
    # Get current level (default to 0 if not set)
    current_level = st.session_state.get('current_level', 0)
    
    # Clean up any stale level data on interface load
    clean_stale_level_data(current_level, st.session_state)
    
    # Show level navigation
    show_level_navigation(session_id, current_level)
    
    # Show the current level page
    show_level_page(current_level, available_scenarios, api_keys_available, model, session_id)


def show_level_page(level, available_scenarios, api_keys_available, model, session_id):
    """Show a complete level page with scenario, email input, and results"""
    
    # Get scenario data
    scenario_content = get_scenario_data(level, available_scenarios)
    
    # Show Gmail inbox section instead of traditional scenario
    show_gmail_inbox_section(scenario_content, level)
    
    # Show additional emails if available
    scenario_filename = st.session_state.get('selected_scenario_file', '')
    show_additional_emails(scenario_filename)
    
    # Show level-specific progression logic
    show_level_progression_logic(level)
    
    # Handle multi-turn vs single-turn levels - only show email input if scenario email is selected
    if st.session_state.get('show_scenario_email', False):
        if level in MULTI_TURN_LEVELS:
            handle_multi_turn_level(session_id, level, scenario_content, model, api_keys_available)
        else:
            handle_single_turn_level(session_id, level, scenario_content, model, api_keys_available)
    
    # Show results if available
    if level in st.session_state.get('level_evaluations', {}):
        # For multi-turn levels, only show final results when level is complete
        if level in MULTI_TURN_LEVELS:
            # Check if level should show final results
            level_evaluation = st.session_state.level_evaluations[level]
            show_final_results = (
                level_evaluation.get('goal_achieved', False) or 
                level_evaluation.get('max_turns_reached', False)
            )
            if show_final_results:
                show_level_results(level)
        else:
            # For single-turn levels, always show results
            show_level_results(level)


def handle_multi_turn_level(session_id, level, scenario_content, model, api_keys_available):
    """Handle multi-turn level display and interaction"""
    
    # Show conversation history
    show_conversation_history(session_id, level)
    
    # Show turn status and determine if input should be shown
    show_input = show_turn_status(session_id, level, MAX_TURNS)
    
    # Check if turn limit has been reached and set evaluation state if needed
    if not show_input:
        turn_info = get_current_turn_info(session_id, level)
        current_turn = turn_info['current_turn']
        
        # If turn limit reached and no evaluation data exists, create it
        if (current_turn > MAX_TURNS and 
            level not in st.session_state.get('level_evaluations', {})):
            
            # Create evaluation data for turn limit reached using actual evaluation from last turn
            conversation_history = get_conversation_history(session_id, level)
            last_turn = conversation_history[-1] if conversation_history else None
            
            if last_turn:
                evaluation_data = {
                    "scenario": scenario_content,
                    "email": last_turn['email_content'],
                    "recipient_reply": last_turn['recipient_reply'] or "",
                    "rubric": last_turn.get('rubric'),  # Use rubric from last turn if available
                    "evaluation": last_turn['evaluation_result'] or "Turn limit reached without achieving the goal.",
                    "goal_achieved": False,  # Since we reached turn limit, goal was not achieved
                    "turn_number": last_turn['turn_number'],
                    "max_turns_reached": True
                }
                
                # Store the max_turns_reached flag in the database for persistence
                _store_max_turns_reached_flag(session_id, level, last_turn['turn_number'])
            else:
                # Fallback if no conversation history exists
                evaluation_data = {
                    "scenario": scenario_content,
                    "email": "",
                    "recipient_reply": "",
                    "rubric": None,
                    "evaluation": "Turn limit reached without achieving the goal.",
                    "goal_achieved": False,
                    "turn_number": MAX_TURNS,
                    "max_turns_reached": True
                }
            
            if 'level_evaluations' not in st.session_state:
                st.session_state.level_evaluations = {}
            st.session_state.level_evaluations[level] = evaluation_data
    
    if show_input:
        # Email input section for multi-turn
        st.subheader("✍️ Your Email")
        
        turn_info = get_current_turn_info(session_id, level)
        current_turn = turn_info['current_turn']
        
        email_content = create_turn_email_input(level, current_turn, MAX_TURNS)
        
        # Submit button for multi-turn
        if st.button(
            "📝 Send",
            type="primary",
            disabled=not api_keys_available or not email_content.strip(),
            help="Submit your email for AI evaluation"
        ):
            if show_email_submission_validation(email_content, api_keys_available):
                # Process multi-turn email evaluation
                process_email_evaluation_user_mode_multi_turn(
                    scenario_content, email_content, model, level, session_id, current_turn
                )


def handle_single_turn_level(session_id, level, scenario_content, model, api_keys_available):
    """Handle single-turn level display and interaction"""
    
    # Create email input section
    email_content = create_email_input_section(level, api_keys_available)
    
    # Submit button
    if create_submit_button(api_keys_available, email_content):
        if show_email_submission_validation(email_content, api_keys_available):
            # Process single-turn email evaluation
            process_email_evaluation_user_mode_inline(
                scenario_content, email_content, model, level, session_id
            )


def handle_turn_edit(session_id: str, level: float, turn_number: int, new_email_content: str):
    """
    Handle editing a turn: update database, clear future turns, and re-evaluate.
    """
    # Step 1: Update database and clear future turns
    success = update_turn_and_clear_future(session_id, level, turn_number, new_email_content)
    
    if success:
        # Step 2: Clear session state
        if level in st.session_state.get('level_evaluations', {}):
            del st.session_state.level_evaluations[level]
        
        completed_levels = st.session_state.get('completed_levels', set())
        if level in completed_levels:
            completed_levels.remove(level)
        
        # Step 3: Re-evaluate the edited turn
        st.info(f"🔄 Re-evaluating Turn {turn_number} with your updated email...")
        
        # Load scenario content
        scenario_content = st.session_state.get('selected_scenario', '')
        model = DEFAULT_MODEL
        
        # Re-evaluate the existing turn
        re_evaluate_existing_turn(session_id, level, turn_number, new_email_content, scenario_content, model)
        
        # Force page refresh
        st.rerun()
    else:
        st.error("❌ Failed to update turn. Please try again.")


def re_evaluate_existing_turn(session_id: str, level: float, turn_number: int, 
                             email_content: str, scenario_content: str, model: str):
    """Re-evaluate an existing turn with updated email content."""
    
    try:
        from models import EmailRecipient, EmailEvaluator, RubricGenerator
        from utils import load_recipient_prompt, extract_goal_achievement_score
        
        # Initialize AI services
        email_recipient = EmailRecipient()
        email_evaluator = EmailEvaluator()
        rubric_generator = RubricGenerator()
        
        # Get conversation history up to this turn
        conversation_history = get_conversation_history(session_id, level)
        conversation_context = _build_conversation_context(conversation_history, turn_number)
        
        # Load recipient prompt and add conversation context
        scenario_file = st.session_state.get('selected_scenario_file', 'scenario_5.4.txt')
        recipient_prompt = load_recipient_prompt(scenario_file)
        contextualized_prompt = (
            recipient_prompt + conversation_context + 
            f"\n\nNow respond to this new email from HR:\n{email_content}"
        )
        
        # Load rubric for evaluation-based majority voting
        use_rubric = st.session_state.get('use_rubric', True)
        rubric = None
        if use_rubric:
            rubric = rubric_generator.get_or_generate_rubric(scenario_content, scenario_file, model)
        
        # Generate Adam's new response with majority voting
        with st.status("Generating Adam's response (using 5 concurrent samples for consistency)...", expanded=False) as status:
            reply_result = email_recipient.generate_reply_with_majority(
                contextualized_prompt, email_content, model, num_samples=5,
                scenario=scenario_content, rubric=rubric, scenario_filename=scenario_file
            )
            if not reply_result:
                st.error("Failed to generate Adam's reply")
                return
            
            recipient_reply = reply_result['reply']
            majority_outcome = reply_result['majority_outcome']
            outcome_counts = reply_result['outcome_counts']
            
            status.update(label=f"✅ Adam's response generated! (Majority: {majority_outcome}, Distribution: {outcome_counts})", state="complete")
        
        # Store debug info in session state so it persists in results
        if 'debug_reply_data' not in st.session_state:
            st.session_state.debug_reply_data = {}
        st.session_state.debug_reply_data[level] = reply_result
        
        # Generate evaluation
        with st.status("Evaluating updated email...", expanded=False) as status:
            evaluation_result = _generate_evaluation(
                email_evaluator, rubric_generator, scenario_content, conversation_context,
                email_content, recipient_reply, model
            )
            if not evaluation_result:
                st.error("Failed to evaluate email")
                return
            status.update(label="✅ Evaluation complete!", state="complete")
        
        # Update database with new evaluation
        _update_turn_evaluation(session_id, level, turn_number, evaluation_result)
        
        # Show updated response
        from ui_components.html_helpers import create_updated_response_display
        st.markdown("**🔄 Adam's Updated Response:**")
        response_html = create_updated_response_display(recipient_reply)
        st.markdown(response_html, unsafe_allow_html=True)
        
        # Handle level success if goal achieved
        if evaluation_result['goal_achieved']:
            st.success(f"🎯 **Goal achieved in Turn {turn_number}!**")
            
            level_success = handle_level_success(session_id, level)
            if level_success:
                # Add to completed levels
                if 'completed_levels' not in st.session_state:
                    st.session_state.completed_levels = set()
                st.session_state.completed_levels.add(level)
                
                # Store final evaluation results in session state for show_level_results
                # Only store when goal is achieved (final result)
                if 'level_evaluations' not in st.session_state:
                    st.session_state.level_evaluations = {}
                st.session_state.level_evaluations[level] = evaluation_result
        else:
            st.info(f"📧 **Turn {turn_number} updated.** Continue the conversation to achieve your goal.")
            
            # Don't store in level_evaluations for intermediate results
            # This prevents premature final verdict display
        
        st.success("🔄 Turn updated successfully! The page will refresh to show the new response.")
        
    except Exception as e:
        st.error(f"❌ Error re-evaluating turn: {str(e)}")
    
    # Force page refresh
    st.rerun()


def _build_conversation_context(conversation_history, turn_number):
    """Build conversation context for re-evaluation"""
    conversation_context = ""
    
    if conversation_history:
        conversation_context = "\n\nPrevious conversation:\n"
        for turn_data in conversation_history:
            if turn_data['turn_number'] < turn_number:
                conversation_context += f"\nTurn {turn_data['turn_number']}:\n"
                conversation_context += f"HR: {turn_data['email_content']}\n"
                if turn_data['recipient_reply']:
                    conversation_context += f"Adam: {turn_data['recipient_reply']}\n"
    
    return conversation_context


def _display_majority_reply_debug(reply_result: dict, expanded: bool = False, unique_id: str = ""):
    """
    Display debugging information for majority reply generation.
    
    Args:
        reply_result: Result from generate_reply_with_majority
        expanded: Whether to show the expander expanded by default
    """
    if not reply_result:
        return
    
    # Get data from result
    all_replies = reply_result.get('all_replies', [])
    outcomes = reply_result.get('outcome_analysis', {}).get('outcomes', [])
    majority_outcome = reply_result.get('majority_outcome', 'Unknown')
    outcome_counts = reply_result.get('outcome_counts', {})
    selected_reply = reply_result.get('reply', '')
    
    with st.expander(f"🔍 Debug: Majority Reply Analysis ({len(all_replies)} samples)", expanded=expanded):
        st.markdown(f"**Majority Outcome:** `{majority_outcome}`")
        st.markdown(f"**Distribution:** {dict(outcome_counts)}")
        
        # Show all replies with their outcomes (without nested expanders)
        st.markdown("**All Generated Replies:**")
        for i, (reply, outcome) in enumerate(zip(all_replies, outcomes)):
            is_selected = reply == selected_reply
            status_icon = "👑" if is_selected else "📧"
            outcome_color = {
                'POSITIVE': '🟢',
                'NEGATIVE': '🔴', 
                'NEUTRAL': '🟡'
            }.get(outcome, '⚪')
            
            selection_text = " (SELECTED)" if is_selected else ""
            st.markdown(f"{status_icon} **Reply {i+1}** - {outcome_color} {outcome}{selection_text}")
            
            # Show reply content in a code block instead of nested expander
            st.code(reply, language=None)


def _generate_evaluation(email_evaluator, rubric_generator, scenario_content, 
                        conversation_context, email_content, recipient_reply, model):
    """Generate evaluation for re-evaluated turn"""
    
    # Load rubric if needed
    use_rubric = st.session_state.get('use_rubric', True)
    rubric = None
    if use_rubric:
        scenario_filename = st.session_state.get("selected_scenario_file", "")
        rubric = rubric_generator.get_or_generate_rubric(scenario_content, scenario_filename, model)
    
    # Build evaluation context
    evaluation_context = (
        scenario_content + conversation_context + 
        f"\n\nLatest email from HR:\n{email_content}\n\nAdam's response:\n{recipient_reply}"
    )
    
    # Generate evaluation
    evaluation = email_evaluator.evaluate_email(
        evaluation_context, 
        email_content, 
        rubric, 
        recipient_reply, 
        model,
        scenario_filename=st.session_state.get("selected_scenario_file")
    )
    
    if not evaluation:
        return None
    
    from utils import extract_goal_achievement_score
    goal_achieved = extract_goal_achievement_score(evaluation)
    
    return {
        'evaluation': evaluation,
        'recipient_reply': recipient_reply,
        'rubric': rubric,
        'goal_achieved': goal_achieved
    }


def _update_turn_evaluation(session_id, level, turn_number, evaluation_result):
    """Update turn evaluation in database"""
    
    db_session = get_database_session()
    try:
        # Find the existing submission
        submission = db_session.query(SessionEmailSubmission).filter(
            SessionEmailSubmission.session_id == session_id,
            SessionEmailSubmission.level == level,
            SessionEmailSubmission.turn_number == turn_number
        ).first()
        
        if submission:
            # Delete old evaluation result
            db_session.query(EvaluationResult).filter_by(submission_id=submission.id).delete()
            
            # Create new evaluation result
            evaluation_result_obj = EvaluationResult(
                submission_id=submission.id,
                evaluation_text=evaluation_result['evaluation'],
                recipient_reply=evaluation_result['recipient_reply'],
                rubric=evaluation_result['rubric'],
                goal_achieved=evaluation_result['goal_achieved']
            )
            
            db_session.add(evaluation_result_obj)
            db_session.commit()
            
            # Don't automatically update session state here
            # Let the caller decide when to store final results
            # This prevents intermediate turn results from triggering final verdict display
            
    finally:
        db_session.close()


def _store_max_turns_reached_flag(session_id: str, level: float, turn_number: int):
    """Store max_turns_reached flag in database by updating the evaluation text"""
    
    db_session = get_database_session()
    try:
        # Find the existing submission
        submission = db_session.query(SessionEmailSubmission).filter(
            SessionEmailSubmission.session_id == session_id,
            SessionEmailSubmission.level == level,
            SessionEmailSubmission.turn_number == turn_number
        ).first()
        
        if submission:
            # Get the evaluation result
            evaluation = db_session.query(EvaluationResult).filter_by(
                submission_id=submission.id
            ).first()
            
            if evaluation:
                # Update the evaluation text to include max_turns_reached flag
                current_evaluation = evaluation.evaluation_text or ""
                if "MAX_TURNS_REACHED" not in current_evaluation:
                    updated_evaluation = current_evaluation + "\n\n[MAX_TURNS_REACHED]"
                    evaluation.evaluation_text = updated_evaluation
                    db_session.commit()
            
    except Exception as e:
        db_session.rollback()
        raise e
    finally:
        db_session.close()


def determine_next_level(current_level, session_state):
    """Determine the next level based on current level and conditional progression rules."""
    
    # Level 3 conditional progression (formerly Level 2)
    if current_level == 3:
        strategy_analysis = session_state.get('strategy_analysis', {}).get(3)
        completed_levels = session_state.get('completed_levels', set())
        
        used_forbidden_strategies = (
            strategy_analysis and strategy_analysis.get('used_forbidden_strategies')
        ) or (3.5 in completed_levels)
        
        if used_forbidden_strategies:
            return 3.5
        else:
            return 4
    
    # Level 3.5 always goes to Level 4 (formerly Level 2.5 going to Level 3)
    if current_level == 3.5:
        return 4
    
    # Standard progression for all other levels
    return current_level + 1


def determine_previous_level(current_level, session_state):
    """Determine the previous level based on current level and conditional progression rules."""
    
    # Level 4 can come from either Level 3 or Level 3.5 (formerly Level 3 could come from Level 2 or Level 2.5)
    if current_level == 4:
        strategy_analysis = session_state.get('strategy_analysis', {}).get(3)
        completed_levels = session_state.get('completed_levels', set())
        
        used_forbidden_strategies = (
            strategy_analysis and strategy_analysis.get('used_forbidden_strategies')
        ) or (3.5 in completed_levels)
        
        if used_forbidden_strategies:
            return 3.5
        else:
            return 3
    
    # Level 3.5 always comes from Level 3 (formerly Level 2.5 always came from Level 2)
    if current_level == 3.5:
        return 3
    
    # Standard progression for all other levels
    if current_level > 0:
        return current_level - 1
    else:
        return None


def clean_stale_level_data(current_level, session_state):
    """Clean up stale level data that might make levels appear as completed when they shouldn't be."""
    
    completed_levels = session_state.get('completed_levels', set())
    level_evaluations = session_state.get('level_evaluations', {})
    
    # Clean up evaluations for levels that shouldn't be accessible yet
    levels_to_clean = []
    
    for eval_level in level_evaluations.keys():
        if eval_level != current_level and eval_level not in completed_levels:
            if eval_level > current_level:
                levels_to_clean.append(eval_level)
    
    # Remove stale evaluation data
    for level_to_clean in levels_to_clean:
        if level_to_clean in level_evaluations:
            del level_evaluations[level_to_clean]
            
    # Clean up emails for levels that shouldn't have data
    level_emails = session_state.get('level_emails', {})
    for level_to_clean in levels_to_clean:
        if level_to_clean in level_emails:
            del level_emails[level_to_clean] 