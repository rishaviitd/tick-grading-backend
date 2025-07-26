"""
Database Integration for TickAI Pipeline

This module provides functions to integrate database operations with the existing
CBSE processing pipeline, allowing automatic saving of results to MongoDB.
"""

import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .connection import pipeline_db, initialize_database
from .schema import (
    # Core business logic schemas
    Teacher, Student, Assignment, Question, StudentResponse, StudentAssignmentResponse, QuestionResponseMapping,
    
    # Legacy pipeline processing schemas
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
            # Handle marks data that might be a list or string
            marks_value = marks_data.get("marks", "")
            if isinstance(marks_value, list):
                # Already a list, use as is
                marks_list = [str(mark) for mark in marks_value]
            elif isinstance(marks_value, str):
                # Single string, convert to list
                marks_list = [marks_value]
            else:
                # Convert any other type to list
                marks_list = [str(marks_value)]
            
            entry = MarksMappingEntry(
                question_type=marks_data.get("question_type", ""),
                marks=marks_list
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
    
    async def combine_and_save_questions(self, run_id: str, assignment_title: str = None, assignment_marks: int = None) -> bool:
        """Combine data from all steps and save questions to database with assignment"""
        if not await self.initialize():
            return False
        
        try:
            # Get data from all previous steps
            print(f"Retrieving data for question combination: run_id={run_id}")
            question_extraction = await self._get_question_extraction_data(run_id)
            marks_mapping = await self._get_marks_mapping_data(run_id)
            diagram_mapping = await self._get_diagram_mapping_data(run_id)
            
            print(f"Data retrieval results:")
            print(f"  - Question extraction: {'Found' if question_extraction else 'Missing'}")
            print(f"  - Marks mapping: {'Found' if marks_mapping else 'Missing'}")
            print(f"  - Diagram mapping: {'Found' if diagram_mapping else 'Missing'}")
            
            if not question_extraction or not marks_mapping:
                print(f"Missing required data for question combination: run_id={run_id}")
                if not question_extraction:
                    print("  - Question extraction data is missing")
                if not marks_mapping:
                    print("  - Marks mapping data is missing")
                return False
            
            # Create assignment first
            assignment_id = await self.create_assignment(run_id, assignment_title, assignment_marks)
            if not assignment_id:
                print(f"Failed to create assignment for run_id: {run_id}")
                return False
            
            print(f"Created assignment with ID: {assignment_id}")
            
            # Parse questions from markdown
            questions = self._parse_questions_from_markdown(question_extraction["questions_markdown"])
            
            # Combine and save each question with assignment
            saved_count = 0
            question_ids = []
            combined_questions = []
            
            for question_data in questions:
                combined_question = self._combine_question_data(
                    question_data, marks_mapping, diagram_mapping, run_id, assignment_id
                )
                if combined_question:
                    # Save question using the new method that includes assignment_id
                    question_id = await self.save_question_with_assignment(
                        combined_question.dict(by_alias=True), assignment_id, run_id
                    )
                    if question_id:
                        saved_count += 1
                        question_ids.append(question_id)
                        combined_questions.append(combined_question.dict(by_alias=True))
            
            # Update assignment with question IDs
            if question_ids:
                await self.update_assignment_questions(assignment_id, question_ids)
                print(f"Updated assignment {assignment_id} with {len(question_ids)} questions")
            
            # Save to logs folder using the logger
            if combined_questions:
                import sys
                import os
                # Add the project root to the path for absolute import
                project_root = os.path.join(os.path.dirname(__file__), '..')
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                from app.logging.logger import UnifiedLogger
                logger = UnifiedLogger()
                logger.save_combined_questions(run_id, combined_questions)
            
            print(f"Successfully combined and saved {saved_count} questions for run_id={run_id}")
            return saved_count > 0
            
        except Exception as e:
            print(f"Error combining questions: {e}")
            return False
    
    async def _get_question_extraction_data(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get question extraction data from database"""
        try:
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["question_extraction"])
            if collection is None:
                print(f"Question extraction collection not found for run_id: {run_id}")
                return None
            
            doc = await collection.find_one({"run_id": run_id})
            if doc:
                print(f"Found question extraction data for run_id: {run_id}")
                return {
                    "questions_markdown": doc.get("questions_markdown", ""),
                    "questions_count": doc.get("questions_count", 0)
                }
            else:
                print(f"No question extraction data found for run_id: {run_id}")
            return None
        except Exception as e:
            print(f"Error getting question extraction data: {e}")
            return None
    
    async def _get_marks_mapping_data(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get marks mapping data from database"""
        try:
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["marks_mapping"])
            if collection is None:
                print(f"Marks mapping collection not found for run_id: {run_id}")
                return None
            
            doc = await collection.find_one({"run_id": run_id})
            if doc and "marks_mapping" in doc:
                print(f"Found marks mapping data for run_id: {run_id}")
                return doc["marks_mapping"]
            else:
                print(f"No marks mapping data found for run_id: {run_id}")
            return None
        except Exception as e:
            print(f"Error getting marks mapping data: {e}")
            return None
    
    async def _get_diagram_mapping_data(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get diagram mapping data from database"""
        try:
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["diagram_mapping"])
            if collection is None:
                return None
            
            doc = await collection.find_one({"run_id": run_id})
            if doc and "mapping" in doc:
                return doc["mapping"]
            return None
        except Exception as e:
            print(f"Error getting diagram mapping data: {e}")
            return None
    
    def _parse_questions_from_markdown(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Parse questions from markdown content"""
        from app.utils.identifier_normalizer import normalize_identifier
        
        questions = []
        
        # Split by [####] to get individual questions
        question_chunks = markdown_content.split("[####]")
        
        question_number = 1  # Start from 1 for actual questions
        for chunk in question_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            
            # Create identifier and normalize it (strip ANS- prefix for internal use)
            raw_identifier = f"ANS-{question_number}"
            question_identifier = normalize_identifier(raw_identifier)
            
            # Check for internal choice (we'll determine case study later from marks mapping)
            if "[%OR%]" in chunk:
                # Internal choice: split by [%OR%]
                parts = chunk.split("[%OR%]")
                primary_question = parts[0].strip()
                secondary_question = parts[1].strip() if len(parts) > 1 else None
                
                questions.append({
                    "question_identifier": question_identifier,
                    "has_internal_choice": True,
                    "primary_question": primary_question,
                    "secondary_question": secondary_question
                })
            else:
                # No internal choice
                questions.append({
                    "question_identifier": question_identifier,
                    "has_internal_choice": False,
                    "primary_question": chunk,
                    "secondary_question": None
                })
            
            question_number += 1  # Increment for next question
        
        return questions
    

    
    def _combine_question_data(self, question_data: Dict[str, Any], 
                              marks_mapping: Dict[str, Any], 
                              diagram_mapping: Dict[str, Any],
                              run_id: str, assignment_id: str) -> Optional[Question]:
        """Combine question data with marks and diagram mapping"""
        from app.utils.identifier_normalizer import normalize_identifier
        
        try:
            # Normalize the question identifier
            question_identifier = normalize_identifier(question_data["question_identifier"])
            question_key = f"question-{question_identifier}"
            
            # Get marks data
            marks_data = marks_mapping.get(question_key, {})
            question_type = marks_data.get("question_type", "Unknown")
            marks = marks_data.get("marks", "")
            
            # Determine if it's actually a case study (override the text-based detection)
            is_case_study = question_type.lower() == "case study"
            
            # Adjust has_internal_choice based on question type
            has_internal_choice = question_data["has_internal_choice"]
            if is_case_study:
                has_internal_choice = False
                # For case study, reconstruct the full question text including [%OR%]
                if question_data["secondary_question"]:
                    primary_question = f"{question_data['primary_question']}\n[%OR%]\n{question_data['secondary_question']}"
                else:
                    primary_question = question_data["primary_question"]
            else:
                primary_question = question_data["primary_question"]
            
            # Process marks
            primary_marks, secondary_marks = self._process_marks(marks, has_internal_choice)
            
            # Process diagrams
            primary_diagram_url, secondary_diagram_url = self._process_diagrams(
                question_identifier, diagram_mapping, has_internal_choice
            )
            
            # Create Question object
            question = Question(
                assignment_id=assignment_id,
                run_id=run_id,
                question_identifier=question_identifier,
                has_internal_choice=has_internal_choice,
                primary_question=primary_question,
                secondary_question=None if is_case_study else question_data["secondary_question"],
                primary_diagram_url=primary_diagram_url,
                secondary_diagram_url=secondary_diagram_url,
                table_url=None,  # Currently null as mentioned
                primary_marks=primary_marks,
                secondary_marks=secondary_marks,
                question_type=question_type,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return question
            
        except Exception as e:
            print(f"Error combining question data: {e}")
            return None
    
    def _process_marks(self, marks: List[str], has_internal_choice: bool) -> Tuple[str, Optional[str]]:
        """Process marks list into primary and secondary marks"""
        if not has_internal_choice:
            # For non-internal choice, return the first mark as primary
            return marks[0] if marks else "", None
        
        # For internal choice, return first and second marks
        if len(marks) >= 2:
            return marks[0], marks[1]
        elif len(marks) == 1:
            # Only one mark available, use as primary
            return marks[0], None
        else:
            # No marks available
            return "", None
    
    def _process_diagrams(self, question_identifier: str, diagram_mapping: Dict[str, Any], 
                         has_internal_choice: bool) -> Tuple[Optional[str], Optional[str]]:
        """Process diagram mapping for a question"""
        from app.utils.identifier_normalizer import normalize_identifier
        
        primary_diagram_url = None
        secondary_diagram_url = None
        
        # Find diagrams for this question (normalize both identifiers for comparison)
        normalized_question_id = normalize_identifier(question_identifier)
        for figure_key, figure_data in diagram_mapping.items():
            figure_question_id = normalize_identifier(figure_data.get("question_identifier", ""))
            if figure_question_id == normalized_question_id:
                cloudinary_url = figure_data.get("cloudinary_url")
                choice_location = figure_data.get("choice_location", "null")
                
                if choice_location == "null" or not has_internal_choice:
                    # Diagram applies to entire question or no internal choice
                    primary_diagram_url = cloudinary_url
                elif choice_location == "first":
                    primary_diagram_url = cloudinary_url
                elif choice_location == "second":
                    secondary_diagram_url = cloudinary_url
        
        return primary_diagram_url, secondary_diagram_url
    

    
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
    
    # =============================================================================
    # CORE BUSINESS LOGIC METHODS
    # =============================================================================
    
    async def create_teacher(self, name: str, class_name: str, board: str) -> Optional[str]:
        """Create a new teacher and return the teacher ID"""
        if not await self.initialize():
            return None
        
        try:
            teacher = Teacher(
                name=name,
                class_name=class_name,
                board=board,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            success = await pipeline_db.save_teacher(teacher)
            if success:
                return str(teacher.id)
            return None
            
        except Exception as e:
            print(f"Error creating teacher: {e}")
            return None
    
    async def create_student(self, name: str) -> Optional[str]:
        """Create a new student and return the student ID"""
        if not await self.initialize():
            return None
        
        try:
            student = Student(
                name=name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            success = await pipeline_db.save_student(student)
            if success:
                return str(student.id)
            return None
            
        except Exception as e:
            print(f"Error creating student: {e}")
            return None
    
    async def create_assignment(self, run_id: str, title: str = None, total_marks: int = None) -> Optional[str]:
        """Create a new assignment and return the assignment ID"""
        if not await self.initialize():
            return None
        
        try:
            # Use default values if not provided
            if title is None:
                title = f"Assignment {run_id}"
            if total_marks is None:
                total_marks = 100
            
            assignment = Assignment(
                run_id=run_id,
                title=title,
                total_marks=total_marks,
                questions=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            assignment_id = await pipeline_db.save_assignment(assignment)
            return assignment_id
            
        except Exception as e:
            print(f"Error creating assignment: {e}")
            return None
    
    async def save_question_with_assignment(self, question_data: Dict[str, Any], assignment_id: str, run_id: str) -> Optional[str]:
        """Save a question with assignment_id and return the question ID"""
        if not await self.initialize():
            return None
        
        try:
            question = Question(
                assignment_id=assignment_id,
                run_id=run_id,
                question_identifier=question_data["question_identifier"],
                has_internal_choice=question_data["has_internal_choice"],
                primary_question=question_data["primary_question"],
                secondary_question=question_data.get("secondary_question"),
                primary_diagram_url=question_data.get("primary_diagram_url"),
                secondary_diagram_url=question_data.get("secondary_diagram_url"),
                table_url=question_data.get("table_url"),
                primary_marks=question_data["primary_marks"],
                secondary_marks=question_data.get("secondary_marks"),
                question_type=question_data["question_type"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            question_id = await pipeline_db.save_question(question)
            return question_id
            
        except Exception as e:
            print(f"Error saving question: {e}")
            return None
    
    async def update_assignment_questions(self, assignment_id: str, question_ids: List[str]) -> bool:
        """Update the questions array in an assignment"""
        if not await self.initialize():
            return False
        
        try:
            success = await pipeline_db.update_assignment_questions(assignment_id, question_ids)
            return success
            
        except Exception as e:
            print(f"Error updating assignment questions: {e}")
            return False
    
    async def save_student_assignment_response(self, student_id: str, assignment_id: str, 
                                             run_id: str, student_responses: List[StudentResponse]) -> Optional[str]:
        """Save student assignment response and return the response ID"""
        if not await self.initialize():
            return None
        
        try:
            response = StudentAssignmentResponse(
                student_id=student_id,
                assignment_id=assignment_id,
                run_id=run_id,
                student_responses=student_responses,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            success = await pipeline_db.save_student_assignment_response(response)
            if success:
                return str(response.id)
            return None
            
        except Exception as e:
            print(f"Error saving student assignment response: {e}")
            return None
    
    async def create_question_response_mapping(self, student_id: str, assignment_id: str, run_id: str,
                                             question_data: Dict[str, Any], response_url: str) -> Optional[str]:
        """Create a question response mapping and return the mapping ID"""
        if not await self.initialize():
            return None
        
        try:
            mapping = QuestionResponseMapping(
                student_id=student_id,
                assignment_id=assignment_id,
                run_id=run_id,
                question_identifier=question_data["question_identifier"],
                has_internal_choice=question_data["has_internal_choice"],
                primary_question=question_data["primary_question"],
                secondary_question=question_data.get("secondary_question"),
                primary_diagram_url=question_data.get("primary_diagram_url"),
                secondary_diagram_url=question_data.get("secondary_diagram_url"),
                table_url=question_data.get("table_url"),
                primary_marks=question_data["primary_marks"],
                secondary_marks=question_data.get("secondary_marks"),
                question_type=question_data["question_type"],
                response_cloudinary_url=response_url,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Save mapping and get the inserted ID
            mapping_id = await pipeline_db.save_question_response_mapping(mapping)
            return mapping_id
            
        except Exception as e:
            print(f"Error creating question response mapping: {e}")
            return None


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