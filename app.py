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


def main():
    """Main application entry point"""
    
    # Always use collapsed sidebar and centered layout for user mode
    st.set_page_config(
        page_title="The Ghostwriter",
        page_icon="📧",
        layout="centered",
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

    # Run the main interface
    main_interface()


if __name__ == "__main__":
    main() 