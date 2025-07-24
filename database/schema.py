"""
MongoDB Schema for TickAI CBSE Processing Pipeline

This module defines the database schemas for storing the results of each step
in the CBSE question paper processing pipeline.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
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
# STEP 1: DIAGRAM EXTRACTION SCHEMA
# =============================================================================

class DiagramExtractionResult(BaseModel):
    """Schema for Step 1: Diagram Extraction results"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: str = Field(..., description="Unique run identifier")
    step: str = Field(default="diagram_extraction", description="Step identifier")
    
    # Extraction metadata
    total_figures: int = Field(..., description="Total number of figures extracted")
    pages_processed: int = Field(..., description="Number of pages processed")
    extraction_success: bool = Field(..., description="Whether extraction was successful")
    
    # Figure details
    figures: List[Dict[str, Any]] = Field(default_factory=list, description="List of extracted figures")
    
    # File references
    figure_files: List[str] = Field(default_factory=list, description="List of figure file paths")
    overview_image_path: Optional[str] = Field(None, description="Path to overview image")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# =============================================================================
# STEP 2: DIAGRAM MAPPING SCHEMA
# =============================================================================

class DiagramMappingEntry(BaseModel):
    """Schema for individual diagram mapping entry"""
    question_identifier: str = Field(..., description="Question number/identifier")
    choice_location: str = Field(..., description="Location in internal choice (first/second/both/null)")
    cloudinary_url: Optional[str] = Field(None, description="Cloudinary URL for the figure")


class DiagramMappingResult(BaseModel):
    """Schema for Step 2: Diagram Mapping results"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: str = Field(..., description="Unique run identifier")
    step: str = Field(default="diagram_mapping", description="Step identifier")
    
    # Mapping data
    mapping: Dict[str, DiagramMappingEntry] = Field(..., description="Figure to question mapping")
    total_mappings: int = Field(..., description="Total number of mappings created")
    
    # Processing metadata
    mapping_success: bool = Field(..., description="Whether mapping was successful")
    raw_response: Optional[str] = Field(None, description="Raw response from Gemini AI")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# =============================================================================
# STEP 3: QUESTION EXTRACTION SCHEMA
# =============================================================================

class QuestionExtractionResult(BaseModel):
    """Schema for Step 3: Question Extraction results"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: str = Field(..., description="Unique run identifier")
    step: str = Field(default="question_extraction", description="Step identifier")
    
    # Question data
    questions_markdown: str = Field(..., description="Questions in markdown format")
    questions_count: int = Field(..., description="Total number of questions extracted")
    content_length: int = Field(..., description="Length of markdown content in characters")
    
    # Processing metadata
    extraction_success: bool = Field(..., description="Whether extraction was successful")
    raw_response: Optional[str] = Field(None, description="Raw response from Gemini AI")
    
    # File reference
    markdown_file_path: Optional[str] = Field(None, description="Path to markdown file")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# =============================================================================
# STEP 4: MARKS MAPPING SCHEMA
# =============================================================================

class MarksMappingEntry(BaseModel):
    """Schema for individual marks mapping entry"""
    question_type: str = Field(..., description="Type of question (MCQ/Case Study/Normal Subjective/etc.)")
    marks: List[str] = Field(..., description="Marks allocation description (list for internal choice, single item for others)")


class MarksMappingResult(BaseModel):
    """Schema for Step 4: Marks Mapping results"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: str = Field(..., description="Unique run identifier")
    step: str = Field(default="marks_mapping", description="Step identifier")
    
    # Mapping data
    marks_mapping: Dict[str, MarksMappingEntry] = Field(..., description="Question to marks mapping")
    total_questions: int = Field(..., description="Total number of questions mapped")
    
    # Processing metadata
    mapping_success: bool = Field(..., description="Whether mapping was successful")
    raw_response: Optional[str] = Field(None, description="Raw response from Gemini AI")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# =============================================================================
# STEP 5: COMBINED QUESTIONS SCHEMA
# =============================================================================

class Question(BaseModel):
    """Schema for combined questions from all processing steps"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: str = Field(..., description="Unique run identifier")
    
    # Question identification
    question_identifier: str = Field(..., description="Question number/identifier")
    has_internal_choice: bool = Field(..., description="Whether question has internal choice")
    
    # Question content
    primary_question: str = Field(..., description="Primary question text")
    secondary_question: Optional[str] = Field(None, description="Secondary question text (for internal choice)")
    
    # Diagram URLs
    primary_diagram_url: Optional[str] = Field(None, description="Cloudinary URL for primary diagram")
    secondary_diagram_url: Optional[str] = Field(None, description="Cloudinary URL for secondary diagram")
    table_url: Optional[str] = Field(None, description="Cloudinary URL for table")
    
    # Marks
    primary_marks: str = Field(..., description="Primary marks allocation")
    secondary_marks: Optional[str] = Field(None, description="Secondary marks allocation (for internal choice)")
    
    # Question type
    question_type: str = Field(..., description="Type of question (MCQ/Assertion Reasoning/Case Study/Normal Subjective/Internal Choice)")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# =============================================================================
# RESPONSE PROCESSING SCHEMA
# =============================================================================

class ResponseProcessingResult(BaseModel):
    """Schema for Response Processing (crop-margins) results"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: str = Field(..., description="Unique run identifier")
    
    # Simple mapping: question_id -> image_url
    responses: Dict[str, str] = Field(..., description="Mapping of question_id to image_url")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# =============================================================================
# MAIN PIPELINE SCHEMA
# =============================================================================

class ProcessingStep(BaseModel):
    """Schema for individual processing step"""
    name: str = Field(..., description="Step name")
    timestamp: datetime = Field(..., description="Step timestamp")
    input: str = Field(..., description="Step input")
    output: str = Field(..., description="Step output")


class PipelineResult(BaseModel):
    """Schema for complete pipeline result"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    run_id: str = Field(..., description="Unique run identifier")
    
    # Pipeline metadata
    title: str = Field(..., description="Pipeline title")
    log_type: str = Field(..., description="Type of processing")
    status: str = Field(..., description="Pipeline status (active/completed/failed)")
    
    # File information
    original_filename: str = Field(..., description="Original uploaded filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    
    # Step results
    steps: List[ProcessingStep] = Field(default_factory=list, description="Processing steps")
    step_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Detailed step results")
    
    # Final outputs
    final_outputs: Dict[str, Any] = Field(default_factory=dict, description="Final pipeline outputs")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


# =============================================================================
# DATABASE COLLECTION NAMES
# =============================================================================

COLLECTION_NAMES = {
    "pipeline_results": "pipeline_results",
    "diagram_extraction": "diagram_extraction_results",
    "diagram_mapping": "diagram_mapping_results", 
    "question_extraction": "question_extraction_results",
    "marks_mapping": "marks_mapping_results",
    "questions": "questions",
    "response_processing": "response_processing_results"
}


# =============================================================================
# DATABASE INDEXES
# =============================================================================

INDEXES = {
    "pipeline_results": [
        [("run_id", 1)],  # Primary lookup by run_id
        [("status", 1)],  # Filter by status
        [("created_at", -1)],  # Sort by creation time
        [("log_type", 1)],  # Filter by log type
    ],
    "diagram_extraction_results": [
        [("run_id", 1)],  # Primary lookup by run_id
        [("created_at", -1)],  # Sort by creation time
    ],
    "diagram_mapping_results": [
        [("run_id", 1)],  # Primary lookup by run_id
        [("created_at", -1)],  # Sort by creation time
    ],
    "question_extraction_results": [
        [("run_id", 1)],  # Primary lookup by run_id
        [("created_at", -1)],  # Sort by creation time
    ],
    "marks_mapping_results": [
        [("run_id", 1)],  # Primary lookup by run_id
        [("created_at", -1)],  # Sort by creation time
    ],
    "questions": [
        [("run_id", 1)],  # Primary lookup by run_id
        [("question_identifier", 1)],  # Secondary lookup by question identifier
        [("created_at", -1)]  # Sort by creation time
    ],
    "response_processing_results": [
        [("run_id", 1)],  # Primary lookup by run_id
        [("created_at", -1)],  # Sort by creation time
    ]
} 