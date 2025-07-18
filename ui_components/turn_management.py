"""
Turn Management Components

Handles turn editing and conversation history display for multi-turn levels.
"""

import streamlit as st
from config import EMAIL_MAX_CHARS
from .html_helpers import create_email_display, create_recipient_reply_display


def show_conversation_history(session_id: str, level: float):
    """Show conversation history for multi-turn levels"""
    from session_manager import get_conversation_history
    
    conversation_history = get_conversation_history(session_id, level)
    
    if conversation_history:
        st.subheader("💬 Conversation History")
        
        for turn_data in conversation_history:
            _show_turn_display(turn_data, session_id, level)


def _show_turn_display(turn_data: dict, session_id: str, level: float):
    """Show a single turn in the conversation history"""
    turn_num = turn_data['turn_number']
    
    # User email - make it editable for turn invalidation
    # Add some top padding for better visual separation
    st.markdown("<div style='padding-top: 20px;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(f"**Turn {turn_num} - Your Email:**")
    
    with col2:
        edit_key = f"edit_turn_{turn_num}"
        if st.button(f"✏️ Edit", key=f"edit_button_{turn_num}", help=f"Edit Turn {turn_num} email"):
            st.session_state[edit_key] = True
    
    # Show editable text area if in edit mode, otherwise show formatted display
    if st.session_state.get(edit_key, False):
        _show_turn_edit_form(turn_data, session_id, level, edit_key)
    else:
        _show_turn_display_only(turn_data)


def _show_turn_edit_form(turn_data: dict, session_id: str, level: float, edit_key: str):
    """Show the edit form for a turn"""
    turn_num = turn_data['turn_number']
    
    edited_email = st.text_area(
        f"Edit Turn {turn_num} email:",
        value=turn_data['email_content'],
        height=200,
        max_chars=EMAIL_MAX_CHARS,
        key=f"email_edit_{turn_num}"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("💾 Save", key=f"save_turn_{turn_num}", type="primary"):
            # Update turn and clear future turns
            from ui_user_refactored import handle_turn_edit
            # Exit edit mode before calling handle_turn_edit
            st.session_state[edit_key] = False
            handle_turn_edit(session_id, level, turn_num, edited_email)
            # handle_turn_edit already calls st.rerun(), so we don't need to call it again
    
    with col2:
        if st.button("❌ Cancel", key=f"cancel_turn_{turn_num}"):
            st.session_state[edit_key] = False
            st.rerun()


def _show_turn_display_only(turn_data: dict):
    """Show the read-only display for a turn"""
    # User email display
    email_html = create_email_display(turn_data['email_content'])
    st.markdown(email_html, unsafe_allow_html=True)
    
    # Adam's reply (if available)
    if turn_data['recipient_reply']:
        st.markdown(f"**Turn {turn_data['turn_number']} - Adam's Reply:**")
        reply_html = create_recipient_reply_display(turn_data['recipient_reply'])
        st.markdown(reply_html, unsafe_allow_html=True)
    
    # Show if goal was achieved in this turn
    if turn_data['goal_achieved']:
        st.success(f"🎯 **Goal achieved in Turn {turn_data['turn_number']}!**")


def show_turn_status(session_id: str, level: float, max_turns: int):
    """Show turn status and controls for multi-turn levels"""
    from session_manager import get_next_turn_number, is_level_complete_multi_turn
    from .html_helpers import create_turn_counter_display, create_level_complete_display, create_turn_limit_display
    
    current_turn = get_next_turn_number(session_id, level)
    level_complete = is_level_complete_multi_turn(session_id, level)
    
    # Show turn counter and status
    if level_complete:
        create_level_complete_display(level)
        return False  # Don't show email input
    elif current_turn > max_turns:
        create_turn_limit_display(max_turns)
        return False  # Don't show email input
    else:
        create_turn_counter_display(current_turn, max_turns)
        return True  # Show email input


def get_current_turn_info(session_id: str, level: float):
    """Get current turn information"""
    from session_manager import get_next_turn_number, is_level_complete_multi_turn
    
    current_turn = get_next_turn_number(session_id, level)
    level_complete = is_level_complete_multi_turn(session_id, level)
    
    return {
        'current_turn': current_turn,
        'level_complete': level_complete
    }


def create_turn_email_input(level: float, current_turn: int, max_turns: int):
    """Create email input for multi-turn levels"""
    return st.text_area(
        f"Write your email to Adam (Turn {current_turn}):",
        value="",
        height=400,
        max_chars=EMAIL_MAX_CHARS,
        placeholder="Continue the conversation with Adam. Try to understand what's really bothering him...",
        help="Write an email that helps Adam open up about his true concerns",
        key=f"email_input_level_{level}_turn_{current_turn}"
    )


def handle_turn_restart(session_id: str, level: float):
    """Handle restarting a multi-turn level"""
    from session_manager import clear_level_data
    
    # Clear Level data from session state
    if level in st.session_state.get('level_evaluations', {}):
        del st.session_state.level_evaluations[level]
    if level in st.session_state.get('level_emails', {}):
        del st.session_state.level_emails[level]
    
    # Clear Level data from database
    success = clear_level_data(session_id, level)
    
    if success:
        st.success(f"🔄 Level {level} restarted! You can now try again.")
    else:
        st.error("❌ Failed to restart level. Please try again.")
    
    return success 