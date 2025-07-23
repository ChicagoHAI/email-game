"""
Email Writing Game - Main Application

A Streamlit application for practicing email communication skills with AI feedback.
This is the main entry point that orchestrates all the modular components.

Features:
- Multiple communication scenarios with level progression
- AI-powered email generation and evaluation
- Recipient simulation and response generation
- Custom rubric generation and evaluation
- Browser-like history navigation system
- User and Developer modes

Dependencies:
- streamlit>=1.39.0
- openai>=1.13.0

Environment Variables:
- OPENAI_API_KEY or GROQ_API_KEY: Required API keys for AI functionalities

Author: Complex Communication Research Project
"""

import streamlit as st
from ui import main_interface


# =============================================================================
# WIDTH CUSTOMIZATION SETTINGS
# =============================================================================
# 
# Easy width customization for developers:
#
# OPTION 1 - Basic Layout Control:
#   Change APP_LAYOUT to "wide" for full-width or "centered" for standard
#
# OPTION 2 - Custom Width Control:
#   Set CUSTOM_WIDTH_ENABLED = True and specify CUSTOM_MAX_WIDTH
#   Examples:
#     CUSTOM_MAX_WIDTH = "800px"   # Narrow width
#     CUSTOM_MAX_WIDTH = "1600px"  # Wide width  
#     CUSTOM_MAX_WIDTH = "90%"     # Percentage-based
#     CUSTOM_MAX_WIDTH = "100%"    # Full width
#
# =============================================================================

# Layout option: "centered" or "wide"
# - "centered": Standard centered layout with max width ~1200px
# - "wide": Full-width layout that uses entire browser width
APP_LAYOUT = "wide"

# Custom width control (optional, overrides APP_LAYOUT when enabled)
CUSTOM_WIDTH_ENABLED = True
CUSTOM_MAX_WIDTH = "60%"  # Only used when CUSTOM_WIDTH_ENABLED = True

# =============================================================================


def main():
    
    """Main application entry point"""

    
    # Configure page layout with customizable width
    st.set_page_config(
        page_title="The Ghostwriter",
        page_icon="📧",
        layout=APP_LAYOUT,  # Use configurable layout setting
        initial_sidebar_state="collapsed",
        menu_items={
            'Get Help': 'https://github.com/your-repo/email-game',
            'Report a bug': 'https://github.com/your-repo/email-game/issues',
            'About': """
            # The Ghostwriter
            Practice your email communication skills with AI-powered feedback!
            
            This app helps you improve professional email writing through:
            - Realistic scenarios
            - AI feedback and scoring
            - Recipient response simulation
            
            Built with Streamlit and OpenAI GPT-4o.
            """
        }
    )
    
    # Apply custom width styling if enabled
    if CUSTOM_WIDTH_ENABLED and CUSTOM_MAX_WIDTH:
        st.markdown(f"""
        <style>
        /* Main content container with gray background */
        .main .block-container {{
            max-width: {CUSTOM_MAX_WIDTH} !important;
            width: 100% !important;
            padding-top: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            background-color: rgba(240, 240, 240, 0.5) !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
            margin: 1rem auto !important;
        }}
        
        /* Alternative selectors for different Streamlit versions */
        .block-container {{
            max-width: {CUSTOM_MAX_WIDTH} !important;
            background-color: rgba(240, 240, 240, 0.5) !important;
        }}
        
        .stApp > div:first-child > div:first-child > div:first-child {{
            max-width: {CUSTOM_MAX_WIDTH} !important;
        }}
        
        /* Hide Streamlit header bar */
        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        
        /* Hide Streamlit menu button */
        button[title="View fullscreen"] {{
            display: none !important;
        }}
        
        /* Hide footer */
        footer {{
            display: none !important;
        }}
        
        /* Optional: Hide the "Made with Streamlit" footer */
        .css-1dp5vir {{
            display: none !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    # Run the main interface
    main_interface()


if __name__ == "__main__":
    main() 