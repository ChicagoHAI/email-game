"""
Email Evaluation Processing

This module handles the email evaluation workflow, including
AI generation, evaluation, and result processing.
"""

import json
import logging
import streamlit as st
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)
from config import MAX_AVAILABLE_LEVEL, DEFAULT_RECIPIENT_PROMPT, MAX_TURNS, MULTI_TURN_LEVELS
from models import RubricGenerator, EmailRecipient, EmailEvaluator, EmailGenerator, GameMaster
from utils import (
    load_recipient_prompt, 
    extract_goal_achievement_score, 
    process_evaluation_text,
    get_scenario_recipients,
    is_multi_recipient_scenario,
    load_game_master_prompt,
    has_game_master
)
from session_manager import is_game_complete


def _display_majority_reply_debug(reply_result: dict, expanded: bool = False, unique_id: str = ""):
    """
    Display debugging information for majority reply generation.
    
    Args:
        reply_result: Result from generate_reply_with_majority
        expanded: Whether to show the expander expanded by default
        unique_id: Unique identifier to prevent key collisions (e.g., recipient name)
    """
    if not reply_result:
        return
    
    # Get data from result
    all_replies = reply_result.get('all_replies', [])
    outcomes = reply_result.get('outcome_analysis', {}).get('outcomes', [])
    evaluations = reply_result.get('outcome_analysis', {}).get('evaluations', [])
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
                    f"Evaluation for Reply {i+1}",
                    value=evaluation_text,
                    height=200,
                    key=f"eval_debug_{unique_id}_{i}_{hash(reply[:20])}",
                    disabled=True
                )
            
            if i < len(all_replies) - 1:  # Not the last reply
                st.markdown("---")


def detect_forbidden_strategies(email_content: str, model: str = "gpt-4o") -> dict:
    """
    Detect if an email uses forbidden strategies (layoffs or salary increases) using LLM analysis.
    
    Args:
        email_content: The email content to analyze
        model: The model to use for analysis
        
    Returns:
        dict: {
            'used_layoff': bool,
            'used_salary_increase': bool,
            'used_forbidden_strategies': bool,
            'explanation': str
        }
    """
    from utils import get_api_client
    
    try:
        client = get_api_client()
        
        analysis_prompt = f"""Analyze this email to determine if it uses forbidden strategies to convince someone to return to in-person work.

FORBIDDEN STRATEGIES:
1. LAYOFF THREATS: Firing, termination, layoffs, job cuts, dismissal, job security threats, performance-based termination, ultimatums about job consequences
2. SALARY INCREASES: Raises, bonuses, salary bumps, financial incentives, compensation increases, promotions tied to in-person work

EMAIL:
{email_content}

INSTRUCTIONS:
- Look for ANY mention of the forbidden strategies above
- Be thorough - even subtle threats or offers count
- Respond ONLY with valid JSON - no other text

JSON FORMAT:
{{
  "used_layoff": true,
  "used_salary_increase": false,
  "explanation": "Found phrases 'we will fire you' and 'laid off every year' indicating layoff threats"
}}"""
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert analyzer. You MUST respond with valid JSON only. No markdown, no explanations, just JSON."
                },
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.0  # Zero temperature for maximum consistency
        )
        
        # Get the response content and clean it
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse the JSON response
        result = json.loads(response_text)
        
        # Ensure all required fields are present
        result['used_layoff'] = result.get('used_layoff', False)
        result['used_salary_increase'] = result.get('used_salary_increase', False)
        result['used_forbidden_strategies'] = result['used_layoff'] or result['used_salary_increase']
        result['explanation'] = result.get('explanation', 'No explanation provided')
        
        return result
        
    except json.JSONDecodeError as e:
        return {
            'used_layoff': False,
            'used_salary_increase': False,
            'used_forbidden_strategies': False,
            'explanation': f"JSON parsing error: {str(e)}. Response was: {response_text[:100] if 'response_text' in locals() else 'no response'}..."
        }
    except Exception as e:
        return {
            'used_layoff': False,
            'used_salary_increase': False,
            'used_forbidden_strategies': False,
            'explanation': f"Analysis error: {str(e)}"
        }

def _initialize_ai_services():
    """Initialize AI services used in email evaluation"""
    return {
        'email_evaluator': EmailEvaluator(),
        'email_recipient': EmailRecipient(),
        'rubric_generator': RubricGenerator()
    }

def _import_session_manager_functions():
    """Import session manager functions for database operations"""
    from session_manager import (
        save_email_submission,
        save_evaluation_result,
        handle_level_success,
        handle_level_failure,
    )
    return {
        'save_email_submission': save_email_submission,
        'save_evaluation_result': save_evaluation_result,
        'handle_level_success': handle_level_success,
        'handle_level_failure': handle_level_failure,
    }

def _generate_rubric_if_enabled(rubric_generator, scenario, model):
    """Generate rubric if enabled in settings"""
    use_rubric = st.session_state.get('use_rubric', True)
    if not use_rubric:
        return None
        
    try:
        with st.status("Loading evaluation rubric...", expanded=False) as status:
            scenario_filename = st.session_state.get("selected_scenario_file", "")
            
            if scenario_filename:
                rubric = rubric_generator.get_or_generate_rubric(
                    scenario, scenario_filename, model
                )
            else:
                rubric = rubric_generator.generate_rubric(scenario, model)
            
            if not rubric:
                st.warning("⚠️ Rubric generation failed - continuing without rubric")
                return None
            else:
                status.update(label="✅ Rubric ready!", state="complete")
                return rubric
    except Exception as e:
        st.warning(f"⚠️ Rubric generation error: {str(e)} - continuing without rubric")
        return None

def _evaluate_email(email_evaluator, scenario, email_content, rubric, 
                   recipient_reply, model, scenario_filename=None, 
                   conversation_context=""):
    """Evaluate email with proper context"""
    with st.status("Evaluating your email...", expanded=False) as status:
        # Build evaluation context
        evaluation_context = scenario + conversation_context
        if conversation_context:
            evaluation_context += f"\n\nLatest email from HR:\n{email_content}\n\nRecipient's response:\n{recipient_reply}"
        
        evaluation = email_evaluator.evaluate_email(
            evaluation_context if conversation_context else scenario,
            email_content, 
            rubric, 
            recipient_reply, 
            model,
            scenario_filename=scenario_filename
        )
        
        if not evaluation:
            raise ValueError("Email evaluator returned None/empty evaluation")
            
        status.update(label="✅ Evaluation complete!", state="complete")
        return evaluation

def _handle_database_persistence(session_id, level, email_content, evaluation, 
                                recipient_reply, rubric, goal_achieved, 
                                db_functions, turn_number=None, 
                                strategy_analysis=None):
    """Handle database operations for email submissions and evaluations"""
    if not session_id:
        return True
        
    try:
        # Save email submission
        submission_id = db_functions['save_email_submission'](
            session_id, level, email_content, turn_number
        )
        
        if not submission_id:
            raise Exception("Failed to save email submission")
        
        # Prepare evaluation data
        evaluation_data = {
            'evaluation': evaluation,
            'recipient_reply': recipient_reply,
            'rubric': rubric,
            'goal_achieved': goal_achieved
        }
        
        if strategy_analysis:
            evaluation_data["strategy_analysis"] = strategy_analysis
        
        # Save evaluation result
        if not db_functions['save_evaluation_result'](submission_id, evaluation_data):
            raise Exception("save_evaluation_result returned False")
        
        # Handle level success/failure
        if goal_achieved:
            if not db_functions['handle_level_success'](session_id, level):
                st.error("❌ **Database Error:** Goal achieved but failed to mark level as complete.")
                return False
        else:
            db_functions['handle_level_failure'](session_id, level)
            
        return True
        
    except Exception as e:
        st.warning(f"⚠️ Results saved to current session but database save failed: {str(e)}")
        st.info("Your progress is temporarily stored and will be available until you close the browser.")
        return False

def _update_session_state_for_level_completion(level, goal_achieved, email_content, 
                                              evaluation_data, strategy_analysis=None, 
                                              session_id=None):
    """Update session state containers for level completion"""
    # Initialize session state containers if needed
    for key in ['level_emails', 'level_evaluations', 'completed_levels', 'strategy_analysis']:
        if key not in st.session_state:
            if key == 'completed_levels':
                st.session_state[key] = set()
            else:
                st.session_state[key] = {}
    
    # Store email content by level
    st.session_state.level_emails[level] = email_content
    
    # Store strategy analysis if provided
    if strategy_analysis:
        st.session_state.strategy_analysis[level] = strategy_analysis
    
    # Store evaluation results
    st.session_state.level_evaluations[level] = evaluation_data
    
    # Update completed levels based on success/failure
    # Always remove higher levels when redoing a level
    levels_to_remove = {l for l in st.session_state.completed_levels if l > level}
    st.session_state.completed_levels -= levels_to_remove
    
    # Clean up evaluation data and emails for invalidated levels
    for invalid_level in levels_to_remove:
        for state_key in ['level_evaluations', 'level_emails']:
            if invalid_level in st.session_state.get(state_key, {}):
                del st.session_state[state_key][invalid_level]
    
    if goal_achieved:
        st.session_state.completed_levels.add(level)
        
        # Check if this completes the entire game
        from config import MAX_AVAILABLE_LEVEL
        if level == MAX_AVAILABLE_LEVEL and session_id and is_game_complete(session_id):
            st.session_state.game_completed = True
    else:
        st.session_state.completed_levels.discard(level)

def process_email_evaluation_user_mode_inline(scenario, email_content, model, level, session_id=None):
    """Process email evaluation for user mode with inline results display and database persistence"""
    
    # Initialize AI services and database functions
    ai_services = _initialize_ai_services()
    db_functions = _import_session_manager_functions()
    
    with st.spinner("🤖 Processing your email..."):
        try:
            # Step 1: Generate rubric (conditional)
            rubric = _generate_rubric_if_enabled(
                ai_services['rubric_generator'], scenario, model
            )
            
            # Step 2: Generate recipient reply(ies)
            scenario_filename = st.session_state.get("selected_scenario_file", "")
            is_multi_recipient = is_multi_recipient_scenario(scenario_filename)
            
            if is_multi_recipient:
                # Multi-recipient scenario (Level 2 with Emily/Mark)
                with st.status("Generating recipient responses (using majority voting)...", expanded=False) as status:
                    recipients = get_scenario_recipients(scenario_filename)
                    recipient_replies = {}
                    recipient_debug_data = {}
                    
                    for recipient_name, recipient_prompt in recipients.items():
                        reply_result = ai_services['email_recipient'].generate_reply_with_majority(
                            recipient_prompt, email_content, model, scenario=scenario, rubric=rubric, scenario_filename=scenario_filename
                        )
                        if not reply_result:
                            st.error(f"Failed to generate {recipient_name}'s reply")
                            return
                        recipient_replies[recipient_name] = reply_result['reply']
                        recipient_debug_data[recipient_name] = reply_result
                    
                    # Combine replies for display
                    combined_replies = []
                    for name, reply in recipient_replies.items():
                        combined_replies.append(f"**{name.title()}'s Reply:**\n{reply}")
                    recipient_reply = "\n\n---\n\n".join(combined_replies)
                    
                    status.update(label="✅ Recipient replies generated!", state="complete")
                
                # DEBUG: Show majority reply analysis for multi-recipient
                for recipient_name, reply_data in recipient_debug_data.items():
                    st.markdown(f"**{recipient_name.title()} Debug Analysis:**")
                    _display_majority_reply_debug(reply_data, expanded=False, unique_id=recipient_name)
                
                # Store debug info in session state
                if 'debug_reply_data' not in st.session_state:
                    st.session_state.debug_reply_data = {}
                st.session_state.debug_reply_data[level] = recipient_debug_data
            else:
                # Single recipient scenario
                with st.status("Generating recipient response (using 5 concurrent samples for consistency)...", expanded=False) as status:
                    # Load recipient prompt
                    if st.session_state.get("selected_scenario_file"):
                        recipient_prompt = load_recipient_prompt(st.session_state.selected_scenario_file)
                    else:
                        recipient_prompt = DEFAULT_RECIPIENT_PROMPT
                    
                    reply_result = ai_services['email_recipient'].generate_reply_with_majority(
                        recipient_prompt, email_content, model, scenario=scenario, rubric=rubric, scenario_filename=scenario_filename
                    )
                    if not reply_result:
                        st.error("Failed to generate recipient reply")
                        return
                    
                    recipient_reply = reply_result['reply']
                    majority_outcome = reply_result['majority_outcome']
                    outcome_counts = reply_result['outcome_counts']
                    
                    status.update(label=f"✅ Recipient reply generated! (Majority: {majority_outcome}, Distribution: {outcome_counts})", state="complete")
                
                # DEBUG: Show majority reply analysis
                _display_majority_reply_debug(reply_result, expanded=False, unique_id="single")
                
                # Store debug info in session state
                if 'debug_reply_data' not in st.session_state:
                    st.session_state.debug_reply_data = {}
                st.session_state.debug_reply_data[level] = reply_result
                
                # Game Master workflow for scenarios with GM
                if has_game_master(scenario_filename):
                    with st.status("Determining story outcome...", expanded=False) as gm_status:
                        game_master = GameMaster()
                        gm_prompt = load_game_master_prompt(scenario_filename)
                        
                        if gm_prompt:
                            story_outcome = game_master.generate_story_outcome(
                                gm_prompt, email_content, recipient_reply, model
                            )
                            
                            if story_outcome:
                                recipient_reply = f"{recipient_reply}\n\n---\n\n**Story Outcome:**\n{story_outcome}"
                                gm_status.update(label="✅ Story outcome determined!", state="complete")
                            else:
                                gm_status.update(label="⚠️ Story outcome generation failed", state="error")
                        else:
                            gm_status.update(label="⚠️ GM prompt not found", state="error")
            
            # Step 3: Evaluate email
            evaluation = _evaluate_email(
                ai_services['email_evaluator'], scenario, email_content, 
                rubric, recipient_reply, model, scenario_filename
            )
            
            # Extract goal achievement
            goal_achieved = extract_goal_achievement_score(evaluation)
            
            # Strategy detection for Level 3 conditional progression
            strategy_analysis = None
            if level == 3 and goal_achieved:
                with st.status("Analyzing persuasion strategies...", expanded=False) as status:
                    strategy_analysis = detect_forbidden_strategies(email_content, model)
                    status.update(label="✅ Strategy analysis complete!", state="complete")
            
            # Prepare evaluation data
            evaluation_data = {
                "scenario": scenario,
                "email": email_content,
                "recipient_reply": recipient_reply,
                "rubric": rubric,
                "evaluation": evaluation,
                "goal_achieved": goal_achieved
            }
            
            if strategy_analysis:
                evaluation_data["strategy_analysis"] = strategy_analysis
            
            # Update session state for level completion
            _update_session_state_for_level_completion(
                level, goal_achieved, email_content, evaluation_data, strategy_analysis, session_id
            )
            
            # Handle database persistence
            _handle_database_persistence(
                session_id, level, email_content, evaluation, recipient_reply,
                rubric, goal_achieved, db_functions, strategy_analysis=strategy_analysis
            )
            
            # Success message and rerun to show results
            st.success("🎉 Evaluation Complete!")
            st.rerun()
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            st.error(f"❌ Error during evaluation: {str(e)}")
            st.error("Please check your API keys and try again.")
            
            # Show detailed error information in an expander for debugging
            with st.expander("🔍 Technical Details (for debugging)", expanded=False):
                st.code(error_details)
                
            # Make sure we don't leave the UI in a broken state
            st.info("💡 If the error persists, try refreshing the page or contact support.")

def process_email_evaluation_user_mode_multi_turn(scenario, email_content, model, level, session_id, turn_number):
    """Process email evaluation for multi-turn levels with conversation context"""
    
    # Initialize AI services and database functions
    ai_services = _initialize_ai_services()
    db_functions = _import_session_manager_functions()
    
    # Import additional function for conversation history
    from session_manager import get_conversation_history
    
    with st.spinner("🤖 Processing your email..."):
        try:
            # Get conversation history to build context
            conversation_history = get_conversation_history(session_id, level)
            
            # Build conversation context for Adam
            conversation_context = ""
            if conversation_history:
                conversation_context = "\n\nPrevious conversation:\n"
                for turn_data in conversation_history:
                    conversation_context += f"\nTurn {turn_data['turn_number']}:\n"
                    conversation_context += f"HR: {turn_data['email_content']}\n"
                    if turn_data['recipient_reply']:
                        conversation_context += f"Adam: {turn_data['recipient_reply']}\n"
            
            # Step 1: Generate Adam's reply
            scenario_file = st.session_state.get('selected_scenario_file', 'scenario_5.4.txt')
            recipient_prompt = load_recipient_prompt(scenario_file)
            if not recipient_prompt:
                st.error("Failed to load recipient prompt")
                return
            
            # Add conversation context to recipient prompt
            contextualized_prompt = recipient_prompt + conversation_context + f"\n\nNow respond to this new email from HR:\n{email_content}"
            
            with st.status("Generating Adam's response (using 5 concurrent samples for consistency)...", expanded=False) as status:
                # Check if we've reached the turn limit
                if turn_number > MAX_TURNS:
                    # Adam's final resignation email
                    recipient_reply = generate_adam_final_response()
                    reply_result = None  # No debug data for final response
                else:
                    reply_result = ai_services['email_recipient'].generate_reply_with_majority(
                        contextualized_prompt, email_content, model, scenario=scenario, rubric=None, scenario_filename=st.session_state.get("selected_scenario_file")
                    )
                    if not reply_result:
                        st.error("Failed to generate Adam's reply")
                        return
                    
                    recipient_reply = reply_result['reply']
                    majority_outcome = reply_result['majority_outcome']
                    outcome_counts = reply_result['outcome_counts']
                    
                    status.update(label=f"✅ Adam's response generated! (Majority: {majority_outcome}, Distribution: {outcome_counts})", state="complete")
                    
                    # Store debug info in session state
                    if 'debug_reply_data' not in st.session_state:
                        st.session_state.debug_reply_data = {}
                    st.session_state.debug_reply_data[level] = reply_result
                
                if turn_number > MAX_TURNS:
                    status.update(label="✅ Adam's final response generated!", state="complete")
            
            # Step 2: Save email submission to database first
            submission_id = db_functions['save_email_submission'](session_id, level, email_content, turn_number)
            if not submission_id:
                st.error("Failed to save email submission")
                return
            
            # Step 3: Generate rubric (optional)
            rubric = _generate_rubric_if_enabled(ai_services['rubric_generator'], scenario, model)
            
            # Step 4: Evaluate the email with conversation context
            try:
                evaluation = _evaluate_email(
                    ai_services['email_evaluator'], scenario, email_content,
                    rubric, recipient_reply, model, 
                    st.session_state.get("selected_scenario_file"),
                    conversation_context
                )
            except Exception as eval_error:
                st.error(f"❌ **Email evaluation failed:** {str(eval_error)}")
                # Use a fallback evaluation
                evaluation = f"Evaluation failed due to error: {str(eval_error)}. Turn {turn_number} completed but could not be properly evaluated."
                st.warning("🔧 Using fallback evaluation to preserve turn data")
            
            # Step 5: Extract goal achievement from evaluation
            try:
                goal_achieved = extract_goal_achievement_score(evaluation)
            except ValueError as e:
                st.error(f"Error extracting goal achievement: {e}")
                goal_achieved = False  # Default to False if extraction fails
            
            # Step 6: Save evaluation result to database
            evaluation_data = {
                "evaluation": evaluation,
                "recipient_reply": recipient_reply,
                "rubric": rubric,
                "goal_achieved": goal_achieved
            }
            
            try:
                if not db_functions['save_evaluation_result'](submission_id, evaluation_data):
                    raise Exception("save_evaluation_result returned False")
                st.write(f"DEBUG: Successfully saved evaluation result for submission {submission_id}")
            except Exception as save_error:
                st.error(f"❌ **Database save failed:** {str(save_error)}")
                st.error("The evaluation was completed but could not be saved to the database")
                return
            
            # Step 7: Handle level completion
            if goal_achieved:
                # Goal achieved - success regardless of turn number!
                level_success = db_functions['handle_level_success'](session_id, level)
                if not level_success:
                    st.error("❌ **Database Error:** Goal achieved but failed to mark level as complete. Please try again.")
                    return
                
                st.success(f"🎯 **Goal achieved in Turn {turn_number}!** You successfully helped Adam express his concerns.")
                
                # Prepare final evaluation data for session state
                final_evaluation_data = {
                    "scenario": scenario,
                    "email": email_content,
                    "recipient_reply": recipient_reply,
                    "rubric": rubric,
                    "evaluation": evaluation,
                    "goal_achieved": goal_achieved,
                    "turn_number": turn_number
                }
                
                # Update session state for level completion
                _update_session_state_for_level_completion(
                    level, goal_achieved, email_content, final_evaluation_data, session_id=session_id
                )
                
                # Check if this completes the entire game
                from config import MAX_AVAILABLE_LEVEL
                if level == MAX_AVAILABLE_LEVEL and is_game_complete(session_id):
                    st.session_state.game_completed = True
                
            elif not goal_achieved and turn_number >= MAX_TURNS:
                recipient_reply = generate_adam_final_response()

                # Turn limit reached AND goal not achieved = failure
                db_functions['handle_level_failure'](session_id, level)
                st.warning(f"⏱️ **Turn limit reached** ({MAX_TURNS} turns)")
                st.info("💼 Adam has decided to just bring noise canceling headphones and a blanket to work.")
                
                # Prepare final evaluation data for session state
                final_evaluation_data = {
                    "scenario": scenario,
                    "email": email_content,
                    "recipient_reply": recipient_reply,
                    "rubric": rubric,
                    "evaluation": evaluation,
                    "goal_achieved": goal_achieved,
                    "turn_number": turn_number,
                    "max_turns_reached": True
                }
                
                # Initialize session state containers if needed
                if 'completed_levels' not in st.session_state:
                    st.session_state.completed_levels = set()
                if 'level_evaluations' not in st.session_state:
                    st.session_state.level_evaluations = {}
                    
                st.session_state.level_evaluations[level] = final_evaluation_data
            
            else:
                # Intermediate turn: goal not achieved and turn limit not reached
                # Don't store in level_evaluations to prevent premature final verdict display
                pass
            
            # Step 8: Display results immediately
            st.markdown("---")
            st.subheader(f"📊 Turn {turn_number} Results")
            
            # Always show Adam's response
            st.markdown(f"**Adam's Response:**")
            st.markdown(
                f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #6c757d;">
                {recipient_reply.replace(chr(10), '<br>')}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Always show evaluation for debugging
            st.markdown("**📋 Evaluation:**")
            
            # Show rubric if available
            use_rubric = st.session_state.get('use_rubric', True)
            if use_rubric and rubric:
                st.markdown("**Rubric Used:**")
                st.markdown(
                    f"""
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 2px solid #6c757d; margin-bottom: 10px;">
                    {rubric}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            processed_evaluation = process_evaluation_text(evaluation)
            
            # Color code based on goal achievement
            bg_color = "#d4edda" if goal_achieved else "#fff3cd"
            border_color = "#155724" if goal_achieved else "#ffc107"
            
            st.markdown(
                f"""
                <div style="background-color: {bg_color}; padding: 15px; border-radius: 5px; border-left: 4px solid {border_color};">
                {processed_evaluation}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Show goal achievement status clearly
            if goal_achieved:
                st.success("🎯 **Goal Achieved!** - Level will be marked as complete")
            else:
                st.warning("⚠️ **Goal Not Achieved** - Conversation continues")
                
                # Show hint for continuing the conversation
                if turn_number < MAX_TURNS:
                    st.info("💡 Adam hasn't fully opened up yet. Try asking more specific questions about his work environment or what has changed recently.")
            
            # Force page refresh to show updated conversation
            st.rerun()
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            st.error(f"❌ **Evaluation Failed:** {str(e)}")
            st.error(f"**Debug Details:**")
            st.code(error_details)
            
            # Log the error for debugging
            logger.error(f"Evaluation failed for session {session_id}, level {level}, turn {turn_number}: {error_details}")
            
            # Try to save a minimal evaluation result so the turn isn't completely lost
            try:
                st.warning("🔧 **Attempting to save partial result...**")
                
                # Use the partial data we have
                minimal_evaluation = f"Evaluation failed due to error: {str(e)}"
                minimal_reply = "Error occurred during response generation."
                
                evaluation_data = {
                    "evaluation": minimal_evaluation,
                    "recipient_reply": minimal_reply, 
                    "rubric": None,
                    "goal_achieved": False
                }
                
                if db_functions['save_evaluation_result'](submission_id, evaluation_data):
                    st.success("✅ **Partial result saved** - turn data preserved")
                else:
                    st.error("❌ **Failed to save even partial result**")
                    
            except Exception as save_error:
                st.error(f"❌ **Could not save partial result:** {str(save_error)}")
            
            return


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

def process_email_evaluation_developer_mode(scenario, email_content, model):
    """Process email evaluation using custom settings from developer mode"""
    
    # Initialize AI services
    ai_services = _initialize_ai_services()
    
    with st.spinner("🤖 Processing your email..."):
        try:
            # Step 1: Generate rubric (conditional)
            rubric = _generate_rubric_if_enabled(ai_services['rubric_generator'], scenario, model)
            
            # Step 2: Generate recipient reply with majority voting
            with st.status("Generating recipient response (using 5 concurrent samples for consistency)...", expanded=False) as status:
                # Use custom recipient prompt from developer interface
                recipient_prompt_value = st.session_state.get("recipient_prompt", "")
                if not recipient_prompt_value.strip():
                    recipient_prompt_value = DEFAULT_RECIPIENT_PROMPT
                
                scenario_filename = st.session_state.get("selected_scenario_file", "")
                reply_result = ai_services['email_recipient'].generate_reply_with_majority(
                    recipient_prompt_value, email_content, model, scenario=scenario, rubric=rubric, scenario_filename=scenario_filename
                )
                if not reply_result:
                    st.error("Failed to generate recipient reply")
                    return
                
                recipient_reply = reply_result['reply']
                majority_outcome = reply_result['majority_outcome']
                outcome_counts = reply_result['outcome_counts']
                
                status.update(label=f"✅ Recipient reply generated! (Majority: {majority_outcome}, Distribution: {outcome_counts})", state="complete")
            
            # DEBUG: Show majority reply analysis
            _display_majority_reply_debug(reply_result, expanded=False, unique_id="dev_mode")
            
            # Store debug info in session state for developer mode too
            if 'debug_reply_data' not in st.session_state:
                st.session_state.debug_reply_data = {}
            current_level = st.session_state.get('current_level', 0)
            st.session_state.debug_reply_data[current_level] = reply_result
            
            # Game Master workflow for scenarios with GM
            scenario_filename = st.session_state.get("selected_scenario_file", "")
            if has_game_master(scenario_filename):
                with st.status("Determining story outcome...", expanded=False) as gm_status:
                    game_master = GameMaster()
                    gm_prompt = load_game_master_prompt(scenario_filename)
                    
                    if gm_prompt:
                        story_outcome = game_master.generate_story_outcome(
                            gm_prompt, email_content, recipient_reply, model
                        )
                        
                        if story_outcome:
                            # Combine recipient reply with story outcome
                            recipient_reply = f"{recipient_reply}\n\n---\n\n**Story Outcome:**\n{story_outcome}"
                            gm_status.update(label="✅ Story outcome determined!", state="complete")
                        else:
                            gm_status.update(label="⚠️ Story outcome generation failed", state="error")
                    else:
                        gm_status.update(label="⚠️ GM prompt not found", state="error")
            
            # Step 3: Evaluate email
            evaluation = _evaluate_email(
                ai_services['email_evaluator'], scenario, email_content, 
                rubric, recipient_reply, model, scenario_filename
            )
            
            # Display results inline (no page redirect)
            st.success("🎉 Evaluation Complete!")
            
            # Show goal achievement status
            goal_achieved = extract_goal_achievement_score(evaluation)
            if goal_achieved:
                st.success("🎯 **Goal Achieved!** You successfully persuaded the recipient.")
            else:
                st.error("❌ **Goal Not Achieved** - You can improve your approach.")

            # Show recipient's reply
            st.subheader("📨 Recipient's Reply")
            st.markdown(recipient_reply)
            
            # Show rubric (collapsible) - only if using rubrics
            use_rubric = st.session_state.get('use_rubric', True)
            if use_rubric and rubric:
                with st.expander("📏 Evaluation Rubric", expanded=False):
                    st.markdown(rubric)
            
            # Show detailed evaluation (collapsible)
            with st.expander("🤖 Detailed AI Evaluation", expanded=True):
                _show_evaluation_styles()
                processed_evaluation = process_evaluation_text(evaluation)
                st.markdown(f'<div class="evaluation-content">{processed_evaluation}</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"❌ Error during evaluation: {str(e)}")
            st.error("Please check your API keys and try again.")

def generate_adam_final_response():
    """Generate Adam's final resignation response after max turns"""
    return """Hi,

Thank you for reaching out multiple times. I appreciate your concern.

After thinking about it, I've decided that rather than continue to discuss this, I'll just adapt to the current situation. I'm planning to bring noise canceling headphones and a blanket to work to help with the temperature and noise issues I mentioned.

I think this will resolve the concerns I raised, and I can continue focusing on my work as usual.

Thanks again for your time.

Best regards,
Adam""" 