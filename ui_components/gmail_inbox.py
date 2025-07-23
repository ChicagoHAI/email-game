"""
Email Interface Components

Contains all email-related functionality including:
- Gmail-inspired inbox interface with separate inbox and email views
- Additional email display (Emily/Mark context emails)
- Email data management and rendering
"""

import streamlit as st
from datetime import datetime, timedelta

# =============================================================================
# ROW SPACING CUSTOMIZATION
# =============================================================================
# Control spacing between email rows by adjusting these values:
ROW_PADDING = "8px 16px"        # Internal padding of each row
ROW_HEIGHT = "48px"             # Height of each row  
ROW_GAP = "0px"                 # Space between rows (keep at 0px for tight spacing)

# Quick presets - uncomment to use:
# Extra tight:
# ROW_PADDING = "4px 12px"
# ROW_HEIGHT = "32px"

# Comfortable:
# ROW_PADDING = "12px 16px"  
# ROW_HEIGHT = "56px"
# =============================================================================


def create_gmail_inbox(scenario_content: str, level: float):
    """
    Create a Gmail-like inbox interface with separate inbox and email views.
    
    Args:
        scenario_content: The scenario content (Brittany's email)
        level: Current level number
    """
    
    # Check current view state
    view_state = st.session_state.get('gmail_view', 'inbox')  # 'inbox' or 'email'
    selected_email_id = st.session_state.get('selected_email_id', None)
    
    if view_state == 'email' and selected_email_id is not None:
        # Show individual email view
        show_email_view(scenario_content, level, selected_email_id)
    else:
        # Show inbox view
        show_inbox_view(scenario_content, level)


def show_inbox_view(scenario_content: str, level: float):
    """Show the main inbox view with email list"""
    
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
        padding: 2px 16px;
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
    
    .inbox-header {
        background-color: #f8f9fa;
        padding: 8px 16px;
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
    
    # Create inbox container with wider layout
    st.markdown('<div class="gmail-inbox" style="max-width: 1200px; width: 100%;">', unsafe_allow_html=True)
    
    # Email rows data
    emails = _get_email_data(scenario_content, level)
    
    # Inbox header
    unread_count = sum(1 for email in emails if email['unread'])
    header_html = f'''
    <div class="inbox-header">
        <span style="font-size: 18px; font-weight: 600;">📧 Inbox</span>
        <span class="inbox-count" style="font-size: 14px; color: #5f6368;">{unread_count} unread</span>
    </div>
    '''
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Use clean HTML generation for tight email rows
    
    # First add the CSS styling
    st.markdown(f"""
    <style>
    .tight-email-container {{
        position: relative;
        display: flex;
        flex-direction: column;
        gap: {ROW_GAP};
        width: 100%;
    }}
    
    .email-row {{
        display: flex;
        align-items: center;
        padding: {ROW_PADDING};
        height: {ROW_HEIGHT};
        border-bottom: 1px solid #e0e0e0;
        background-color: #ffffff;
        font-weight: normal;
        font-size: 15px;
        color: #202124;
        transition: background-color 0.2s ease;
        user-select: none;
        position: relative;
    }}
    
    .email-row.readonly {{
        background-color: #fafafa;
        font-weight: normal;
        color: #9aa0a6;
        opacity: 0.7;
    }}
    
    .email-row:hover {{
        background-color: #f5f5f5;
    }}
    
    .email-star {{
        margin-right: 12px;
        font-size: 16px;
        min-width: 20px;
        display: inline-block;
        text-align: center;
    }}
    
    .star-empty {{
        font-size: 20px;
        transform: scale(1.1);
    }}
    
    .email-content {{
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-weight: normal;
    }}
    
    .email-content strong {{
        font-weight: 600;
        font-size: 15px;
    }}
    
    .email-time {{
        margin-left: auto;
        padding-left: 16px;
        font-size: 14px;
        color: #5f6368;
        min-width: 80px;
        text-align: right;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Open the container
    st.markdown('<div class="tight-email-container">', unsafe_allow_html=True)
    
    # Render each email row individually to ensure proper HTML rendering
    for i, email in enumerate(emails):
        star_icon = "⭐" if email['starred'] else '<span class="star-empty">☆</span>'
        readonly_class = "readonly" if i > 0 else ""
        
        # Render each row separately
        st.markdown(f"""
        <div class="email-row {readonly_class}" data-email-id="{i}">
            <span class="email-star">{star_icon}</span>
            <span class="email-content">
                <strong>{email['sender']}</strong> | {email['subject']} - {email['snippet'][:50]}...
            </span>
            <span class="email-time">{email['time']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Close the container
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Button styling
    st.markdown("""
    <style>
    .stButton > button {
        background-color: #52a1eb !important;
        color: white !important;
        border: none !important;
        font-size: 13px !important;
        padding: 8px 16px !important;
        border-radius: 4px !important;
        height: auto !important;
    }
    .stButton > button:hover {
        background-color: #3367d6 !important;
        color: white !important;
    }
    .stButton > button:focus {
        background-color: #52a1eb !important;
        color: white !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Simple, reliable button to open Brittany's email
    if st.button("Open Brittany's Email", use_container_width=False, type="primary"):
        st.session_state.gmail_view = 'email'
        st.session_state.selected_email_id = 0
        st.session_state.show_scenario_email = True
        st.rerun()


def show_email_view(scenario_content: str, level: float, email_id: int):
    """Show individual email view (Gmail-like full email display)"""
    
    # Gmail email view styling
    email_view_css = """
    <style>
    .gmail-email-view {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #ffffff;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        max-width: 1200px;
        width: 100%;
    }
    
    .email-view-header {
        background-color: #f8f9fa;
        padding: 16px 20px;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .back-button-container {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .email-title {
        font-size: 20px;
        font-weight: 600;
        color: #202124;
        margin: 0;
    }
    
    .email-content-container {
        padding: 0 20px 20px 20px;
    }
    </style>
    """
    
    st.markdown(email_view_css, unsafe_allow_html=True)
    
    # Get email data
    emails = _get_email_data(scenario_content, level)
    if email_id >= len(emails):
        st.error("Email not found")
        return
    
    email_data = emails[email_id]
    
    # Mark email as read when opened
    if email_id == 0 and email_data.get('unread', True):
        # Store the read state so it persists during the session
        read_emails = st.session_state.get('read_emails', set())
        read_emails.add(email_id)
        st.session_state.read_emails = read_emails
    
    # Create email view container
    # st.markdown('<div class="gmail-email-view">', unsafe_allow_html=True)
    
    # # Email view header with back button and title
    # header_html = f'''
    # <div class="email-view-header">
    #     <div class="back-button-container">
    #         <span style="font-size: 16px; color: #5f6368;">📧</span>
    #         <h1 class="email-title">{email_data['subject']}</h1>
    #     </div>
    # </div>
    # '''
    # st.markdown(header_html, unsafe_allow_html=True)
    
    # Back button (outside the header for better UX)
    if st.button("← Back to Inbox", key="back_to_inbox", help="Return to inbox", type="secondary"):
        st.session_state.gmail_view = 'inbox'
        st.session_state.selected_email_id = None
        st.session_state.show_scenario_email = False  # For compatibility
        st.rerun()
    
    # Email content container
    st.markdown('<div class="email-content-container">', unsafe_allow_html=True)
    
    # Show the email content
    show_selected_email_content(email_data, scenario_content, level)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


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
    
    # Check if emails have been read (from session state)
    read_emails = st.session_state.get('read_emails', set())
    
    emails = [
        {
            'sender': sender_name,
            'subject': subject,
            'snippet': snippet,
            'time': '10:30 AM',
            'unread': 0 not in read_emails,  # Email 0 (Brittany's) is unread unless opened
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
        },
        {
            'sender': 'Finance Department',
            'subject': 'Budget Approval Request',
            'snippet': 'Please review and approve the budget allocation for the next quarter...',
            'time': 'Yesterday',
            'unread': False,
            'starred': False
        },
        {
            'sender': 'Project Manager',
            'subject': 'Sprint Planning Meeting',
            'snippet': 'Team, we need to schedule our next sprint planning session for...',
            'time': '2 days ago',
            'unread': False,
            'starred': False
        },
        # {
        #     'sender': 'Customer Success',
        #     'subject': 'Client Feedback Summary',
        #     'snippet': 'Here is the monthly summary of client feedback and satisfaction scores...',
        #     'time': '2 days ago',
        #     'unread': False,
        #     'starred': False
        # },
        # {
        #     'sender': 'Legal Team',
        #     'subject': 'Contract Review Needed',
        #     'snippet': 'We need your input on the new vendor contract. Please review the terms...',
        #     'time': '3 days ago',
        #     'unread': True,
        #     'starred': False
        # },
        # {
        #     'sender': 'Product Development',
        #     'subject': 'Feature Release Update',
        #     'snippet': 'The new feature rollout has been completed successfully. Here are the metrics...',
        #     'time': '3 days ago',
        #     'unread': False,
        #     'starred': False
        # },
        # {
        #     'sender': 'Sales Team',
        #     'subject': 'Monthly Sales Report',
        #     'snippet': 'Attached is the monthly sales report showing our performance against targets...',
        #     'time': '4 days ago',
        #     'unread': False,
        #     'starred': True
        # },
        # {
        #     'sender': 'Operations',
        #     'subject': 'Facility Access Update',
        #     'snippet': 'New security protocols have been implemented. Please update your access cards...',
        #     'time': '1 week ago',
        #     'unread': False,
        #     'starred': False
        # }
    ]
    
    return emails


def show_selected_email_content(email_data: dict, scenario_content: str = None, level: float = None):
    """Show the content of the selected email"""
    
    # st.markdown("---")
    # st.markdown("### 📖 Email Content")
    
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
        # Show actual scenario content for the first email with reduced paragraph spacing
        body_html = f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; line-height: 1.5;">
            <div style="margin-bottom: 0;">
                {scenario_content.replace(chr(10), '</div><div style="margin-bottom: 8px;">')}
            </div>
        </div>
        """
        st.markdown(body_html, unsafe_allow_html=True)
        
        # Add forwarded emails as toggleable expanders
        _show_forwarded_emails_expanders(level)
        
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


def _show_forwarded_emails_expanders(level: float):
    """Show forwarded emails as toggleable expanders if they exist for this level"""
    if not level:
        return
    
    # Import here to avoid circular imports
    from config import LEVEL_TO_SCENARIO_MAPPING
    from utils import get_all_additional_emails
    from .html_helpers import create_forwarded_email_display
    
    # Get backend scenario ID from user level
    backend_scenario_id = LEVEL_TO_SCENARIO_MAPPING.get(level, "5.0")
    scenario_filename = f"scenario_{backend_scenario_id}.txt"
    
    # Get forwarded emails
    forwarded_emails = get_all_additional_emails(scenario_filename)
    
    if not forwarded_emails['has_emails']:
        return
    
    # Add a visual separator
    st.markdown("""
    <div style="margin: 16px 0; padding: 8px 0; border-top: 1px solid #e0e0e0; color: #5f6368; font-size: 13px; text-align: center;">
        ──────── Forwarded emails ────────
    </div>
    """, unsafe_allow_html=True)
    
    # Show each forwarded email as a collapsible expander
    for i, (email_title, email_content) in enumerate(forwarded_emails['emails']):
        # Parse email content to get subject for better title
        lines = email_content.strip().split('\n')
        subject_line = ""
        
        for line in lines:
            if line.startswith("Subject: "):
                subject_line = line[9:]  # Remove "Subject: "
                break
        
        # Create title for expander
        expander_title = f"📧 {subject_line}" if subject_line else f"📧 Forwarded Email {i+1}"
        
        # Create expander for each forwarded email
        with st.expander(expander_title, expanded=False):
            email_html = create_forwarded_email_display(email_content)
            st.markdown(email_html, unsafe_allow_html=True)


def show_gmail_inbox_section(scenario_content: str, level: float):
    """Show the Gmail-like inbox interface instead of the traditional scenario section"""
    create_gmail_inbox(scenario_content, level)


def show_additional_emails(scenario_filename: str):
    """Show additional emails for a scenario"""
    from utils import is_multi_recipient_scenario
    
    # Skip forwarded emails since they're now shown within Brittany's email in the Gmail inbox
    # Only check for multi-recipient context emails (Emily/Mark)
    if is_multi_recipient_scenario(scenario_filename):
        _show_multi_recipient_emails(scenario_filename)


def _show_multi_recipient_emails(scenario_filename: str):
    """Show multi-recipient context emails"""
    import streamlit as st
    from utils import get_scenario_prompts
    from .html_helpers import create_emily_email_display, create_mark_email_display
    
    recipient_prompts = get_scenario_prompts(scenario_filename)
    
    if 'emily' in recipient_prompts and 'mark' in recipient_prompts:
        st.markdown("**📨 Email Context**")
        st.info("💼 Below are the emails from Emily and Mark that prompted this request.")
        
        # Emily's email
        with st.expander("Emily's Email", expanded=False):
            emily_html = create_emily_email_display(recipient_prompts['emily'])
            st.markdown(emily_html, unsafe_allow_html=True)
        
        # Mark's email
        with st.expander("Mark's Email", expanded=False):
            mark_html = create_mark_email_display(recipient_prompts['mark'])
            st.markdown(mark_html, unsafe_allow_html=True)