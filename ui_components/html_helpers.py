"""
HTML Helper Functions

Pure HTML/CSS generation utilities for the Email Game UI.
No Streamlit-specific business logic - only HTML string generation.
"""


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


 