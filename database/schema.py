"""
MongoDB Schema for TickAI CBSE Processing Pipeline

This module defines the database schemas for storing the results of each step
in the CBSE question paper processing pipeline and the core business logic entities.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from bson import ObjectId


from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

class PyObjectId(ObjectId):
    """Custom ObjectId for Pydantic models"""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.json_schema(
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            )
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


# =============================================================================
# RUBRIC SCHEMAS
# =============================================================================

class MarkingPoint(BaseModel):
    """Schema for individual marking point in subjective/case study questions"""
    stepId: str = Field(..., description="Step identifier")
    MarkType: str = Field(..., description="Mark type (B, M, A)")
    marks: str = Field(..., description="Marks allocated (0.5, 1)")
    Teacher_Expectation: str = Field(..., description="What teacher expects")
    Pass_if: str = Field(..., description="Criteria for passing")
    Fail_if: str = Field(..., description="Criteria for failing")
    guidance: str = Field(..., description="Guidance for marking")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Method(BaseModel):
    """Schema for solution method in subjective/case study questions"""
    methodName: str = Field(..., description="Name of the solution method")
    markingPoints: List[MarkingPoint] = Field(..., description="List of marking points")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class MCQRubric(BaseModel):
    """Rubric schema for MCQ questions"""
    correct_option: str = Field(..., description="Correct option (A, B, C, D)")
    acceptable_answers: List[str] = Field(..., description="List of acceptable answer variations")
    solution: str = Field(..., description="Detailed solution explanation")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class AssertionReasonRubric(BaseModel):
    """Rubric schema for Assertion-Reason questions"""
    correct_option: str = Field(..., description="Correct option (A, B, C, D)")
    acceptable_answers: List[str] = Field(..., description="List of acceptable answer variations")
    solution: str = Field(..., description="Explanation of why assertion/reason are true/false")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class SubjectiveRubric(BaseModel):
    """Rubric schema for Subjective questions"""
    methods: List[Method] = Field(..., description="List of solution methods")
    Question_specific_notes: str = Field(..., description="Specific notes for marking")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class CaseStudyPart(BaseModel):
    """Schema for individual part in case study questions"""
    part_label: str = Field(..., description="Part label (a, b, c)")
    methods: List[Method] = Field(..., description="List of solution methods for this part")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class CaseStudyRubric(BaseModel):
    """Rubric schema for Case Study questions"""
    parts: List[CaseStudyPart] = Field(..., description="List of question parts")
    Question_specific_notes: str = Field(..., description="Specific notes for marking")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class InternalChoiceRubric(BaseModel):
    """Rubric schema for Internal Choice questions"""
    primary_rubric: Optional[SubjectiveRubric] = Field(None, description="Rubric for primary choice")
    secondary_rubric: Optional[SubjectiveRubric] = Field(None, description="Rubric for secondary choice")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# =============================================================================
# CORE BUSINESS LOGIC SCHEMAS
# =============================================================================

class Diagram(BaseModel):
    """Schema for Diagram entity"""
    # VE fields (updated during visual extraction)
    diagram_url: str = Field(..., description="Cloudinary URL for the diagram image")
    diagram_identifier: str = Field(..., description="Diagram identifier")
    
    # VM fields (updated during visual mapping)
    question_identifier: Optional[str] = Field(None, description="Question number/identifier")
    choice_location: Optional[str] = Field(None, description="Location in internal choice (first/second/both/null)")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Table(BaseModel):
    """Schema for Table entity"""
    # VE fields (updated during visual extraction)
    table_url: str = Field(..., description="Cloudinary URL for the table image")
    table_identifier: str = Field(..., description="Table identifier")
    
    # VM fields (updated during visual mapping)
    question_identifier: Optional[str] = Field(None, description="Question number/identifier")
    choice_location: Optional[str] = Field(None, description="Location in internal choice (first/second/both/null)")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Teacher(BaseModel):
    """Schema for Teacher entity"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., description="Teacher name")
    class_name: str = Field(..., description="Class (e.g., '10')")
    board: str = Field(..., description="Board (e.g., 'CBSE')")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Student(BaseModel):
    """Schema for Student entity"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., description="Student name")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class VisualContent(BaseModel):
    """Schema for Visual Content entity - central hub for visual content management"""
    # Visual content references (populated after VE completion)
    tables: List[str] = Field(default_factory=list, description="List of table object IDs")
    diagrams: List[str] = Field(default_factory=list, description="List of diagram object IDs")
    
    # Overview images (available before VM)
    overview_image_tables: Optional[str] = Field(None, description="Cloudinary URL for tables overview image")
    overview_image_diagrams: Optional[str] = Field(None, description="Cloudinary URL for diagrams overview image")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Assignment(BaseModel):
    """Schema for Assignment entity"""
    run_id: str = Field(..., description="Unique run identifier from question processing")
    title: str = Field(..., description="Assignment title/name")
    total_marks: int = Field(..., description="Total marks for the assignment")
    
    # Content references
    visual_content_id: Optional[str] = Field(None, description="Reference to Visual_content")
    question_content_id: Optional[str] = Field(None, description="Reference to Question_content")
    marks_content_id: Optional[str] = Field(None, description="Reference to Marks_content")
    
    # Questions array - populated by question_parsing_consolidation
    questions: Optional[List[Dict[str, Any]]] = Field(None, description="Array of question mappings with question_identifier and question_id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Question(BaseModel):
    """Schema for Question entity - simplified structure for question_parsing_consolidation"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    
    # Question content
    question_text: str = Field(..., description="The actual question text content")
    question_marks: Union[int, float] = Field(..., description="Numerical marks allocation for the question")
    question_marks_analysis: str = Field(..., description="Detailed marks analysis/description")
    question_type: str = Field(..., description="Type of question (MCQ/Assertion Reasoning/Case Study/Normal Subjective/Internal Choice Subjective)")
    
    # Visual content URLs
    diagram_url: Optional[str] = Field(None, description="Cloudinary URL for diagram (if applicable)")
    table_url: Optional[str] = Field(None, description="Cloudinary URL for table (if applicable)")
    
    # NEW: Rubric field - Union of all rubric types based on question_type
    rubric: Optional[Union[MCQRubric, AssertionReasonRubric, SubjectiveRubric, CaseStudyRubric, InternalChoiceRubric]] = Field(
        None, 
        description="Generated rubric based on question type. Structure varies by question_type"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }
    
    def get_expected_rubric_type(self) -> type:
        """Get the expected rubric type based on question_type"""
        type_mapping = {
            "MCQ": MCQRubric,
            "Assertion Reasoning": AssertionReasonRubric,
            "Normal Subjective": SubjectiveRubric,
            "Case Study": CaseStudyRubric,
            "Internal Choice Subjective": InternalChoiceRubric
        }
        return type_mapping.get(self.question_type, SubjectiveRubric)
    
    def validate_rubric_type(self) -> bool:
        """Validate that the rubric matches the expected type for this question"""
        if self.rubric is None:
            return True  # No rubric is valid
        
        expected_type = self.get_expected_rubric_type()
        return isinstance(self.rubric, expected_type)
    
    def set_rubric(self, rubric_data: Union[MCQRubric, AssertionReasonRubric, SubjectiveRubric, CaseStudyRubric, InternalChoiceRubric]) -> None:
        """Set the rubric with type validation"""
        expected_type = self.get_expected_rubric_type()
        if not isinstance(rubric_data, expected_type):
            raise ValueError(f"Expected rubric type {expected_type.__name__} for question type '{self.question_type}', got {type(rubric_data).__name__}")
        
        self.rubric = rubric_data


class StudentResponse(BaseModel):
    """Schema for individual student response"""
    question_identifier: str = Field(..., description="Question identifier (e.g., '1', '15')")
    cloudinary_url: str = Field(..., description="Cloudinary URL for the response image")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class StudentAssignmentResponse(BaseModel):
    """Schema for Student Assignment Response entity"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    student_id: str = Field(..., description="Student ID")
    assignment_id: str = Field(..., description="Assignment ID")
    run_id: str = Field(..., description="Unique run identifier from response processing")
    
    # Student responses
    student_responses: List[StudentResponse] = Field(..., description="List of student responses")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class QuestionResponseMapping(BaseModel):
    """Schema for Question Response Mapping entity"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    student_id: str = Field(..., description="Student ID")
    assignment_id: str = Field(..., description="Assignment ID")
    run_id: str = Field(..., description="Unique run identifier from response processing")
    
    # Question data (from Question entity)
    question_text: str = Field(..., description="The actual question text content")
    question_marks: Union[int, float] = Field(..., description="Numerical marks allocation for the question")
    question_marks_analysis: str = Field(..., description="Detailed marks analysis/description")
    question_type: str = Field(..., description="Type of question (MCQ/Assertion Reasoning/Case Study/Normal Subjective/Internal Choice Subjective)")
    diagram_url: Optional[str] = Field(None, description="Cloudinary URL for diagram (if applicable)")
    table_url: Optional[str] = Field(None, description="Cloudinary URL for table (if applicable)")
    
    # NEW: Rubric field for grading
    rubric: Optional[Union[MCQRubric, AssertionReasonRubric, SubjectiveRubric, CaseStudyRubric, InternalChoiceRubric]] = Field(
        None, 
        description="Generated rubric for grading this question"
    )
    
    # Response data
    response_cloudinary_url: str = Field(..., description="Cloudinary URL for the student response")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class QuestionContent(BaseModel):
    """Schema for Question Content entity - stores extracted questions from PDF"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: str = Field(..., description="Unique run identifier from question processing")
    
    # Question content
    questions_markdown: str = Field(..., description="The extracted questions in markdown format")
    extraction_success: bool = Field(..., description="Boolean indicating if extraction was successful")
    raw_response: Optional[str] = Field(None, description="Raw response from the extraction process")
    
    # Parsed questions structure
    questions: Optional[List[Dict[str, Any]]] = Field(None, description="Parsed questions with internal choice detection")
    total_questions: Optional[int] = Field(None, description="Total number of questions")
    questions_with_internal_choice: Optional[int] = Field(None, description="Number of questions with internal choice")
    questions_without_internal_choice: Optional[int] = Field(None, description="Number of questions without internal choice")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }





# =============================================================================
# =============================================================================
# DATABASE COLLECTION NAMES
# =============================================================================


# =============================================================================
# DATABASE COLLECTION NAMES
# =============================================================================

COLLECTION_NAMES = {
    # Core business logic collections
    "teachers": "teachers",
    "students": "students", 
    "assignments": "assignments",
    "questions": "questions",

    "student_assignment_responses": "student_assignment_responses",
    "question_response_mappings": "question_response_mappings",
    
    # Visual content collections
    "diagrams": "diagrams",
    "tables": "tables",
    "visual_content": "visual_content",
    
    # Pipeline step results collections
    "question_content": "question_content",
    "marks_content": "marks_content",
}

# Database indexes for optimal performance
INDEXES = {
    "questions": [
        [("run_id", 1)]
    ],
    "student_assignment_responses": [
        [("run_id", 1)],
        [("student_id", 1)],
        [("assignment_id", 1)]
    ],
    "question_response_mappings": [
        [("run_id", 1)],
        [("student_id", 1)],
        [("assignment_id", 1)]
    ],
    "assignments": [
        [("run_id", 1)]
    ],
    "diagrams": [
        [("diagram_identifier", 1)]
    ],
    "tables": [
        [("table_identifier", 1)]
    ],
    "visual_content": [
        [("tables", 1)],
        [("diagrams", 1)]
    ],
    "question_content": [
        [("run_id", 1)]
    ],
    "marks_content": [
        [("run_id", 1)]
    ],

} 