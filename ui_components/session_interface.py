"""
Session Interface Components

Handles session selection, creation, and management UI components.
"""

import streamlit as st
from session_manager import create_new_session, session_exists, load_session_data
from .shared_components import create_session_info_display


def show_session_selection_screen():
    """Show the session selection screen for starting new or resuming existing sessions"""
    
    st.markdown("---")
    
    st.markdown("""
    You are a ghostwriter who helps people craft messages in various complex scenarios. Throughout the game, you will receive writing requests from a client. Upon submitting an email, you will receive a response from the email's intended recipient indicating whether you have achieved the scenario's goal. The requests will become increasingly more difficult as the levels progress. Choose your words wisely, but most importantly, have fun!
    
    **Choose an option below to get started:**
    """)
    
    # Two columns for the options
    col1, col2 = st.columns(2)
    
    with col1:
        _show_new_session_option()
    
    with col2:
        _show_resume_session_option()
    
    # Helpful information section
    # st.markdown("---")
    # _show_session_info_section()


def _show_new_session_option():
    """Show the new session creation option"""
    st.markdown("### New Game")
    # st.markdown("Begin a new game session.")
    
    if st.button("Start A New Game", type="primary", use_container_width=True):
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


def _show_resume_session_option():
    """Show the resume session option"""
    st.markdown("### Resume Game")
    # st.markdown("Continue an existing game session using your Session ID.")
    
    # Session ID input
    resume_session_id = st.text_input(
        "Enter your game session ID:",
        placeholder="e.g., da4fe9bc-042b-4533-8a60-68f63773eebd",
        help="Enter the session ID from a previous game"
    )
    
    if st.button("Resume Game", disabled=not resume_session_id.strip(), use_container_width=True):
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
                    
                    # st.success(f"✅ Session resumed successfully!")
                    # st.info(f"📊 Progress: {len(session_data['completed_levels'])} levels completed")
                    
                    # Rerun to show the game interface
                    st.rerun()
                else:
                    st.error("❌ Failed to load session data. Please try again.")
                    
            except Exception as e:
                st.error(f"❌ Failed to resume session: {str(e)}")
        else:
            st.error("❌ Session ID not found. Please check your Session ID and try again.")


def _show_session_info_section():
    """Show helpful information about Session IDs"""
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


def show_session_header(session_id: str):
    """Show the session header with navigation options"""
    # Session info bar
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        create_session_info_display(session_id)
    
    with col2:
        # Check if game is complete and add leaderboard button
        from session_manager import is_game_complete
        if is_game_complete(session_id):
            if st.button("🏆 Leaderboard", help="View the leaderboard"):
                st.session_state.show_leaderboard = True
                st.rerun()
    
    with col3:
        if st.button("New Session", help="Start a fresh session"):
            # Clear current session and return to selection screen
            if 'game_session_id' in st.session_state:
                del st.session_state.game_session_id
            if 'show_leaderboard' in st.session_state:
                del st.session_state.show_leaderboard
            st.rerun()
    
    st.markdown("---") 