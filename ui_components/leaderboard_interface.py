"""
Leaderboard Interface Components

Handles leaderboard display and statistics for completed players.
"""

import streamlit as st
from datetime import timedelta


def show_leaderboard_page(session_id: str):
    """Show the leaderboard page for players who completed all levels"""
    
    st.title("🏆 Leaderboard")
    
    st.markdown("""
    **Congratulations!** 🎉 You've successfully completed all levels of the game!
    """)
    
    # Get leaderboard data
    leaderboard_data = _get_leaderboard_data()
    
    # Create leaderboard table
    _show_leaderboard_table(leaderboard_data, session_id)
    
    st.markdown("---")
    
    # Action buttons
    _show_leaderboard_actions()
    
    # Fun facts section
    _show_statistics_section(leaderboard_data)


def _get_leaderboard_data():
    """Get leaderboard data with loading spinner"""
    with st.spinner("Loading leaderboard..."):
        from session_manager import get_leaderboard_data
        return get_leaderboard_data()


def _show_leaderboard_table(leaderboard_data: list, session_id: str):
    """Show the leaderboard table"""
    # Create leaderboard table
    leaderboard_display = []
    
    for i, player in enumerate(leaderboard_data, 1):
        # Format completion time
        completed_at = player['completed_at'].strftime("%Y-%m-%d %H:%M")
        
        # Format total time
        total_time_str = _format_total_time(player['total_time'])
        
        # Add rank emoji
        rank_emoji = _get_rank_emoji(i)
        
        # Highlight current player
        session_display = player['session_id'][:8] + "..."
        if player['session_id'] == session_id:
            session_display = f"**{session_display} (You!)**"
        
        leaderboard_display.append({
            "Rank": rank_emoji,
            "Player": session_display,
            "Completed": completed_at,
            "Total Time": total_time_str,
            "Submissions": player['total_submissions']
        })
    
    # Display leaderboard table
    st.table(leaderboard_display)


def _format_total_time(total_time):
    """Format total time duration"""
    if not total_time:
        return "N/A"
    
    total_seconds = int(total_time.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def _get_rank_emoji(rank: int):
    """Get rank emoji for position"""
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    else:
        return f"{rank}."


def _show_leaderboard_actions():
    """Show action buttons for leaderboard"""
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 Refresh Leaderboard", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("🆕 Start New Game", use_container_width=True):
            # Clear current session and return to selection screen
            if 'game_session_id' in st.session_state:
                del st.session_state.game_session_id
            if 'show_leaderboard' in st.session_state:
                del st.session_state.show_leaderboard
            st.rerun()
    
    with col3:
        if st.button("🎮 Continue Playing", use_container_width=True, help="Return to Level 5"):
            if 'show_leaderboard' in st.session_state:
                del st.session_state.show_leaderboard
            st.rerun()


def _show_statistics_section(leaderboard_data: list):
    """Show statistics section"""
    st.markdown("---")
    with st.expander("📊 Statistics", expanded=False):
        if leaderboard_data:
            # Calculate some interesting stats
            total_submissions = sum(p['total_submissions'] for p in leaderboard_data)
            avg_submissions = total_submissions / len(leaderboard_data) if leaderboard_data else 0
            
            st.markdown(f"""
            - **Total players completed:** {len(leaderboard_data)}
            - **Total emails written:** {total_submissions:,}
            - **Average emails per player:** {avg_submissions:.1f}
            """)
        else:
            st.markdown("Be the first to set the benchmark for future players!")


def show_game_completion_trigger():
    """Show game completion trigger and redirect to leaderboard"""
    st.success("🎊 **GAME COMPLETE!** 🎊")
    st.balloons()  # Celebration animation!
    st.success("🏆 **You are now a Communication Master!** 🏆")
    
    # Wait a moment then redirect to leaderboard
    import time
    time.sleep(1)
    st.session_state.show_leaderboard = True
    st.session_state.game_completed = False  # Clear the flag
    st.rerun()


def check_and_show_leaderboard_trigger(session_id: str):
    """Check if leaderboard should be shown and trigger if needed"""
    if st.session_state.get('show_leaderboard', False):
        show_leaderboard_page(session_id)
        return True
    return False 