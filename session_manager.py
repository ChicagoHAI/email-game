"""
Session Manager

Handles all session-related operations for the Email Game application.
Provides functions for creating, loading, and managing game sessions using UUIDs.
"""

import uuid
import logging
from typing import Optional, Dict, Set, Any, List
from datetime import datetime
from database.connection import get_database_session, init_database
from database.models import (
    GameSession, 
    SessionEmailSubmission, 
    SessionLevelCompletion, 
    EvaluationResult
)
from config import MAX_TURNS, MULTI_TURN_LEVELS

logger = logging.getLogger(__name__)

# Ensure database is initialized when module is imported
init_database()


def create_new_session() -> str:
    """
    Create a new game session with a unique UUID.
    
    Returns:
        str: Session ID (UUID) for the new session
        
    Raises:
        Exception: If session creation fails
    """
    session_id = str(uuid.uuid4())
    db_session = get_database_session()
    
    try:
        # Create new game session with default values
        new_session = GameSession(
            session_id=session_id,
            current_level=0,  # Start from tutorial
            use_rubric=False  # Default user mode setting
        )
        
        db_session.add(new_session)
        db_session.commit()
        
        logger.info(f"Created new session: {session_id}")
        return session_id
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to create session: {str(e)}")
        raise
    finally:
        db_session.close()


def session_exists(session_id: str) -> bool:
    """
    Check if a session exists in the database.
    
    Args:
        session_id: Session ID to check
        
    Returns:
        bool: True if session exists, False otherwise
    """
    db_session = get_database_session()
    
    try:
        session = db_session.query(GameSession).filter_by(session_id=session_id).first()
        return session is not None
    except Exception as e:
        logger.error(f"Error checking session existence: {str(e)}")
        return False
    finally:
        db_session.close()


def load_session_data(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Load complete session data from database.
    
    Args:
        session_id: Session ID to load
        
    Returns:
        Dict containing session data or None if session not found
        Format:
        {
            'current_level': int,
            'use_rubric': bool,
            'completed_levels': set,
            'level_emails': dict,
            'level_evaluations': dict,
            'last_accessed': datetime
        }
    """
    if not session_exists(session_id):
        logger.warning(f"Session {session_id} not found")
        return None
    
    db_session = get_database_session()
    
    try:
        # Load session metadata
        session = db_session.query(GameSession).filter_by(session_id=session_id).first()
        
        # Load completed levels
        completions = db_session.query(SessionLevelCompletion).filter_by(session_id=session_id).all()
        completed_levels = {comp.level for comp in completions}
        
        # Load latest email for each level
        level_emails = {}
        level_evaluations = {}
        
        # Get latest submission for each level (find all levels that have submissions)
        all_submissions = (
            db_session.query(SessionEmailSubmission)
            .filter_by(session_id=session_id)
            .order_by(SessionEmailSubmission.level, SessionEmailSubmission.submitted_at.desc())
            .all()
        )
        
        # Group by level and get the latest submission for each
        level_submissions = {}
        for submission in all_submissions:
            level = submission.level
            if level not in level_submissions:
                level_submissions[level] = submission
        
        # Load emails and evaluations for all levels with submissions
        for level, latest_submission in level_submissions.items():
            # Load email content for all submissions
            level_emails[level] = latest_submission.email_content
            
            # Load evaluation if exists
            if latest_submission.evaluation_result:
                eval_result = latest_submission.evaluation_result
                evaluation_text = eval_result.evaluation_text or ""
                
                # Check if max_turns_reached flag is present
                max_turns_reached = "MAX_TURNS_REACHED" in evaluation_text
                
                level_evaluations[level] = {
                    'evaluation': eval_result.evaluation_text,
                    'recipient_reply': eval_result.recipient_reply,
                    'rubric': eval_result.rubric,
                    'goal_achieved': eval_result.goal_achieved,
                    'max_turns_reached': max_turns_reached
                }
        
        # Update last accessed time
        session.last_accessed = datetime.utcnow()
        db_session.commit()
        
        # Extract strategy analysis from level evaluations
        strategy_analysis = {}
        for level, evaluation in level_evaluations.items():
            if 'strategy_analysis' in evaluation:
                strategy_analysis[level] = evaluation['strategy_analysis']
        
        session_data = {
            'current_level': session.current_level,
            'use_rubric': session.use_rubric,
            'completed_levels': completed_levels,
            'level_emails': level_emails,
            'level_evaluations': level_evaluations,
            'strategy_analysis': strategy_analysis,
            'last_accessed': session.last_accessed
        }
        
        logger.info(f"Loaded session {session_id}: {len(completed_levels)} levels completed")
        return session_data
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to load session {session_id}: {str(e)}")
        return None
    finally:
        db_session.close()


def save_session_progress(session_id: str, current_level: float, completed_levels: Set[float]) -> bool:
    """
    Save session progress to database.
    
    Args:
        session_id: Session ID
        current_level: Current level user is on (int or float for levels like 2.5)
        completed_levels: Set of completed level numbers (int or float)
        
    Returns:
        bool: True if save successful, False otherwise
    """
    db_session = get_database_session()
    
    try:
        # Update session metadata
        session = db_session.query(GameSession).filter_by(session_id=session_id).first()
        if not session:
            logger.error(f"Session {session_id} not found for progress save")
            return False
        
        session.current_level = current_level
        session.last_accessed = datetime.utcnow()
        
        # Update level completions - remove all first, then add current ones
        db_session.query(SessionLevelCompletion).filter_by(session_id=session_id).delete()
        
        for level in completed_levels:
            completion = SessionLevelCompletion(
                session_id=session_id,
                level=level
            )
            db_session.add(completion)
        
        db_session.commit()
        logger.info(f"Saved progress for session {session_id}: level {current_level}, {len(completed_levels)} completed")
        return True
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to save progress for session {session_id}: {str(e)}")
        return False
    finally:
        db_session.close()


def save_email_submission(session_id: str, level: float, email_content: str, turn_number: int = 1) -> Optional[int]:
    """
    Save an email submission to database.
    
    Args:
        session_id: Session ID
        level: Level number (int or float for levels like 2.5)
        email_content: Email content
        turn_number: Turn number for multi-turn levels
        
    Returns:
        int: Submission ID if successful, None otherwise
    """
    db_session = get_database_session()
    
    try:
        submission = SessionEmailSubmission(
            session_id=session_id,
            level=level,
            email_content=email_content,
            turn_number=turn_number
        )
        
        db_session.add(submission)
        db_session.commit()
        
        submission_id = submission.id
        logger.info(f"Saved email submission {submission_id} for session {session_id}, level {level}")
        return submission_id
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to save email submission: {str(e)}")
        return None
    finally:
        db_session.close()


def save_evaluation_result(submission_id: int, evaluation_data: Dict[str, Any]) -> bool:
    """
    Save evaluation result for an email submission.
    
    Args:
        submission_id: ID of the email submission
        evaluation_data: Dict containing evaluation results
        
    Returns:
        bool: True if save successful, False otherwise
    """
    db_session = get_database_session()
    
    try:
        # Update submission with goal achievement
        submission = db_session.query(SessionEmailSubmission).filter_by(id=submission_id).first()
        if submission:
            submission.goal_achieved = evaluation_data.get('goal_achieved', False)
        
        # Create evaluation result record
        evaluation = EvaluationResult(
            submission_id=submission_id,
            evaluation_text=evaluation_data.get('evaluation', ''),
            recipient_reply=evaluation_data.get('recipient_reply', ''),
            rubric=evaluation_data.get('rubric', ''),
            goal_achieved=evaluation_data.get('goal_achieved', False)
        )
        
        db_session.add(evaluation)
        db_session.commit()
        
        logger.info(f"Saved evaluation result for submission {submission_id}")
        return True
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to save evaluation result: {str(e)}")
        return False
    finally:
        db_session.close()


def handle_level_success(session_id: str, level: float) -> bool:
    """
    Handle successful level completion by adding it to the completion table.
    
    Args:
        session_id: Session ID
        level: Level that was completed
        
    Returns:
        bool: True if successful, False otherwise
    """
    db_session = get_database_session()
    
    try:
        # Check if level is already completed
        existing_completion = db_session.query(SessionLevelCompletion).filter(
            SessionLevelCompletion.session_id == session_id,
            SessionLevelCompletion.level == level
        ).first()
        
        if not existing_completion:
            # Add new completion record
            new_completion = SessionLevelCompletion(
                session_id=session_id,
                level=level
            )
            db_session.add(new_completion)
            db_session.commit()
            logger.info(f"Marked level {level} as completed for session {session_id}")
        
        return True
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to handle level success: {str(e)}")
        return False
    finally:
        db_session.close()


def handle_level_failure(session_id: str, level: float) -> bool:
    """
    Handle level failure by removing current level and all higher levels from completions.
    This implements the "reset progress on failure" logic.
    
    Args:
        session_id: Session ID  
        level: Level that was failed (int or float for levels like 2.5)
        
    Returns:
        bool: True if successful, False otherwise
    """
    db_session = get_database_session()
    
    try:
        # Remove current level and all higher levels from completions
        db_session.query(SessionLevelCompletion).filter(
            SessionLevelCompletion.session_id == session_id,
            SessionLevelCompletion.level >= level
        ).delete()
        
        db_session.commit()
        logger.info(f"Removed level {level}+ completions for session {session_id} due to failure")
        return True
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to handle level failure: {str(e)}")
        return False
    finally:
        db_session.close()


def unlock_levels_up_to(session_id: str, target_level: float) -> bool:
    """
    Unlock all levels up to but NOT including the target level for URL navigation.
    This is used by developers to jump to specific levels without playing through all previous levels.
    
    Args:
        session_id: Session ID
        target_level: The level to unlock prerequisites for (e.g., 5 will unlock levels 0, 1, 2, 3, 4 but NOT 5)
        
    Returns:
        bool: True if successful, False otherwise
    """
    from config import LEVEL_TO_SCENARIO_MAPPING
    
    db_session = get_database_session()
    
    try:
        # Get all levels that should be unlocked (before target_level)
        levels_to_unlock = []
        for level in LEVEL_TO_SCENARIO_MAPPING.keys():
            if level < target_level:  # Changed from <= to < 
                levels_to_unlock.append(level)
        
        # Sort levels to unlock them in order
        levels_to_unlock.sort()
        
        # Get currently completed levels
        existing_completions = db_session.query(SessionLevelCompletion).filter(
            SessionLevelCompletion.session_id == session_id
        ).all()
        
        existing_levels = {comp.level for comp in existing_completions}
        
        # Add completion records for missing levels
        for level in levels_to_unlock:
            if level not in existing_levels:
                new_completion = SessionLevelCompletion(
                    session_id=session_id,
                    level=level
                )
                db_session.add(new_completion)
        
        db_session.commit()
        logger.info(f"Unlocked prerequisite levels (before {target_level}) for session {session_id}")
        return True
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to unlock prerequisite levels for {target_level}: {str(e)}")
        return False
    finally:
        db_session.close()


def get_conversation_history(session_id: str, level: float) -> List[Dict[str, Any]]:
    """
    Get conversation history for a multi-turn level.
    
    Args:
        session_id: Session ID
        level: Level number
        
    Returns:
        List of dictionaries containing conversation history
    """
    db_session = get_database_session()
    
    try:
        # Get all submissions for this session and level, ordered by turn
        submissions = db_session.query(SessionEmailSubmission).filter_by(
            session_id=session_id, level=level
        ).order_by(SessionEmailSubmission.turn_number).all()
        
        conversation = []
        for submission in submissions:
            # Get evaluation result if it exists
            evaluation = db_session.query(EvaluationResult).filter_by(
                submission_id=submission.id
            ).first()
            
            turn_data = {
                'turn_number': submission.turn_number,
                'email_content': submission.email_content,
                'submitted_at': submission.submitted_at,
                'evaluation_result': evaluation.evaluation_text if evaluation else None,
                'recipient_reply': evaluation.recipient_reply if evaluation else None,
                'goal_achieved': evaluation.goal_achieved if evaluation else None,
                'rubric': evaluation.rubric if evaluation else None
            }
            conversation.append(turn_data)
            
        return conversation
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return []
    finally:
        db_session.close()


def get_next_turn_number(session_id: str, level: float) -> int:
    """
    Get the next turn number for a multi-turn level.
    
    Args:
        session_id: Session ID
        level: Level number
        
    Returns:
        int: Next turn number
    """
    db_session = get_database_session()
    
    try:
        # Get the highest turn number for this session and level
        max_turn = db_session.query(SessionEmailSubmission.turn_number).filter_by(
            session_id=session_id, level=level
        ).order_by(SessionEmailSubmission.turn_number.desc()).first()
        
        if max_turn:
            return max_turn[0] + 1
        else:
            return 1
            
    except Exception as e:
        logger.error(f"Error getting next turn number: {e}")
        return 1
    finally:
        db_session.close()


def is_level_complete_multi_turn(session_id: str, level: float) -> bool:
    """
    Check if a multi-turn level is complete by checking the level completion table.
    This ensures consistency with the level invalidation logic.
    
    Args:
        session_id: Session ID
        level: Level number
        
    Returns:
        bool: True if level is complete, False otherwise
    """
    db_session = get_database_session()
    
    try:
        # Check if level is in the completion table (respects level invalidation)
        completion = db_session.query(SessionLevelCompletion).filter_by(
            session_id=session_id,
            level=level
        ).first()
        
        return completion is not None
        
    except Exception as e:
        logger.error(f"Error checking multi-turn level completion: {e}")
        return False
    finally:
        db_session.close()


def get_leaderboard_data() -> List[Dict[str, Any]]:
    """
    Get leaderboard data for players who completed all levels.
    
    Returns:
        List of dictionaries containing leaderboard data sorted by completion time
    """
    from config import LEVEL_TO_SCENARIO_MAPPING
    
    db_session = get_database_session()
    
    try:
        # Get all required levels for completion
        required_levels = set(LEVEL_TO_SCENARIO_MAPPING.keys())
        
        # Find sessions that have completed all required levels
        completed_sessions = []
        
        # Get all sessions
        all_sessions = db_session.query(GameSession).all()
        
        for session in all_sessions:
            # Get all completed levels for this session
            completions = db_session.query(SessionLevelCompletion).filter_by(
                session_id=session.session_id
            ).all()
            
            completed_levels = {comp.level for comp in completions}
            
            # Check if this session completed all required levels
            if required_levels.issubset(completed_levels):
                # Find the completion time (when they finished the last level)
                last_completion = db_session.query(SessionLevelCompletion).filter_by(
                    session_id=session.session_id
                ).order_by(SessionLevelCompletion.first_completed_at.desc()).first()
                
                # Calculate total playtime (from session creation to last level completion)
                total_time = None
                if last_completion:
                    total_time = last_completion.first_completed_at - session.created_at
                
                # Count total email submissions across all levels
                total_submissions = db_session.query(SessionEmailSubmission).filter_by(
                    session_id=session.session_id
                ).count()
                
                completed_sessions.append({
                    'session_id': session.session_id,
                    'completed_at': last_completion.first_completed_at if last_completion else session.created_at,
                    'total_time': total_time,
                    'total_submissions': total_submissions,
                    'levels_completed': len(completed_levels)
                })
        
        # Sort by completion time (fastest first)
        completed_sessions.sort(key=lambda x: x['completed_at'])
        
        return completed_sessions
        
    except Exception as e:
        logger.error(f"Error getting leaderboard data: {e}")
        return []
    finally:
        db_session.close()


def is_game_complete(session_id: str) -> bool:
    """
    Check if a player has completed the entire game (all levels).
    
    Level 3.5 is conditional - only required if the player actually accessed it.
    Core required levels are: 0, 1, 2, 3, 4, 5
    
    Args:
        session_id: Session ID to check
        
    Returns:
        bool: True if all levels are completed, False otherwise
    """
    from config import LEVEL_TO_SCENARIO_MAPPING
    
    db_session = get_database_session()
    
    try:
        # Get all completed levels for this session
        completions = db_session.query(SessionLevelCompletion).filter_by(
            session_id=session_id
        ).all()
        
        completed_levels = {comp.level for comp in completions}
        
        # Core required levels (excluding conditional level 3.5)
        core_required_levels = {0, 1, 2, 3, 4, 5}
        
        # Check if all core levels are completed
        core_completed = core_required_levels.issubset(completed_levels)
        
        # If player accessed level 3.5, it must also be completed
        level_3_5_requirement_met = True
        if 3.5 in completed_levels:
            # Player accessed level 3.5, so it's considered required
            level_3_5_requirement_met = True
        else:
            # Player didn't access level 3.5, check if they should have
            # If player has level 3 and 4 completed, they took direct path
            level_3_5_requirement_met = (3 in completed_levels and 4 in completed_levels)
        
        return core_completed and level_3_5_requirement_met
        
    except Exception as e:
        logger.error(f"Error checking game completion: {e}")
        return False
    finally:
        db_session.close()


def clear_level_data(session_id: str, level: float) -> bool:
    """
    Clear all data for a specific level (submissions, evaluations, completion).
    Used for restarting levels like Level 4 after max turns reached.
    
    Args:
        session_id: Session ID
        level: Level number to clear
        
    Returns:
        bool: True if successful, False otherwise
    """
    db_session = get_database_session()
    
    try:
        # Remove level completion
        db_session.query(SessionLevelCompletion).filter(
            SessionLevelCompletion.session_id == session_id,
            SessionLevelCompletion.level == level
        ).delete()
        
        # Get all submissions for this level
        submissions = db_session.query(SessionEmailSubmission).filter(
            SessionEmailSubmission.session_id == session_id,
            SessionEmailSubmission.level == level
        ).all()
        
        # Delete evaluation results for these submissions
        for submission in submissions:
            db_session.query(EvaluationResult).filter_by(
                submission_id=submission.id
            ).delete()
        
        # Delete the submissions themselves
        db_session.query(SessionEmailSubmission).filter(
            SessionEmailSubmission.session_id == session_id,
            SessionEmailSubmission.level == level
        ).delete()
        
        db_session.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error clearing level {level} data: {e}")
        db_session.rollback()
        return False
    finally:
        db_session.close() 


def update_turn_and_clear_future(session_id: str, level: float, turn_number: int, new_email_content: str) -> bool:
    """
    Update a turn's email content and clear all future turns.
    This enables users to edit previous emails and continue from that point.
    
    Args:
        session_id: Session ID
        level: Level number
        turn_number: Turn to update
        new_email_content: New email content for the turn
        
    Returns:
        bool: True if successful, False otherwise
    """
    db_session = get_database_session()
    
    try:
        # Step 1: Update the email content for the specified turn
        target_submission = db_session.query(SessionEmailSubmission).filter(
            SessionEmailSubmission.session_id == session_id,
            SessionEmailSubmission.level == level,
            SessionEmailSubmission.turn_number == turn_number
        ).first()
        
        if target_submission:
            target_submission.email_content = new_email_content
            target_submission.submitted_at = datetime.utcnow()  # Update timestamp
        else:
            logger.error(f"Turn {turn_number} not found for session {session_id}, level {level}")
            return False
        
        # Step 2: Get all submissions for future turns (turn_number > specified turn)
        future_submissions = db_session.query(SessionEmailSubmission).filter(
            SessionEmailSubmission.session_id == session_id,
            SessionEmailSubmission.level == level,
            SessionEmailSubmission.turn_number > turn_number
        ).all()
        
        # Step 3: Delete evaluation results for future turns
        for submission in future_submissions:
            db_session.query(EvaluationResult).filter_by(
                submission_id=submission.id
            ).delete()
        
        # Step 4: Delete future turn submissions
        db_session.query(SessionEmailSubmission).filter(
            SessionEmailSubmission.session_id == session_id,
            SessionEmailSubmission.level == level,
            SessionEmailSubmission.turn_number > turn_number
        ).delete()
        
        # Step 5: Remove level completion if it exists (since we're invalidating future turns)
        db_session.query(SessionLevelCompletion).filter(
            SessionLevelCompletion.session_id == session_id,
            SessionLevelCompletion.level == level
        ).delete()
        
        db_session.commit()
        logger.info(f"Updated turn {turn_number} and cleared future turns for session {session_id}, level {level}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating turn and clearing future: {e}")
        db_session.rollback()
        return False
    finally:
        db_session.close() 