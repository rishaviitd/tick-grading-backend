"""
Database Module for TickAI Backend

This module provides MongoDB integration for storing CBSE processing pipeline results.
"""

from .schema import (
    # Core business logic schemas
    Teacher, Student, Assignment, Question, StudentResponse, StudentAssignmentResponse, QuestionResponseMapping,
    Diagram, Table, VisualContent,
    
    # Collection names
    COLLECTION_NAMES
)

from .connection import (
    DatabaseManager, PipelineDatabase, db_manager, pipeline_db,
    initialize_database, close_database
)

from .integration import (
    DatabaseIntegration, db_integration, get_db_integration
)

__all__ = [
    # Core business logic schemas
    "Teacher",
    "Student", 
    "Assignment",
    "Question",
    "StudentResponse",
    "StudentAssignmentResponse",
    "QuestionResponseMapping",
    "Diagram",
    "Table",
    "VisualContent",
    
    # Collection names
    "COLLECTION_NAMES",
    
    # Connection classes
    "DatabaseManager",
    "PipelineDatabase",
    "db_manager",
    "pipeline_db",
    "initialize_database",
    "close_database",
    
    # Integration classes
    "DatabaseIntegration",
    "db_integration",
    "get_db_integration"
] 