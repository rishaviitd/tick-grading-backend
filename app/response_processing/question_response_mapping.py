"""
Question-Response Mapping Service

This module handles the mapping between questions and student responses
based on the question_identifier and answer_label pattern (ANS-<number>).
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from database.connection import pipeline_db
from database.schema import QuestionResponseMapping


class QuestionResponseMappingService:
    """Service for mapping questions to student responses"""
    
    @staticmethod
    def extract_question_number_from_answer_label(answer_label: str) -> Optional[str]:
        """
        Extract question number from answer label (e.g., 'ANS-15' -> '15')
        
        Args:
            answer_label: The answer label (e.g., 'ANS-15', 'ANS-18')
            
        Returns:
            Question number as string, or None if pattern doesn't match
        """
        pattern = r'^ANS-(\d+)$'
        match = re.match(pattern, answer_label)
        if match:
            return match.group(1)
        return None
    
    @staticmethod
    async def create_mappings_for_run_id(run_id: str) -> Dict[str, Any]:
        """
        Create question-response mappings for a specific run_id using the new schema
        
        Args:
            run_id: The run identifier
            
        Returns:
            Dictionary with mapping results
        """
        try:
            from database.integration import get_db_integration
            
            # Get questions for this run_id
            questions = await pipeline_db.get_questions_by_run_id(run_id)
            if not questions:
                return {
                    "success": False,
                    "error": f"No questions found for run_id: {run_id}",
                    "mappings_created": 0
                }
            
            # Get student assignment responses for this run_id
            responses_data = await pipeline_db.get_responses_by_run_id(run_id)
            if not responses_data:
                return {
                    "success": False,
                    "error": f"No student assignment responses found for run_id: {run_id}",
                    "mappings_created": 0
                }
            
            # Extract student and assignment information
            student_id = responses_data.get("student_id")
            assignment_id = responses_data.get("assignment_id")
            student_responses = responses_data.get("student_responses", [])
            
            if not student_responses:
                return {
                    "success": False,
                    "error": f"No student responses found for run_id: {run_id}",
                    "mappings_created": 0
                }
            
            from app.utils.identifier_normalizer import normalize_identifier
            
            # Create a mapping of normalized question_identifier to question data
            questions_map = {normalize_identifier(q["question_identifier"]): q for q in questions}
            
            # Process each student response
            mappings_created = 0
            unmapped_responses = []
            
            for response in student_responses:
                question_identifier = normalize_identifier(response.get("question_identifier"))
                cloudinary_url = response.get("cloudinary_url")
                
                if not question_identifier or not cloudinary_url:
                    unmapped_responses.append({
                        "question_identifier": question_identifier,
                        "reason": "Missing question_identifier or cloudinary_url"
                    })
                    continue
                
                # Check if question exists
                if question_identifier not in questions_map:
                    unmapped_responses.append({
                        "question_identifier": question_identifier,
                        "reason": "Question not found"
                    })
                    continue
                
                # Check if mapping already exists to prevent duplicates
                existing_mapping = await pipeline_db.get_question_response_mapping_by_question_id(run_id, question_identifier)
                if existing_mapping:
                    unmapped_responses.append({
                        "question_identifier": question_identifier,
                        "reason": "Mapping already exists"
                    })
                    continue
                
                # Create mapping using the new schema with normalized identifier
                question_data = questions_map[question_identifier]
                mapping = QuestionResponseMapping(
                    student_id=student_id,
                    assignment_id=assignment_id,
                    run_id=run_id,
                    question_identifier=question_identifier,  # Use normalized identifier
                    has_internal_choice=question_data["has_internal_choice"],
                    primary_question=question_data["primary_question"],
                    secondary_question=question_data.get("secondary_question"),
                    primary_diagram_url=question_data.get("primary_diagram_url"),
                    secondary_diagram_url=question_data.get("secondary_diagram_url"),
                    table_url=question_data.get("table_url"),
                    primary_marks=question_data["primary_marks"],
                    secondary_marks=question_data.get("secondary_marks"),
                    question_type=question_data["question_type"],
                    response_cloudinary_url=cloudinary_url,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # Save mapping to database directly using pipeline_db
                mapping_id = await pipeline_db.save_question_response_mapping(mapping)
                
                if mapping_id:
                    mappings_created += 1
                else:
                    unmapped_responses.append({
                        "question_identifier": question_identifier,
                        "reason": "Failed to save mapping"
                    })
            
            return {
                "success": True,
                "mappings_created": mappings_created,
                "total_responses": len(student_responses),
                "unmapped_responses": unmapped_responses,
                "run_id": run_id,
                "student_id": student_id,
                "assignment_id": assignment_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating mappings: {str(e)}",
                "mappings_created": 0
            }
    
    @staticmethod
    async def get_mappings_for_run_id(run_id: str) -> Dict[str, Any]:
        """
        Get all question-response mappings for a specific run_id
        
        Args:
            run_id: The run identifier
            
        Returns:
            Dictionary with mappings data
        """
        try:
            mappings = await pipeline_db.get_question_response_mappings_by_run_id(run_id)
            return {
                "success": True,
                "mappings": mappings,
                "total_mappings": len(mappings),
                "run_id": run_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error retrieving mappings: {str(e)}",
                "mappings": [],
                "total_mappings": 0,
                "run_id": run_id
            }
    
    @staticmethod
    async def get_mapping_for_question(run_id: str, question_identifier: str) -> Dict[str, Any]:
        """
        Get question-response mapping for a specific question
        
        Args:
            run_id: The run identifier
            question_identifier: The question identifier
            
        Returns:
            Dictionary with mapping data
        """
        from app.utils.identifier_normalizer import normalize_identifier
        
        try:
            # Normalize the question identifier for lookup
            normalized_identifier = normalize_identifier(question_identifier)
            mapping = await pipeline_db.get_question_response_mapping_by_question_id(run_id, normalized_identifier)
            if mapping:
                return {
                    "success": True,
                    "mapping": mapping,
                    "run_id": run_id,
                    "question_identifier": question_identifier
                }
            else:
                return {
                    "success": False,
                    "error": f"No mapping found for question {question_identifier} in run {run_id}",
                    "run_id": run_id,
                    "question_identifier": question_identifier
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error retrieving mapping: {str(e)}",
                "run_id": run_id,
                "question_identifier": question_identifier
            } 