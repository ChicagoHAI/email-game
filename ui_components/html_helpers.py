"""
HTML Helper Functions

Common HTML/CSS generation utilities for the Email Game UI.
"""

import streamlit as st


def create_scenario_display(scenario_content: str) -> str:
    """Create formatted HTML display for scenario content"""
    from utils import format_scenario_content
    
    formatted_content = format_scenario_content(scenario_content)
    return f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff;">
    {formatted_content}
    </div>
    """


def create_email_display(email_content: str, sender: str = "HR", 
                        background_color: str = "#e7f3ff", 
                        border_color: str = "#007bff") -> str:
    """Create formatted HTML display for email content"""
    return f"""
    <div style="background-color: {background_color}; padding: 10px; border-radius: 5px; border-left: 3px solid {border_color}; margin-bottom: 10px;">
    {email_content.replace(chr(10), '<br>')}
    </div>
    """


def create_recipient_reply_display(reply_content: str) -> str:
    """Create formatted HTML display for recipient replies"""
    return f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #6c757d;">
    {reply_content.replace(chr(10), '<br>')}
    </div>
    """


def create_updated_response_display(response_content: str) -> str:
    """Create formatted HTML display for updated Adam responses"""
    return f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #6c757d;">
    {response_content.replace(chr(10), '<br>')}
    </div>
    """


def create_forwarded_email_display(email_content: str) -> str:
    """Create formatted HTML display for forwarded emails"""
    from utils import format_scenario_content
    
    email_formatted = format_scenario_content(email_content)
    return f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #6c757d; font-size: 0.9em;">
    {email_formatted}
    </div>
    """


def create_emily_email_display(email_content: str) -> str:
    """Create formatted HTML display for Emily's emails"""
    from utils import format_scenario_content
    
    email_formatted = format_scenario_content(email_content)
    return f"""
    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; font-size: 0.9em;">
    {email_formatted}
    </div>
    """


def create_mark_email_display(email_content: str) -> str:
    """Create formatted HTML display for Mark's emails"""
    from utils import format_scenario_content
    
    email_formatted = format_scenario_content(email_content)
    return f"""
    <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; border-left: 4px solid #17a2b8; font-size: 0.9em;">
    {email_formatted}
    </div>
    """


def show_evaluation_styles():
    """Inject CSS styles for evaluation display"""
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


def create_session_info_display(session_id: str) -> None:
    """Create session info display"""
    st.info(f"📋 **Session ID:** `{session_id}` (copy this to resume the game later)")


def create_level_display(level: float) -> str:
    """Create level display string"""
    if level == 0:
        return "Tutorial"
    elif level == 2.5:
        return "Challenge Level 2.5"
    else:
        return f"Level {level}"


def create_success_message(level: float) -> str:
    """Create success message for level completion"""
    if level == 2.5:
        return "🎉 **Success!** You completed the challenge level!"
    else:
        return "🎉 **Success!** You persuaded the recipient and completed this level!"


def create_strategy_warning() -> None:
    """Create strategy analysis warning display"""
    st.warning("⚠️ **Strategy Analysis**: You used forbidden strategies (layoffs or salary increases)!")
    st.info("🎯 **Next Challenge**: You'll be directed to Level 2.5 where these strategies are prohibited.")


def create_strategy_success() -> None:
    """Create strategy analysis success display"""
    st.info("✅ **Strategy Analysis**: Great! You didn't use any forbidden strategies. You can proceed directly to Level 3.")


def create_turn_counter_display(current_turn: int, max_turns: int) -> None:
    """Create turn counter display for multi-turn levels"""
    st.info(f"📧 **Turn {current_turn} of {max_turns}** - Continue the conversation with Adam")


def create_level_complete_display(level: float) -> None:
    """Create level complete display"""
    st.success(f"🎉 **Level {level} Complete!** You successfully helped Adam express his concerns.")


def create_turn_limit_display(max_turns: int) -> None:
    """Create turn limit reached display"""
    st.warning(f"⏱️ **Turn limit reached** ({max_turns} turns)")
    st.info("💼 Adam has decided to just bring noise canceling headphones and a blanket to work.") 