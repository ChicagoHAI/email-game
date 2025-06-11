import streamlit as st
import openai
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import os
import glob

# Initialize session state
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = []
if 'current_score' not in st.session_state:
    st.session_state.current_score = None
if 'show_breakdown' not in st.session_state:
    st.session_state.show_breakdown = False
if 'evaluating' not in st.session_state:
    st.session_state.evaluating = False
if 'selected_scenario' not in st.session_state:
    st.session_state.selected_scenario = None
if 'generated_email' not in st.session_state:
    st.session_state.generated_email = ""
if 'current_page' not in st.session_state:
    st.session_state.current_page = "game"
if 'evaluation_result' not in st.session_state:
    st.session_state.evaluation_result = None

class EmailGenerator:
    def __init__(self):
        # Try specific generator key first, fall back to general key
        api_key = os.getenv("OPENAI_API_KEY_CLAB")
        if not api_key:
            raise ValueError("No API key found. Set OPENAI_API_KEY_GENERATOR or OPENAI_API_KEY_CLAB environment variable.")
        self.client = openai.OpenAI(api_key=api_key)
    
    def generate_email(self, scenario: str, model: str = "gpt-4o") -> str:
        """Generate an email response for the given scenario"""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are writing an email in response to the given scenario. Write only the email content, no additional commentary."},
                    {"role": "user", "content": scenario}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating email: {str(e)}")
            return None

class EmailEvaluator:
    def __init__(self):
        # Try specific evaluator key first, fall back to general key
        api_key = os.getenv("OPENAI_API_KEY_CLAB")
        if not api_key:
            raise ValueError("No API key found. Please set the environment variable.")
        self.client = openai.OpenAI(api_key=api_key)
    
    def evaluate_email(self, scenario: str, email: str, 
                      prompt: str, model: str = "gpt-4o") -> str:
        """Evaluate an email using the specified model and prompt"""
        
        evaluation_prompt = f"""
        {prompt}
        
        Scenario: {scenario}
        
        Email to evaluate: {email}
        
        Please provide your detailed evaluation and feedback:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert email "
                     "evaluator. Provide detailed, constructive feedback."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error evaluating email: {str(e)}")
            return None

def load_scenarios_from_folder(folder_path: str = "../../outputs/scenarios/manual") -> Dict[str, str]:
    """Load all scenario files from the specified folder"""
    scenarios = {}
    
    # Adjust path relative to current working directory
    if not os.path.isabs(folder_path):
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(script_dir, folder_path)
    
    if os.path.exists(folder_path):
        scenario_files = glob.glob(os.path.join(folder_path, "scenario_*.txt"))
        
        for file_path in sorted(scenario_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    
                # Extract scenario number from filename
                filename = os.path.basename(file_path)
                scenario_num = filename.replace('scenario_', '').replace('.txt', '')
                
                # Create display name
                display_name = f"Scenario {scenario_num}"
                
                # Try to extract a summary from the first line or paragraph
                first_line = content.split('\n')[0][:100]
                if len(first_line) == 100:
                    first_line += "..."
                
                display_name += f" - {first_line}"
                
                scenarios[display_name] = content
                
            except Exception as e:
                st.error(f"Error loading scenario from {file_path}: {str(e)}")
    
    return scenarios

def show_game_page():
    """Show the main game interface"""
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
    st.markdown("**Write emails for various scenarios and get AI feedback!**")
    
    # Load available scenarios
    available_scenarios = load_scenarios_from_folder()
    
    # Check API key availability
    try:
        api_keys_available = bool(os.getenv("OPENAI_API_KEY_CLAB"))
    except:
        api_keys_available = False
    
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
                scenario_content = available_scenarios[selected_scenario_name]
                st.session_state.selected_scenario = scenario_content
            else:
                scenario_content = st.session_state.selected_scenario or ""
        else:
            # Fallback to default scenario if no scenarios found
            scenario_content = """You are coordinating a weekend trip to a national park with 5 friends. You need to organize transportation, accommodation, and activities. Some friends prefer camping while others want a hotel. The trip is in 3 weeks and you need everyone to confirm their participation and preferences by Friday."""
            st.warning("No scenarios found in manual folder. Using default scenario.")
        
        scenario = st.text_area(
            "Current Scenario",
            value=scenario_content,
            height=350,
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
                                st.session_state.generated_email = generated_email
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
        
        # Use generated email if available, otherwise use empty string
        email_value = st.session_state.generated_email if st.session_state.generated_email else ""
        
        email_content = st.text_area(
            "Write your email here",
            value=email_value,
            height=400,
            placeholder="Type your email response to the scenario above, or use the AI generation button...",
            help="Write the best email you can for the given scenario, or generate one with AI",
            key="email_input"
        )
        
        # Clear AI state if user manually edits the email (different from generated)
        if email_content != st.session_state.generated_email and st.session_state.generated_email:
            if email_content.strip():  # Only clear if there's actual content
                st.session_state.generated_email = ""
    
    with col2:
        # Developer mode - Evaluator prompt
        st.subheader("🛠️ Grading Instructions")
        st.markdown("*Tell the AI evaluator how to assess the email*")
        
        default_prompt = """Please evaluate this email based on the following criteria:
        
        1. **Clarity**: How clear and easy to understand is the message?
        2. **Appropriateness**: How appropriate is the tone and content for the scenario?
        3. **Effectiveness**: How likely is this email to achieve its intended purpose?
        4. **Grammar**: How good is the grammar, spelling, and writing quality?
        
        Provide detailed feedback and suggestions for improvement."""
        
        evaluator_prompt = st.text_area(
            "Grading Instructions",
            value=default_prompt,
            height=300,
            help="Instructions for the AI evaluator on how to assess emails"
        )
    
    # Submit button
    st.markdown("---")
    if st.button(
        "📝 Get AI Evaluation",
        type="primary",
        disabled=not api_keys_available or not email_content.strip(),
        help="Submit your email for AI evaluation"
    ):
        if not email_content.strip():
            st.error("Please write an email before submitting!")
        elif not api_keys_available:
            st.error("API keys not available")
        else:
            # Show loading screen
            with st.spinner("🤖 AI is evaluating your email..."):
                try:
                    evaluator = EmailEvaluator()
                    result = evaluator.evaluate_email(
                        scenario, email_content, evaluator_prompt, model
                    )
                    
                    if result:
                        # Store evaluation data for results page
                        st.session_state.evaluation_result = {
                            "scenario": scenario,
                            "email": email_content,
                            "evaluation": result,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Switch to results page
                        st.session_state.current_page = "results"
                        st.rerun()
                    else:
                        st.error("Failed to evaluate email")
                except Exception as e:
                    st.error(f"Error during evaluation: {str(e)}")

def show_results_page():
    """Show the evaluation results"""
    st.markdown("""
    <style>
    .compact-header h2 {
        margin-top: 0rem !important;
        margin-bottom: 0.5rem !important;
        padding-top: 0rem !important;
    }
    </style>
    <div class="compact-header">
    
    ## 📊 Email Evaluation Results
    
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.evaluation_result:
        result = st.session_state.evaluation_result
        
        # Back button
        if st.button("← Back to Game", type="secondary"):
            st.session_state.current_page = "game"
            st.rerun()
        
        st.markdown("---")
        
        # Show the scenario
        st.subheader("📋 Scenario")
        st.text_area("", value=result["scenario"], height=200, disabled=True)
        
        # Show the email
        st.subheader("✍️ Your Email")
        st.text_area("", value=result["email"], height=300, disabled=True)
        
        # Show the evaluation
        st.subheader("🤖 AI Evaluation")
        st.markdown("""
        <style>
        .stMarkdown p {
            font-size: 1.1rem !important;
            line-height: 1.6 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        st.markdown(result["evaluation"])
        
        st.markdown("---")
        st.caption(f"Evaluated on {result['timestamp']}")
        
        # Back button at bottom too
        if st.button("← Back to Game", type="secondary", key="back_bottom"):
            st.session_state.current_page = "game"
            st.rerun()
    
    else:
        st.error("No evaluation results found.")
        if st.button("← Back to Game"):
            st.session_state.current_page = "game"
            st.rerun()

def main():
    st.set_page_config(
        page_title="Email.io: Can You Write Better Emails than AI?",
        page_icon="📧",
        layout="wide"
    )
    
    # Simple page navigation
    if st.session_state.current_page == "game":
        show_game_page()
    elif st.session_state.current_page == "results":
        show_results_page()
    else:
        # Default to game page
        st.session_state.current_page = "game"
        show_game_page()

if __name__ == "__main__":
    main()