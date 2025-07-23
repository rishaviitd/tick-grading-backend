# this is the backend for the demo

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List
import httpx
from dotenv import load_dotenv
from .response_processing.utils import margin_crop_images, process_crop_for_image, crop_questions_full_width, merge_continued_headers,upload_crops_to_cloudinary
from .question_parsing.question_extraction import (
    run_end_to_end_processing,
    DEPENDENCIES_OK,
    GEMINI_CLIENT_OK
)
from .logging import UnifiedLogger, LogType, LogViewer
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

class CropRequest(BaseModel):
    urls: List[str]

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

@app.get('/')
async def health_check():
    return {'status': 'ok'}

@app.get('/demo', response_class=HTMLResponse)
async def demo_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post('/crop-margins', response_model=UploadsResponse)
async def crop_margins(request: CropRequest):
    print(f"[crop-margins] Received URLs: {request.urls}")
    if not request.urls:
        raise HTTPException(status_code=400, detail='`urls` list is empty')

    # Initialize unified logger
    logger = UnifiedLogger()
    run_id = logger.create_run(LogType.RESPONSE_PROCESSING, "Response Processing", {"urls": request.urls})
    
    try:
        logger.log_step(run_id, "Received URLs", request.urls)
        
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
        
        # Complete the run successfully
        logger.complete_run(run_id, success=True)
        
        # Build and return final response
        return UploadsResponse(
            uploads=[
                AnswerUpload(
                    question_id=u['question_id'],
                    image_url=u['image_url']
                ) for u in uploads_meta
            ]
        )
        
    except Exception as exc:
        logger.log_error(run_id, "Unexpected error in crop_margins", exc)
        logger.complete_run(run_id, success=False)
        raise

# =============================================================================
# NEW QUESTION EXTRACTION ENDPOINTS
# =============================================================================

@app.post('/process-cbse-paper', response_model=QuestionExtractionResponse)
async def process_cbse_paper(pdf_file: UploadFile = File(...)):
    """
    Run the complete CBSE question paper processing pipeline.
    
    This endpoint processes a CBSE Mathematics question paper through all steps:
    1. Extract diagrams from PDF using DocYOLO
    2. Map diagrams to questions using Gemini AI
    3. Extract questions in Markdown format using Gemini AI
    
    Returns detailed results from each step and final outputs.
    """
    print(f"[process-cbse-paper] Processing file: {pdf_file.filename}")
    
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
        
        # Run the end-to-end processing
        results = await run_end_to_end_processing(file_content, pdf_file.filename)
        
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