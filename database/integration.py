"""
Database Integration for TickAI Pipeline

This module provides functions to integrate database operations with the existing
CBSE processing pipeline, allowing automatic saving of results to MongoDB.
"""

import os
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime

from .connection import pipeline_db, initialize_database
from .schema import (
    # Core business logic schemas
    Teacher, Student, Assignment, Question, StudentResponse, StudentAssignmentResponse, QuestionResponseMapping,
    Diagram, Table, VisualContent, QuestionContent
)


class DatabaseIntegration:
    """Integrates database operations with the application"""
    
    def __init__(self):
        self.db_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize database connection"""
        if not self.db_initialized:
            self.db_initialized = await initialize_database()
        return self.db_initialized
    
    async def save_diagram(self, diagram_url: str, diagram_identifier: str, run_id: str) -> Optional[str]:
        """Save a single diagram to the diagrams collection"""
        if not await self.initialize():
            return None
        
        diagram = Diagram(
            diagram_url=diagram_url,
            diagram_identifier=diagram_identifier,
            run_id=run_id
        )
        
        return await pipeline_db.save_diagram(diagram)
    
    async def save_table(self, table_url: str, table_identifier: str, run_id: str) -> Optional[str]:
        """Save a single table to the tables collection"""
        if not await self.initialize():
            return None
        
        table = Table(
            table_url=table_url,
            table_identifier=table_identifier,
            run_id=run_id
        )
        
        return await pipeline_db.save_table(table)
    
    async def save_visual_content(self, tables: List[str] = None, diagrams: List[str] = None,
                                 overview_image_tables: str = None, overview_image_diagrams: str = None) -> Optional[str]:
        """Save visual content to the visual_content collection"""
        if not await self.initialize():
            return None
        
        visual_content = VisualContent(
            tables=tables or [],
            diagrams=diagrams or [],
            overview_image_tables=overview_image_tables,
            overview_image_diagrams=overview_image_diagrams
        )
        
        return await pipeline_db.save_visual_content(visual_content)
    
    async def save_question_content(self, run_id: str, questions_markdown: str, 
                                   extraction_success: bool = True, raw_response: str = None,
                                   parsed_questions: Dict[str, Any] = None) -> Optional[str]:
        """Save question content to the question_content collection"""
        if not await self.initialize():
            return None
        
        try:
            question_content = QuestionContent(
                run_id=run_id,
                questions_markdown=questions_markdown,
                extraction_success=extraction_success,
                raw_response=raw_response,
                questions=parsed_questions.get("questions") if parsed_questions else None,
                total_questions=parsed_questions.get("total_questions") if parsed_questions else None,
                questions_with_internal_choice=parsed_questions.get("questions_with_internal_choice") if parsed_questions else None,
                questions_without_internal_choice=parsed_questions.get("questions_without_internal_choice") if parsed_questions else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return await pipeline_db.save_question_content(question_content)
            
        except Exception as e:
            print(f"Error saving question content: {e}")
            return None
    
    async def save_question_content_with_assignment_update(self, run_id: str, questions_markdown: str, 
                                                          assignment_id: str, extraction_success: bool = True, 
                                                          raw_response: str = None, parsed_questions: Dict[str, Any] = None) -> Optional[str]:
        """Save question content and update assignment with question_content_id"""
        if not await self.initialize():
            return None
        
        try:
            # Save question content
            question_content_id = await self.save_question_content(
                run_id=run_id,
                questions_markdown=questions_markdown,
                extraction_success=extraction_success,
                raw_response=raw_response,
                parsed_questions=parsed_questions
            )
            
            if question_content_id:
                # Update assignment with question_content_id
                success = await self.update_assignment_question_content(assignment_id, question_content_id)
                if success:
                    print(f"  - Assignment updated with question content ID: {question_content_id}")
                else:
                    print(f"  - Failed to update assignment with question content ID: {question_content_id}")
                
                return question_content_id
            else:
                print("  - Failed to save question content")
                return None
                
        except Exception as e:
            print(f"Error saving question content with assignment update: {e}")
            return None
    
    async def save_marks_content(self, run_id: str, marks_mapping: Dict[str, Any], 
                                total_questions: int, mapping_success: bool = True, 
                                raw_response: str = None) -> Optional[str]:
        """Save marks mapping data to the marks_content collection"""
        if not await self.initialize():
            return None
        
        try:
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["marks_content"])
            if collection is None:
                print("Marks content collection not found")
                return None
            
            # Create document for marks_content collection
            marks_content_doc = {
                "run_id": run_id,
                "marks_mapping": marks_mapping,
                "total_questions": total_questions,
                "mapping_success": mapping_success,
                "raw_response": raw_response,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await collection.insert_one(marks_content_doc)
            print(f"Saved marks content with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"Error saving marks content: {e}")
            return None
    
    async def save_marks_content_with_assignment_update(self, run_id: str, marks_mapping: Dict[str, Any], 
                                                       total_questions: int, assignment_id: str, 
                                                       mapping_success: bool = True, raw_response: str = None) -> Optional[str]:
        """Save marks content and update assignment with marks_content_id"""
        if not await self.initialize():
            return None
        
        try:
            # Save marks content
            marks_content_id = await self.save_marks_content(
                run_id=run_id,
                marks_mapping=marks_mapping,
                total_questions=total_questions,
                mapping_success=mapping_success,
                raw_response=raw_response
            )
            
            if marks_content_id:
                # Update assignment with marks_content_id
                success = await self.update_assignment_marks_content(assignment_id, marks_content_id)
                if success:
                    print(f"  - Assignment updated with marks content ID: {marks_content_id}")
                else:
                    print(f"  - Failed to update assignment with marks content ID: {marks_content_id}")
                
                return marks_content_id
            else:
                print("  - Failed to save marks content")
                return None
                
        except Exception as e:
            print(f"Error saving marks content with assignment update: {e}")
            return None
    

    
    async def save_visual_extraction_result(self, run_id: str, total_figures: int, pages_processed: int,
                                          figures: List[Dict[str, Any]], overview_image_figures: str = None,
                                          tables: List[Dict[str, Any]] = None, overview_image_tables: str = None,
                                          assignment_id: str = None) -> Optional[str]:
        """Save visual extraction results to database with new schema (diagrams and tables saved to separate collections)"""
        if not await self.initialize():
            return None
        
        try:
            # Save individual diagrams to diagrams collection
            diagram_ids = []
            for figure_data in figures:
                diagram_url = figure_data.get("cloudinary_url")
                diagram_identifier = f"figure-{figure_data.get('figure_counter', 'unknown')}"
                if diagram_url:
                    diagram_id = await self.save_diagram(diagram_url, diagram_identifier, run_id)
                    if diagram_id:
                        diagram_ids.append(diagram_id)
            
            # Save individual tables to tables collection
            table_ids = []
            if tables:
                for table_data in tables:
                    table_url = table_data.get("cloudinary_url")
                    table_identifier = f"table-{table_data.get('table_counter', 'unknown')}"
                    if table_url:
                        table_id = await self.save_table(table_url, table_identifier, run_id)
                        if table_id:
                            table_ids.append(table_id)
            
            # Save visual content with references to diagrams and tables
            visual_content_id = await self.save_visual_content(
                tables=table_ids,
                diagrams=diagram_ids,
                overview_image_tables=overview_image_tables,
                overview_image_diagrams=overview_image_figures
            )
            
            # Update assignment with visual content ID if provided
            if assignment_id and visual_content_id:
                await self.update_assignment_visual_content(assignment_id, visual_content_id)
                print(f"  - Assignment updated with visual content ID: {visual_content_id}")
            
            print(f"Visual extraction result saved:")
            print(f"  - Run ID: {run_id}")
            print(f"  - Total figures: {total_figures}")
            print(f"  - Pages processed: {pages_processed}")
            print(f"  - Diagrams saved: {len(diagram_ids)}")
            print(f"  - Tables saved: {len(table_ids)}")
            print(f"  - Visual content ID: {visual_content_id}")
            
            return visual_content_id
            
        except Exception as e:
            print(f"Error saving visual extraction result: {e}")
            return None
    
    async def start_pipeline(self, run_id: str, title: str, filename: str, file_size: int, total_marks: int = None) -> Optional[str]:
        """Initialize a new pipeline run in the database and create assignment"""
        if not await self.initialize():
            return None
        
        try:
            print(f"Starting pipeline: {title}")
            print(f"  - Run ID: {run_id}")
            print(f"  - Filename: {filename}")
            print(f"  - File size: {file_size} bytes")
            print(f"  - Total marks: {total_marks}")
            
            # Create assignment without visual_content_id initially (will be updated after Step 1)
            assignment_id = await self.create_assignment(run_id, title, total_marks)
            if assignment_id:
                print(f"  - Assignment created with ID: {assignment_id}")
                return assignment_id
            else:
                print("  - Failed to create assignment")
                return None
                
        except Exception as e:
            print(f"Error starting pipeline: {e}")
            return None
    
    async def complete_pipeline(self, run_id: str, assignment_id: str, success: bool = True) -> bool:
        """Mark pipeline as completed"""
        if not await self.initialize():
            return False
        
        try:
            status = "completed successfully" if success else "failed"
            print(f"Pipeline {status} for run_id: {run_id}")
            print(f"  - Assignment ID: {assignment_id}")
            return True
        except Exception as e:
            print(f"Error completing pipeline: {e}")
            return False
    
    async def update_visual_content_mapping(self, mapping_data: Dict[str, Any], run_id: str = None) -> bool:
        """Update visual content with mapping results (VM fields)"""
        if not await self.initialize():
            return False
        
        try:
            print(f"Updating visual content mapping with data: {mapping_data}")
            if run_id:
                print(f"Using run_id: {run_id}")
            
            # Update diagrams with mapping data
            if "figures" in mapping_data:
                for figure_identifier, mapping_info in mapping_data["figures"].items():
                    # Find diagram by identifier and run_id
                    diagram = await pipeline_db.get_diagram_by_identifier(figure_identifier, run_id)
                    if diagram:
                        diagram_id = str(diagram.get("_id"))
                        await pipeline_db.update_diagram_mapping(
                            diagram_id=diagram_id,
                            question_identifier=mapping_info.get("question_identifier"),
                            choice_location=mapping_info.get("choice_location")
                        )
                        print(f"Updated diagram {diagram_id} ({figure_identifier}) with question_identifier: {mapping_info.get('question_identifier')}, choice_location: {mapping_info.get('choice_location')}")
                    else:
                        print(f"Warning: Could not find diagram with identifier: {figure_identifier}" + (f" and run_id: {run_id}" if run_id else ""))
            
            # Update tables with mapping data
            if "tables" in mapping_data:
                for table_identifier, mapping_info in mapping_data["tables"].items():
                    # Find table by identifier and run_id
                    table = await pipeline_db.get_table_by_identifier(table_identifier, run_id)
                    if table:
                        table_id = str(table.get("_id"))
                        await pipeline_db.update_table_mapping(
                            table_id=table_id,
                            question_identifier=mapping_info.get("question_identifier"),
                            choice_location=mapping_info.get("choice_location")
                        )
                        print(f"Updated table {table_id} ({table_identifier}) with question_identifier: {mapping_info.get('question_identifier')}, choice_location: {mapping_info.get('choice_location')}")
                    else:
                        print(f"Warning: Could not find table with identifier: {table_identifier}" + (f" and run_id: {run_id}" if run_id else ""))
            
            return True
            
        except Exception as e:
            print(f"Error updating visual content mapping: {e}")
            return False
    

    

    
    def _create_structured_questions_output(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create structured output for questions with internal choice detection"""
        structured_questions = []
        questions_with_internal_choice = 0
        questions_without_internal_choice = 0
        
        for question_data in questions:
            question_identifier = question_data["question_identifier"]
            has_internal_choice = question_data["has_internal_choice"]
            question_text = question_data["question_text"]
            
            if has_internal_choice:
                questions_with_internal_choice += 1
                # For internal choice, question_text is already an array
                structured_questions.append({
                    "question_identifier": question_identifier,
                    "has_internal_choice": True,
                    "question_text": question_text
                })
            else:
                questions_without_internal_choice += 1
                # For single questions, question_text is a string
                structured_questions.append({
                    "question_identifier": question_identifier,
                    "has_internal_choice": False,
                    "question_text": question_text
                })
        
        return {
            "questions": structured_questions,
            "total_questions": len(questions),
            "questions_with_internal_choice": questions_with_internal_choice,
            "questions_without_internal_choice": questions_without_internal_choice
        }
    
    async def _get_question_extraction_data(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get question extraction data from database"""
        try:
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["question_content"])
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
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["marks_content"])
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
    

    
    def _parse_questions_from_markdown(self, markdown_content: str, marks_mapping: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Parse questions from markdown content using marks mapping to determine internal choice"""
        import re
        
        questions = []
        
        # Split by [####] to get individual questions
        question_chunks = markdown_content.split("[####]")
        
        for chunk in question_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            
            # Extract question identifier from the beginning of the chunk
            # Look for patterns like "1.", "22.", "36." etc.
            identifier_match = re.match(r'^(\d+)\.', chunk)
            if identifier_match:
                question_identifier = identifier_match.group(1)
            else:
                # Fallback: use sequential numbering
                question_identifier = str(len(questions) + 1)
            
            # Check if this question has internal choice based on marks mapping
            has_internal_choice = False
            question_type = "Normal Subjective"  # Default question type
            if marks_mapping:
                question_key = f"question-{question_identifier}"
                if question_key in marks_mapping:
                    question_info = marks_mapping[question_key]
                    question_type = question_info.get("question_type", "Normal Subjective")
                    has_internal_choice = question_type == "Internal Choice Subjective"
            
            # Remove the question number from the beginning if present
            cleaned_chunk = re.sub(r'^\d+\.\s*', '', chunk).strip()
            
            if has_internal_choice:
                # Check for internal choice using [%OR%] only if question_type indicates internal choice
                if "[%OR%]" in cleaned_chunk:
                    # Internal choice: split by [%OR%]
                    parts = cleaned_chunk.split("[%OR%]")
                    
                    # Clean up each part and extract question text
                    question_texts = []
                    for part in parts:
                        part = part.strip()
                        if part:
                            question_texts.append(part)
                    
                    # Ensure we have at least one question text
                    if question_texts:
                        questions.append({
                            "question_identifier": question_identifier,
                            "has_internal_choice": True,
                            "question_text": question_texts if len(question_texts) > 1 else question_texts[0],
                            "question_type": question_type
                        })
                else:
                    # Question type indicates internal choice but no [%OR%] found
                    questions.append({
                        "question_identifier": question_identifier,
                        "has_internal_choice": True,
                        "question_text": cleaned_chunk,
                        "question_type": question_type
                    })
            else:
                # No internal choice
                questions.append({
                    "question_identifier": question_identifier,
                    "has_internal_choice": False,
                    "question_text": cleaned_chunk,
                    "question_type": question_type
                })
        
        return questions
    

    

    

    

    

    

    

    
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
                question_text=question_data["question_text"],
                question_marks=question_data["question_marks"],
                question_type=question_data["question_type"],
                diagram_url=question_data.get("diagram_url"),
                table_url=question_data.get("table_url"),
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
    
    async def update_assignment_visual_content(self, assignment_id: str, visual_content_id: str) -> bool:
        """Update assignment with visual content ID"""
        if not await self.initialize():
            return False
        
        try:
            success = await pipeline_db.update_assignment_visual_content(assignment_id, visual_content_id)
            return success
            
        except Exception as e:
            print(f"Error updating assignment visual content: {e}")
            return False
    
    async def update_assignment_question_content(self, assignment_id: str, question_content_id: str) -> bool:
        """Update assignment with question content ID"""
        if not await self.initialize():
            return False
        
        try:
            success = await pipeline_db.update_assignment_question_content(assignment_id, question_content_id)
            return success
            
        except Exception as e:
            print(f"Error updating assignment question content: {e}")
            return False
    
    async def update_assignment_marks_content(self, assignment_id: str, marks_content_id: str) -> bool:
        """Update assignment with marks content ID"""
        if not await self.initialize():
            return False
        
        try:
            success = await pipeline_db.update_assignment_marks_content(assignment_id, marks_content_id)
            return success
            
        except Exception as e:
            print(f"Error updating assignment marks content: {e}")
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
                question_text=question_data["question_text"],
                question_marks=question_data["question_marks"],
                question_marks_analysis=question_data["question_marks_analysis"],
                question_type=question_data["question_type"],
                diagram_url=question_data.get("diagram_url"),
                table_url=question_data.get("table_url"),
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
    
    async def question_parsing_consolidation(self, run_id: str, assignment_id: str) -> bool:
        """
        Final step: Process question content and create individual question documents
        with proper diagram/table mapping and update assignment with questions array
        """
        if not await self.initialize():
            return False
        
        try:
            print(f"Starting question parsing consolidation for run_id: {run_id}")
            
            # Step 1: Get question content from database
            question_content = await self._get_question_content_by_run_id(run_id)
            if not question_content or not question_content.get("questions"):
                print(f"No question content found for run_id: {run_id}")
                return False
            
            # Step 2: Get marks mapping for internal choice detection
            marks_mapping = await self._get_marks_mapping_data(run_id)
            if not marks_mapping:
                print(f"No marks mapping found for run_id: {run_id}")
                return False
            
            # Step 3: Get visual content for diagram/table URLs
            visual_content = await self._get_visual_content_by_run_id(run_id)
            
            # Step 4: Get tables and diagrams collections for mapping
            tables = await self._get_tables_by_run_id(run_id)
            diagrams = await self._get_diagrams_by_run_id(run_id)
            
            # Step 4: Process each question and create question documents
            assignment_questions = []
            
            for question_data in question_content["questions"]:
                question_identifier = question_data["question_identifier"]
                question_text = question_data["question_text"]
                
                # Determine internal choice based on marks mapping
                has_internal_choice = False
                question_key = f"question-{question_identifier}"
                if question_key in marks_mapping:
                    question_info = marks_mapping[question_key]
                    question_type = question_info.get("question_type", "")
                    has_internal_choice = question_type == "Internal Choice Subjective"
                
                print(f"Processing question {question_identifier} (internal choice: {has_internal_choice})")
                
                if has_internal_choice:
                    # Handle internal choice questions
                    if isinstance(question_text, list):
                        # question_text is already a list of sub-questions
                        sub_questions = question_text
                    else:
                        # Split question by [%OR%] to get two sub-questions
                        sub_questions = question_text.split("[%OR%]")
                    
                    if len(sub_questions) != 2:
                        print(f"Warning: Question {question_identifier} has internal choice but doesn't split into 2 parts")
                        continue
                    
                    # Get marks for internal choice questions (should be an array in marks_analysis)
                    marks_analysis_array = question_info.get("marks_analysis", [])
                    question_marks = question_info.get("marks", 1)  # Numerical value
                    
                    if not isinstance(marks_analysis_array, list) or len(marks_analysis_array) != 2:
                        print(f"Warning: Question {question_identifier} has invalid marks_analysis array: {marks_analysis_array}")
                        continue
                    
                    question_ids = []
                    for i, sub_question in enumerate(sub_questions):
                        choice_location = "first" if i == 0 else "second"
                        
                        # Get diagram/table URLs for this choice
                        diagram_url = await self._get_diagram_url_for_question(
                            question_identifier, choice_location, diagrams
                        )
                        table_url = await self._get_table_url_for_question(
                            question_identifier, choice_location, tables
                        )
                        
                        # Use the corresponding mark analysis from the array (top to bottom order)
                        question_marks_analysis = marks_analysis_array[i] if i < len(marks_analysis_array) else "1 mark"
                        
                        # Create question document
                        question_id = await self._create_question_document(
                            question_text=sub_question.strip() if isinstance(sub_question, str) else sub_question,
                            question_marks=question_marks,  # Use numerical marks from marks mapping
                            question_marks_analysis=question_marks_analysis,  # Use marks_analysis from marks mapping
                            question_type=question_type,  # Use the question_type from marks mapping
                            diagram_url=diagram_url,
                            table_url=table_url
                        )
                        
                        if question_id:
                            question_ids.append(question_id)
                            print(f"  - Created question {question_identifier}{'a' if i == 0 else 'b'}: {question_id}")
                        else:
                            print(f"  - Failed to create question {question_identifier}{'a' if i == 0 else 'b'}")
                    
                    # Add to assignment with array of question IDs
                    if len(question_ids) == 2:
                        assignment_questions.append({
                            "question_identifier": question_identifier,
                            "question_id": question_ids
                        })
                        print(f"  - Added internal choice question {question_identifier} with {len(question_ids)} sub-questions")
                    else:
                        print(f"  - Warning: Question {question_identifier} didn't create both sub-questions")
                
                else:
                    # Single question - get diagram/table URLs
                    diagram_url = await self._get_diagram_url_for_question(
                        question_identifier, None, diagrams
                    )
                    table_url = await self._get_table_url_for_question(
                        question_identifier, None, tables
                    )
                    
                    # Get marks for single questions
                    question_marks = question_info.get("marks", 1) if question_info else 1  # Numerical value
                    question_marks_analysis = question_info.get("marks_analysis", "1 mark") if question_info else "1 mark"
                    
                    # Create question document
                    question_id = await self._create_question_document(
                        question_text=question_text,
                        question_marks=question_marks,  # Use numerical marks from marks mapping
                        question_marks_analysis=question_marks_analysis,  # Use marks_analysis from marks mapping
                        question_type=question_type,  # Use the question_type from marks mapping
                        diagram_url=diagram_url,
                        table_url=table_url
                    )
                    
                    if question_id:
                        assignment_questions.append({
                            "question_identifier": question_identifier,
                            "question_id": question_id
                        })
                        print(f"  - Created single question {question_identifier}: {question_id}")
                    else:
                        print(f"  - Failed to create question {question_identifier}")
            
            # Step 5: Update assignment with questions array
            if assignment_questions:
                success = await self._update_assignment_questions_array(assignment_id, assignment_questions)
                if success:
                    print(f"✅ Successfully updated assignment with {len(assignment_questions)} questions")
                    return True
                else:
                    print(f"❌ Failed to update assignment with questions array")
                    return False
            else:
                print(f"❌ No questions were created for assignment")
                return False
                
        except Exception as e:
            print(f"Error in question parsing consolidation: {e}")
            return False
    
    async def _get_question_content_by_run_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get question content by run_id"""
        try:
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["question_content"])
            if collection is None:
                return None
            
            doc = await collection.find_one({"run_id": run_id})
            return doc
        except Exception as e:
            print(f"Error getting question content: {e}")
            return None
    
    async def _get_visual_content_by_run_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get visual content by run_id by first getting the assignment"""
        try:
            # First get the assignment to get the visual_content_id
            from .schema import COLLECTION_NAMES
            assignments_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["assignments"])
            if assignments_collection is None:
                return None
            
            assignment = await assignments_collection.find_one({"run_id": run_id})
            if not assignment or not assignment.get("visual_content_id"):
                print(f"No assignment or visual_content_id found for run_id: {run_id}")
                return None
            
            # Now get the visual content using the visual_content_id
            visual_content_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["visual_content"])
            if visual_content_collection is None:
                return None
            
            try:
                from bson import ObjectId
                visual_content = await visual_content_collection.find_one({"_id": ObjectId(assignment["visual_content_id"])})
                return visual_content
            except Exception as e:
                print(f"Error getting visual content by ID: {e}")
                return None
                
        except Exception as e:
            print(f"Error getting visual content: {e}")
            return None
    
    async def _get_tables_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all tables for a run_id by getting visual content first"""
        try:
            # First get the visual content document to get table object IDs
            visual_content = await self._get_visual_content_by_run_id(run_id)
            if not visual_content or not visual_content.get("tables"):
                return []
            
            # Get the actual table documents using the object IDs
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["tables"])
            if collection is None:
                return []
            
            tables = []
            for table_id in visual_content["tables"]:
                try:
                    from bson import ObjectId
                    table = await collection.find_one({"_id": ObjectId(table_id)})
                    if table:
                        tables.append(table)
                except Exception as e:
                    print(f"Error getting table {table_id}: {e}")
            
            return tables
        except Exception as e:
            print(f"Error getting tables: {e}")
            return []
    
    async def _get_diagrams_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all diagrams for a run_id by getting visual content first"""
        try:
            # First get the visual content document to get diagram object IDs
            visual_content = await self._get_visual_content_by_run_id(run_id)
            if not visual_content or not visual_content.get("diagrams"):
                return []
            
            # Get the actual diagram documents using the object IDs
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["diagrams"])
            if collection is None:
                return []
            
            diagrams = []
            for diagram_id in visual_content["diagrams"]:
                try:
                    from bson import ObjectId
                    diagram = await collection.find_one({"_id": ObjectId(diagram_id)})
                    if diagram:
                        diagrams.append(diagram)
                except Exception as e:
                    print(f"Error getting diagram {diagram_id}: {e}")
            
            return diagrams
        except Exception as e:
            print(f"Error getting diagrams: {e}")
            return []
    
    async def _get_diagram_url_for_question(self, question_identifier: str, choice_location: str, 
                                          diagrams: List[Dict[str, Any]]) -> Optional[str]:
        """Get diagram URL for a specific question and choice location"""
        try:
            # Normalize choice_location for comparison
            # Database stores 'null' as string, but we pass None for single questions
            normalized_choice_location = choice_location if choice_location is not None else 'null'
            
            for diagram in diagrams:
                if (diagram.get("question_identifier") == question_identifier and 
                    diagram.get("choice_location") == normalized_choice_location):
                    return diagram.get("diagram_url")
            return None
        except Exception as e:
            print(f"Error getting diagram URL: {e}")
            return None
    
    async def _get_table_url_for_question(self, question_identifier: str, choice_location: str, 
                                        tables: List[Dict[str, Any]]) -> Optional[str]:
        """Get table URL for a specific question and choice location"""
        try:
            # Normalize choice_location for comparison
            # Database stores 'null' as string, but we pass None for single questions
            normalized_choice_location = choice_location if choice_location is not None else 'null'
            
            for table in tables:
                if (table.get("question_identifier") == question_identifier and 
                    table.get("choice_location") == normalized_choice_location):
                    return table.get("table_url")
            return None
        except Exception as e:
            print(f"Error getting table URL: {e}")
            return None
    
    async def _create_question_document(self, question_text: str, question_marks: Union[int, float], question_marks_analysis: str, question_type: str,
                                       diagram_url: str = None, table_url: str = None) -> Optional[str]:
        """Create a question document in the questions collection using simplified Question schema"""
        try:
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["questions"])
            if collection is None:
                return None
            
            question_doc = {
                "question_text": question_text,
                "question_marks": question_marks,
                "question_marks_analysis": question_marks_analysis,
                "question_type": question_type,
                "diagram_url": diagram_url,
                "table_url": table_url,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await collection.insert_one(question_doc)
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"Error creating question document: {e}")
            return None
    
    async def _update_assignment_questions_array(self, assignment_id: str, 
                                               questions_array: List[Dict[str, Any]]) -> bool:
        """Update assignment with questions array"""
        try:
            from .schema import COLLECTION_NAMES
            collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["assignments"])
            if collection is None:
                return False
            
            # Try with string ID first
            result = await collection.update_one(
                {"_id": assignment_id},
                {
                    "$set": {
                        "questions": questions_array,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                return True
            else:
                # Try with ObjectId as fallback
                try:
                    from bson import ObjectId
                    result = await collection.update_one(
                        {"_id": ObjectId(assignment_id)},
                        {
                            "$set": {
                                "questions": questions_array,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    return result.modified_count > 0
                except Exception:
                    return False
                    
        except Exception as e:
            print(f"Error updating assignment questions array: {e}")
            return False


# Global integration instance
db_integration = DatabaseIntegration()


def get_db_integration() -> DatabaseIntegration:
    """Get the global database integration instance"""
    return db_integration 