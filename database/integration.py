"""
Database Integration for TickAI Pipeline

This module provides functions to integrate database operations with the existing
CBSE processing pipeline, allowing automatic saving of results to MongoDB.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json

from .connection import pipeline_db, initialize_database
from .schema import (
    PipelineResult, DiagramExtractionResult, DiagramMappingResult,
    QuestionExtractionResult, MarksMappingResult, ProcessingStep,
    DiagramMappingEntry, MarksMappingEntry
)


class PipelineDatabaseIntegration:
    """Integrates database operations with the processing pipeline"""
    
    def __init__(self):
        self.db_initialized = False
        self.current_run_id: Optional[str] = None
        self.pipeline_data: Dict[str, Any] = {}
    
    async def initialize(self) -> bool:
        """Initialize database connection"""
        if not self.db_initialized:
            self.db_initialized = await initialize_database()
        return self.db_initialized
    
    async def start_pipeline(self, run_id: str, title: str, filename: str, file_size: Optional[int] = None) -> bool:
        """Start a new pipeline and save initial data"""
        if not await self.initialize():
            return False
        
        self.current_run_id = run_id
        
        # Create initial pipeline result
        pipeline_result = PipelineResult(
            run_id=run_id,
            title=title,
            log_type="question_extraction",
            status="active",
            original_filename=filename,
            file_size=file_size,
            steps=[],
            step_results={},
            final_outputs={},
            errors=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        success = await pipeline_db.save_pipeline_result(pipeline_result)
        if success:
            self.pipeline_data = pipeline_result.dict()
        
        return success
    
    async def save_step_log(self, step_name: str, input_data: str, output_data: str) -> bool:
        """Save a processing step log"""
        if not self.current_run_id:
            return False
        
        # Create processing step
        step = ProcessingStep(
            name=step_name,
            timestamp=datetime.utcnow(),
            input=input_data,
            output=output_data
        )
        
        # Add to pipeline data
        if "steps" not in self.pipeline_data:
            self.pipeline_data["steps"] = []
        self.pipeline_data["steps"].append(step.dict())
        
        # Update in database
        return await self._update_pipeline_data()
    
    async def save_step_result(self, step_name: str, step_data: Dict[str, Any]) -> bool:
        """Save detailed step results"""
        if not self.current_run_id:
            return False
        
        # Add to pipeline data
        if "step_results" not in self.pipeline_data:
            self.pipeline_data["step_results"] = {}
        self.pipeline_data["step_results"][step_name] = step_data
        
        # Update in database
        return await self._update_pipeline_data()
    
    async def save_diagram_extraction_result(self, run_id: str, total_figures: int, pages_processed: int, 
                                     figure_files: List[str], overview_image_path: Optional[str] = None) -> bool:
        """Save diagram extraction results"""
        if not await self.initialize():
            return False
        
        extraction_result = DiagramExtractionResult(
            run_id=run_id,
            total_figures=total_figures,
            pages_processed=pages_processed,
            extraction_success=True,
            figure_files=figure_files,
            overview_image_path=overview_image_path,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return await pipeline_db.save_diagram_extraction(extraction_result)
    
    async def save_diagram_mapping_result(self, run_id: str, mapping_json: Dict[str, Any], 
                                  raw_response: Optional[str] = None) -> bool:
        """Save diagram mapping results"""
        if not await self.initialize():
            return False
        
        # Convert mapping JSON to proper format
        mapping_entries = {}
        for figure_key, mapping_data in mapping_json.items():
            entry = DiagramMappingEntry(
                question_identifier=mapping_data.get("question_identifier", ""),
                choice_location=mapping_data.get("choice_location", "null"),
                cloudinary_url=mapping_data.get("cloudinary_url", "")
            )
            mapping_entries[figure_key] = entry
        
        mapping_result = DiagramMappingResult(
            run_id=run_id,
            mapping=mapping_entries,
            total_mappings=len(mapping_entries),
            mapping_success=True,
            raw_response=raw_response,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return await pipeline_db.save_diagram_mapping(mapping_result)
    
    async def save_question_extraction_result(self, run_id: str, questions_markdown: str, 
                                      markdown_file_path: Optional[str] = None,
                                      raw_response: Optional[str] = None) -> bool:
        """Save question extraction results"""
        if not await self.initialize():
            return False
        
        # Count questions (simple count of [####] markers)
        questions_count = questions_markdown.count("[####]")
        
        extraction_result = QuestionExtractionResult(
            run_id=run_id,
            questions_markdown=questions_markdown,
            questions_count=questions_count,
            content_length=len(questions_markdown),
            extraction_success=True,
            raw_response=raw_response,
            markdown_file_path=markdown_file_path,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return await pipeline_db.save_question_extraction(extraction_result)
    
    async def save_marks_mapping_result(self, run_id: str, marks_json: Dict[str, Any],
                                raw_response: Optional[str] = None) -> bool:
        """Save marks mapping results"""
        if not await self.initialize():
            return False
        
        # Convert marks JSON to proper format
        marks_entries = {}
        for question_key, marks_data in marks_json.items():
            entry = MarksMappingEntry(
                question_type=marks_data.get("question_type", ""),
                marks=marks_data.get("marks", "")
            )
            marks_entries[question_key] = entry
        
        mapping_result = MarksMappingResult(
            run_id=run_id,
            marks_mapping=marks_entries,
            total_questions=len(marks_entries),
            mapping_success=True,
            raw_response=raw_response,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return await pipeline_db.save_marks_mapping(mapping_result)
    
    async def save_final_outputs(self, final_outputs: Dict[str, Any]) -> bool:
        """Save final pipeline outputs"""
        if not self.current_run_id:
            return False
        
        # Add to pipeline data
        self.pipeline_data["final_outputs"] = final_outputs
        
        # Update in database
        return await self._update_pipeline_data()
    
    async def add_error(self, error_message: str) -> bool:
        """Add error to pipeline"""
        if not self.current_run_id:
            return False
        
        # Add to pipeline data
        if "errors" not in self.pipeline_data:
            self.pipeline_data["errors"] = []
        self.pipeline_data["errors"].append(error_message)
        
        # Update in database
        return await self._update_pipeline_data()
    
    async def complete_pipeline(self, success: bool = True) -> bool:
        """Mark pipeline as completed"""
        if not self.current_run_id:
            return False
        
        status = "completed" if success else "failed"
        return await pipeline_db.update_pipeline_status(self.current_run_id, status)
    
    async def _update_pipeline_data(self) -> bool:
        """Update pipeline data in database"""
        if not self.current_run_id:
            return False
        
        try:
            # Update the pipeline document with new data
            collection = pipeline_db.db_manager.get_collection("pipeline_results")
            if collection is None:
                return False
            
            # Update only the fields that have changed
            update_data = {
                "updated_at": datetime.utcnow()
            }
            
            if "steps" in self.pipeline_data:
                update_data["steps"] = self.pipeline_data["steps"]
            if "step_results" in self.pipeline_data:
                update_data["step_results"] = self.pipeline_data["step_results"]
            if "final_outputs" in self.pipeline_data:
                update_data["final_outputs"] = self.pipeline_data["final_outputs"]
            if "errors" in self.pipeline_data:
                update_data["errors"] = self.pipeline_data["errors"]
            
            result = await collection.update_one(
                {"run_id": self.current_run_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Failed to update pipeline data: {e}")
            return False


# Global integration instance
db_integration = PipelineDatabaseIntegration()


def get_db_integration() -> PipelineDatabaseIntegration:
    """Get the global database integration instance"""
    return db_integration


async def save_logs_to_database(run_id: str, logs_dir: str) -> bool:
    """Legacy function to save existing logs to database"""
    """This function can be used to migrate existing logs to the database"""
    
    if not await db_integration.initialize():
        return False
    
    logs_path = Path(logs_dir)
    metadata_file = logs_path / "metadata.json"
    
    if not metadata_file.exists():
        print(f"Metadata file not found: {metadata_file}")
        return False
    
    try:
        # Read metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Start pipeline
        success = await db_integration.start_pipeline(
            run_id=run_id,
            title=metadata.get("title", "Unknown Pipeline"),
            filename=metadata.get("data", {}).get("filename", "unknown.pdf")
        )
        
        if not success:
            return False
        
        # Save steps
        for step in metadata.get("steps", []):
            await db_integration.save_step_log(
                step_name=step.get("name", ""),
                input_data=step.get("input", ""),
                output_data=step.get("output", "")
            )
        
        # Save step results if available
        step2_file = logs_path / "step2_diagram_mapping" / "step2_diagram_mapping.json"
        if step2_file.exists():
            with open(step2_file, 'r') as f:
                mapping_data = json.load(f)
            await db_integration.save_diagram_mapping_result(run_id, mapping_data)
        
        step3_file = logs_path / "step3_question_extraction" / "step3_questions.md"
        if step3_file.exists():
            with open(step3_file, 'r') as f:
                questions_markdown = f.read()
            await db_integration.save_question_extraction_result(run_id, questions_markdown, str(step3_file))
        
        step4_file = logs_path / "step4_marks_mapping" / "step4_marks_mapping.json"
        if step4_file.exists():
            with open(step4_file, 'r') as f:
                marks_data = json.load(f)
            await db_integration.save_marks_mapping_result(run_id, marks_data)
        
        # Complete pipeline
        await db_integration.complete_pipeline(success=True)
        
        print(f"Successfully migrated logs for run_id: {run_id}")
        return True
        
    except Exception as e:
        print(f"Failed to migrate logs: {e}")
        return False 