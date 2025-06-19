import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import os
import base64
import httpx
import google.auth
from google.auth.transport.requests import Request
import cloudinary.uploader
import cloudinary
from io import BytesIO
from dotenv import load_dotenv
import boto3
from .tocr import extract_answers_from_margin, merge_answers_with_ocr

load_dotenv()  # Load .env variables

# Configure Cloudinary using loaded environment variables
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

def margin_crop_images(image_bytes_list: List[bytes]) -> List[int]:
    '''
    Perform Sobel vertical margin crop on each image bytes.
    Returns a list of margin_x values corresponding to each image.
    '''
    margins = []
    for content in image_bytes_list:
        arr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            margins.append(0)
            continue
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        sobelx = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
        abs_sobelx = np.absolute(sobelx)
        scaled_sobel = np.uint8(255 * abs_sobelx / np.max(abs_sobelx))
        _, binary = cv2.threshold(scaled_sobel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, max(5, h // 50)))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        left_region = closed[:, :w // 2]
        col_sums = np.sum(left_region, axis=0)
        # region width ~10% of full width for brightness comparison
        d = max(1, int(w * 0.05))
        scores = []
        for i, s in enumerate(col_sums):
            # skip if too close to left edge for sampling
            if i < d:
                scores.append(0.0)
                continue
            # sample brightness strips in grayscale
            left_strip = gray[:, i-d:i]
            right_strip = gray[:, i:i+d]
            mean_l = float(np.mean(left_strip))
            mean_r = float(np.mean(right_strip))
            diff = abs(mean_l - mean_r)
            # similarity factor: high when brightness is similar
            sim = 1.0 / (1.0 + diff)
            scores.append(s * sim)
        # choose column with highest combined score
        margin_x = int(np.argmax(scores))
        margins.append(margin_x)
    return margins

def process_crop_for_image(content: bytes, margin: int):
    """Process a single image by cropping using margin, calling Google Document AI, and returning a CropResult"""
    from .main import CropResult, Box
    arr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return CropResult(margin=margin, boxes=[])
    cropped_img = img[:, :margin] if margin > 0 else img
    success, buffer = cv2.imencode('.jpg', cropped_img)
    if not success:
        return CropResult(margin=margin, boxes=[])
    cropped_bytes = buffer.tobytes()
    # Use AWS Textract instead of Google Document AI
    client = boto3.client(
        'textract',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    try:
        response = client.detect_document_text(Document={'Bytes': cropped_bytes})
    except Exception:
        return CropResult(margin=margin, boxes=[])
    boxes_data = []
    h, w = cropped_img.shape[:2]
    for block in response.get('Blocks', []):
        if block.get('BlockType') != 'LINE':
            continue
        bbox = block.get('Geometry', {}).get('BoundingBox', {})
        left, top = bbox.get('Left', 0), bbox.get('Top', 0)
        width, height = bbox.get('Width', 0), bbox.get('Height', 0)
        x1 = int(left * w)
        y1 = int(top * h)
        x2 = int((left + width) * w)
        y2 = int((top + height) * h)
        text = block.get('Text', '')
        boxes_data.append(Box(coordinates=[x1, y1, x2, y2], text=text))
    # Attempt to correct OCR labels using Gemini vision margin extraction
    try:
        # Build simple OCR box list for merging
        ocr_boxes = [{"coords": b.coordinates, "text": b.text} for b in boxes_data]
        print(f"[process_crop_for_image] OCR detected {len(ocr_boxes)} boxes: {[b['text'] for b in ocr_boxes]}")
        # Pass image to Gemini for answer extraction
        answers = extract_answers_from_margin(cropped_bytes)
        print(f"[process_crop_for_image] Gemini returned {len(answers)} answers: {answers}")
        merged = merge_answers_with_ocr(answers, ocr_boxes)
        # Rebuild boxes_data with merged labels
        boxes_data = [Box(coordinates=m["coords"], text=m["text"]) for m in merged]
        print(f"[process_crop_for_image] Final merged labels: {[b.text for b in boxes_data]}")
    except Exception as e:
        print(f"[process_crop_for_image] Answer merge failed: {e}")
        import traceback
        traceback.print_exc()
    return CropResult(margin=margin, boxes=boxes_data)

def extend_boxes_to_full_width(boxes_json: List[dict], full_width: int) -> List[dict]:
    """
    Extend each bounding box to span the full page width, preserving its vertical position and height.

    Args:
        boxes_json: List of boxes, each with a 'bbox' tuple (x, y, w, h) and optional other keys.
        full_width: The width of the page to extend boxes across.

    Returns:
        A new list of boxes where each 'bbox' is reset to (0, y, full_width, h).
    """
    extended = []
    for box in boxes_json:
        # Unpack original bbox; default to (0,0,0,0) if missing
        x, y, w, h = box.get("bbox", (0, 0, 0, 0))
        new_box = box.copy()
        new_box["bbox"] = (0, y, full_width, h)
        extended.append(new_box)
    return extended

def crop_questions_full_width(
    original_image: np.ndarray,
    boxes_json: List[dict],
    mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Tuple[np.ndarray, str]]:
    """
    Crop questions from the original full-width image using extended bounding boxes.
    Each crop extends from the top of the current bounding box to the top of the next box.
    For the first box, the crop starts from the top of the image to include any content above.
    Returns a dict mapping question IDs (or 'header') to (RGB_crop, ocr_text).
    """
    if mapping is None:
        mapping = {}
    # image dimensions
    height, width = original_image.shape[:2]
    # extend boxes horizontally
    extended = extend_boxes_to_full_width(boxes_json, width)
    # convert to RGB for consistent display
    disp_img = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
    crops: Dict[str, Tuple[np.ndarray, str]] = {}
    # build and sort regions
    regions: List[Dict[str, object]] = []
    for box in extended:
        idx = box.get("id")
        # extract OCR text for this margin label
        ocr_text = box.get("text", "").strip()
        # use OCR text as question ID if available, otherwise fallback to mapping or index
        if ocr_text:
            label = ocr_text
        else:
            label = mapping.get(str(idx), str(idx))
        if label == "skip":
            continue
        x, y, w, h = box.get("bbox", (0, 0, 0, 0))
        regions.append({"id": label, "y_min": y, "ocr_text": ocr_text})
    regions.sort(key=lambda r: r["y_min"])
    # header above first question
    if regions:
        first_y = regions[0]["y_min"]
        if first_y > 0:
            crops["header"] = (disp_img[0:first_y, :], "")
    # crop each question region
    for i, r in enumerate(regions):
        y_min = r["y_min"]
        y_max = regions[i+1]["y_min"] if i+1 < len(regions) else height
        if 0 <= y_min < y_max <= height:
            crops[r["id"]] = (disp_img[y_min:y_max, :], r.get("ocr_text", ""))
    return crops

def merge_continued_headers(
    pages_crops: List[Dict[str, Tuple[np.ndarray, str]]]
) -> List[Tuple[str, np.ndarray, str]]:
    """
    Merge 'header' crops (continuations) from each page into the preceding question crop.

    Args:
        pages_crops: Ordered list of per-page crop dicts from crop_questions_full_width.
    Returns:
        A list of tuples (question_id, image_crop, ocr_text) with headers merged.
    """
    merged: List[Tuple[str, np.ndarray, str]] = []
    for page_idx, crops in enumerate(pages_crops):
        header_item = crops.get('header')
        if page_idx == 0:
            # For first page, just take all non-header crops in order
            for label, (img, text) in crops.items():
                if label == 'header':
                    continue
                merged.append((label, img, text))
        else:
            # Merge header into last question if present
            if header_item:
                header_img, header_text = header_item
                if merged:
                    last_id, last_img, last_text = merged[-1]
                    # Ensure both images have same width before vertical stack
                    h1, w1 = last_img.shape[:2]
                    h2, w2 = header_img.shape[:2]
                    max_w = max(w1, w2)
                    # pad last_img if needed
                    if w1 < max_w:
                        pad_last = np.full((h1, max_w, last_img.shape[2]), 255, dtype=last_img.dtype)
                        pad_last[:, :w1, :] = last_img
                        last_img = pad_last
                    # pad header_img if needed
                    if w2 < max_w:
                        pad_header = np.full((h2, max_w, header_img.shape[2]), 255, dtype=header_img.dtype)
                        pad_header[:, :w2, :] = header_img
                        header_img = pad_header
                    # Concatenate vertically
                    concat_img = np.vstack([last_img, header_img])
                    concat_text = last_text + header_text
                    merged[-1] = (last_id, concat_img, concat_text)
            # Append this page's new questions
            for label, (img, text) in crops.items():
                if label == 'header':
                    continue
                merged.append((label, img, text))
    return merged

def upload_crops_to_cloudinary(
    crops: List[Tuple[str, np.ndarray, str]]
) -> List[Dict[str, str]]:
    """
    Upload question crops to Cloudinary and return list of metadata dicts.

    Args:
        crops: List of tuples (question_id, image_rgb, ocr_text).
    Returns:
        [{'question_id': id, 'image_url': url, 'ocr_text': text}, ...]
    """
    uploads: List[Dict[str, str]] = []
    for qid, img, text in crops:
        # Convert RGB image back to BGR for OpenCV
        bgr_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        success, buf = cv2.imencode('.jpg', bgr_img)
        if not success:
            continue
        blob = BytesIO(buf.tobytes())
        result = cloudinary.uploader.upload(
            blob,
            resource_type='image',
            format='jpg'
        )
        uploads.append({
            'question_id': qid,
            'image_url': result.get('secure_url', ''),
            'ocr_text': text
        })
    return uploads 