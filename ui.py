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
from ui_user import show_user_interface_with_levels
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
    
    # 📧 Email.io: Can You Write Better Emails than AI? 
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
        mode_display = "👤 User Mode" if st.session_state.app_mode == "user" else "🛠️ Developer Mode"
        st.markdown(f"**Current Mode:** {mode_display}")
    with back_col:
        if st.button("↩️ Change Mode", help="Go back to mode selection"):
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
    
    ## 📧 Email.io: Can You Write Better Emails than AI?
    
    </div>
    """, unsafe_allow_html=True)
    st.markdown("**Write emails for various scenarios and AI-generated responses!**")
    
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
    
    # Simple page navigation based on current_page
    if st.session_state.get('current_page') == "game":
        show_game_page()
    elif st.session_state.get('current_page') == "mode_selection":
        show_mode_selection()
    else:
        # Default to mode selection page
        st.session_state.current_page = "mode_selection"
        show_mode_selection() 