"""
User Mode UI Components

This module contains UI components specific to the user mode,
including the session-based authentication and level-based navigation system with inline results.
"""

import streamlit as st
from config import (
    LEVEL_TO_SCENARIO_MAPPING,
    MAX_AVAILABLE_LEVEL,
    EMAIL_MAX_CHARS,
    DEFAULT_SCENARIO,
    DEFAULT_MODEL,
    MAX_TURNS,
    MULTI_TURN_LEVELS
)
from utils import (
    format_scenario_content, 
    process_evaluation_text, 
    get_all_additional_emails,
    is_multi_recipient_scenario
)
from evaluation import process_email_evaluation_user_mode_inline, process_email_evaluation_user_mode_multi_turn
from session_manager import (
    create_new_session,
    session_exists, 
    load_session_data,
    save_session_progress,
    get_conversation_history,
    get_next_turn_number,
    is_level_complete_multi_turn,
    get_leaderboard_data,
    is_game_complete,
    update_turn_and_clear_future,
    handle_level_success
)


def handle_turn_edit(session_id: str, level: float, turn_number: int, new_email_content: str):
    """
    Handle editing a turn: update database, clear future turns, and re-evaluate.
    
    Args:
        session_id: Session ID
        level: Level number  
        turn_number: Turn to update
        new_email_content: New email content
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
        
        # Step 3: Re-evaluate the edited turn to get Adam's new response
        st.info(f"🔄 Re-evaluating Turn {turn_number} with your updated email...")
        
        # Load scenario content
        scenario_content = st.session_state.get('selected_scenario', '')
        model = DEFAULT_MODEL
        
        # Re-evaluate the existing turn (without creating new submission)
        re_evaluate_existing_turn(session_id, level, turn_number, new_email_content, scenario_content, model)
        
        # Force page refresh to show updated conversation history
        st.rerun()
    else:
        st.error("❌ Failed to update turn. Please try again.")


def re_evaluate_existing_turn(session_id: str, level: float, turn_number: int, email_content: str, scenario_content: str, model: str):
    """
    Re-evaluate an existing turn with updated email content.
    Updates Adam's response and evaluation without creating new database entries.
    """
    from models import EmailRecipient, EmailEvaluator, RubricGenerator
    from utils import load_recipient_prompt, extract_goal_achievement_score
    from session_manager import get_conversation_history, get_database_session, SessionEmailSubmission, EvaluationResult
    
    try:
        # Initialize AI services
        email_recipient = EmailRecipient()
        email_evaluator = EmailEvaluator()
        rubric_generator = RubricGenerator()
        
        # Get conversation history up to (but not including) this turn
        conversation_history = get_conversation_history(session_id, level)
        conversation_context = ""
        
        if conversation_history:
            conversation_context = "\n\nPrevious conversation:\n"
            for turn_data in conversation_history:
                if turn_data['turn_number'] < turn_number:  # Only include earlier turns
                    conversation_context += f"\nTurn {turn_data['turn_number']}:\n"
                    conversation_context += f"HR: {turn_data['email_content']}\n"
                    if turn_data['recipient_reply']:
                        conversation_context += f"Adam: {turn_data['recipient_reply']}\n"
        
        # Load recipient prompt and add conversation context
        scenario_file = st.session_state.get('selected_scenario_file', 'scenario_5.4.txt')
        recipient_prompt = load_recipient_prompt(scenario_file)
        contextualized_prompt = recipient_prompt + conversation_context + f"\n\nNow respond to this new email from HR:\n{email_content}"
        
        # Generate Adam's new response
        with st.status("Generating Adam's new response...", expanded=False) as status:
            recipient_reply = email_recipient.generate_reply(contextualized_prompt, email_content, model)
            if not recipient_reply:
                st.error("Failed to generate Adam's reply")
                return
            status.update(label="✅ Adam's new response generated!", state="complete")
        
        # Generate evaluation
        with st.status("Evaluating updated email...", expanded=False) as status:
            # Load rubric if needed
            use_rubric = st.session_state.get('use_rubric', True)
            if use_rubric:
                scenario_filename = st.session_state.get("selected_scenario_file", "")
                rubric = rubric_generator.get_or_generate_rubric(scenario_content, scenario_filename, model)
                if not rubric:
                    rubric = None
            else:
                rubric = None
            
            # Build evaluation context
            evaluation_context = scenario_content + conversation_context + f"\n\nLatest email from HR:\n{email_content}\n\nAdam's response:\n{recipient_reply}"
            
            evaluation = email_evaluator.evaluate_email(
                evaluation_context, 
                email_content, 
                rubric, 
                recipient_reply, 
                model,
                scenario_filename=st.session_state.get("selected_scenario_file")
            )
            
            if not evaluation:
                st.error("Failed to evaluate email")
                return
                
            goal_achieved = extract_goal_achievement_score(evaluation)
            status.update(label="✅ Evaluation complete!", state="complete")
        
        # Update the existing submission's evaluation result
        db_session = get_database_session()
        try:
            # Find the existing submission
            submission = db_session.query(SessionEmailSubmission).filter(
                SessionEmailSubmission.session_id == session_id,
                SessionEmailSubmission.level == level,
                SessionEmailSubmission.turn_number == turn_number
            ).first()
            
            if submission:
                # Delete old evaluation result if it exists
                deleted_count = db_session.query(EvaluationResult).filter_by(submission_id=submission.id).delete()
                st.write(f"DEBUG: Deleted {deleted_count} old evaluation results")
                
                # Create new evaluation result directly
                evaluation_result = EvaluationResult(
                    submission_id=submission.id,
                    evaluation_text=evaluation,
                    recipient_reply=recipient_reply,
                    rubric=rubric,
                    goal_achieved=goal_achieved
                )
                
                db_session.add(evaluation_result)
                db_session.commit()
                                
                # Show the updated response
                st.markdown("**🔄 Adam's Updated Response:**")
                st.markdown(
                    f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #6c757d;">
                    {recipient_reply.replace(chr(10), '<br>')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Always update session state so results will be shown
                if 'level_evaluations' not in st.session_state:
                    st.session_state.level_evaluations = {}
                
                # Create evaluation data structure similar to normal evaluation flow
                st.session_state.level_evaluations[level] = {
                    "evaluation": evaluation,
                    "recipient_reply": recipient_reply,
                    "rubric": rubric,
                    "goal_achieved": goal_achieved
                }
                
                if goal_achieved:
                    st.success(f"🎯 **Goal achieved in Turn {turn_number}!**")
                    
                    # Call the same level completion logic as normal evaluation
                    level_success = handle_level_success(session_id, level)
                    if not level_success:
                        st.error("❌ **Database Error:** Goal achieved but failed to mark level as complete. Please try again.")
                        return
                    
                    # Add to completed levels
                    if 'completed_levels' not in st.session_state:
                        st.session_state.completed_levels = set()
                    st.session_state.completed_levels.add(level)
                    
                else:
                    st.info(f"📧 **Turn {turn_number} updated.** Continue the conversation to achieve your goal.")
                
                # Force refresh by clearing any cached conversation data
                # The next page load will fetch fresh data from database
                st.success("🔄 Turn updated successfully! The page will refresh to show the new response.")
                
        finally:
            db_session.close()
            
    except Exception as e:
        st.error(f"❌ Error re-evaluating turn: {str(e)}")
    
    # Force page refresh to clear edit mode and show updated data
    st.rerun()


def determine_next_level(current_level, session_state):
    """
    Determine the next level based on current level and conditional progression rules.
    
    Args:
        current_level: Current level number
        session_state: Streamlit session state
        
    Returns:
        int/float: Next level number or None if no next level
    """
    # Level 2 conditional progression
    if current_level == 2:
        strategy_analysis = session_state.get('strategy_analysis', {}).get(2)
        completed_levels = session_state.get('completed_levels', set())
        
        # Check if strategy analysis shows forbidden strategies
        used_forbidden_strategies = strategy_analysis and strategy_analysis.get('used_forbidden_strategies')
        
        # If no strategy analysis but user has completed Level 2.5, 
        # we can infer they used forbidden strategies in Level 2
        if not used_forbidden_strategies and 2.5 in completed_levels:
            used_forbidden_strategies = True
        
        if used_forbidden_strategies:
            # Used forbidden strategies → go to Level 2.5 (harder challenge)
            return 2.5
        else:
            # Didn't use forbidden strategies → skip to Level 3
            return 3
    
    # Level 2.5 always goes to Level 3
    if current_level == 2.5:
        return 3
    
    # Standard progression for all other levels
    return current_level + 1


def determine_previous_level(current_level, session_state):
    """
    Determine the previous level based on current level and conditional progression rules.
    
    Args:
        current_level: Current level number
        session_state: Streamlit session state
        
    Returns:
        int/float: Previous level number or None if no previous level
    """
    # Level 3 can come from either Level 2 (clean) or Level 2.5 (after forbidden strategies)
    if current_level == 3:
        # Check if user came from Level 2.5 path (used forbidden strategies in Level 2)
        strategy_analysis = session_state.get('strategy_analysis', {}).get(2)
        completed_levels = session_state.get('completed_levels', set())
        
        # Check if strategy analysis shows forbidden strategies
        used_forbidden_strategies = strategy_analysis and strategy_analysis.get('used_forbidden_strategies')
        
        # If no strategy analysis but user has completed Level 2.5, 
        # we can infer they used forbidden strategies in Level 2
        if not used_forbidden_strategies and 2.5 in completed_levels:
            used_forbidden_strategies = True
        
        if used_forbidden_strategies:
            # They used forbidden strategies in Level 2, so they must have gone through 2.5
            return 2.5
        else:
            # They didn't use forbidden strategies, so they went directly from Level 2
            return 2
    
    # Level 2.5 always comes from Level 2
    if current_level == 2.5:
        return 2
    
    # Standard progression for all other levels
    if current_level > 0:
        return current_level - 1
    else:
        return None


def clean_stale_level_data(current_level, session_state):
    """
    Clean up stale level data that might make levels appear as completed when they shouldn't be.
    
    This prevents issues where navigating to a level shows old results or completion status
    that doesn't match the actual progression state.
    """
    completed_levels = session_state.get('completed_levels', set())
    level_evaluations = session_state.get('level_evaluations', {})
    
    # Clean up evaluations for levels that shouldn't be accessible yet
    levels_to_clean = []
    
    for eval_level in level_evaluations.keys():
        # If there's evaluation data for a level that's not in completed_levels
        # and it's not the current level, it might be stale
        if eval_level != current_level and eval_level not in completed_levels:
            # Additional check: if it's a level that's higher than what should be accessible
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


def show_session_selection_screen():
    """Show the session selection screen for starting new or resuming existing sessions"""
    
    # st.title("🎮 Email Communication Training")
    st.markdown("---")
    
    st.markdown("""
    You are a ghostwriter who helps people craft messages in various complex scenarios. Throughout the game, you will receive writing requests from a client. Upon submitting an email, you will receive a response from the email's intended recipient indicating whether you have achieved the scenario's goal. The requests will become increasingly more difficult as the levels progress. Choose your words wisely, but most importantly, have fun!
    
    **Choose an option below to get started:**
    """)
    
    # Two columns for the options
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Start New Session")
        st.markdown("Begin a new game session.")
        
        if st.button("🚀 Start New Session", type="primary", use_container_width=True):
            try:
                # Create new session
                new_session_id = create_new_session()
                st.session_state.game_session_id = new_session_id
                
                # Initialize session state with default values
                st.session_state.current_level = 0
                st.session_state.completed_levels = set()
                st.session_state.level_emails = {}
                st.session_state.level_evaluations = {}
                st.session_state.strategy_analysis = {}
                st.session_state.use_rubric = False
                
                st.success(f"✅ New session created successfully!")
                st.info(f"📋 **Your Session ID:** `{new_session_id}`")
                st.info("💾 **Bookmark this page** to resume your session later!")
                
                # Rerun to show the game interface
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to create session: {str(e)}")
    
    with col2:
        st.markdown("### Resume Session")
        st.markdown("Continue an existing game session using your Session ID.")
        
        # Session ID input
        resume_session_id = st.text_input(
            "Enter your Session ID:",
            placeholder="e.g., da4fe9bc-042b-4533-8a60-68f63773eebd",
            help="Enter the Session ID from a previous session"
        )
        
        if st.button("▶️ Resume Session", disabled=not resume_session_id.strip(), use_container_width=True):
            resume_session_id = resume_session_id.strip()
            
            if session_exists(resume_session_id):
                try:
                    # Load session data
                    session_data = load_session_data(resume_session_id)
                    
                    if session_data:
                        # Set session ID and load data into session state
                        st.session_state.game_session_id = resume_session_id
                        st.session_state.current_level = session_data['current_level']
                        st.session_state.completed_levels = session_data['completed_levels']
                        st.session_state.level_emails = session_data['level_emails']
                        st.session_state.level_evaluations = session_data['level_evaluations']
                        st.session_state.strategy_analysis = session_data.get('strategy_analysis', {})
                        st.session_state.use_rubric = session_data['use_rubric']
                        
                        st.success(f"✅ Session resumed successfully!")
                        st.info(f"📊 Progress: {len(session_data['completed_levels'])} levels completed")
                        
                        # Rerun to show the game interface
                        st.rerun()
                    else:
                        st.error("❌ Failed to load session data. Please try again.")
                        
                except Exception as e:
                    st.error(f"❌ Failed to resume session: {str(e)}")
            else:
                st.error("❌ Session ID not found. Please check your Session ID and try again.")
    
    # Helpful information section
    st.markdown("---")
    with st.expander("ℹ️ About Session IDs", expanded=False):
        st.markdown("""
        **What is a Session ID?**
        - A unique identifier for your training session
        - Allows you to resume your progress after closing the browser
        - Safe to share with others for collaborative training
        
        **How to use:**
        1. **New users**: Click "Start New Session" to get a Session ID
        2. **Returning users**: Enter your Session ID and click "Resume Session"
        3. **Always bookmark** the page after starting to easily return later
        
        **Session IDs look like:** `da4fe9bc-042b-4533-8a60-68f63773eebd`
        """)


def show_game_interface_with_session(available_scenarios, api_keys_available, session_id):
    """Show the main game interface with session information"""
    
    # Check if we should show the leaderboard
    if st.session_state.get('show_leaderboard', False):
        show_leaderboard_page(session_id)
        return
    
    # Display session info at the top
    # st.markdown("### 🎮 Email Communication Training")
    
    # Session info bar
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info(f"📋 **Session ID:** `{session_id}` (copy this to resume the game later)")
    
    with col2:
        # Check if game is complete and add leaderboard button
        from session_manager import is_game_complete
        if is_game_complete(session_id):
            if st.button("🏆 Leaderboard", help="View the leaderboard"):
                st.session_state.show_leaderboard = True
                st.rerun()
    
    with col3:
        if st.button("🆕 New Session", help="Start a fresh session"):
            # Clear current session and return to selection screen
            if 'game_session_id' in st.session_state:
                del st.session_state.game_session_id
            if 'show_leaderboard' in st.session_state:
                del st.session_state.show_leaderboard
            st.rerun()
    
    st.markdown("---")
    
    # Show the existing game interface
    show_level_based_game_interface(available_scenarios, api_keys_available, session_id)


def show_level_based_game_interface(available_scenarios, api_keys_available, session_id):
    """Show the level-based game interface (renamed from show_user_interface_with_levels)"""
    
    # Set default model for user version (no sidebar configuration)
    model = DEFAULT_MODEL
    
    # Use the global level mapping
    level_to_scenario_mapping = LEVEL_TO_SCENARIO_MAPPING
    max_level = MAX_AVAILABLE_LEVEL
    total_levels = len(level_to_scenario_mapping)  # Total number of levels available
    
    # Get current level (default to 0 if not set)
    current_level = st.session_state.get('current_level', 0)
    
    # Clean up any stale level data on interface load
    clean_stale_level_data(current_level, st.session_state)
    
    # Navigation header with level controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        # Previous level button with conditional progression logic
        previous_level = determine_previous_level(current_level, st.session_state)
        can_go_back = previous_level is not None
        if st.button("← Previous Level", disabled=not can_go_back, help="Go to previous level"):
            st.session_state.current_level = previous_level
            # Clean up stale level data
            clean_stale_level_data(previous_level, st.session_state)
            # Auto-save progress
            save_session_progress(session_id, st.session_state.current_level, st.session_state.get('completed_levels', set()))
            st.rerun()
    
    with col2:
        # Current level indicator
        if current_level == 0:
            level_display = "Tutorial"
        elif current_level == 2.5:
            level_display = "Challenge Level 2.5"
        else:
            level_display = f"Level {current_level}"
        st.markdown(f"**🎮 {level_display}**")
    
    with col3:
        # Next level button with conditional progression logic
        next_level = determine_next_level(current_level, st.session_state)
        can_go_forward = (next_level is not None and 
                         next_level in level_to_scenario_mapping and 
                         current_level in st.session_state.get('completed_levels', set()))
        
        next_level_text = f"Next Level →"
        help_text = "Go to next level"
        
        # Special messaging for Level 2 progression
        if current_level == 2 and can_go_forward:
            strategy_analysis = st.session_state.get('strategy_analysis', {}).get(2)
            completed_levels = st.session_state.get('completed_levels', set())
            
            # Check if forbidden strategies were used (either from analysis or inferred from 2.5 completion)
            used_forbidden_strategies = (strategy_analysis and strategy_analysis.get('used_forbidden_strategies')) or (2.5 in completed_levels)
            
            if used_forbidden_strategies and next_level == 2.5:
                next_level_text = "Challenge Level 2.5 →"
                help_text = "You used forbidden strategies! Try the harder challenge."
                    
        if st.button(next_level_text, disabled=not can_go_forward, help=help_text):
            st.session_state.current_level = next_level
            # Clean up stale level data
            clean_stale_level_data(next_level, st.session_state)
            # Auto-save progress
            save_session_progress(session_id, st.session_state.current_level, st.session_state.get('completed_levels', set()))
            st.rerun()
    
    # Level progression info
    st.info("🎯 **Level Progression**: Complete this level to unlock the next!")
    
    # Show the current level page
    show_level_page(current_level, available_scenarios, level_to_scenario_mapping, api_keys_available, model, session_id)


def show_level_page(level, available_scenarios, level_to_scenario_mapping, api_keys_available, model, session_id):
    """Show a complete level page with scenario, email input, and results"""
    
    # Get backend scenario ID from user level
    backend_scenario_id = level_to_scenario_mapping.get(level, "5.0")
    
    # Get scenario data based on backend scenario ID
    scenario_data = None
    scenario_content = ""
    
    if available_scenarios:
        # Look for the backend scenario ID with exact matching
        target_scenario = f"scenario_{backend_scenario_id}.txt"
        for scenario_name, scenario_info in available_scenarios.items():
            # Use exact filename matching to avoid partial matches (e.g., 5.2 matching 5.2.5)
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
    
    # Get scenario filename for additional content
    scenario_filename = st.session_state.get('selected_scenario_file', '')
    
    # Show additional emails (Level 3: Emily/Mark emails, Level 5: Forwarded emails, etc.)
    show_additional_emails(scenario_filename)
    
    # Check if this is a multi-turn level
    is_multi_turn = level in MULTI_TURN_LEVELS
    
    # Multi-turn conversation history (for Level 4)
    if is_multi_turn:
        conversation_history = get_conversation_history(session_id, level)
        current_turn = get_next_turn_number(session_id, level)
        level_complete = is_level_complete_multi_turn(session_id, level)
        
        # Show conversation history if it exists
        if conversation_history:
            st.subheader("💬 Conversation History")
            
            for turn_data in conversation_history:
                turn_num = turn_data['turn_number']
                
                # User email - make it editable for turn invalidation
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**Turn {turn_num} - Your Email:**")
                
                with col2:
                    edit_key = f"edit_turn_{turn_num}"
                    if st.button(f"✏️ Edit", key=f"edit_button_{turn_num}", help=f"Edit Turn {turn_num} email"):
                        st.session_state[edit_key] = True
                
                # Show editable text area if in edit mode, otherwise show formatted display
                if st.session_state.get(edit_key, False):
                    edited_email = st.text_area(
                        f"Edit Turn {turn_num} email:",
                        value=turn_data['email_content'],
                        height=200,
                        max_chars=EMAIL_MAX_CHARS,
                        key=f"email_edit_{turn_num}"
                    )
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("💾 Save", key=f"save_turn_{turn_num}", type="primary"):
                            # Update turn and clear future turns
                            handle_turn_edit(session_id, level, turn_num, edited_email)
                            st.session_state[edit_key] = False
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ Cancel", key=f"cancel_turn_{turn_num}"):
                            st.session_state[edit_key] = False
                            st.rerun()
                            
                else:
                    st.markdown(
                        f"""
                        <div style="background-color: #e7f3ff; padding: 10px; border-radius: 5px; border-left: 3px solid #007bff; margin-bottom: 10px;">
                        {turn_data['email_content'].replace(chr(10), '<br>')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Adam's reply (if available)
                if turn_data['recipient_reply']:
                    st.markdown(f"**Turn {turn_num} - Adam's Reply:**")
                    st.markdown(
                        f"""
                        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 3px solid #6c757d; margin-bottom: 15px;">
                        {turn_data['recipient_reply'].replace(chr(10), '<br>')}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Show if goal was achieved in this turn
                if turn_data['goal_achieved']:
                    level_complete = True
                    st.success(f"🎯 **Goal achieved in Turn {turn_num}!**")
                
    # Email input section  
    if is_multi_turn:
        # Multi-turn email input (Level 4)
        st.subheader("✍️ Your Email")
        
        # # Check if level is complete or turn limit reached (get fresh values)
        # conversation_history = get_conversation_history(session_id, level)
        # current_turn = get_next_turn_number(session_id, level)
        # level_complete = is_level_complete_multi_turn(session_id, level)
        
        # Show turn counter and status (using fresh level_complete value)
        if level_complete:
            st.success(f"🎉 **Level {level} Complete!** You successfully helped Adam express his concerns.")
        elif current_turn > MAX_TURNS:
            st.warning(f"⏱️ **Turn limit reached** ({MAX_TURNS} turns)")
            st.info("💼 Adam has decided to just bring noise canceling headphones and a blanket to work.")
        else:
            st.info(f"📧 **Turn {current_turn} of {MAX_TURNS}** - Continue the conversation with Adam")
            
            # Email text area for multi-turn
            email_content = st.text_area(
                f"Write your email to Adam (Turn {current_turn}):",
                value="",
                height=400,
                max_chars=EMAIL_MAX_CHARS,
                placeholder="Continue the conversation with Adam. Try to understand what's really bothering him...",
                help="Write an email that helps Adam open up about his true concerns",
                key=f"email_input_level_{level}_turn_{current_turn}"
            )
            
            # Submit button for multi-turn
            if st.button(
                f"📝 Send",
                type="primary",
                disabled=not api_keys_available or not email_content.strip(),
                help="Submit your email for AI evaluation"
            ):
                if not email_content.strip():
                    st.error("Please write an email before submitting!")
                elif not api_keys_available:
                    st.error("API keys not available")
                else:
                    # Process multi-turn email evaluation
                    process_email_evaluation_user_mode_multi_turn(scenario_content, email_content, model, level, session_id, current_turn)
    elif level == 3:
        # Level 3 email input (multi-recipient scenario)
        st.subheader("✍️ Your Email")
        scenario_filename = st.session_state.get('selected_scenario_file', '')
        is_multi_recipient = is_multi_recipient_scenario(scenario_filename)
        
        if is_multi_recipient:
            st.info("📝 **Level 3**: Write a single email that will be sent to both Emily and Mark.")
            placeholder_text = "Type your email response that addresses both Emily's and Mark's concerns..."
            help_text = "Write an email that will resolve the conflict between Emily and Mark"
        else:
            st.info("📝 **Level 3**: Write an email that addresses the situation described in the scenario.")
            placeholder_text = "Type your email response that addresses the situation..."
            help_text = "Write an email that addresses the situation described in the scenario"
        
        # Pre-populate email if returning to a completed level
        initial_email_value = ""
        if level in st.session_state.get('level_emails', {}):
            level_emails = st.session_state.level_emails[level]
            if isinstance(level_emails, str):
                initial_email_value = level_emails
            elif isinstance(level_emails, dict) and level_emails:
                # If somehow stored as dict, use the first value
                initial_email_value = list(level_emails.values())[0]
        
        email_content = st.text_area(
            "Write your email response:",
            value=initial_email_value,
            height=350,
            max_chars=EMAIL_MAX_CHARS,
            placeholder=placeholder_text,
            help=help_text,
            key=f"email_input_level_{level}"
        )
        
    else:
        # Single recipient email input (Levels 0, 1, 2, 2.5)
        st.subheader("✍️ Your Email")
        
        # Pre-populate email if returning to a completed level
        initial_email_value = ""
        if level in st.session_state.get('level_emails', {}):
            level_emails = st.session_state.level_emails[level]
            if isinstance(level_emails, str):
                initial_email_value = level_emails
            elif isinstance(level_emails, dict) and level_emails:
                # If somehow stored as dict, use the first value
                initial_email_value = list(level_emails.values())[0]
        
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

    # Submit button (only for single-turn levels)
    if not is_multi_turn:
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
                # Process email evaluation inline - handles both single and multi-recipient
                process_email_evaluation_user_mode_inline(scenario_content, email_content, model, level, session_id)
    
    # Show results based on level type
    if level in st.session_state.get('level_evaluations', {}):
        # Check if we should show results for this level
        should_show_results = True
        
        # For multi-turn levels, only show results when conversation is complete
        if is_multi_turn:
            current_turn = get_next_turn_number(session_id, level)
            # level_complete = is_level_complete_multi_turn(session_id, level)
            
            # Only show results if level is complete OR max turns reached
            should_show_results = level_complete or current_turn > MAX_TURNS
        
        if should_show_results:
            show_level_results(level)


def show_level_results(level):
    """Show the evaluation results for a level inline"""
    
    result = st.session_state.level_evaluations[level]
    
    # Check if game was just completed and trigger leaderboard
    if st.session_state.get('game_completed', False):
        st.success("🎊 **GAME COMPLETE!** 🎊")
        st.balloons()  # Celebration animation!
        st.success("🏆 **You are now a Communication Master!** 🏆")
        
        # Wait a moment then redirect to leaderboard
        import time
        time.sleep(1)
        st.session_state.show_leaderboard = True
        st.session_state.game_completed = False  # Clear the flag
        st.rerun()
    
    # Success indicator first
    st.markdown("---")
    st.subheader("📊 Results")
    
    # Show goal achievement status prominently
    if "goal_achieved" in result:
        if result["goal_achieved"]:
            st.success("🎉 **Success!** You persuaded the recipient and completed this level!")
            
            # Show strategy analysis for Level 2
            if level == 2 and "strategy_analysis" in result:
                strategy_analysis = result["strategy_analysis"]
                
                if strategy_analysis.get("used_forbidden_strategies"):
                    st.warning("⚠️ **Strategy Analysis**: You used forbidden strategies (layoffs or salary increases)!")
                    st.info("🎯 **Next Challenge**: You'll be directed to Level 2.5 where these strategies are prohibited.")
                    
                    # Show details
                    with st.expander("📊 Strategy Details", expanded=False):
                        if strategy_analysis.get("used_layoff"):
                            st.write("❌ **Layoff threats detected** in your email")
                        if strategy_analysis.get("used_salary_increase"):
                            st.write("❌ **Salary increase offers detected** in your email")
                        st.write(f"**Analysis**: {strategy_analysis.get('explanation', 'No explanation available')}")
                else:
                    st.info("✅ **Strategy Analysis**: Great! You didn't use any forbidden strategies. You can proceed directly to Level 3.")
                    
        else:
            st.error("❌ **Goal Not Achieved** - You can edit your email above and try again.")

    # Show the recipient reply(ies)
    if "recipient_reply" in result:
        # Check if this is a multi-recipient scenario for display formatting
        scenario_filename = st.session_state.get('selected_scenario_file', '')
        is_multi_recipient = is_multi_recipient_scenario(scenario_filename)
        
        if is_multi_recipient:
            st.subheader("📨 Recipients' Replies")
        else:
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
    if result.get("goal_achieved"):
        from session_manager import is_game_complete
        from config import MAX_AVAILABLE_LEVEL
        
        # Check if this is the final level completion
        if level == MAX_AVAILABLE_LEVEL and is_game_complete(st.session_state.get('game_session_id')):
            # Game completed! Show leaderboard option
            st.success("🎊 **GAME COMPLETE!** You are now a Communication Master!")
            
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
        else:
            # Regular level progression
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
    
    # Show "Try Again" hint if unsuccessful
    elif not result.get("goal_achieved"):
        # Special handling for Level 4 when max turns reached
        if level in MULTI_TURN_LEVELS and result.get("max_turns_reached"):
            st.info("💡 **Level 4 ended after maximum turns.** You can restart the level to try a different approach.")
            
            if st.button("🔄 Restart Level 4", type="secondary", use_container_width=True):
                # Clear Level 4 data and restart
                session_id = st.session_state.get('game_session_id')
                if session_id:
                    # Clear Level 4 from session state
                    if level in st.session_state.get('level_evaluations', {}):
                        del st.session_state.level_evaluations[level]
                    if level in st.session_state.get('level_emails', {}):
                        del st.session_state.level_emails[level]
                    
                    # Clear Level 4 from database (submissions, evaluations, completion)
                    from session_manager import clear_level_data
                    clear_level_data(session_id, level)
                    
                    st.success("🔄 Level 4 restarted! You can now try again.")
                    st.rerun()
        else:
            st.info("💡 **Tip:** Edit your email above and click Send again to improve your result!")


def show_additional_emails(scenario_filename: str):
    """
    Show additional emails for a scenario (both multi-recipient context and forwarded emails).
    
    Args:
        scenario_filename: The scenario filename to check for additional emails
    """
    # First check for forwarded emails (context emails)
    forwarded_emails = get_all_additional_emails(scenario_filename)
    
    if forwarded_emails['has_emails']:
        st.markdown(f"**{forwarded_emails['title']}**")
        st.info(forwarded_emails['description'])
        
        for email_title, email_content in forwarded_emails['emails']:
            with st.expander(email_title, expanded=False):
                # Format the email content
                email_formatted = format_scenario_content(email_content)
                
                # Use gray styling for forwarded emails
                st.markdown(
                    f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #6c757d; font-size: 0.9em;">
                    {email_formatted}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    
    # Then check for multi-recipient context emails (Emily/Mark)
    if is_multi_recipient_scenario(scenario_filename):
        from utils import get_scenario_prompts
        recipient_prompts = get_scenario_prompts(scenario_filename)
        
        if 'emily' in recipient_prompts and 'mark' in recipient_prompts:
            st.markdown("**📨 Email Context**")
            st.info("💼 Below are the emails from Emily and Mark that prompted this request.")
            
            # Emily's email
            with st.expander("Emily's Email", expanded=False):
                email_formatted = format_scenario_content(recipient_prompts['emily'])
                st.markdown(
                    f"""
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; font-size: 0.9em;">
                    {email_formatted}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            # Mark's email
            with st.expander("Mark's Email", expanded=False):
                email_formatted = format_scenario_content(recipient_prompts['mark'])
                st.markdown(
                    f"""
                    <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; border-left: 4px solid #17a2b8; font-size: 0.9em;">
                    {email_formatted}
                    </div>
                    """,
                    unsafe_allow_html=True
                )


def show_leaderboard_page(session_id: str):
    """Show the leaderboard page for players who completed all levels"""
    
    from session_manager import get_leaderboard_data
    from datetime import timedelta
    
    st.title("🏆 Leaderboard")
    
    st.markdown("""
    **Congratulations!** 🎉 You've successfully completed all levels of the game!
    """)
    
    # Get leaderboard data
    with st.spinner("Loading leaderboard..."):
        leaderboard_data = get_leaderboard_data()
    
    # if not leaderboard_data:
    #     st.info("🎯 You're the first to complete all levels! More players will appear here as they finish the training.")
    # else:
    #     st.subheader(f"🌟 {len(leaderboard_data)} Communication Masters")
        
    # Find current player's position
    current_player_rank = None
    for i, player in enumerate(leaderboard_data, 1):
        if player['session_id'] == session_id:
            current_player_rank = i
            break
    
    # if current_player_rank:
    #     if current_player_rank == 1:
    #         st.success(f"🥇 **Amazing!** You're ranked #1 on the leaderboard!")
    #     elif current_player_rank <= 3:
    #         st.success(f"🥉 **Excellent!** You're ranked #{current_player_rank} on the leaderboard!")
    #     else:
    #         st.info(f"🎯 **Great job!** You're ranked #{current_player_rank} on the leaderboard!")
    
    # Create leaderboard table
    leaderboard_display = []
    for i, player in enumerate(leaderboard_data, 1):
        # Format completion time
        completed_at = player['completed_at'].strftime("%Y-%m-%d %H:%M")
        
        # Format total time
        total_time_str = "N/A"
        if player['total_time']:
            total_seconds = int(player['total_time'].total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                total_time_str = f"{hours}h {minutes}m"
            elif minutes > 0:
                total_time_str = f"{minutes}m {seconds}s"
            else:
                total_time_str = f"{seconds}s"
        
        # Add rank emoji
        rank_emoji = ""
        if i == 1:
            rank_emoji = "🥇"
        elif i == 2:
            rank_emoji = "🥈"
        elif i == 3:
            rank_emoji = "🥉"
        else:
            rank_emoji = f"{i}."
        
        # Highlight current player
        session_display = player['session_id'][:8] + "..."
        if player['session_id'] == session_id:
            session_display = f"**{session_display} (You!)**"
        
        leaderboard_display.append({
            "Rank": rank_emoji,
            "Player": session_display,
            "Completed": completed_at,
            "Total Time": total_time_str,
            "Submissions": player['total_submissions']
        })
    
    # Display leaderboard table
    st.table(leaderboard_display)
    
    st.markdown("---")
    
    # # Achievement section
    # st.subheader("🎖️ Your Achievement")
    
    # col1, col2, col3 = st.columns(3)
    
    # with col1:
    #     st.metric("Levels Completed", "6", help="Tutorial + Levels 1-5")
    
    # with col2:
    #     st.metric("Scenarios Mastered", "6", help="Complex communication scenarios")
    
    # with col3:
    #     if leaderboard_data:
    #         total_players = len(leaderboard_data)
    #         st.metric("Players Completed", total_players, help="Total players who finished all levels")
    #     else:
    #         st.metric("Players Completed", "1", help="You're the first!")
    
    # st.markdown("---")
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 Refresh Leaderboard", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("🆕 Start New Game", use_container_width=True):
            # Clear current session and return to selection screen
            if 'game_session_id' in st.session_state:
                del st.session_state.game_session_id
            if 'show_leaderboard' in st.session_state:
                del st.session_state.show_leaderboard
            st.rerun()
    
    with col3:
        if st.button("🎮 Continue Playing", use_container_width=True, help="Return to Level 5"):
            if 'show_leaderboard' in st.session_state:
                del st.session_state.show_leaderboard
            st.rerun()
    
    # Fun facts section
    st.markdown("---")
    with st.expander("📊 Statistics", expanded=False):
        if leaderboard_data:
            # Calculate some interesting stats
            total_submissions = sum(p['total_submissions'] for p in leaderboard_data)
            avg_submissions = total_submissions / len(leaderboard_data) if leaderboard_data else 0
            
            st.markdown(f"""
            - **Total players completed:** {len(leaderboard_data)}
            - **Total emails written:** {total_submissions:,}
            - **Average emails per player:** {avg_submissions:.1f}
            """)
        else:
            st.markdown("Be the first to set the benchmark for future players!")


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