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
    load_communication_goal,
    get_all_additional_emails,
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

# def process_email_evaluation_with_history(scenario, email_content, model, level):
#     """Process email evaluation with history management for user mode"""
    
#     # Initialize AI services
#     email_generator = EmailGenerator()
#     email_evaluator = EmailEvaluator()
#     email_recipient = EmailRecipient()
#     rubric_generator = RubricGenerator()
    
#     with st.spinner("🤖 Processing your email..."):
#         try:
#             # Step 1: Load or generate rubric (conditional)
#             use_rubric = st.session_state.get('use_rubric', True)
#             if use_rubric:
#                 with st.status("Loading evaluation rubric...", expanded=False) as status:
#                     scenario_filename = st.session_state.get("selected_scenario_file", "default_scenario.txt")
#                     rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
#                     status.update(label="✅ Rubric ready!", state="complete")
#             else:
#                 rubric = None
            
#             # Step 2: Generate recipient reply
#             with st.status("Generating recipient response...", expanded=False) as status:
#                 # Load recipient prompt based on selected scenario file
#                 if st.session_state.get("selected_scenario_file"):
#                     recipient_prompt = load_recipient_prompt(st.session_state.selected_scenario_file)
#                 else:
#                     recipient_prompt = DEFAULT_RECIPIENT_PROMPT
                
#                 recipient_reply = email_recipient.generate_reply(recipient_prompt, email_content, model)
#                 status.update(label="✅ Recipient reply generated!", state="complete")
            
#             # Step 3: Evaluate email
#             with st.status("Evaluating your email...", expanded=False) as status:
#                 evaluation = email_evaluator.evaluate_email(scenario, email_content, rubric, recipient_reply, model)
#                 status.update(label="✅ Evaluation complete!", state="complete")
            
#             # Extract goal achievement
#             goal_achieved = extract_goal_achievement_score(evaluation)
            
#             # Store email content by level
#             st.session_state.level_emails[level] = email_content
            
#             # Store evaluation results
#             st.session_state.level_evaluations[level] = {
#                 "scenario": scenario,
#                 "email": email_content,
#                 "recipient_reply": recipient_reply,
#                 "rubric": rubric,
#                 "evaluation": evaluation,
#                 "goal_achieved": goal_achieved
#             }
            
#             # Update completed levels if successful
#             if goal_achieved and level not in st.session_state.completed_levels:
#                 st.session_state.completed_levels.add(level)
            
#             # Add evaluation page to history
#             evaluation_page = {"type": "evaluation", "level": level}
            
#             # Check if we're retrying a level (if the last page in history is evaluation for the same level)
#             if (st.session_state.page_history and 
#                 st.session_state.page_history[-1].get("type") == "evaluation" and 
#                 st.session_state.page_history[-1].get("level") == level):
#                 # We're retrying - replace the last evaluation page
#                 st.session_state.page_history[-1] = evaluation_page
#             else:
#                 # Normal flow - add new evaluation page
#                 st.session_state.page_history.append(evaluation_page)
            
#             # Navigate to evaluation page
#             st.session_state.current_history_index = len(st.session_state.page_history) - 1
            
#             # Success message
#             st.success("🎉 Evaluation Complete! Showing results...")
#             st.rerun()
            
#         except Exception as e:
#             st.error(f"❌ Error during evaluation: {str(e)}")
#             st.error("Please check your API keys and try again.")


def process_email_evaluation_user_mode_inline(scenario, email_content, model, level, session_id=None):
    """Process email evaluation for user mode with inline results display and database persistence"""
    
    # Initialize AI services
    email_generator = EmailGenerator()
    email_evaluator = EmailEvaluator()
    email_recipient = EmailRecipient()
    rubric_generator = RubricGenerator()
    
    # Import session manager functions for database operations
    from session_manager import (
        save_email_submission,
        save_evaluation_result,
        handle_level_success,
        handle_level_failure,
        get_conversation_history,
        get_next_turn_number
    )
    
    with st.spinner("🤖 Processing your email..."):
        try:
            # Step 1: Load or generate rubric (conditional)
            use_rubric = st.session_state.get('use_rubric', True)
            if use_rubric:
                with st.status("Loading evaluation rubric...", expanded=False) as status:
                    scenario_filename = st.session_state.get("selected_scenario_file", "")
                    
                    if scenario_filename:
                        rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
                    else:
                        # Fallback to direct generation if no filename available
                        rubric = rubric_generator.generate_rubric(scenario, model)
                    
                    if not rubric:
                        st.warning("⚠️ Rubric generation failed - continuing without rubric")
                        rubric = None
                    else:
                        status.update(label="✅ Rubric ready!", state="complete")
            else:
                rubric = None
            
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
                        reply_result = email_recipient.generate_reply_with_majority(
                            recipient_prompt, email_content, model, num_samples=5,
                            scenario=scenario, rubric=rubric, scenario_filename=scenario_filename
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
                
                # DEBUG: Show majority reply analysis for multi-recipient (TODO: Remove after debugging)
                for recipient_name, reply_data in recipient_debug_data.items():
                    st.markdown(f"**{recipient_name.title()} Debug Analysis:**")
                    _display_majority_reply_debug(reply_data, expanded=False, unique_id=recipient_name)
                
                # Store debug info in session state so it persists in results
                if 'debug_reply_data' not in st.session_state:
                    st.session_state.debug_reply_data = {}
                st.session_state.debug_reply_data[level] = recipient_debug_data
            else:
                # Single recipient scenario (Levels 0, 1, 3, 3.5, 4, 5)
                with st.status("Generating recipient response (using 5 concurrent samples for consistency)...", expanded=False) as status:
                    # Load recipient prompt based on selected scenario file
                    if st.session_state.get("selected_scenario_file"):
                        recipient_prompt = load_recipient_prompt(st.session_state.selected_scenario_file)
                    else:
                        recipient_prompt = DEFAULT_RECIPIENT_PROMPT
                    
                    reply_result = email_recipient.generate_reply_with_majority(
                        recipient_prompt, email_content, model, num_samples=5,
                        scenario=scenario, rubric=rubric, scenario_filename=scenario_filename
                    )
                    if not reply_result:
                        st.error("Failed to generate recipient reply")
                        return
                    
                    recipient_reply = reply_result['reply']
                    majority_outcome = reply_result['majority_outcome']
                    outcome_counts = reply_result['outcome_counts']
                    
                    status.update(label=f"✅ Recipient reply generated! (Majority: {majority_outcome}, Distribution: {outcome_counts})", state="complete")
                
                # DEBUG: Show majority reply analysis (TODO: Remove after debugging)
                _display_majority_reply_debug(reply_result, expanded=False, unique_id="single")
                
                # Store debug info in session state so it persists in results
                if 'debug_reply_data' not in st.session_state:
                    st.session_state.debug_reply_data = {}
                st.session_state.debug_reply_data[level] = reply_result
                
                # Game Master workflow for scenarios with GM (moved outside of recipient status)
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
            with st.status("Evaluating your email...", expanded=False) as status:
                evaluation = email_evaluator.evaluate_email(
                    scenario, email_content, rubric, recipient_reply, model, 
                    scenario_filename=scenario_filename
                )
                if not evaluation:
                    st.error("Failed to evaluate email")
                    return
                status.update(label="✅ Evaluation complete!", state="complete")
            
            # Extract goal achievement
            goal_achieved = extract_goal_achievement_score(evaluation)
            
            # Strategy detection for Level 3 conditional progression
            strategy_analysis = None
            if level == 3 and goal_achieved:
                with st.status("Analyzing persuasion strategies...", expanded=False) as status:
                    strategy_analysis = detect_forbidden_strategies(email_content, model)
                    status.update(label="✅ Strategy analysis complete!", state="complete")
            
            # Initialize session state containers if needed
            if 'level_emails' not in st.session_state:
                st.session_state.level_emails = {}
            if 'level_evaluations' not in st.session_state:
                st.session_state.level_evaluations = {}
            if 'completed_levels' not in st.session_state:
                st.session_state.completed_levels = set()
            if 'strategy_analysis' not in st.session_state:
                st.session_state.strategy_analysis = {}
            
            # Store email content by level (session state for immediate UI)
            st.session_state.level_emails[level] = email_content
            
            # Store strategy analysis for Level 2
            if strategy_analysis:
                st.session_state.strategy_analysis[level] = strategy_analysis
            
            # Store evaluation results (session state for immediate UI)
            evaluation_data = {
                "scenario": scenario,
                "email": email_content,
                "recipient_reply": recipient_reply,
                "rubric": rubric,
                "evaluation": evaluation,
                "goal_achieved": goal_achieved
            }
            
            # Add strategy analysis to evaluation data if available
            if strategy_analysis:
                evaluation_data["strategy_analysis"] = strategy_analysis
                
            st.session_state.level_evaluations[level] = evaluation_data
            
            # Update completed levels based on success/failure (session state for immediate UI)
            # Always remove higher levels when redoing a level, as the progression path might have changed
            levels_to_remove = {l for l in st.session_state.completed_levels if l > level}
            st.session_state.completed_levels -= levels_to_remove
            
            # Clean up evaluation data and emails for invalidated levels
            for invalid_level in levels_to_remove:
                if invalid_level in st.session_state.get('level_evaluations', {}):
                    del st.session_state.level_evaluations[invalid_level]
                if invalid_level in st.session_state.get('level_emails', {}):
                    del st.session_state.level_emails[invalid_level]
            
            if goal_achieved:
                # Add this level to completed levels if successful
                st.session_state.completed_levels.add(level)
                
                # Check if this completes the entire game
                from config import MAX_AVAILABLE_LEVEL
                
                if level == MAX_AVAILABLE_LEVEL and session_id and is_game_complete(session_id):
                    # Game completed! Set flag for automatic leaderboard redirect
                    st.session_state.game_completed = True
            else:
                # If failed, also remove this level from completed levels
                st.session_state.completed_levels.discard(level)
            
            # Database persistence (if session_id provided)
            if session_id:
                try:
                    # Save email submission to database
                    submission_id = save_email_submission(session_id, level, email_content)
                    
                    if submission_id:
                        # Save evaluation result to database
                        evaluation_data = {
                            'evaluation': evaluation,
                            'recipient_reply': recipient_reply,
                            'rubric': rubric,
                            'goal_achieved': goal_achieved
                        }
                        save_evaluation_result(submission_id, evaluation_data)
                        
                        # Handle level success/failure in database
                        if goal_achieved:
                            level_success = handle_level_success(session_id, level)
                            if not level_success:
                                st.error("❌ **Database Error:** Goal achieved but failed to mark level as complete.")
                        else:
                            handle_level_failure(session_id, level)
                            
                except Exception as e:
                    # Don't fail the entire evaluation if database save fails
                    st.warning(f"⚠️ Results saved to current session but database save failed: {str(e)}")
                    st.info("Your progress is temporarily stored and will be available until you close the browser.")
            
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


# def process_email_evaluation_user_mode(scenario, email_content, model):
#     """Process email evaluation using default settings for user mode"""
#     # Show loading screen with multiple steps
#     progress_text = st.empty()
#     progress_bar = st.progress(0)
    
#     try:
#         # Step 1: Load or generate rubric (conditional)
#         use_rubric = st.session_state.get('use_rubric', True)
#         if use_rubric:
#             progress_text.text("🔄 Loading evaluation rubric...")
#             progress_bar.progress(0.25)
            
#             rubric_generator = RubricGenerator()
#             scenario_filename = st.session_state.get("selected_scenario_file", "")
            
#             if scenario_filename:
#                 rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
#             else:
#                 # Fallback to direct generation if no filename available
#                 rubric = rubric_generator.generate_rubric(scenario, model)
            
#             if not rubric:
#                 st.error("Failed to generate rubric")
#                 return
#         else:
#             rubric = None
        
#         # Step 2: Generate recipient reply (using default recipient prompt for user version)
#         progress_text.text("📨 Awaiting response from recipient...")
#         progress_bar.progress(0.33 if use_rubric else 0.5)
        
#         # Load default recipient prompt based on selected scenario
#         if st.session_state.get("selected_scenario_file"):
#             default_recipient_prompt = load_recipient_prompt(st.session_state.selected_scenario_file)
#         else:
#             default_recipient_prompt = DEFAULT_RECIPIENT_PROMPT
        
#         recipient = EmailRecipient()
#         recipient_reply = recipient.generate_reply(
#             default_recipient_prompt, email_content, model
#         )
        
#         if not recipient_reply:
#             st.error("Failed to generate recipient reply")
#             return
        
#         # Game Master workflow for scenarios with GM
#         scenario_filename = st.session_state.get("selected_scenario_file", "")
#         if has_game_master(scenario_filename):
#             progress_text.text("🎲 Determining story outcome...")
#             progress_bar.progress(0.5)
            
#             game_master = GameMaster()
#             gm_prompt = load_game_master_prompt(scenario_filename)
            
#             if gm_prompt:
#                 story_outcome = game_master.generate_story_outcome(
#                     gm_prompt, email_content, recipient_reply, model
#                 )
                
#                 if story_outcome:
#                     # Combine recipient reply with story outcome
#                     recipient_reply = f"{recipient_reply}\n\n---\n\n**Story Outcome:**\n{story_outcome}"
        
#         # Step 3: Evaluate the email using the generated rubric (using default evaluator prompt)
#         progress_text.text("📊 Evaluating your email...")
#         progress_bar.progress(0.66 if use_rubric else 0.75)
        
#         evaluator = EmailEvaluator()
#         scenario_filename = st.session_state.get("selected_scenario_file", "")
#         evaluation_result = evaluator.evaluate_email(
#             scenario, email_content, rubric, recipient_reply, model, 
#             scenario_filename=scenario_filename
#         )
        
#         if not evaluation_result:
#             st.error("Failed to evaluate email")
#             return
        
#         # Step 4: Complete
#         progress_text.text("✅ Evaluation complete!")
#         progress_bar.progress(1.0)
        
#         # Store all data for results page
#         st.session_state.evaluation_result = {
#             "scenario": scenario,
#             "email": email_content,
#             "rubric": rubric,
#             "recipient_reply": recipient_reply,
#             "evaluation": evaluation_result,
#             "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         }
        
#         # Store the email for this level
#         if 'current_level' in st.session_state:
#             if 'level_emails' not in st.session_state:
#                 st.session_state.level_emails = {}
#             st.session_state.level_emails[st.session_state.current_level] = email_content
        
#         # Check if user successfully achieved the goal before marking level complete
#         goal_success = extract_goal_achievement_score(evaluation_result)
        
#         # Handle level progression based on success (only for user mode)
#         if 'current_level' in st.session_state:
#             if 'completed_levels' not in st.session_state:
#                 st.session_state.completed_levels = set()
                
#             if goal_success:
#                 # Mark current level as completed
#                 st.session_state.completed_levels.add(st.session_state.current_level)
                
#                 # Store the level they just completed for navigation
#                 st.session_state.evaluation_result["completed_level"] = st.session_state.current_level
                
#                 # Auto-advance to next level if available
#                 if st.session_state.current_level < MAX_AVAILABLE_LEVEL:
#                     st.session_state.current_level += 1
#             else:
#                 # Store the current level for "try again" scenario
#                 st.session_state.evaluation_result["failed_level"] = st.session_state.current_level
            
#         # Store goal achievement result for display
#         st.session_state.evaluation_result["goal_achieved"] = goal_success
        
#         # Switch to results page
#         st.session_state.current_page = "results"
#         st.rerun()
        
#     except Exception as e:
#         st.error(f"Error during processing: {str(e)}")


def process_email_evaluation_developer_mode(scenario, email_content, model):
    """Process email evaluation using custom settings from developer mode"""
    
    # Initialize AI services
    email_generator = EmailGenerator()
    email_evaluator = EmailEvaluator()
    email_recipient = EmailRecipient()
    rubric_generator = RubricGenerator()
    
    with st.spinner("🤖 Processing your email..."):
        try:
            # Step 1: Load or generate rubric (conditional)
            use_rubric = st.session_state.get('use_rubric', True)
            if use_rubric:
                with st.status("Loading evaluation rubric...", expanded=False) as status:
                    scenario_filename = st.session_state.get("selected_scenario_file", "")
                    
                    if scenario_filename:
                        rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
                    else:
                        # Fallback to direct generation if no filename available
                        rubric = rubric_generator.generate_rubric(scenario, model)
                    
                    if not rubric:
                        st.warning("⚠️ Rubric generation failed - continuing without rubric")
                        rubric = None
                    else:
                        status.update(label="✅ Rubric ready!", state="complete")
            else:
                rubric = None
            
            # Step 2: Generate recipient reply with majority voting
            with st.status("Generating recipient response (using 5 concurrent samples for consistency)...", expanded=False) as status:
                # Use custom recipient prompt from developer interface
                recipient_prompt_value = st.session_state.get("recipient_prompt", "")
                if not recipient_prompt_value.strip():
                    recipient_prompt_value = DEFAULT_RECIPIENT_PROMPT
                
                reply_result = email_recipient.generate_reply_with_majority(
                    recipient_prompt_value, email_content, model, num_samples=5,
                    scenario=scenario, rubric=rubric, scenario_filename=scenario_filename
                )
                if not reply_result:
                    st.error("Failed to generate recipient reply")
                    return
                
                recipient_reply = reply_result['reply']
                majority_outcome = reply_result['majority_outcome']
                outcome_counts = reply_result['outcome_counts']
                
                status.update(label=f"✅ Recipient reply generated! (Majority: {majority_outcome}, Distribution: {outcome_counts})", state="complete")
            
            # DEBUG: Show majority reply analysis (TODO: Remove after debugging)
            _display_majority_reply_debug(reply_result, expanded=False, unique_id="dev_mode")
            
            # Store debug info in session state for developer mode too
            if 'debug_reply_data' not in st.session_state:
                st.session_state.debug_reply_data = {}
            current_level = st.session_state.get('current_level', 0)
            st.session_state.debug_reply_data[current_level] = reply_result
            
            # Game Master workflow for scenarios with GM (moved outside of recipient status)
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
            with st.status("Evaluating your email...", expanded=False) as status:
                scenario_filename = st.session_state.get("selected_scenario_file", "")
                evaluation = email_evaluator.evaluate_email(
                    scenario, email_content, rubric, recipient_reply, model, 
                    scenario_filename=scenario_filename
                )
                if not evaluation:
                    st.error("Failed to evaluate email")
                    return
                status.update(label="✅ Evaluation complete!", state="complete")
            
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


def process_email_evaluation_user_mode_multi_turn(scenario, email_content, model, level, session_id, turn_number):
    """Process email evaluation for multi-turn levels with conversation context"""
    
    # Initialize AI services
    email_generator = EmailGenerator()
    email_evaluator = EmailEvaluator()
    email_recipient = EmailRecipient()
    rubric_generator = RubricGenerator()
    
    # Import session manager functions for database operations
    from session_manager import (
        save_email_submission,
        save_evaluation_result,
        handle_level_success,
        handle_level_failure,
        get_conversation_history
    )
    
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
            
            # Step 1: Load recipient prompt and add conversation context
            scenario_file = st.session_state.get('selected_scenario_file', 'scenario_5.4.txt')
            recipient_prompt = load_recipient_prompt(scenario_file)
            if not recipient_prompt:
                st.error("Failed to load recipient prompt")
                return
            
            # Add conversation context to recipient prompt
            contextualized_prompt = recipient_prompt + conversation_context + f"\n\nNow respond to this new email from HR:\n{email_content}"
            
            # Step 2: Generate Adam's reply with majority voting
            with st.status("Generating Adam's response (using 5 concurrent samples for consistency)...", expanded=False) as status:
                # Check if we've reached the turn limit
                if turn_number > MAX_TURNS:
                    # Adam's final resignation email (but still evaluate the user's email!)
                    recipient_reply = generate_adam_final_response()
                    reply_result = None  # No debug data for final response
                    # Note: Don't set goal_achieved here - let the evaluation determine it
                else:
                    reply_result = email_recipient.generate_reply_with_majority(
                        contextualized_prompt, email_content, model, num_samples=5,
                        scenario=scenario, rubric=rubric, scenario_filename=st.session_state.get("selected_scenario_file")
                    )
                    if not reply_result:
                        st.error("Failed to generate Adam's reply")
                        return
                    
                    recipient_reply = reply_result['reply']
                    majority_outcome = reply_result['majority_outcome']
                    outcome_counts = reply_result['outcome_counts']
                    
                    status.update(label=f"✅ Adam's response generated! (Majority: {majority_outcome}, Distribution: {outcome_counts})", state="complete")
                    
                    # Store debug info in session state so it persists in results
                    # (Don't show debug expander here to avoid nested expander issues in multi-turn)
                    if 'debug_reply_data' not in st.session_state:
                        st.session_state.debug_reply_data = {}
                    st.session_state.debug_reply_data[level] = reply_result
                
                if turn_number <= MAX_TURNS:
                    pass  # Status already updated above
                else:
                    status.update(label="✅ Adam's final response generated!", state="complete")
            
            # Step 3: Save email submission to database
            submission_id = save_email_submission(session_id, level, email_content, turn_number)
            if not submission_id:
                st.error("Failed to save email submission")
                return
            
            # Step 4: Load or generate rubric (optional)
            use_rubric = st.session_state.get('use_rubric', True)
            rubric = None
            if use_rubric:
                try:
                    with st.status("Loading evaluation rubric...", expanded=False) as status:
                        scenario_filename = st.session_state.get("selected_scenario_file", "")
                        if scenario_filename:
                            rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
                        else:
                            rubric = rubric_generator.generate_rubric(scenario, model)
                        
                        if not rubric:
                            st.warning("⚠️ Rubric generation failed - continuing without rubric")
                            rubric = None
                        else:
                            status.update(label="✅ Rubric ready!", state="complete")
                except Exception as rubric_error:
                    st.warning(f"⚠️ Rubric generation error: {str(rubric_error)} - continuing without rubric")
                    rubric = None
            
            # Step 5: Always evaluate the email (with or without rubric)
            evaluation = None
            try:
                with st.status("Evaluating your email...", expanded=False) as status:
                    # Build evaluation context with conversation history
                    evaluation_context = scenario + conversation_context + f"\n\nLatest email from HR:\n{email_content}\n\nAdam's response:\n{recipient_reply}"
                    
                    evaluation = email_evaluator.evaluate_email(
                        evaluation_context, 
                        email_content, 
                        rubric, 
                        recipient_reply, 
                        model,
                        scenario_filename=st.session_state.get("selected_scenario_file")
                    )
                    
                    if not evaluation:
                        raise ValueError("Email evaluator returned None/empty evaluation")
                    
                    # Debug: Log evaluation result
                    st.write(f"DEBUG: Evaluation result received, length: {len(evaluation)}")
                    status.update(label="✅ Evaluation complete!", state="complete")
                    
            except Exception as eval_error:
                st.error(f"❌ **Email evaluation failed:** {str(eval_error)}")
                # Use a fallback evaluation
                evaluation = f"Evaluation failed due to error: {str(eval_error)}. Turn {turn_number} completed but could not be properly evaluated."
                st.warning("🔧 Using fallback evaluation to preserve turn data")
            
            # Step 6: Extract goal achievement from evaluation
            try:
                goal_achieved = extract_goal_achievement_score(evaluation)
            except ValueError as e:
                st.error(f"Error extracting goal achievement: {e}")
                goal_achieved = False  # Default to False if extraction fails
            
            # Step 7: Save evaluation result to database
            evaluation_data = {
                "evaluation": evaluation,  # This key matches what save_evaluation_result expects
                "recipient_reply": recipient_reply,
                "rubric": rubric,
                "goal_achieved": goal_achieved
            }
            
            try:
                if not save_evaluation_result(submission_id, evaluation_data):
                    raise Exception("save_evaluation_result returned False")
                st.write(f"DEBUG: Successfully saved evaluation result for submission {submission_id}")
            except Exception as save_error:
                st.error(f"❌ **Database save failed:** {str(save_error)}")
                st.error("The evaluation was completed but could not be saved to the database")
                return
            
            # Step 8: Handle level completion
            if goal_achieved:
                # Goal achieved - success regardless of turn number!
                level_success = handle_level_success(session_id, level)
                if not level_success:
                    st.error("❌ **Database Error:** Goal achieved but failed to mark level as complete. Please try again.")
                    return
                
                st.success(f"🎯 **Goal achieved in Turn {turn_number}!** You successfully helped Adam express his concerns.")
                
                # Initialize session state containers if needed
                if 'completed_levels' not in st.session_state:
                    st.session_state.completed_levels = set()
                if 'level_evaluations' not in st.session_state:
                    st.session_state.level_evaluations = {}
                    
                # Update session state - remove higher levels when completing a level
                levels_to_remove = {l for l in st.session_state.completed_levels if l > level}
                st.session_state.completed_levels -= levels_to_remove
                
                # Clean up evaluation data and emails for invalidated levels
                for invalid_level in levels_to_remove:
                    if invalid_level in st.session_state.get('level_evaluations', {}):
                        del st.session_state.level_evaluations[invalid_level]
                    if invalid_level in st.session_state.get('level_emails', {}):
                        del st.session_state.level_emails[invalid_level]
                
                # Add this level to completed levels
                st.session_state.completed_levels.add(level)
                
                # Check if this completes the entire game
                from config import MAX_AVAILABLE_LEVEL
                
                if level == MAX_AVAILABLE_LEVEL and is_game_complete(session_id):
                    # Game completed! Set flag for automatic leaderboard redirect
                    st.session_state.game_completed = True
                
                # Store final evaluation results in session state for show_level_results
                final_evaluation_data = {
                    "scenario": scenario,
                    "email": email_content,
                    "recipient_reply": recipient_reply,
                    "rubric": rubric,
                    "evaluation": evaluation,
                    "goal_achieved": goal_achieved,
                    "turn_number": turn_number
                }
                    
                st.session_state.level_evaluations[level] = final_evaluation_data
            
            elif not goal_achieved and turn_number >= MAX_TURNS:
                recipient_reply = generate_adam_final_response()

                # Turn limit reached AND goal not achieved = failure
                handle_level_failure(session_id, level)
                st.warning(f"⏱️ **Turn limit reached** ({MAX_TURNS} turns)")
                st.info("💼 Adam has decided to just bring noise canceling headphones and a blanket to work.")
                
                # Initialize session state containers if needed
                if 'completed_levels' not in st.session_state:
                    st.session_state.completed_levels = set()
                if 'level_evaluations' not in st.session_state:
                    st.session_state.level_evaluations = {}
                
                # Store final evaluation results in session state for show_level_results
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
                    
                st.session_state.level_evaluations[level] = final_evaluation_data
            
            else:
                # Intermediate turn: goal not achieved and turn limit not reached
                # Don't store in level_evaluations to prevent premature final verdict display
                # Just show the turn results inline
                pass
            
            # Step 9: Display results immediately
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
            
            # Always show evaluation for debugging (regardless of use_rubric setting)
            st.markdown("**📋 Evaluation:**")
            
            # Show rubric if available
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
                
                # # If we're at max turns, use Adam's final response
                # if turn_number > MAX_TURNS:
                #     minimal_reply = generate_adam_final_response()
                #     minimal_evaluation = f"Turn limit reached ({MAX_TURNS} turns). Evaluation failed but Adam's final response generated."
                
                evaluation_data = {
                    "evaluation": minimal_evaluation,
                    "recipient_reply": minimal_reply, 
                    "rubric": None,
                    "goal_achieved": False
                }
                
                if save_evaluation_result(submission_id, evaluation_data):
                    st.success("✅ **Partial result saved** - turn data preserved")
                else:
                    st.error("❌ **Failed to save even partial result**")
                    
            except Exception as save_error:
                st.error(f"❌ **Could not save partial result:** {str(save_error)}")
            
            return


def generate_adam_final_response():
    """Generate Adam's final resignation response after max turns"""
    return """Hi,

Thank you for reaching out multiple times. I appreciate your concern.

After thinking about it, I've decided that rather than continue to discuss this, I'll just adapt to the current situation. I'm planning to bring noise canceling headphones and a blanket to work to help with the temperature and noise issues I mentioned.

I think this will resolve the concerns I raised, and I can continue focusing on my work as usual.

Thanks again for your time.

Best regards,
Adam""" 