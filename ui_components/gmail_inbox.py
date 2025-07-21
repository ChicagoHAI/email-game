"""
Gmail-like Inbox Component

A Gmail-inspired inbox interface for the Email Game.
"""

import streamlit as st
from datetime import datetime, timedelta


def create_gmail_inbox(scenario_content: str, level: float):
    """
    Create a Gmail-like inbox interface with email rows.
    
    Args:
        scenario_content: The scenario content (Brittany's email)
        level: Current level number
    """
    
    # Gmail-like styling
    gmail_css = """
    <style>
    .gmail-inbox {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #ffffff;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .email-row {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid #e0e0e0;
        cursor: pointer;
        transition: background-color 0.2s ease;
    }
    
    .email-row:hover {
        background-color: #f5f5f5;
    }
    
    .email-row.unread {
        background-color: #ffffff;
        font-weight: 600;
    }
    
    .email-row.read {
        background-color: #fafafa;
        font-weight: normal;
    }
    
    .email-checkbox {
        margin-right: 12px;
        width: 16px;
        height: 16px;
    }
    
    .email-star {
        margin-right: 12px;
        color: #fbbc04;
        font-size: 16px;
        cursor: pointer;
    }
    
    .email-star.empty {
        color: #dadce0;
    }
    
    .email-sender {
        min-width: 180px;
        font-size: 14px;
        color: #202124;
        margin-right: 12px;
    }
    
    .email-subject {
        flex: 1;
        font-size: 14px;
        color: #202124;
        margin-right: 12px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .email-snippet {
        color: #5f6368;
        font-size: 13px;
        margin-left: 4px;
    }
    
    .email-time {
        font-size: 12px;
        color: #5f6368;
        min-width: 60px;
        text-align: right;
    }
    
    .inbox-header {
        background-color: #f8f9fa;
        padding: 12px 16px;
        border-bottom: 1px solid #e0e0e0;
        font-size: 14px;
        font-weight: 500;
        color: #5f6368;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .inbox-count {
        font-size: 12px;
        color: #5f6368;
    }
    </style>
    """
    
    st.markdown(gmail_css, unsafe_allow_html=True)
    
    # Create inbox container
    st.markdown('<div class="gmail-inbox">', unsafe_allow_html=True)
    
    # Email rows data
    emails = _get_email_data(scenario_content, level)
    
    # Inbox header
    unread_count = sum(1 for email in emails if email['unread'])
    header_html = f'''
    <div class="inbox-header">
        <span>📧 Inbox</span>
        <span class="inbox-count">{unread_count} unread</span>
    </div>
    '''
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Display email rows
    for i, email in enumerate(emails):
        email_key = f"email_{i}"
        
        # Create email row
        star_icon = "⭐" if email['starred'] else "☆"
        
        # Create button label with email info
        button_label = f"{star_icon} **{email['sender']}** | {email['subject']} - {email['snippet'][:50]}... | {email['time']}"
        
        # Style for tighter rows
        button_style = f"""
        <style>
        div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {{
            width: 100%;
            text-align: left;
            padding: 8px 16px;
            border: none;
            border-bottom: 1px solid #e0e0e0;
            background-color: {'#ffffff' if email['unread'] else '#fafafa'};
            font-weight: {'600' if email['unread'] else 'normal'};
            font-size: 14px;
            color: #202124;
            border-radius: 0;
            min-height: 40px;
        }}
        
        div[data-testid="stButton"] > button[data-testid="baseButton-secondary"]:hover {{
            background-color: #f5f5f5;
            border-color: #e0e0e0;
        }}
        </style>
        """
        st.markdown(button_style, unsafe_allow_html=True)
        
        if i == 0:  # First email (Brittany's) - clickable
            # Add active state styling if email is selected
            is_selected = st.session_state.get('show_scenario_email', False)
            if is_selected:
                active_style = """
                <style>
                div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {
                    background-color: #e8f0fe !important;
                    border-left: 4px solid #1a73e8 !important;
                }
                </style>
                """
                st.markdown(active_style, unsafe_allow_html=True)
            
            button_text = f"{'📖 ' if is_selected else ''}{button_label}"
            
            if st.button(
                button_text,
                key=email_key,
                help=f"Click to {'close' if is_selected else 'open'} email from {email['sender']}",
                use_container_width=True
            ):
                # Toggle the scenario email display
                current_state = st.session_state.get('show_scenario_email', False)
                st.session_state.show_scenario_email = not current_state
                st.session_state.selected_email = i if not current_state else None
                st.rerun()
        else:  # Other emails - read-only (display as disabled button)
            disabled_style = f"""
            <style>
            div[data-testid="stButton"] > button[data-testid="baseButton-secondary"]:disabled {{
                background-color: #fafafa;
                color: #9aa0a6;
                cursor: not-allowed;
                opacity: 0.7;
            }}
            </style>
            """
            st.markdown(disabled_style, unsafe_allow_html=True)
            
            st.button(
                button_label,
                key=email_key,
                help="This email is read-only in the demo",
                use_container_width=True,
                disabled=True
            )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show selected email content only if Brittany's email is toggled on
    if st.session_state.get('show_scenario_email', False) and st.session_state.get('selected_email') == 0:
        show_selected_email_content(emails[0], scenario_content)


def _get_email_data(scenario_content: str, level: float):
    """Generate email data for the inbox rows"""
    
    # Extract sender name and subject from scenario content
    scenario_lines = scenario_content.strip().split('\n')
    sender_line = scenario_lines[0] if scenario_lines else ""
    
    # Try to extract sender name (looking for "I'm [Name]")
    sender_name = "Brittany (HR)"  # Default
    if "I'm " in sender_line:
        try:
            name_part = sender_line.split("I'm ")[1].split(",")[0]
            sender_name = f"{name_part} (HR)"
        except:
            pass
    
    # Generate subject based on level/scenario
    subject = f"Level {level}: New Task Assignment"
    if level == 0:
        subject = "Welcome Email Request"
    elif level == 1:
        subject = "Office Space Policy Question"
    elif level == 2:
        subject = "Team Communication Task"
    
    # Create snippet from scenario content
    snippet = scenario_content.replace('\n', ' ')[:80] + "..."
    
    # Current time variations
    now = datetime.now()
    
    emails = [
        {
            'sender': sender_name,
            'subject': subject,
            'snippet': snippet,
            'time': '10:30 AM',
            'unread': True,
            'starred': True
        },
        {
            'sender': 'Marketing Team',
            'subject': 'Q4 Campaign Review Meeting',
            'snippet': 'Hi everyone, please join us for the quarterly campaign review...',
            'time': '9:15 AM',
            'unread': False,
            'starred': False
        },
        {
            'sender': 'IT Support',
            'subject': 'System Maintenance Scheduled',
            'snippet': 'This is to inform you that we will be performing system maintenance...',
            'time': 'Yesterday',
            'unread': False,
            'starred': False
        }
    ]
    
    return emails


def show_selected_email_content(email_data: dict, scenario_content: str = None):
    """Show the content of the selected email"""
    
    st.markdown("---")
    st.markdown("### 📖 Email Content")
    
    # Email header
    header_html = f"""
    <div style="background-color: #f8f9fa; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
        <div style="font-size: 18px; font-weight: 600; color: #202124; margin-bottom: 8px;">
            {email_data['subject']}
        </div>
        <div style="font-size: 14px; color: #5f6368; margin-bottom: 4px;">
            <strong>From:</strong> {email_data['sender']}
        </div>
        <div style="font-size: 14px; color: #5f6368;">
            <strong>Time:</strong> {email_data['time']}
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Email body
    if scenario_content:
        # Show actual scenario content for the first email
        body_html = f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; line-height: 1.6;">
            {scenario_content.replace(chr(10), '<br><br>')}
        </div>
        """
    else:
        # Show placeholder content for other emails
        placeholder_content = f"""
        This is a placeholder email from {email_data['sender']}.
        
        {email_data['snippet']}
        
        This email is part of the Gmail-like interface demo. In a real implementation, 
        this would contain the actual email content.
        """
        body_html = f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; line-height: 1.6; color: #5f6368; font-style: italic;">
            {placeholder_content.replace(chr(10), '<br><br>')}
        </div>
        """
    
    st.markdown(body_html, unsafe_allow_html=True) 