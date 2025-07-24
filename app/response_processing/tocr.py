import os
import uuid
import base64
import json
import io
from typing import List, Dict
from pathlib import Path

# Load the GenAI client from google-generativeai
try:
    import google.generativeai as genai
except ImportError:
    raise ImportError(
        "GenAI client not found: please install 'google-generativeai'"
    )


def _configure_genai():
    """
    Configure the Gemini API using the GEMINI_API_KEY environment variable.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment")
    if genai is None:
        raise RuntimeError("GenAI client not available: please install 'google-generativeai'")
    genai.configure(api_key=api_key)


def extract_answers_from_margin(margin_image_bytes: bytes) -> List[str]:
    """
    Send the margin-cropped image to Gemini and extract ordered answer labels.

    Args:
        margin_image_bytes: JPEG or PNG bytes of the left-margin strip.

    Returns:
        A list of answer labels in top-to-bottom order, e.g. ["ANS-1", "ANS-2", ...].

    Raises:
        ValueError if the response cannot be parsed or lacks the expected structure.
    """
    # Debug: save the margin image sent to Gemini for inspection
    try:
        log_dir = Path(__file__).parent.parent.parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        img_path = log_dir / f'margin_input_{uuid.uuid4().hex}.jpg'
        with open(img_path, 'wb') as f:
            f.write(margin_image_bytes)
        print(f"\033[91m[extract_answers_from_margin] Margin image saved to: {img_path}\033[0m")
    except Exception as e:
        print(f"[extract_answers_from_margin] Failed to save margin image: {e}")
    
    # Load image using PIL for proper format
    from PIL import Image as PILImage
    image = PILImage.open(io.BytesIO(margin_image_bytes))
    
    # Simple prompt as requested
    prompt_text = (
        "Identify all answer labels in this margin-stripped image, ordered top-to-bottom. "
        "Return ONLY a JSON object in the form {\"answers\": [\"ANS-<number>\", \"ANS-<number>\", ...]}, with no additional text or formatting."
    )
    
    _configure_genai()
    # Call the Gemini model using google-generativeai API
    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    response = model.generate_content(
        [prompt_text, image],
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    raw = response.text
    print(f"\n{'='*60}")
    print(f"🧠 GEMINI RESPONSE")
    print(f"{'='*60}")
    print(f"📄 Raw response: {raw}")
    print(f"{'='*60}")
    
    # Log the response to file
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'gemini_margin.log'
    try:
        with open(log_file, 'a') as f:
            f.write(f"Raw Gemini output: {raw}\n")
            f.write("---\n")
    except Exception:
        pass
    
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse Gemini output as JSON: {e}")
        print(f"📄 Raw output: {raw}")
        raise ValueError(f"Failed to parse Gemini output as JSON: {e}\nRaw output: {raw}")
    
    answers = data.get("answers")
    print(f"✅ Parsed answers: {answers}")
    print(f"{'='*60}\n")
    
    if not isinstance(answers, list):
        raise ValueError(f"Gemini response JSON missing 'answers' list: {data}")
    
    return answers


def merge_answers_with_ocr(answers: List[str], ocr_boxes: List[Dict]) -> List[Dict]:
    """
    Merge cleaned labels from Gemini with OCR-detected boxes in positional order.

    Args:
        answers: List of labels from Gemini, e.g. ["ANS-1", "ANS-2", ...].
        ocr_boxes: List of dicts each with 'coords' and 'text'.

    Returns:
        A new list of dicts, each containing:
          - 'coords': original bounding box coordinates
          - 'text': the cleaned label from Gemini

    Raises:
        ValueError if the lengths differ.
    """
    print(f"\n{'='*60}")
    print(f"🔗 MERGING DETAILS")
    print(f"{'='*60}")
    
    if len(answers) != len(ocr_boxes):
        print(f"❌ MISMATCH: Gemini answers ({len(answers)}) != OCR boxes ({len(ocr_boxes)})")
        raise ValueError(
            f"Mismatch between number of Gemini answers ({len(answers)}) and OCR boxes ({len(ocr_boxes)})"
        )
    
    print(f"✅ MATCH: {len(answers)} Gemini answers and {len(ocr_boxes)} OCR boxes")
    print(f"\n📋 MERGING TABLE:")
    print(f"{'='*60}")
    print(f"{'Position':<8} {'OCR Text':<15} {'→':<3} {'Gemini Label':<15} {'Coordinates':<20}")
    print(f"{'='*60}")
    
    merged = []
    for i, (label, box) in enumerate(zip(answers, ocr_boxes)):
        coords = box.get("coords")
        ocr_text = box.get("text", "")
        merged_item = {
            "coords": coords,
            "text": label  # Override the raw OCR text with the cleaned label
        }
        merged.append(merged_item)
        
        # Display the merging process
        coord_str = f"[{coords[0]},{coords[1]},{coords[2]},{coords[3]}]" if coords else "N/A"
        print(f"{i+1:<8} {ocr_text:<15} {'→':<3} {label:<15} {coord_str:<20}")
    
    print(f"{'='*60}")
    print(f"✅ Successfully merged {len(merged)} items")
    print(f"{'='*60}\n")
    
    return merged 