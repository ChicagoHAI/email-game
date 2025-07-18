"""
Database Connection

Handles SQLite database connection, engine creation, and table initialization
for the Email Game application.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_FILENAME = "email_game.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILENAME}"

# Global variables
_engine = None
_SessionLocal = None


def get_database_engine():
    """
    Get or create the SQLAlchemy database engine.
    
    Returns:
        sqlalchemy.engine.Engine: Database engine instance
    """
    global _engine
    
    if _engine is None:
        # Create engine with SQLite-specific optimizations
        _engine = create_engine(
            DATABASE_URL,
            echo=False,  # Set to True for SQL debugging
            connect_args={
                "check_same_thread": False,  # Allow sharing across threads
                "timeout": 30  # 30 second timeout for database locks
            }
        )
        logger.info(f"Created database engine: {DATABASE_URL}")
    
    return _engine


def get_session_factory():
    """
    Get or create the SQLAlchemy session factory.
    
    Returns:
        sessionmaker: Session factory for creating database sessions
    """
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_database_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Created session factory")
    
    return _SessionLocal


def create_tables():
    """
    Create all database tables if they don't exist.
    This is safe to call multiple times.
    """
    engine = get_database_engine()
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        return False


def get_database_session():
    """
    Get a new database session for performing operations.
    
    Returns:
        sqlalchemy.orm.Session: Database session instance
        
    Example usage:
        session = get_database_session()
        try:
            # Perform database operations
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    """
    SessionLocal = get_session_factory()
    return SessionLocal()


def add_turn_number_column():
    """
    Add the turn_number column to session_email_submissions table.
    This is a migration for multi-turn functionality.
    """
    engine = get_database_engine()
    
    try:
        # Check if column already exists
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = inspector.get_columns('session_email_submissions')
        column_names = [column['name'] for column in columns]
        
        if 'turn_number' not in column_names:
            # Add the column
            with engine.connect() as connection:
                connection.execute(text(
                    "ALTER TABLE session_email_submissions ADD COLUMN turn_number INTEGER DEFAULT 1"
                ))
                connection.commit()
                logger.info("Added turn_number column to session_email_submissions table")
            return True
        else:
            logger.info("turn_number column already exists")
            return True
            
    except Exception as e:
        logger.error(f"Error adding turn_number column: {str(e)}")
        return False


def init_database():
    """
    Initialize the database by creating tables and any required setup.
    Call this once when the application starts.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        # Ensure database directory exists
        db_path = os.path.dirname(os.path.abspath(DATABASE_FILENAME))
        if db_path and not os.path.exists(db_path):
            os.makedirs(db_path)
        
        # Create tables
        if create_tables():
            # Apply migrations
            if add_turn_number_column():
                logger.info("Database initialization completed successfully")
                return True
            else:
                logger.error("Database migration failed")
                return False
        else:
            logger.error("Database initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}")
        return False


def check_database_health():
    """
    Perform a basic health check on the database connection.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        engine = get_database_engine()
        with engine.connect() as connection:
            # Simple query to test connection
            from sqlalchemy import text
            result = connection.execute(text("SELECT 1"))
            return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False 