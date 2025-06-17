import streamlit as st
import openai
from datetime import datetime
from typing import Dict
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
if 'recipient_reply' not in st.session_state:
    st.session_state.recipient_reply = None
if 'selected_scenario_file' not in st.session_state:
    st.session_state.selected_scenario_file = None
if 'cached_rubrics' not in st.session_state:
    st.session_state.cached_rubrics = {}

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
                      rubric: str, recipient_reply: str, model: str = "gpt-4o") -> str:
        """Evaluate an email using the specified model, rubric, and recipient response"""
        
        # Load evaluation prompt template
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            eval_prompt_path = os.path.join(script_dir, "prompts", "evaluation", "default.txt")
            with open(eval_prompt_path, "r") as f:
                evaluation_template = f.read()
        except:
            # Fallback template if file not found
            evaluation_template = """
            Please evaluate the email based on the rubric provided:
            
            Scenario: {scenario}
            Rubric: {rubric}
            Email: {email}
            Response email: {response}
            
            Your evaluation:
            """
        
        # Populate the template with actual values
        evaluation_prompt = evaluation_template.format(
            scenario=scenario,
            rubric=rubric,
            email=email,
            response=recipient_reply
        )
        
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

class EmailRecipient:
    def __init__(self):
        # Use the same API key as other components
        api_key = os.getenv("OPENAI_API_KEY_CLAB")
        if not api_key:
            raise ValueError("No API key found. Please set the environment variable.")
        self.client = openai.OpenAI(api_key=api_key)
    
    def generate_reply(self, recipient_prompt: str, user_email: str, 
                      model: str = "gpt-4o") -> str:
        """Generate a reply email from the recipient persona"""
        
        reply_prompt = f"""
        {recipient_prompt}
        
        You just received this email:
        {user_email}
        
        Please write a reply email as this character. Write only the email content, no additional commentary.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are roleplaying as the specified character. Write a natural email reply that fits your persona and responds appropriately to the received email."},
                    {"role": "user", "content": reply_prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating recipient reply: {str(e)}")
            return None

class RubricGenerator:
    def __init__(self):
        # Use the same API key as other components
        api_key = os.getenv("OPENAI_API_KEY_CLAB")
        if not api_key:
            raise ValueError("No API key found. Please set the environment variable.")
        self.client = openai.OpenAI(api_key=api_key)
    
    def get_or_generate_rubric(self, scenario: str, scenario_filename: str, model: str = "gpt-4o") -> str:
        """Load existing rubric or generate and save a new one"""
        
        # First, check session state cache
        if scenario_filename in st.session_state.cached_rubrics:
            return st.session_state.cached_rubrics[scenario_filename]
        
        # Second, try to load from file (for local development)
        existing_rubric = load_rubric_from_file(scenario_filename)
        if existing_rubric:
            # Cache in session state
            st.session_state.cached_rubrics[scenario_filename] = existing_rubric
            return existing_rubric
        
        # If no existing rubric, generate a new one
        new_rubric = self.generate_rubric(scenario, model)
        if new_rubric:
            # Cache in session state
            st.session_state.cached_rubrics[scenario_filename] = new_rubric
            # Try to save to file (works in local development)
            save_rubric_to_file(scenario_filename, new_rubric)
        
        return new_rubric
    
    def generate_rubric(self, scenario: str, model: str = "gpt-4o") -> str:
        """Generate a custom rubric for evaluating emails based on the scenario"""
        
        # Load rubric generation prompt
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            rubric_prompt_path = os.path.join(script_dir, "prompts", "rubric_generation", "default.txt")
            with open(rubric_prompt_path, "r") as f:
                rubric_template = f.read()
        except:
            rubric_template = """I'm creating an AI-driven game where the player attempts to write emails to negotiate an outcome in a scenario. Can you look at the scenario and come up with a rubric to grade the email? The last item, on whether the email successfully achieves the goal, must always be included and worth 10 points.

Ready? Here's the scenario:

{scenario}

Rubric:"""
        
        rubric_prompt = rubric_template.format(scenario=scenario)
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert educator creating detailed rubrics for email evaluation. Create specific, measurable criteria based on the given scenario."},
                    {"role": "user", "content": rubric_prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating rubric: {str(e)}")
            return None

def load_scenarios_from_folder(folder_path: str = "prompts/scenarios") -> Dict[str, Dict[str, str]]:
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
                
                scenarios[display_name] = {
                    'content': content,
                    'filename': filename
                }
                
            except Exception as e:
                st.error(f"Error loading scenario from {file_path}: {str(e)}")
    
    return scenarios

def load_recipient_prompt(scenario_filename: str) -> str:
    """Load recipient prompt for a given scenario filename"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    recipient_path = os.path.join(script_dir, "prompts", "recipients", scenario_filename)
    
    if os.path.exists(recipient_path):
        try:
            with open(recipient_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            st.error(f"Error loading recipient prompt: {str(e)}")
            return ""
    else:
        return f"You are the recipient of an email. Please respond naturally and appropriately to the email you receive."

def load_rubric_from_file(scenario_filename: str) -> str:
    """Load rubric from rubrics folder for a given scenario filename"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rubric_path = os.path.join(script_dir, "rubrics", scenario_filename)
    
    if os.path.exists(rubric_path):
        try:
            with open(rubric_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            st.error(f"Error loading rubric: {str(e)}")
            return None
    else:
        return None

def save_rubric_to_file(scenario_filename: str, rubric: str) -> bool:
    """Save generated rubric to rubrics folder"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rubrics_dir = os.path.join(script_dir, "rubrics")
    
    # Create rubrics directory if it doesn't exist
    if not os.path.exists(rubrics_dir):
        try:
            os.makedirs(rubrics_dir)
        except Exception as e:
            st.error(f"Error creating rubrics directory: {str(e)}")
            return False
    
    rubric_path = os.path.join(rubrics_dir, scenario_filename)
    
    try:
        with open(rubric_path, 'w', encoding='utf-8') as f:
            f.write(rubric)
        return True
    except Exception as e:
        st.error(f"Error saving rubric: {str(e)}")
        return False

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
                scenario_data = available_scenarios[selected_scenario_name]
                scenario_content = scenario_data['content']
                st.session_state.selected_scenario = scenario_content
                st.session_state.selected_scenario_file = scenario_data['filename']
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
        # Developer mode section
        st.subheader("🛠️ Developer Mode")
        
        # Recipient persona section (collapsible)
        with st.expander("📨 Recipient Persona", expanded=False):
            st.markdown("*Define who will reply to the user's email*")
            
            # Load recipient prompt based on selected scenario
            if st.session_state.selected_scenario_file:
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
        with st.expander("📝 Grading Instructions", expanded=False):
            st.markdown("*Tell the AI evaluator how to assess the email*")
            
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                eval_prompt_path = os.path.join(script_dir, "prompts", "evaluation", "default.txt")
                with open(eval_prompt_path, "r") as f:
                    default_prompt = f.read()
            except:
                default_prompt = """Given the following scenario, how would you evaluate the email? Please come up with some criteria and then evaluate the email based on those criteria. Give a numerical scale for each criterion and tally up a total score for the email."""
            
            evaluator_prompt = st.text_area(
                "Grading Instructions",
                value=default_prompt,
                height=300,
                help="Instructions for the AI evaluator on how to assess emails",
                key="evaluator_prompt"
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
        
        # Show the generated rubric
        if "rubric" in result:
            st.subheader("📏 Evaluation Rubric")
            st.markdown(result["rubric"])
        
        # Show the email
        st.subheader("✍️ Your Email")
        st.text_area("", value=result["email"], height=300, disabled=True)
        
        # Show the recipient reply
        if "recipient_reply" in result:
            st.subheader("📨 Recipient's Reply")
            st.markdown(result["recipient_reply"])
        
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