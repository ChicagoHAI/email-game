"""
Database Package

This package contains all database-related modules for the Email Game application.
"""

from .models import *
from .connection import get_database_engine, create_tables 