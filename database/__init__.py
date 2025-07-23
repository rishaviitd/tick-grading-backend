"""
Database Module for TickAI Backend

This module provides MongoDB integration for storing CBSE processing pipeline results.
"""

from .schema import (
    PipelineResult, DiagramExtractionResult, DiagramMappingResult,
    QuestionExtractionResult, MarksMappingResult, ProcessingStep,
    DiagramMappingEntry, MarksMappingEntry, COLLECTION_NAMES, INDEXES
)

from .connection import (
    DatabaseManager, PipelineDatabase, db_manager, pipeline_db,
    initialize_database, close_database
)

from .integration import (
    PipelineDatabaseIntegration, db_integration, get_db_integration,
    save_logs_to_database
)

__all__ = [
    # Schema classes
    "PipelineResult",
    "DiagramExtractionResult", 
    "DiagramMappingResult",
    "QuestionExtractionResult",
    "MarksMappingResult",
    "ProcessingStep",
    "DiagramMappingEntry",
    "MarksMappingEntry",
    "COLLECTION_NAMES",
    "INDEXES",
    
    # Connection classes
    "DatabaseManager",
    "PipelineDatabase",
    "db_manager",
    "pipeline_db",
    "initialize_database",
    "close_database",
    
    # Integration classes
    "PipelineDatabaseIntegration",
    "db_integration",
    "get_db_integration",
    "save_logs_to_database"
] 