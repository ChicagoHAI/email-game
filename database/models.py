"""
Database Models

SQLAlchemy models for the Email Game application using session-based tracking.
Implements a dual-tracking approach:
- session_email_submissions: Immutable history of all attempts
- session_level_completions: Current completion status (mutable)
"""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class GameSession(Base):
    """
    Represents a game session identified by UUID.
    Stores session-level configuration and metadata.
    """
    __tablename__ = 'game_sessions'
    
    session_id = Column(String(36), primary_key=True)  # UUID
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    current_level = Column(Integer, default=0)
    use_rubric = Column(Boolean, default=False)
    
    # Relationships
    email_submissions = relationship("SessionEmailSubmission", back_populates="session")
    level_completions = relationship("SessionLevelCompletion", back_populates="session")
    
    def __repr__(self):
        return f"<GameSession(session_id='{self.session_id}', current_level={self.current_level})>"


class SessionEmailSubmission(Base):
    """
    Immutable history table - records every single email attempt.
    Never deleted, provides complete audit trail.
    """
    __tablename__ = 'session_email_submissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('game_sessions.session_id'), nullable=False)
    level = Column(Integer, nullable=False)
    email_content = Column(Text, nullable=False)
    goal_achieved = Column(Boolean, nullable=True)  # Null until evaluated
    submitted_at = Column(DateTime, default=datetime.utcnow)
    turn_number = Column(Integer, default=1)  # Track turn number for multi-turn levels
    
    # Relationship
    session = relationship("GameSession", back_populates="email_submissions")
    evaluation_result = relationship("EvaluationResult", back_populates="submission", uselist=False)
    
    def __repr__(self):
        return f"<SessionEmailSubmission(id={self.id}, session_id='{self.session_id}', level={self.level}, goal_achieved={self.goal_achieved})>"


class SessionLevelCompletion(Base):
    """
    Current completion status - mirrors st.session_state.completed_levels.
    Gets modified when users succeed/fail, represents "what's unlocked now".
    """
    __tablename__ = 'session_level_completions'
    
    session_id = Column(String(36), ForeignKey('game_sessions.session_id'), primary_key=True)
    level = Column(Integer, primary_key=True)
    first_completed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    session = relationship("GameSession", back_populates="level_completions")
    
    def __repr__(self):
        return f"<SessionLevelCompletion(session_id='{self.session_id}', level={self.level})>"


class EvaluationResult(Base):
    """
    Stores AI evaluation results for email submissions.
    Linked to specific submission attempts.
    """
    __tablename__ = 'evaluation_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey('session_email_submissions.id'), nullable=False)
    evaluation_text = Column(Text)
    recipient_reply = Column(Text)
    rubric = Column(Text)
    goal_achieved = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    submission = relationship("SessionEmailSubmission", back_populates="evaluation_result")
    
    def __repr__(self):
        return f"<EvaluationResult(id={self.id}, submission_id={self.submission_id}, goal_achieved={self.goal_achieved})>" 