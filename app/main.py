# this is the backend for the demo

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
import httpx
from dotenv import load_dotenv
from .response_processing.utils import margin_crop_images, process_crop_for_image, crop_questions_full_width, merge_continued_headers,upload_crops_to_cloudinary
from .question_parsing.question_extraction import (
    run_end_to_end_processing,
    DEPENDENCIES_OK,
    GEMINI_CLIENT_OK
)
from .logging import UnifiedLogger, LogType, LogViewer
from database.connection import pipeline_db, initialize_database
from database.schema import StudentAssignmentResponse
import cv2
import numpy as np
import uuid
from pathlib import Path
import json
import re
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse
import traceback
from datetime import datetime


load_dotenv()

# Chunk 0: Ensure logs directory exists before mounting static routes
LOGS_ROOT = Path(__file__).parent.parent / "logs"
LOGS_ROOT.mkdir(parents=True, exist_ok=True)

# Create FastAPI app
app = FastAPI()

# Mount app static (CSS) and logs static (images)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.mount("/logs/static", StaticFiles(directory=str(LOGS_ROOT)), name="logs_static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    await initialize_database()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    from database.connection import close_database
    await close_database()

class CropRequest(BaseModel):
    urls: List[str]
    assignment_id: Optional[str] = None
    student_id: Optional[str] = None
    student_name: Optional[str] = None

class Box(BaseModel):
    coordinates: List[int]
    text: str

class CropResult(BaseModel):
    margin: int
    boxes: List[Box]

class CropResponse(BaseModel):
    results: List[CropResult]

class AnswerUpload(BaseModel):
    question_id: str
    image_url: str

class UploadsResponse(BaseModel):
    uploads: List[AnswerUpload]

# New models for question extraction
class ProcessingStepResult(BaseModel):
    success: bool
    error: str = None
    total_figures: int = None
    images_dir: str = None
    meta_path: str = None
    mapping_path: str = None
    questions_path: str = None

class QuestionExtractionResponse(BaseModel):
    success: bool
    errors: List[str] = []
    step_results: dict = {}
    final_outputs: dict = {}
    message: str = ""

class AssignmentDetails(BaseModel):
    title: str
    total_marks: int

@app.get('/')
async def health_check():
    return {'status': 'ok'}

@app.get('/demo', response_class=HTMLResponse)
async def demo_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post('/crop-margins')
async def crop_margins(request: CropRequest):
    print(f"[crop-margins] Received URLs: {request.urls}")
    print(f"[crop-margins] Student ID: {request.student_id}, Student Name: {request.student_name}")
    if not request.urls:
        raise HTTPException(status_code=400, detail='`urls` list is empty')

    # Initialize unified logger
    logger = UnifiedLogger()
    run_id = logger.create_run(LogType.RESPONSE_PROCESSING, "Response Processing", {"urls": request.urls})
    
    try:
        logger.log_step(run_id, "Received URLs", request.urls)
        if request.student_id or request.student_name:
            logger.log_step(run_id, "Student Information", 
                          {"student_id": request.student_id, "student_name": request.student_name}, 
                          "Student data received with request")
        
        # Use extended timeouts for potentially large image downloads
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=60.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            images = []
            for url in request.urls:
                print(f"[crop-margins] Downloading image: {url}")
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    images.append(response.content)
                    logger.log_step(run_id, "Downloaded Image", url, f"{len(response.content)} bytes")
                except Exception as exc:
                    print(f"[crop-margins] Failed to download {url}: {type(exc).__name__}: {repr(exc)}")
                    logger.log_error(run_id, f"Failed to download {url}", exc)
                    traceback.print_exc()
                    raise HTTPException(status_code=502, detail=f'Failed to download image {url}: {type(exc).__name__}: {exc}')

        try:
            margins = margin_crop_images(images)
            print(f"[crop-margins] Computed margins: {margins}")
            logger.log_step(run_id, "Margin Detection", f"{len(images)} images", margins)
        except Exception as exc:
            print(f"[crop-margins] margin_crop_images error: {exc}", exc_info=True)
            logger.log_error(run_id, "Margin crop failed", exc)
            raise HTTPException(status_code=500, detail=f'margin crop failed: {exc}')

        results = []
        for idx, (content, margin) in enumerate(zip(images, margins)):
            try:
                cr = process_crop_for_image(content, margin)
                print(f"[crop-margins] Page {idx} processed -> margin={cr.margin}, boxes={len(cr.boxes)}")
                logger.log_step(run_id, "Process Page", {"page": idx, "margin": margin}, {"boxes": len(cr.boxes)})
                # Log extracted answer labels from margin for this page
                labels = [b.text for b in cr.boxes]
                logger.log_step(run_id, "Extract Answers", {"page": idx}, labels)
                
                # Create and save Textract annotated image
                cv_img = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
                if cv_img is not None:
                    # Create margin-cropped image for annotation
                    h, w = cv_img.shape[:2]
                    if 0 < margin < w:
                        cropped_img = cv_img[:, :margin].copy()
                    else:
                        cropped_img = cv_img.copy()
                    
                    # Create annotated image showing Textract results
                    annotated_img = cropped_img.copy()
                    
                    # Draw boxes and text from Textract results
                    for i, box in enumerate(cr.boxes):
                        x1, y1, x2, y2 = box.coordinates
                        # Draw bounding box (green for filtered/outer boxes)
                        cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        # Add text label
                        label = f"{box.text}"
                        cv2.putText(annotated_img, label, (x1, max(y1-5, 10)), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    
                    # Add filtering statistics to the image
                    stats_text = f"Filtered: {len(cr.boxes)} ANS boxes kept"
                    cv2.putText(annotated_img, stats_text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # Save the annotated image
                    logger.save_image(run_id, annotated_img, f'page_{idx}_textract_annotated.jpg', 'textract_results')
                    
                    # Log Textract statistics
                    textract_stats = {
                        "total_boxes": len(cr.boxes),
                        "detected_texts": [b.text for b in cr.boxes],
                        "margin_width": margin,
                        "image_dimensions": f"{h}x{w}"
                    }
                    logger.log_step(run_id, f"Textract Results Page {idx}", textract_stats, "Saved annotated image")
                
            except Exception as exc:
                print(f"[crop-margins] process_crop_for_image error on page {idx}: {exc}", exc_info=True)
                logger.log_error(run_id, f"Process crop error on page {idx}", exc)
                cr = CropResult(margin=margin, boxes=[])
            results.append(cr)
        
        # Log number of boxes extracted per page
        logger.log_step(run_id, "Extract Boxes", f"{len(images)} pages", [len(cr.boxes) for cr in results])

        # Process and save images using unified logger
        cv_images = [cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR) for content in images]
        
        # Save raw and margin-cropped images
        for idx, (img, margin) in enumerate(zip(cv_images, margins)):
            # Save raw image
            logger.save_image(run_id, img, f'page_{idx}_raw.jpg', 'margins')
            # Save margin-cropped image
            h, w = img.shape[:2]
            if 0 < margin < w:
                cropped = img[:, :margin]
            else:
                cropped = img
            logger.save_image(run_id, cropped, f'page_{idx}_cropped.jpg', 'margins')
        
        # Annotate detected boxes on cropped images
        for idx, cr in enumerate(results):
            ann_img = cv_images[idx]
            h, w = ann_img.shape[:2]
            if 0 < cr.margin < w:
                ann_img = ann_img[:, :cr.margin].copy()
            else:
                ann_img = ann_img.copy()
            # Draw boxes and labels
            for b in cr.boxes:
                x1, y1, x2, y2 = b.coordinates
                cv2.rectangle(ann_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(ann_img, b.text[:15], (x1, max(y1-5, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            logger.save_image(run_id, ann_img, f'page_{idx}_annotation.jpg', 'annotations')
        
        # Process crops and headers
        pages_boxes: List[List[dict]] = []
        for cr in results:
            page_boxes: List[dict] = []
            for idx, b in enumerate(cr.boxes):
                x1, y1, x2, y2 = b.coordinates
                page_boxes.append({
                    'id': idx,
                    'bbox': (x1, y1, x2 - x1, y2 - y1),
                    'text': b.text
                })
            pages_boxes.append(page_boxes)
        
        pages_crops = [crop_questions_full_width(img, boxes) for img, boxes in zip(cv_images, pages_boxes)]
        logger.log_step(run_id, "Page Crops", pages_boxes, [list(c.keys()) for c in pages_crops])
        
        merged_crops = merge_continued_headers(pages_crops)
        logger.log_step(run_id, "Merge Headers", [list(c.keys()) for c in pages_crops], [c[0] for c in merged_crops])
        
        # Save per-page question crops
        for idx, crops in enumerate(pages_crops):
            for label, (img, text) in crops.items():
                safe = re.sub(r"\W+", "_", label)
                filename = f'page_{idx}_{safe}.jpg'
                # Convert RGB back to BGR for saving
                bgr_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                logger.save_image(run_id, bgr_img, filename, 'crops')
        
        # Save merged question images
        for label, img, text in merged_crops:
            safe = re.sub(r"\W+", "_", label)
            filename = f'{safe}.jpg'
            # Convert RGB back to BGR for saving
            bgr_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            logger.save_image(run_id, bgr_img, filename, 'merged')
        
        # Upload merged question crops to Cloudinary
        uploads_meta = upload_crops_to_cloudinary(merged_crops)
        logger.log_step(run_id, "Upload to Cloudinary", f"{len(merged_crops)} items", [u['image_url'] for u in uploads_meta])
        
        # Create student responses for database using new schema
        from database.integration import get_db_integration
        from database.schema import StudentResponse
        
        # Initialize database integration
        db_integration = get_db_integration()
        
        # Handle assignment validation and linking
        assignment_id = request.assignment_id
        if not assignment_id:
            raise HTTPException(status_code=400, detail="assignment_id is required. Please select an assignment from the dropdown.")
        
        # Validate that the assignment exists
        try:
            assignments_collection = pipeline_db.db_manager.get_collection("assignments")
            if assignments_collection is None:
                raise HTTPException(status_code=500, detail="Database collection not available")
            
            # Check if the assignment exists
            assignment = await assignments_collection.find_one({"_id": assignment_id})
            if assignment is None:
                raise HTTPException(status_code=404, detail=f"Assignment with ID {assignment_id} not found. Please select a valid assignment.")
            
            logger.log_step(run_id, "Assignment Validated", 
                          f"Using assignment_id: {assignment_id}", 
                          f"Assignment: {assignment.get('title', 'Unknown')}")
            
        except HTTPException:
            raise
        except Exception as assignment_error:
            logger.log_error(run_id, "Assignment validation failed", assignment_error)
            raise HTTPException(status_code=500, detail=f"Assignment validation failed: {str(assignment_error)}")
        
        # Get questions for the selected assignment
        try:
            questions_collection = pipeline_db.db_manager.get_collection("questions")
            if questions_collection is not None:
                # Get questions that are already linked to this assignment
                questions = await questions_collection.find({"assignment_id": assignment_id}).to_list(length=None)
                
                if questions:
                    logger.log_step(run_id, "Found Questions for Assignment", 
                                  f"Found {len(questions)} questions for assignment {assignment_id}", 
                                  "Questions are already linked to this assignment")
                else:
                    logger.log_step(run_id, "No Questions Found", 
                                  f"No questions found for assignment {assignment_id}", 
                                  "Assignment may not have questions yet")
            else:
                logger.log_error(run_id, "Questions collection not found", 
                               "Could not retrieve questions for assignment")
        except Exception as question_error:
            logger.log_error(run_id, "Failed to get questions for assignment", question_error)
            # Don't fail the entire request, just log the error
        
        from app.utils.identifier_normalizer import normalize_identifier
        
        student_responses = []
        for upload_meta in uploads_meta:
            # Create student response object with normalized identifier
            student_response = StudentResponse(
                question_identifier=normalize_identifier(upload_meta['question_id']),
                cloudinary_url=upload_meta['image_url']
            )
            student_responses.append(student_response)
        
        # Save student assignment response to database
        if request.student_id:
            save_success = await db_integration.save_student_assignment_response(
                student_id=request.student_id,
                assignment_id=assignment_id,
                run_id=run_id,
                student_responses=student_responses
            )
            if not save_success:
                logger.log_error(run_id, "Failed to save student assignment response to database")
                raise HTTPException(status_code=500, detail="Failed to save results to database")
        else:
            logger.log_step(run_id, "No student_id provided", "Skipping database save", "Student responses not saved to database")
        
        # Initialize response data
        response_data = {}
        
        # Create question-response mappings automatically
        if request.student_id and assignment_id:
            try:
                from .response_processing.question_response_mapping import QuestionResponseMappingService
                mapping_result = await QuestionResponseMappingService.create_mappings_for_run_id(run_id)
                
                if mapping_result["success"]:
                    logger.log_step(run_id, "Question-Response Mapping", 
                                  f"Created {mapping_result['mappings_created']} mappings", 
                                  f"Total responses: {mapping_result['total_responses']}")
                    response_data["mappings_created"] = mapping_result["mappings_created"]
                else:
                    logger.log_error(run_id, "Failed to create question-response mappings", 
                                   mapping_result.get("error", "Unknown error"))
                    response_data["mapping_error"] = mapping_result.get("error", "Failed to create mappings")
            except Exception as mapping_error:
                logger.log_error(run_id, "Exception during mapping creation", mapping_error)
                response_data["mapping_error"] = f"Mapping creation failed: {str(mapping_error)}"
        else:
            logger.log_step(run_id, "Skipping Mapping Creation", 
                          f"No student_id ({request.student_id}) or assignment_id ({assignment_id})", 
                          "Mappings must be created manually")
        
        # Generate final consolidated JSON
        final_json = None
        if request.student_id and assignment_id:
            try:
                # Get all related data for the final JSON
                final_json = {
                    "run_id": run_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "metadata": {
                        "total_questions": 0,
                        "total_responses": len(student_responses),
                        "total_mappings": 0,
                        "total_diagrams": 0,
                        "total_tables": 0
                    }
                }
                
                # Get teacher information (assuming single teacher for now)
                teachers_collection = pipeline_db.db_manager.get_collection("teachers")
                if teachers_collection is not None:
                    teacher = await teachers_collection.find_one()
                    if teacher:
                        final_json["teacher"] = {
                            "id": str(teacher["_id"]),
                            "name": teacher["name"],
                            "class_name": teacher["class_name"],
                            "board": teacher["board"]
                        }
                
                # Get student information
                students_collection = pipeline_db.db_manager.get_collection("students")
                if students_collection is not None:
                    student = await students_collection.find_one({"_id": request.student_id})
                    if student:
                        final_json["student"] = {
                            "id": str(student["_id"]),
                            "name": student["name"]
                        }
                
                # Get assignment information
                assignments_collection = pipeline_db.db_manager.get_collection("assignments")
                if assignments_collection is not None:
                    assignment = await assignments_collection.find_one({"_id": assignment_id})
                    if assignment:
                        final_json["assignment"] = {
                            "id": str(assignment["_id"]),
                            "run_id": assignment["run_id"],
                            "questions": assignment.get("questions", [])
                        }
                
                # Get questions for this assignment
                questions_collection = pipeline_db.db_manager.get_collection("questions")
                if questions_collection is not None:
                    questions = await questions_collection.find({"assignment_id": assignment_id}).to_list(length=None)
                    if questions:
                        final_json["questions"] = []
                        for question in questions:
                            question_data = {
                                "id": str(question["_id"]),
                                "assignment_id": question["assignment_id"],
                                "question_identifier": question["question_identifier"],
                                "has_internal_choice": question["has_internal_choice"],
                                "primary_question": question["primary_question"],
                                "secondary_question": question.get("secondary_question"),
                                "primary_diagram_url": question.get("primary_diagram_url"),
                                "secondary_diagram_url": question.get("secondary_diagram_url"),
                                "table_url": question.get("table_url"),
                                "primary_marks": question["primary_marks"],
                                "secondary_marks": question.get("secondary_marks"),
                                "question_type": question["question_type"]
                            }
                            final_json["questions"].append(question_data)
                        final_json["metadata"]["total_questions"] = len(questions)
                
                # Get diagrams and tables from the new collections
                diagrams = await pipeline_db.get_diagrams_by_run_id(run_id)
                if diagrams:
                    final_json["diagrams"] = []
                    for diagram in diagrams:
                        diagram_data = {
                            "id": str(diagram["_id"]),
                            "run_id": diagram["run_id"],
                            "cloudinary_url": diagram["cloudinary_url"],
                            "page_number": diagram["page_number"],
                            "figure_id": diagram["figure_id"],
                            "created_at": diagram["created_at"].isoformat() if isinstance(diagram["created_at"], datetime) else str(diagram["created_at"])
                        }
                        final_json["diagrams"].append(diagram_data)
                    final_json["metadata"]["total_diagrams"] = len(diagrams)
                
                tables = await pipeline_db.get_tables_by_run_id(run_id)
                if tables:
                    final_json["tables"] = []
                    for table in tables:
                        table_data = {
                            "id": str(table["_id"]),
                            "run_id": table["run_id"],
                            "cloudinary_url": table["cloudinary_url"],
                            "page_number": table["page_number"],
                            "table_id": table["table_id"],
                            "created_at": table["created_at"].isoformat() if isinstance(table["created_at"], datetime) else str(table["created_at"])
                        }
                        final_json["tables"].append(table_data)
                    final_json["metadata"]["total_tables"] = len(tables)
                
                # Add student responses
                final_json["student_responses"] = {
                    "student_id": request.student_id,
                    "assignment_id": assignment_id,
                    "run_id": run_id,
                    "responses": [
                        {
                            "question_identifier": response.question_identifier,
                            "cloudinary_url": response.cloudinary_url
                        } for response in student_responses
                    ]
                }
                
                # Get question-response mappings for this student and assignment
                mappings_collection = pipeline_db.db_manager.get_collection("question_response_mappings")
                if mappings_collection is not None:
                    mappings = await mappings_collection.find({
                        "student_id": request.student_id,
                        "assignment_id": assignment_id
                    }).to_list(length=None)
                    if mappings:
                        final_json["question_response_mappings"] = []
                        for mapping in mappings:
                            mapping_data = {
                                "id": str(mapping["_id"]),
                                "student_id": mapping["student_id"],
                                "assignment_id": mapping["assignment_id"],
                                "run_id": mapping["run_id"],
                                "question_identifier": mapping["question_identifier"],
                                "has_internal_choice": mapping["has_internal_choice"],
                                "primary_question": mapping["primary_question"],
                                "secondary_question": mapping.get("secondary_question"),
                                "primary_diagram_url": mapping.get("primary_diagram_url"),
                                "secondary_diagram_url": mapping.get("secondary_diagram_url"),
                                "table_url": mapping.get("table_url"),
                                "primary_marks": mapping["primary_marks"],
                                "secondary_marks": mapping.get("secondary_marks"),
                                "question_type": mapping["question_type"],
                                "response_cloudinary_url": mapping["response_cloudinary_url"]
                            }
                            final_json["question_response_mappings"].append(mapping_data)
                        final_json["metadata"]["total_mappings"] = len(mappings)
                
                logger.log_step(run_id, "Final JSON Generated", 
                              f"Consolidated data with {final_json['metadata']['total_questions']} questions, {final_json['metadata']['total_responses']} responses, {final_json['metadata']['total_mappings']} mappings, {final_json['metadata']['total_diagrams']} diagrams, {final_json['metadata']['total_tables']} tables",
                              "Complete workflow data consolidated")
                
            except Exception as json_error:
                logger.log_error(run_id, "Failed to generate final JSON", json_error)
                final_json = None
        
        # Complete the run successfully
        logger.complete_run(run_id, success=True)
        
        # Return success message with final JSON
        response_data.update({
            "message": "Response processing completed and saved to database", 
            "run_id": run_id,
            "assignment_id": assignment_id
        })
        
        # Add student information to response if provided
        if request.student_id or request.student_name:
            response_data["student_id"] = request.student_id
            response_data["student_name"] = request.student_name
        
        # Add final consolidated JSON if generated
        if final_json:
            response_data["final_json"] = final_json
        
        return response_data
        
    except Exception as exc:
        logger.log_error(run_id, "Unexpected error in crop_margins", exc)
        logger.complete_run(run_id, success=False)
        raise


@app.get('/response-processing/{run_id}')
async def get_response_processing(run_id: str):
    """Get response processing results by run_id"""
    try:
        # Initialize database if not already connected
        if not pipeline_db.db_manager.is_connected():
            await initialize_database()
        
        # Get response processing results from database
        collection = pipeline_db.db_manager.get_collection("response_processing_results")
        if collection is None:
            raise HTTPException(status_code=500, detail="Database collection not found")
        
        result = await collection.find_one({"run_id": run_id})
        if not result:
            raise HTTPException(status_code=404, detail="Response processing results not found")
        
        # Convert ObjectId to string for JSON serialization
        result["_id"] = str(result["_id"])
        result["created_at"] = result["created_at"].isoformat()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve response processing results: {str(e)}")


@app.post('/upload-to-cloudinary')
async def upload_to_cloudinary(file: UploadFile = File(...)):
    """Upload a single image to Cloudinary and return the URL"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files are allowed")
        
        # Read file content
        file_content = await file.read()
        
        # Upload to Cloudinary using the existing utility function
        from .response_processing.utils import upload_single_image_to_cloudinary
        
        image_url = upload_single_image_to_cloudinary(file_content)
        
        return {"url": image_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

# =============================================================================
# NEW QUESTION EXTRACTION ENDPOINTS
# =============================================================================

@app.post('/process-cbse-paper', response_model=QuestionExtractionResponse)
async def process_cbse_paper(
    pdf_file: UploadFile = File(...),
    assignment_title: str = Form(None),
    assignment_marks: str = Form(None)
):
    """
    Run the complete CBSE question paper processing pipeline.
    
    This endpoint processes a CBSE Mathematics question paper through all steps:
    1. Extract diagrams from PDF using DocYOLO
    2. Map diagrams to questions using Gemini AI
    3. Extract questions in Markdown format using Gemini AI
    
    Returns detailed results from each step and final outputs.
    """
    print(f"[process-cbse-paper] Processing file: {pdf_file.filename}")
    print(f"[process-cbse-paper] Assignment title: {assignment_title}")
    print(f"[process-cbse-paper] Assignment marks: {assignment_marks}")
    print(f"[process-cbse-paper] File content type: {pdf_file.content_type}")
    print(f"[process-cbse-paper] File size: {pdf_file.size if hasattr(pdf_file, 'size') else 'Unknown'}")
    
    # Check dependencies
    if not DEPENDENCIES_OK:
        raise HTTPException(
            status_code=503,
            detail="Missing required dependencies. Please install PyTorch, DocLayout YOLO, and other required packages."
        )
    
    if not GEMINI_CLIENT_OK:
        raise HTTPException(
            status_code=503,
            detail="Gemini client not available. Please check your API key configuration."
        )
    
    # Validate file type
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    try:
        # Read file content
        file_content = await pdf_file.read()
        
        # Convert assignment_marks to int if provided
        assignment_marks_int = None
        if assignment_marks:
            try:
                assignment_marks_int = int(assignment_marks)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="assignment_marks must be a valid integer"
                )
        
        # Run the end-to-end processing
        results = await run_end_to_end_processing(file_content, pdf_file.filename, assignment_title, assignment_marks_int)
        
        # Build response
        response = QuestionExtractionResponse(
            success=results['success'],
            errors=results.get('errors', []),
            step_results=results.get('step_results', {}),
            final_outputs=results.get('final_outputs', {}),
            message="Processing completed successfully" if results['success'] else "Processing completed with errors"
        )
        
        print(f"[process-cbse-paper] Completed processing for {pdf_file.filename}")
        return response
        
    except Exception as e:
        print(f"[process-cbse-paper] Error processing {pdf_file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/logs/", response_class=HTMLResponse)
async def list_runs(request: Request):
    viewer = LogViewer()
    context = viewer.generate_runs_index_context()
    return templates.TemplateResponse("unified_logs_index.html", {"request": request, **context})

@app.get("/logs/{run_id}", response_class=HTMLResponse)
async def view_log(request: Request, run_id: str):
    viewer = LogViewer()
    context = viewer.generate_run_detail_context(run_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Run ID not found")
    
    template_name = viewer.get_template_name(context["log_type"])
    return templates.TemplateResponse(template_name, {"request": request, **context})


# =============================================================================
# QUESTION-RESPONSE MAPPING ENDPOINTS
# =============================================================================

@app.post('/question-response-mapping/{run_id}/create')
async def create_question_response_mappings(run_id: str):
    """
    Create question-response mappings for a specific run_id.
    
    This endpoint maps questions to student responses based on the ANS-<number> pattern
    in the answer_label field, where the number matches the question_identifier.
    
    Args:
        run_id: The run identifier
        
    Returns:
        Mapping results with success status and details
    """
    try:
        from .response_processing.question_response_mapping import QuestionResponseMappingService
        
        result = await QuestionResponseMappingService.create_mappings_for_run_id(run_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Successfully created {result['mappings_created']} mappings",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Failed to create mappings"),
                "data": result
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create mappings: {str(e)}")


@app.get('/question-response-mapping/{run_id}')
async def get_question_response_mappings(run_id: str):
    """
    Get all question-response mappings for a specific run_id.
    
    Args:
        run_id: The run identifier
        
    Returns:
        List of question-response mappings
    """
    try:
        from .response_processing.question_response_mapping import QuestionResponseMappingService
        
        result = await QuestionResponseMappingService.get_mappings_for_run_id(run_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Found {result['total_mappings']} mappings",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Failed to retrieve mappings"),
                "data": result
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve mappings: {str(e)}")


@app.get('/question-response-mapping/{run_id}/question/{question_identifier}')
async def get_question_response_mapping(run_id: str, question_identifier: str):
    """
    Get question-response mapping for a specific question.
    
    Args:
        run_id: The run identifier
        question_identifier: The question identifier
        
    Returns:
        Question-response mapping data
    """
    try:
        from .response_processing.question_response_mapping import QuestionResponseMappingService
        
        result = await QuestionResponseMappingService.get_mapping_for_question(run_id, question_identifier)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Mapping found",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Mapping not found"),
                "data": result
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve mapping: {str(e)}")


@app.get('/final-json/{run_id}')
async def get_final_consolidated_json(run_id: str):
    """
    Generate final consolidated JSON combining all data for a specific run_id.
    
    This endpoint creates a comprehensive JSON that includes:
    - Teacher information
    - Student information
    - Assignment details
    - Questions
    - Student responses
    - Question-response mappings
    
    Args:
        run_id: The run identifier
        
    Returns:
        Consolidated JSON with all related data
    """
    try:
        from database.connection import pipeline_db
        from database.integration import get_db_integration
        
        # Initialize database integration
        db_integration = get_db_integration()
        await db_integration.initialize()
        
        # Get student assignment response to extract student_id and assignment_id
        responses_data = await pipeline_db.get_responses_by_run_id(run_id)
        if not responses_data:
            raise HTTPException(status_code=404, detail=f"No student responses found for run_id: {run_id}")
        
        student_id = responses_data.get("student_id")
        assignment_id = responses_data.get("assignment_id")
        
        if not student_id or not assignment_id:
            raise HTTPException(status_code=400, detail="Missing student_id or assignment_id in response data")
        
        # Build consolidated JSON
        final_json = {
            "run_id": run_id,
            "generated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "total_questions": 0,
                "total_responses": 0,
                "total_mappings": 0,
                "total_diagrams": 0,
                "total_tables": 0
            }
        }
        
        # Get teacher information (assuming single teacher for now)
        teachers_collection = pipeline_db.db_manager.get_collection("teachers")
        if teachers_collection is not None:
            teacher = await teachers_collection.find_one()
            if teacher:
                final_json["teacher"] = {
                    "id": str(teacher["_id"]),
                    "name": teacher["name"],
                    "class_name": teacher["class_name"],
                    "board": teacher["board"]
                }
        
        # Get student information
        students_collection = pipeline_db.db_manager.get_collection("students")
        if students_collection is not None:
            student = await students_collection.find_one({"_id": student_id})
            if student:
                final_json["student"] = {
                    "id": str(student["_id"]),
                    "name": student["name"]
                }
        
        # Get assignment information
        assignments_collection = pipeline_db.db_manager.get_collection("assignments")
        if assignments_collection is not None:
            assignment = await assignments_collection.find_one({"_id": assignment_id})
            if assignment:
                final_json["assignment"] = {
                    "id": str(assignment["_id"]),
                    "run_id": assignment["run_id"],
                    "questions": assignment.get("questions", [])
                }
        
        # Get questions
        questions = await pipeline_db.get_questions_by_run_id(run_id)
        if questions:
            final_json["questions"] = []
            for question in questions:
                question_data = {
                    "id": str(question["_id"]),
                    "assignment_id": question["assignment_id"],
                    "question_identifier": question["question_identifier"],
                    "has_internal_choice": question["has_internal_choice"],
                    "primary_question": question["primary_question"],
                    "secondary_question": question.get("secondary_question"),
                    "primary_diagram_url": question.get("primary_diagram_url"),
                    "secondary_diagram_url": question.get("secondary_diagram_url"),
                    "table_url": question.get("table_url"),
                    "primary_marks": question["primary_marks"],
                    "secondary_marks": question.get("secondary_marks"),
                    "question_type": question["question_type"]
                }
                final_json["questions"].append(question_data)
            final_json["metadata"]["total_questions"] = len(questions)
        
        # Get diagrams and tables from the new collections
        diagrams = await pipeline_db.get_diagrams_by_run_id(run_id)
        if diagrams:
            final_json["diagrams"] = []
            for diagram in diagrams:
                diagram_data = {
                    "id": str(diagram["_id"]),
                    "run_id": diagram["run_id"],
                    "cloudinary_url": diagram["cloudinary_url"],
                    "page_number": diagram["page_number"],
                    "figure_id": diagram["figure_id"],
                    "created_at": diagram["created_at"].isoformat() if isinstance(diagram["created_at"], datetime) else str(diagram["created_at"])
                }
                final_json["diagrams"].append(diagram_data)
            final_json["metadata"]["total_diagrams"] = len(diagrams)
        
        tables = await pipeline_db.get_tables_by_run_id(run_id)
        if tables:
            final_json["tables"] = []
            for table in tables:
                table_data = {
                    "id": str(table["_id"]),
                    "run_id": table["run_id"],
                    "cloudinary_url": table["cloudinary_url"],
                    "page_number": table["page_number"],
                    "table_id": table["table_id"],
                    "created_at": table["created_at"].isoformat() if isinstance(table["created_at"], datetime) else str(table["created_at"])
                }
                final_json["tables"].append(table_data)
            final_json["metadata"]["total_tables"] = len(tables)
        
        # Get student responses
        if responses_data:
            final_json["student_responses"] = {
                "id": str(responses_data["_id"]),
                "student_id": responses_data["student_id"],
                "assignment_id": responses_data["assignment_id"],
                "run_id": responses_data["run_id"],
                "responses": responses_data.get("student_responses", [])
            }
            final_json["metadata"]["total_responses"] = len(responses_data.get("student_responses", []))
        
        # Get question-response mappings
        mappings = await pipeline_db.get_question_response_mappings_by_run_id(run_id)
        if mappings:
            final_json["question_response_mappings"] = []
            for mapping in mappings:
                mapping_data = {
                    "id": str(mapping["_id"]),
                    "student_id": mapping["student_id"],
                    "assignment_id": mapping["assignment_id"],
                    "run_id": mapping["run_id"],
                    "question_identifier": mapping["question_identifier"],
                    "has_internal_choice": mapping["has_internal_choice"],
                    "primary_question": mapping["primary_question"],
                    "secondary_question": mapping.get("secondary_question"),
                    "primary_diagram_url": mapping.get("primary_diagram_url"),
                    "secondary_diagram_url": mapping.get("secondary_diagram_url"),
                    "table_url": mapping.get("table_url"),
                    "primary_marks": mapping["primary_marks"],
                    "secondary_marks": mapping.get("secondary_marks"),
                    "question_type": mapping["question_type"],
                    "response_cloudinary_url": mapping["response_cloudinary_url"]
                }
                final_json["question_response_mappings"].append(mapping_data)
            final_json["metadata"]["total_mappings"] = len(mappings)
        
        return {
            "success": True,
            "message": f"Final consolidated JSON generated for run_id: {run_id}",
            "data": final_json
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate final JSON: {str(e)}")

@app.get('/api/current-teacher')
async def get_current_teacher():
    """
    Get the current teacher information.
    
    Returns:
        Teacher information including name, class, and board
    """
    try:
        from database.connection import pipeline_db
        
        # Get teacher information (assuming single teacher for now)
        teachers_collection = pipeline_db.db_manager.get_collection("teachers")
        if teachers_collection is None:
            raise HTTPException(status_code=404, detail="Teachers collection not found")
        
        teacher = await teachers_collection.find_one()
        if not teacher:
            raise HTTPException(status_code=404, detail="No teacher found in database")
        
        return {
            "success": True,
            "teacher": {
                "id": str(teacher["_id"]),
                "name": teacher["name"],
                "class_name": teacher["class_name"],
                "board": teacher["board"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get teacher information: {str(e)}")

@app.get('/api/assignments')
async def get_assignments():
    """
    Get all assignments with their details.
    
    Returns:
        List of assignments with questions and metadata
    """
    try:
        from database.connection import pipeline_db
        
        # Get assignments collection
        assignments_collection = pipeline_db.db_manager.get_collection("assignments")
        if assignments_collection is None:
            raise HTTPException(status_code=404, detail="Assignments collection not found")
        
        # Get questions collection
        questions_collection = pipeline_db.db_manager.get_collection("questions")
        
        # Get all assignments
        assignments = await assignments_collection.find().to_list(length=None)
        
        # Get questions for each assignment
        questions_collection = pipeline_db.db_manager.get_collection("questions")
        assignments_with_details = []
        
        for assignment in assignments:
            assignment_data = {
                "id": str(assignment["_id"]),
                "run_id": assignment["run_id"],
                "title": assignment.get("title", f"Assignment {assignment['run_id']}"),
                "total_marks": assignment.get("total_marks", 100),
                "questions": assignment.get("questions", []),
                "created_at": assignment["created_at"],
                "updated_at": assignment["updated_at"]
            }
            
            # Get questions for this assignment
            if questions_collection is not None:
                questions = await questions_collection.find({"assignment_id": assignment_data["id"]}).to_list(length=None)
                assignment_data["question_details"] = []
                
                for question in questions:
                    question_data = {
                        "id": str(question["_id"]),
                        "question_identifier": question["question_identifier"],
                        "has_internal_choice": question["has_internal_choice"],
                        "primary_question": question["primary_question"],
                        "secondary_question": question.get("secondary_question"),
                        "primary_diagram_url": question.get("primary_diagram_url"),
                        "secondary_diagram_url": question.get("secondary_diagram_url"),
                        "table_url": question.get("table_url"),
                        "primary_marks": question["primary_marks"],
                        "secondary_marks": question.get("secondary_marks"),
                        "question_type": question["question_type"]
                    }
                    assignment_data["question_details"].append(question_data)
                
                assignment_data["total_questions"] = len(assignment_data["question_details"])
            
            assignments_with_details.append(assignment_data)
        
        return {
            "success": True,
            "assignments": assignments_with_details,
            "total_assignments": len(assignments_with_details)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get assignments: {str(e)}")