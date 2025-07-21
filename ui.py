"""
Main UI Components

This module contains the main UI components including mode selection
and developer interface components.
"""

import streamlit as st
import os
from config import (
    LEVEL_TO_SCENARIO_MAPPING,
    MAX_AVAILABLE_LEVEL,
    EMAIL_MAX_CHARS,
    DEFAULT_SCENARIO,
    MODELS,
    USER_MODE_USE_RUBRIC,
    DEFAULT_USE_RUBRIC,
    EVALUATION_PROMPT_PATH
)
from utils import (
    load_scenarios,
    check_api_keys,
    format_scenario_content,
    process_evaluation_text,
    extract_goal_achievement_score,
    initialize_session_state,
    load_recipient_prompt,
    load_file_content
)
from ui_user_refactored import show_user_interface_with_levels
from evaluation import process_email_evaluation_developer_mode
from models import EmailGenerator


def show_mode_selection():
    """Show the mode selection page"""
    st.markdown("""
    <style>
    .mode-header {
        text-align: center;
        padding: 2rem 0;
    }
    .mode-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 2rem;
        margin: 1rem 0;
        border-left: 5px solid #007bff;
        height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .user-card {
        border-left-color: #28a745 !important;
    }
    .dev-card {
        border-left-color: #ffc107 !important;
    }
    </style>
    
    <div class="mode-header">
    
    # 📧 The Ghostwriter
    </div>
    """, unsafe_allow_html=True)
    
    # Create two columns for the mode selection
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="mode-card user-card">
        <h3>👤 User Mode</h3>
        <p>Play as a user. Craft emails for increasingly difficult scenarios!</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Play Now", type="primary", use_container_width=True):
            st.session_state.app_mode = "user"
            st.session_state.use_rubric = USER_MODE_USE_RUBRIC  # Set non-rubric mode for user
            st.session_state.current_page = "game"
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="mode-card dev-card">
        <h3>🛠️ Developer Mode</h3>
        <p>If you want to customize the scenario and prompts to models.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⚙️ Run As Developer", type="secondary", use_container_width=True):
            st.session_state.app_mode = "developer"
            st.session_state.use_rubric = DEFAULT_USE_RUBRIC  # Set rubric mode for developer
            st.session_state.current_page = "game"
            st.rerun()
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6c757d;">
    <small>
    💡 <strong>Tip:</strong> You can switch modes anytime by refreshing the page.
    </small>
    </div>
    """, unsafe_allow_html=True)


def show_developer_interface(available_scenarios, api_keys_available):
    """Show the full developer interface with all controls"""
    # Sidebar for configuration
    with st.sidebar:
        st.subheader("Configuration")
        
        # API Key status
        if api_keys_available:
            st.success("✅ API keys loaded from environment")
        else:
            st.error("❌ Missing API keys")
            st.info("Set OPENAI_API_KEY_CLAB environment variable")
        
        # Model selection
        model = st.selectbox(
            "Evaluator Model",
            ["gpt-4o"],
            help="Select the model to evaluate emails"
        )
        
        # Rubric toggle
        st.session_state.use_rubric = st.checkbox(
            "📏 Use Evaluation Rubric",
            value=st.session_state.get('use_rubric', True),
            help="Toggle whether to generate and display evaluation rubrics"
        )
        
        st.markdown("---")
        st.markdown("**Scenarios**")
        if available_scenarios:
            st.success(f"Loaded {len(available_scenarios)} scenario(s)")
        else:
            st.warning("No scenarios found in manual folder")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Scenario section
        st.subheader("📋 Scenario")
        
        # Scenario selection dropdown
        if available_scenarios:
            scenario_options = ["Select a scenario..."] + list(available_scenarios.keys())
            selected_scenario_name = st.selectbox(
                "Choose a scenario",
                scenario_options,
                index=0,
                help="Select from available scenarios in the manual folder"
            )
            
            if selected_scenario_name != "Select a scenario...":
                scenario_data = available_scenarios[selected_scenario_name]
                scenario_content = scenario_data['content']
                st.session_state.selected_scenario = scenario_content
                st.session_state.selected_scenario_file = scenario_data['filename']
            else:
                scenario_content = st.session_state.get('selected_scenario', "")
        else:
            # Fallback to default scenario if no scenarios found
            scenario_content = DEFAULT_SCENARIO
            st.warning("No scenarios found in manual folder. Using default scenario.")
        
        scenario = st.text_area(
            "Current Scenario",
            value=scenario_content,
            height=350,
            max_chars=5000,  # Prevent excessively long scenarios
            help="The scenario for which participants will write emails"
        )
        
        # Email input section
        col_email_header, col_ai_button = st.columns([3, 1])
        with col_email_header:
            st.subheader("✍️ Your Email")
        with col_ai_button:
            if st.button("🤖 Generate email with AI", help="Generate an email using AI for the current scenario"):
                if api_keys_available and scenario.strip():
                    with st.spinner("🤖 AI is writing an email..."):
                        try:
                            generator = EmailGenerator()
                            generated_email = generator.generate_email(scenario, model)
                            if generated_email:
                                # Set the generated email directly in the widget state
                                st.session_state["email_input"] = generated_email
                                st.success("✅ Email generated!")
                                st.rerun()
                            else:
                                st.error("Failed to generate email")
                        except Exception as e:
                            st.error(f"Error initializing generator: {str(e)}")
                elif not api_keys_available:
                    st.error("API keys not available")
                else:
                    st.error("Please select a scenario first")
        
        # Email text area - uses key to maintain state automatically
        email_content = st.text_area(
            "Write your email here",
            height=400,
            max_chars=3000,  # Prevent excessively long emails
            placeholder="Type your email response to the scenario above, or use the AI generation button...",
            help="Write the best email you can for the given scenario, or generate one with AI",
            key="email_input"
        )
    
    with col2:
        # Developer mode section
        st.subheader("🛠️ Developer Mode")
        
        # Recipient persona section (collapsible)
        with st.expander("📨 Recipient Persona", expanded=False):
            st.markdown("*Define who will reply to the user's email*")
            
            # Load recipient prompt based on selected scenario
            if st.session_state.get('selected_scenario_file'):
                default_recipient_prompt = load_recipient_prompt(st.session_state.selected_scenario_file)
            else:
                default_recipient_prompt = "You are the recipient of an email. Please respond naturally and appropriately to the email you receive."
            
            recipient_prompt = st.text_area(
                "Recipient Persona Instructions",
                value=default_recipient_prompt,
                height=300,
                help="Instructions for the AI to roleplay as the email recipient",
                key="recipient_prompt"
            )
        
        # Evaluator prompt section (collapsible)
        with st.expander("📝 Custom Evaluation Template", expanded=False):
            st.markdown("*Provide your own evaluation prompt template*")
            st.markdown("**Available placeholders:** `{scenario}` `{email}` `{response}` `{rubric}` (if rubrics enabled)")
            
            try:
                default_prompt = load_file_content(EVALUATION_PROMPT_PATH, "")
                if not default_prompt:
                    default_prompt = ""
            except Exception as e:
                default_prompt = ""
            
            evaluator_prompt = st.text_area(
                "Custom Evaluation Template",
                value=default_prompt,
                height=300,
                placeholder="Enter your custom evaluation prompt template here. Use {email}, {response}, {scenario}, and optionally {rubric} placeholders. Leave blank to use default evaluation.",
                help="Custom prompt template for email evaluation. Use placeholders like {email}, {response}, etc. If blank, will use default evaluation method.",
                key="evaluator_prompt"
            )
    
    # Submit button for developer mode
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
            # Process email evaluation using custom settings from developer mode
            scenario = st.session_state.get('selected_scenario', DEFAULT_SCENARIO)
            process_email_evaluation_developer_mode(scenario, email_content, model)





def show_game_page():
    """Show the main game interface"""
    
    # Add mode indicator and back button
    mode_col, back_col = st.columns([4, 1])
    with mode_col:
        mode_display = "👤 User" if st.session_state.app_mode == "user" else "🛠️ Developer"
        st.markdown(f"**Current Mode:** {mode_display}")
    with back_col:
        if st.button("Change Mode", help="Go back to mode selection"):
            st.session_state.current_page = "mode_selection"
            st.session_state.app_mode = None
            st.rerun()
    
    st.markdown("""
    <style>
    .compact-header h2 {
        margin-top: 0rem !important;
        margin-bottom: 0.5rem !important;
        padding-top: 0rem !important;
    }
    </style>
    <div class="compact-header">
    
    ## 📧 The Ghostwriter
    
    </div>
    """, unsafe_allow_html=True)
    # st.markdown("**Write emails for various scenarios and AI-generated responses!**")
    st.markdown("**Help a client achieve their communication goals**")
    
    # Load available scenarios
    available_scenarios = load_scenarios()
    
    # Check API key availability
    api_keys_available = check_api_keys()
    
    # Render UI based on mode
    if st.session_state.app_mode == "developer":
        show_developer_interface(available_scenarios, api_keys_available)
    else:  # user mode
        show_user_interface_with_levels(available_scenarios, api_keys_available)


def main_interface():
    """Main interface controller"""
    
    # Initialize session state
    initialize_session_state()
    
    # Automatically update URL with session info if session exists
    _ensure_session_in_url()
    
    # Handle URL parameters for developer level navigation
    _handle_url_parameters()
    
    # Simple page navigation based on current_page
    if st.session_state.get('current_page') == "game":
        show_game_page()
    elif st.session_state.get('current_page') == "mode_selection":
        show_mode_selection()
    else:
        # Default to mode selection page
        st.session_state.current_page = "mode_selection"
        show_mode_selection()


def _ensure_session_in_url():
    """Automatically add session ID to URL if session exists but URL doesn't have it"""
    try:
        # Check if there's an active session
        session_id = st.session_state.get('game_session_id')
        
        if session_id:
            from session_manager import session_exists, load_session_data
            
            # Verify session still exists in database
            if session_exists(session_id):
                # Sync session state with database to ensure consistency
                _sync_session_state_with_database(session_id)
                
                query_params = st.query_params
                
                # Check if URL is missing session info
                url_session = query_params.get('session')
                
                # Auto-update URL if it's missing session (but keep gang_level hidden by default)
                should_update = False
                
                if not url_session:
                    should_update = True
                elif url_session != session_id:
                    should_update = True
                
                if should_update:
                    # Update URL to include current session only (keep gang_level hidden)
                    st.query_params.update({"session": session_id})
            else:
                # Session doesn't exist in DB, clear it from session state
                if 'game_session_id' in st.session_state:
                    del st.session_state.game_session_id
    except Exception as e:
        # URL updates are not critical, continue silently
        pass


def _sync_session_state_with_database(session_id: str):
    """Sync session state with database to ensure consistency - never lose progress"""
    try:
        from session_manager import load_session_data, save_session_progress
        
        # Get current session state
        current_completed = st.session_state.get('completed_levels', set())
        current_level = st.session_state.get('current_level', 0)
        
        # Load from database
        session_data = load_session_data(session_id)
        db_completed = set()
        if session_data:
            db_completed = session_data.get('completed_levels', set())
        
        # Always merge ALL sources (never lose any progress from anywhere)
        merged_completed = current_completed | db_completed
        
        # Always update session state with the complete merged progress
        st.session_state.completed_levels = merged_completed
        
        # **FIX: Also sync level_emails and level_evaluations from database**
        if session_data:
            # Load email content for all levels from database
            db_level_emails = session_data.get('level_emails', {})
            if db_level_emails:
                # Merge with existing session state emails (preserve any in-session changes)
                current_emails = st.session_state.get('level_emails', {})
                # Update session state with database emails, but don't overwrite current session emails
                for level, email_content in db_level_emails.items():
                    if level not in current_emails:
                        current_emails[level] = email_content
                st.session_state.level_emails = current_emails
            
            # Load evaluation results from database
            db_level_evaluations = session_data.get('level_evaluations', {})
            if db_level_evaluations:
                current_evaluations = st.session_state.get('level_evaluations', {})
                # Update session state with database evaluations
                for level, evaluation_data in db_level_evaluations.items():
                    if level not in current_evaluations:
                        current_evaluations[level] = evaluation_data
                st.session_state.level_evaluations = current_evaluations
        
        # Always save back to database to ensure both are in sync
        save_session_progress(session_id, current_level, merged_completed)
            
        # Sync other session data if needed
        if 'current_level' not in st.session_state and session_data:
            st.session_state.current_level = session_data.get('current_level', 0)
                    
    except Exception as e:
        # Sync failures are not critical, but log for debugging
        import logging
        logging.error(f"Session sync failed: {e}")
        pass


def _handle_url_parameters():
    """Handle URL parameters for developer navigation"""
    try:
        # Get URL parameters
        query_params = st.query_params
        
        # **FIX 1: Clear parameters on actual page refresh**
        # Check if this is an actual browser refresh (no session state exists yet)
        if 'gang_level' in query_params and not hasattr(st.session_state, 'initialized'):
            # This is a fresh page load with parameters - clear them after first load
            # We'll clear them at the end of processing, not here
            is_fresh_page_load = True
        else:
            is_fresh_page_load = False
        
        # Check for gang_level parameter
        if 'gang_level' in query_params:
            target_level_str = query_params['gang_level']
            
            # **FIX 2: Always trigger session sync for URL navigation**
            # Don't skip processing based on "processed params" - always ensure session data is loaded
            # The old logic was preventing data loading when jumping back to the same level
            
            # Auto-include session ID if not provided but available in session state
            if 'session' not in query_params:
                # Check if there's an active session we can use
                active_session_id = st.session_state.get('game_session_id')
                if active_session_id:
                    from session_manager import session_exists
                    if session_exists(active_session_id):
                        # Automatically use the active session
                        st.info(f"🔗 **Auto-using active session:** {active_session_id[:8]}... (you can override with `?session=OTHER_ID&gang_level=X`)")
                        # Add session to query params for processing
                        query_params = dict(query_params)  # Convert to mutable dict
                        query_params['session'] = active_session_id
                    else:
                        # Session in state doesn't exist in DB, clear it
                        if 'game_session_id' in st.session_state:
                            del st.session_state.game_session_id
                        active_session_id = None
                
                if not active_session_id:
                    st.error("❌ **No Active Session:** Please create or select a session first!")
                    st.info("💡 **Tip:** Once you have a session, you can use `?gang_level=X` for quick navigation!")
                    return
            
            try:
                target_level = float(target_level_str)
                
                # Import here to avoid circular imports
                from config import LEVEL_TO_SCENARIO_MAPPING
                from session_manager import unlock_levels_up_to, session_exists, create_new_session
                
                # Validate level exists in mapping
                if target_level in LEVEL_TO_SCENARIO_MAPPING:
                    # Handle session ID from URL or use existing session
                    session_id = None
                    
                    # First, check if session ID is provided in URL
                    if 'session' in query_params:
                        url_session_id = query_params['session']
                        if session_exists(url_session_id):
                            session_id = url_session_id
                            st.session_state.game_session_id = session_id
                            st.info(f"🔗 **Using session from URL:** {session_id[:8]}...")
                        else:
                            st.error(f"❌ **Session not found:** {url_session_id[:8]}... does not exist")
                            return
                    
                    # Second, check if there's already an active session
                    elif st.session_state.get('game_session_id'):
                        existing_session_id = st.session_state.get('game_session_id')
                        if session_exists(existing_session_id):
                            session_id = existing_session_id
                            st.info(f"🔄 **Using existing session:** {session_id[:8]}...")
                        else:
                            # Session in state doesn't exist in DB, clear it
                            del st.session_state.game_session_id
                    
                    # Third, create a new session if none exists
                    if not session_id:
                        session_id = create_new_session()
                        st.session_state.game_session_id = session_id
                        st.info(f"🆕 **Created new session:** {session_id[:8]}...")
                    
                    # Allow URL navigation in both user and developer modes
                    current_mode = st.session_state.get('app_mode')
                    
                    # Set mode if not already set
                    if not current_mode:
                        st.session_state.app_mode = "user"
                        st.session_state.use_rubric = False  # User mode default
                        current_mode = "user"
                        st.info("👤 **Auto-switched to User Mode** for URL navigation")
                    
                    # **FIX 2: Always unlock levels and sync session data**
                    # This ensures data is loaded even when jumping to the same level multiple times
                    success = unlock_levels_up_to(session_id, target_level)
                    
                    if success:
                        # Force session sync to load email content and evaluations
                        _sync_session_state_with_database(session_id)
                        
                        # Import needed functions at the top
                        from session_manager import load_session_data, save_session_progress
                        
                        # STEP 1: Gather ALL sources of progress (never lose anything)
                        # Get current session state progress
                        session_state_completed = st.session_state.get('completed_levels', set())
                        
                        # Force save current session state to database first
                        current_level = st.session_state.get('current_level', 0)
                        if session_state_completed:
                            save_session_progress(session_id, current_level, session_state_completed)
                        
                        # Load from database after saving
                        existing_session_data = load_session_data(session_id)
                        database_completed = set()
                        if existing_session_data:
                            database_completed = existing_session_data.get('completed_levels', set())
                        
                        # Get prerequisites needed for target level
                        prerequisite_levels = set()
                        for level in LEVEL_TO_SCENARIO_MAPPING.keys():
                            if level < target_level:  
                                prerequisite_levels.add(level)
                        
                        # STEP 2: Merge ALL progress sources (union of all sets)
                        all_completed_levels = session_state_completed | database_completed | prerequisite_levels
                        
                        # STEP 3: Update both session state and database with complete progress
                        st.session_state.completed_levels = all_completed_levels
                        st.session_state.current_level = target_level
                        st.session_state.current_page = "game"
                        
                        # Force save the complete merged progress back to database
                        save_session_progress(session_id, target_level, all_completed_levels)
                        
                        # STEP 4: Show detailed progress information
                        mode_display = "Developer" if current_mode == 'developer' else "User"
                        
                        # Calculate what was preserved vs what was added
                        user_progress = session_state_completed | database_completed  # All user progress
                        new_prerequisites = prerequisite_levels - user_progress  # Only new unlocks
                        
                        if user_progress:
                            st.success(f"🚀 **{mode_display} Navigation:** Jumped to Level {target_level}")
                            st.info(f"✅ **Your progress preserved:** {sorted(user_progress)} | **Prerequisites added:** {sorted(new_prerequisites)}")
                        else:
                            st.success(f"🚀 **{mode_display} Navigation:** Unlocked prerequisites and jumped to Level {target_level}")
                            st.info(f"📋 **All levels unlocked:** {sorted(all_completed_levels)}")
                        
                        # **FIX 1: Clear gang_level after processing to prevent refresh issues**
                        # Always clear gang_level parameter after successful processing
                        st.query_params.clear()
                        if session_id:
                            st.query_params.update({"session": session_id})
                        
                        # Mark this processing as completed but don't store processed_url_params
                        # since we always want to allow re-processing for the same level
                        st.session_state.url_navigation_processed = True
                        
                    else:
                        st.error(f"❌ Failed to unlock prerequisite levels for Level {target_level}")
                        
                else:
                    st.error(f"❌ **Invalid Level:** {target_level} not found in available levels: {list(LEVEL_TO_SCENARIO_MAPPING.keys())}")
                    
            except ValueError:
                st.error(f"❌ **Invalid Level Parameter:** '{target_level_str}' is not a valid number")
                
    except Exception as e:
        # Don't show error for normal usage without URL parameters
        if 'gang_level' in st.query_params:
            st.error(f"❌ **URL Parameter Error:** {str(e)}") 