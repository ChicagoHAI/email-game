"""
Email Evaluation Processing

This module handles the email evaluation workflow, including
AI generation, evaluation, and result processing.
"""

import streamlit as st
from datetime import datetime
from config import MAX_AVAILABLE_LEVEL
from models import RubricGenerator, EmailRecipient, EmailEvaluator, EmailGenerator
from utils import load_recipient_prompt, extract_goal_achievement_score, process_evaluation_text


def process_email_evaluation(scenario, email_content, model):
    """Process email evaluation for developer mode (simple evaluation)"""
    
    # Initialize AI services
    email_generator = EmailGenerator()
    email_evaluator = EmailEvaluator()
    email_recipient = EmailRecipient()
    rubric_generator = RubricGenerator()
    
    with st.spinner("🤖 Processing your email..."):
        try:
            # Step 1: Load or generate rubric
            with st.status("Loading evaluation rubric...", expanded=False) as status:
                scenario_filename = st.session_state.get("selected_scenario_file", "default_scenario.txt")
                rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
                status.update(label="✅ Rubric ready!", state="complete")
            
            # Step 2: Generate recipient reply
            with st.status("Generating recipient response...", expanded=False) as status:
                # Load recipient prompt based on selected scenario
                if st.session_state.get("selected_scenario_file"):
                    recipient_prompt = load_recipient_prompt(st.session_state.selected_scenario_file)
                else:
                    from config import DEFAULT_RECIPIENT_PROMPT
                    recipient_prompt = DEFAULT_RECIPIENT_PROMPT
                
                recipient_reply = email_recipient.generate_reply(recipient_prompt, email_content, model)
                status.update(label="✅ Recipient reply generated!", state="complete")
            
            # Step 3: Evaluate email
            with st.status("Evaluating your email...", expanded=False) as status:
                evaluation = email_evaluator.evaluate_email(scenario, email_content, rubric, recipient_reply, model)
                status.update(label="✅ Evaluation complete!", state="complete")
            
            # Display results
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
            
            # Show rubric (collapsible)
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


def process_email_evaluation_with_history(scenario, email_content, model, level):
    """Process email evaluation with history management for user mode"""
    
    # Initialize AI services
    email_generator = EmailGenerator()
    email_evaluator = EmailEvaluator()
    email_recipient = EmailRecipient()
    rubric_generator = RubricGenerator()
    
    with st.spinner("🤖 Processing your email..."):
        try:
            # Step 1: Load or generate rubric
            with st.status("Loading evaluation rubric...", expanded=False) as status:
                scenario_filename = st.session_state.get("selected_scenario_file", "default_scenario.txt")
                rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
                status.update(label="✅ Rubric ready!", state="complete")
            
            # Step 2: Generate recipient reply
            with st.status("Generating recipient response...", expanded=False) as status:
                # Load recipient prompt based on selected scenario file
                if st.session_state.get("selected_scenario_file"):
                    recipient_prompt = load_recipient_prompt(st.session_state.selected_scenario_file)
                else:
                    from config import DEFAULT_RECIPIENT_PROMPT
                    recipient_prompt = DEFAULT_RECIPIENT_PROMPT
                
                recipient_reply = email_recipient.generate_reply(recipient_prompt, email_content, model)
                status.update(label="✅ Recipient reply generated!", state="complete")
            
            # Step 3: Evaluate email
            with st.status("Evaluating your email...", expanded=False) as status:
                evaluation = email_evaluator.evaluate_email(scenario, email_content, rubric, recipient_reply, model)
                status.update(label="✅ Evaluation complete!", state="complete")
            
            # Extract goal achievement
            goal_achieved = extract_goal_achievement_score(evaluation)
            
            # Store email content by level
            st.session_state.level_emails[level] = email_content
            
            # Store evaluation results
            st.session_state.level_evaluations[level] = {
                "scenario": scenario,
                "email": email_content,
                "recipient_reply": recipient_reply,
                "rubric": rubric,
                "evaluation": evaluation,
                "goal_achieved": goal_achieved
            }
            
            # Update completed levels if successful
            if goal_achieved and level not in st.session_state.completed_levels:
                st.session_state.completed_levels.add(level)
            
            # Add evaluation page to history
            evaluation_page = {"type": "evaluation", "level": level}
            
            # Check if we're retrying a level (if the last page in history is evaluation for the same level)
            if (st.session_state.page_history and 
                st.session_state.page_history[-1].get("type") == "evaluation" and 
                st.session_state.page_history[-1].get("level") == level):
                # We're retrying - replace the last evaluation page
                st.session_state.page_history[-1] = evaluation_page
            else:
                # Normal flow - add new evaluation page
                st.session_state.page_history.append(evaluation_page)
            
            # Navigate to evaluation page
            st.session_state.current_history_index = len(st.session_state.page_history) - 1
            
            # Success message
            st.success("🎉 Evaluation Complete! Showing results...")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error during evaluation: {str(e)}")
            st.error("Please check your API keys and try again.")


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


def process_email_evaluation_user_mode(scenario, email_content, model):
    """Process email evaluation using default settings for user mode"""
    # Show loading screen with multiple steps
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # Step 1: Load or generate rubric
        progress_text.text("🔄 Loading evaluation rubric...")
        progress_bar.progress(0.25)
        
        rubric_generator = RubricGenerator()
        scenario_filename = st.session_state.get("selected_scenario_file", "")
        
        if scenario_filename:
            rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
        else:
            # Fallback to direct generation if no filename available
            rubric = rubric_generator.generate_rubric(scenario, model)
        
        if not rubric:
            st.error("Failed to generate rubric")
            return
        
        # Step 2: Generate recipient reply (using default recipient prompt for user version)
        progress_text.text("📨 Awaiting response from recipient...")
        progress_bar.progress(0.5)
        
        # Load default recipient prompt based on selected scenario
        if st.session_state.get("selected_scenario_file"):
            default_recipient_prompt = load_recipient_prompt(st.session_state.selected_scenario_file)
        else:
            from .config import DEFAULT_RECIPIENT_PROMPT
            default_recipient_prompt = DEFAULT_RECIPIENT_PROMPT
        
        recipient = EmailRecipient()
        recipient_reply = recipient.generate_reply(
            default_recipient_prompt, email_content, model
        )
        
        if not recipient_reply:
            st.error("Failed to generate recipient reply")
            return
        
        # Step 3: Evaluate the email using the generated rubric (using default evaluator prompt)
        progress_text.text("📊 Evaluating your email...")
        progress_bar.progress(0.75)
        
        evaluator = EmailEvaluator()
        evaluation_result = evaluator.evaluate_email(
            scenario, email_content, rubric, recipient_reply, model
        )
        
        if not evaluation_result:
            st.error("Failed to evaluate email")
            return
        
        # Step 4: Complete
        progress_text.text("✅ Evaluation complete!")
        progress_bar.progress(1.0)
        
        # Store all data for results page
        st.session_state.evaluation_result = {
            "scenario": scenario,
            "email": email_content,
            "rubric": rubric,
            "recipient_reply": recipient_reply,
            "evaluation": evaluation_result,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Store the email for this level
        if 'current_level' in st.session_state:
            if 'level_emails' not in st.session_state:
                st.session_state.level_emails = {}
            st.session_state.level_emails[st.session_state.current_level] = email_content
        
        # Check if user successfully achieved the goal before marking level complete
        goal_success = extract_goal_achievement_score(evaluation_result)
        
        # Handle level progression based on success (only for user mode)
        if 'current_level' in st.session_state:
            if 'completed_levels' not in st.session_state:
                st.session_state.completed_levels = set()
                
            if goal_success:
                # Mark current level as completed
                st.session_state.completed_levels.add(st.session_state.current_level)
                
                # Store the level they just completed for navigation
                st.session_state.evaluation_result["completed_level"] = st.session_state.current_level
                
                # Auto-advance to next level if available
                if st.session_state.current_level < MAX_AVAILABLE_LEVEL:
                    st.session_state.current_level += 1
            else:
                # Store the current level for "try again" scenario
                st.session_state.evaluation_result["failed_level"] = st.session_state.current_level
            
        # Store goal achievement result for display
        st.session_state.evaluation_result["goal_achieved"] = goal_success
        
        # Switch to results page
        st.session_state.current_page = "results"
        st.rerun()
        
    except Exception as e:
        st.error(f"Error during processing: {str(e)}")


def process_email_evaluation_developer_mode(scenario, email_content, model):
    """Process email evaluation using custom settings from developer mode"""
    # Show loading screen with multiple steps
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # Step 1: Load or generate rubric
        progress_text.text("🔄 Loading evaluation rubric...")
        progress_bar.progress(0.25)
        
        rubric_generator = RubricGenerator()
        scenario_filename = st.session_state.get("selected_scenario_file", "")
        
        if scenario_filename:
            rubric = rubric_generator.get_or_generate_rubric(scenario, scenario_filename, model)
        else:
            # Fallback to direct generation if no filename available
            rubric = rubric_generator.generate_rubric(scenario, model)
        
        if not rubric:
            st.error("Failed to generate rubric")
            return
        
        # Step 2: Generate recipient reply
        progress_text.text("📨 Awaiting response from recipient...")
        progress_bar.progress(0.5)
        
        recipient_prompt_value = st.session_state.get("recipient_prompt", "")
        recipient = EmailRecipient()
        recipient_reply = recipient.generate_reply(
            recipient_prompt_value, email_content, model
        )
        
        if not recipient_reply:
            st.error("Failed to generate recipient reply")
            return
        
        # Step 3: Evaluate the email using the generated rubric
        progress_text.text("📊 Evaluating your email...")
        progress_bar.progress(0.75)
        
        evaluator = EmailEvaluator()
        evaluation_result = evaluator.evaluate_email(
            scenario, email_content, rubric, recipient_reply, model
        )
        
        if not evaluation_result:
            st.error("Failed to evaluate email")
            return
        
        # Step 4: Complete
        progress_text.text("✅ Evaluation complete!")
        progress_bar.progress(1.0)
        
        # Store all data for results page
        st.session_state.evaluation_result = {
            "scenario": scenario,
            "email": email_content,
            "rubric": rubric,
            "recipient_reply": recipient_reply,
            "evaluation": evaluation_result,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Switch to results page
        st.session_state.current_page = "results"
        st.rerun()
        
    except Exception as e:
        st.error(f"Error during processing: {str(e)}") 