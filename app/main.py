from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import httpx
from dotenv import load_dotenv
from .utils import margin_crop_images, process_crop_for_image, crop_questions_full_width, merge_continued_headers,upload_crops_to_cloudinary
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

@app.get('/')
async def health_check():
    return {'status': 'ok'}

@app.post('/crop-margins', response_model=UploadsResponse)
async def crop_margins(request: CropRequest):
    print(f"[crop-margins] Received URLs: {request.urls}")
    if not request.urls:
        raise HTTPException(status_code=400, detail='`urls` list is empty')

    # Chunk 1: set up logging directories
    run_id = uuid.uuid4().hex
    run_dir = LOGS_ROOT / run_id
    for sub in ["margins", "annotations", "crops", "merged"]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    # Initialize metadata with steps log
    metadata = {"run_id": run_id, "urls": request.urls, "steps": []}
    # Log initial step
    metadata['steps'].append({"name": "Received URLs", "input": request.urls, "output": ""})

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
                metadata['steps'].append({"name": "Downloaded Image", "input": url, "output": f"{len(response.content)} bytes"})
            except Exception as exc:
                print(f"[crop-margins] Failed to download {url}: {type(exc).__name__}: {repr(exc)}")
                traceback.print_exc()
                raise HTTPException(status_code=502, detail=f'Failed to download image {url}: {type(exc).__name__}: {exc}')

    try:
        margins = margin_crop_images(images)
        print(f"[crop-margins] Computed margins: {margins}")
        metadata['steps'].append({"name": "Margin Detection", "input": f"{len(images)} images", "output": margins})
    except Exception as exc:
        print(f"[crop-margins] margin_crop_images error: {exc}", exc_info=True)
        metadata['steps'].append({"name": "Margin Detection Error", "input": images, "output": str(exc)})
        raise HTTPException(status_code=500, detail=f'margin crop failed: {exc}')

    results = []
    for idx, (content, margin) in enumerate(zip(images, margins)):
        try:
            cr = process_crop_for_image(content, margin)
            print(f"[crop-margins] Page {idx} processed -> margin={cr.margin}, boxes={len(cr.boxes)}")
            metadata['steps'].append({"name": "Process Page", "input": {"page": idx, "margin": margin}, "output": {"boxes": len(cr.boxes)}})
            # Log extracted answer labels from margin for this page
            labels = [b.text for b in cr.boxes]
            metadata['steps'].append({"name": "Extract Answers", "input": {"page": idx}, "output": labels})
        except Exception as exc:
            print(f"[crop-margins] process_crop_for_image error on page {idx}: {exc}", exc_info=True)
            cr = CropResult(margin=margin, boxes=[])
        results.append(cr)
    # Log number of boxes extracted per page
    metadata['steps'].append({
        "name": "Extract Boxes",
        "input": f"{len(images)} pages",
        "output": [len(cr.boxes) for cr in results]
    })

    # Chunk 2: log raw and margin-cropped images and prepare page metadata
    cv_images = [cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR) for content in images]
    metadata['pages'] = []
    for idx, (img, margin) in enumerate(zip(cv_images, margins)):
        # Save raw image
        raw_path = run_dir / 'margins' / f'page_{idx}_raw.jpg'
        cv2.imwrite(str(raw_path), img)
        # Save margin-cropped image
        h, w = img.shape[:2]
        if 0 < margin < w:
            cropped = img[:, :margin]
        else:
            cropped = img
        cropped_path = run_dir / 'margins' / f'page_{idx}_cropped.jpg'
        cv2.imwrite(str(cropped_path), cropped)
        # Initialize metadata for this page
        metadata['pages'].append({
            'raw': f"margins/{raw_path.name}",
            'cropped': f"margins/{cropped_path.name}",
            'margin': margin
        })
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
        ann_path = run_dir / 'annotations' / f'page_{idx}.jpg'
        cv2.imwrite(str(ann_path), ann_img)
        metadata['pages'][idx]['annotation'] = f"annotations/{ann_path.name}"
        metadata['pages'][idx]['boxes'] = [
            {'coords': b.coordinates, 'text': b.text}
            for b in cr.boxes
        ]
    # STEP: slice and merge headers across pages
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
    metadata['steps'].append({"name": "Page Crops", "input": pages_boxes, "output": [list(c.keys()) for c in pages_crops]})
    merged_crops = merge_continued_headers(pages_crops)
    metadata['steps'].append({"name": "Merge Headers", "input": [list(c.keys()) for c in pages_crops], "output": [c[0] for c in merged_crops]})
    # Chunk 2: save question crops and merged images
    # Save per-page question crops
    for idx, crops in enumerate(pages_crops):
        page_crops = []
        for label, (img, text) in crops.items():
            safe = re.sub(r"\W+", "_", label)
            crop_path = run_dir / 'crops' / f'page_{idx}_{safe}.jpg'
            # Convert RGB back to BGR for saving
            cv2.imwrite(str(crop_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            page_crops.append({ 'label': label, 'text': text, 'file': f"crops/{crop_path.name}" })
        metadata['pages'][idx]['crops'] = page_crops
    # Save merged question images
    metadata['merged'] = []
    for label, img, text in merged_crops:
        safe = re.sub(r"\W+", "_", label)
        merge_path = run_dir / 'merged' / f'{safe}.jpg'
        cv2.imwrite(str(merge_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        metadata['merged'].append({ 'label': label, 'text': text, 'file': f"merged/{merge_path.name}" })
    # Write updated metadata including steps
    with open(run_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    # Upload merged question crops to Cloudinary
    uploads_meta = upload_crops_to_cloudinary(merged_crops)
    # Log upload results
    metadata['steps'].append({
        "name": "Upload to Cloudinary",
        "input": f"{len(merged_crops)} items",
        "output": [u['image_url'] for u in uploads_meta]
    })
    # Build and return final response
    return UploadsResponse(
        uploads=[
            AnswerUpload(
                question_id=u['question_id'],
                image_url=u['image_url']
            ) for u in uploads_meta
        ]
    )



@app.get("/logs/", response_class=HTMLResponse)
async def list_runs(request: Request):
    run_ids = sorted([p.name for p in LOGS_ROOT.iterdir() if p.is_dir()])
    return templates.TemplateResponse("index.html", {"request": request, "runs": run_ids})

@app.get("/logs/{run_id}", response_class=HTMLResponse)
async def view_log(request: Request, run_id: str):
    run_dir = LOGS_ROOT / run_id
    metadata_file = run_dir / "metadata.json"
    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail="Run ID not found")
    metadata = json.loads(metadata_file.read_text())
    static_url = f"/logs/static/{run_id}/"
    return templates.TemplateResponse("log.html", {"request": request, "metadata": metadata, "static_url": static_url})