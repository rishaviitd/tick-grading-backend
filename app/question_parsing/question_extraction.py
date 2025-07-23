import os
import sys
import re
import json
import torch
import torchvision
import tempfile
import time
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import fitz
from pdf2image import convert_from_bytes
import hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import types
from huggingface_hub import snapshot_download
from doclayout_yolo import YOLOv10
import cv2
import io
import base64
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
from collections import defaultdict
from ..logging import UnifiedLogger, LogType
from pathlib import Path
import cloudinary.uploader
import cloudinary
from io import BytesIO
from database import get_db_integration

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

# Environment variable for Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Environment variable GEMINI_API_KEY must be set")

# Dependency checks
def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import torch
        import torchvision
    except ImportError:
        missing_deps.append("PyTorch")
    
    try:
        from google import genai
    except ImportError:
        missing_deps.append("Google Genai")
    
    try:
        from doclayout_yolo import YOLOv10
    except ImportError:
        missing_deps.append("DocLayout YOLO")
    
    try:
        import fitz  # PyMuPDF
    except ImportError:
        missing_deps.append("PyMuPDF")
    
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        missing_deps.append("pdf2image")
    
    if missing_deps:
        error_msg = f"Missing required dependencies: {', '.join(missing_deps)}"
        raise ImportError(error_msg)
    
    return True

# Check dependencies on import
try:
    check_dependencies()
    DEPENDENCIES_OK = True
except ImportError as e:
    print(f"Dependency check failed: {e}")
    DEPENDENCIES_OK = False

# Initialize Gemini client
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    GEMINI_CLIENT_OK = True
except Exception as e:
    print(f"Failed to initialize Gemini client: {e}")
    GEMINI_CLIENT_OK = False

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_dir_exists(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_output_filename(page_num, total_pages):
    """Generate formatted filename for page"""
    padding = len(str(total_pages))
    return f"page_{page_num:0{padding}d}.pdf"

# =============================================================================
# DIAGRAM EXTRACTION FUNCTIONS
# =============================================================================

def _load_model():
    """Load the DocLayout YOLO model"""
    try:
        # Check if CUDA is available
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if device == 'cuda':
            print("Using CUDA GPU for model inference")
        else:
            print("Using CPU for model inference")
            
        # Create models directory in the question_parsing folder
        models_dir = os.path.join(os.path.dirname(__file__), 'models', 'DocLayout-YOLO-DocStructBench')
        model_dir = snapshot_download(
            'juliozhao/DocLayout-YOLO-DocStructBench',
            local_dir=os.path.abspath(models_dir)
        )
        model_path = os.path.join(model_dir, 'doclayout_yolo_docstructbench_imgsz1024.pt')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
            
        model = YOLOv10(model_path)
        return model, device
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        return None, None

# Global model initialization
_model, _device = _load_model()

# Mapping of class IDs to names
ID_TO_NAMES = {
    0: 'title',
    1: 'plain text',
    2: 'abandon',
    3: 'figure',
    4: 'figure_caption',
    5: 'table',
    6: 'table_caption',
    7: 'table_footnote',
    8: 'isolate_formula',
    9: 'formula_caption'
}

def visualize_bbox(image, boxes, classes, scores, id_to_names):
    """Visualize bounding boxes on image"""
    try:
        # Convert PIL image to numpy array
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # Create figure and axis
        fig, ax = plt.subplots(1, figsize=(12, 8))
        ax.imshow(image)
        
        # Draw bounding boxes
        for box, cls, score in zip(boxes, classes, scores):
            x1, y1, x2, y2 = box
            width = x2 - x1
            height = y2 - y1
            
            # Create rectangle
            rect = Rectangle((x1, y1), width, height, 
                           linewidth=2, edgecolor='red', facecolor='none')
            ax.add_patch(rect)
            
            # Add label
            label = f"{id_to_names.get(int(cls), 'unknown')} {score:.2f}"
            ax.text(x1, y1-5, label, fontsize=8, color='red', 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
        
        ax.axis('off')
        
        # Convert matplotlib figure to PIL Image
        fig.canvas.draw()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        result_image = Image.open(buf)
        plt.close(fig)
        
        return np.array(result_image)
        
    except Exception as e:
        print(f"Error in visualization: {str(e)}")
        return image

# Replace the old log_diagram_snippets function
def log_diagram_snippets(figure_snippets: List[List]) -> Tuple[str, str]:
    """Save figure snippets and create metadata using unified logger"""
    logger = UnifiedLogger()
    
    run_id = logger.create_run(
        LogType.DIAGRAM_EXTRACTION,
        "Diagram Extraction", 
        {
            "total_pages": len(figure_snippets),
            "total_figures": sum(len(figs) for figs in figure_snippets)
        }
    )
    
    # Save each figure
    for page_idx, page_figures in enumerate(figure_snippets):
        for fig_idx, figure_img in enumerate(page_figures):
            filename = f'page_{page_idx+1}_figure_{fig_idx+1}.png'
            logger.save_image(run_id, figure_img, filename, 'images')
    
    logger.complete_run(run_id)
    
    run_dir = logger.logs_root / run_id
    metadata_file = run_dir / "metadata.json"
    return str(run_dir), str(metadata_file)

def compose_diagram_preview(
    figure_snippets: List[List[Image.Image]],
    dpi: int = 300,
    thumb_width: int = 200,
    font_path: str = None
) -> Image.Image:
    """
    Build a single PIL image that mirrors the UI layout:
      - "Here are figures present:" heading
      - For each page:
          - Subheader "Page X"
          - For each figure:
              - Label "Figure Y"
              - Thumbnail image resized to thumb_width
    """
    # Load fonts: H1 (48px bold), H2 (36px bold), H3 (24px regular)
    if font_path:
        try:
            heading_font = ImageFont.truetype(font_path, size=48)
            subheader_font = ImageFont.truetype(font_path, size=36)
            label_font = ImageFont.truetype(font_path, size=30)
        except Exception:
            heading_font = ImageFont.load_default()
            subheader_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
    else:
        # Try common system fonts for bold and regular
        font_bold_candidates = [
            "DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]
        font_reg_candidates = [
            "DejaVuSans.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        heading_font = subheader_font = None
        for fb in font_bold_candidates:
            try:
                heading_font = ImageFont.truetype(fb, size=48)
                subheader_font = ImageFont.truetype(fb, size=36)
                break
            except Exception:
                continue
        label_font = None
        for fr in font_reg_candidates:
            try:
                label_font = ImageFont.truetype(fr, size=30)
                break
            except Exception:
                continue
        # Fallback to default bitmap font if any loading failed
        if heading_font is None or subheader_font is None or label_font is None:
            heading_font = ImageFont.load_default()
            subheader_font = ImageFont.load_default()
            label_font = ImageFont.load_default()

    # Layout parameters
    left_margin = 20
    # Increase top margin and vertical padding for better spacing
    top_margin = 30
    v_padding = 20
    heading_text = "Here are figures present:"

    # First pass: calculate canvas size
    # Dummy draw to measure text using textbbox
    dummy_img = Image.new("RGB", (10, 10))
    draw_dummy = ImageDraw.Draw(dummy_img)
    bbox = draw_dummy.textbbox((0, 0), heading_text, font=heading_font)
    h_heading = bbox[3] - bbox[1]
    total_height = top_margin
    total_height += h_heading + v_padding

    fig_counter = 1
    for page_idx, figs in enumerate(figure_snippets):
        if figs:
            page_text = f"Page {page_idx + 1}"
            bbox = draw_dummy.textbbox((0, 0), page_text, font=subheader_font)
            h_page = bbox[3] - bbox[1]
            total_height += h_page + v_padding
            for fig_img in figs:
                fig_label = f"VISUAL-{fig_counter}"
                bbox = draw_dummy.textbbox((0, 0), fig_label, font=label_font)
                h_label = bbox[3] - bbox[1]
                total_height += h_label + v_padding
                # thumbnail height
                orig_w, orig_h = fig_img.size
                scale = thumb_width / orig_w
                thumb_h = int(orig_h * scale)
                total_height += thumb_h + v_padding
                fig_counter += 1
    total_height += top_margin

    # Canvas width and creation
    canvas_width = thumb_width + left_margin * 2
    canvas = Image.new("RGB", (canvas_width, total_height), "white")
    draw = ImageDraw.Draw(canvas)

    # Second pass: render content
    y = top_margin
    # Heading
    draw.text((left_margin, y), heading_text, fill="black", font=heading_font)
    y += h_heading + v_padding

    fig_counter = 1
    for page_idx, figs in enumerate(figure_snippets):
        if figs:
            page_text = f"Page {page_idx + 1}"
            draw.text((left_margin, y), page_text, fill="black", font=subheader_font)
            bbox = draw.textbbox((0, 0), page_text, font=subheader_font)
            h_page = bbox[3] - bbox[1]
            y += h_page + v_padding
            for fig_img in figs:
                fig_label = f"VISUAL-{fig_counter}"
                draw.text((left_margin, y), fig_label, fill="black", font=label_font)
                bbox = draw.textbbox((0, 0), fig_label, font=label_font)
                h_label = bbox[3] - bbox[1]
                y += h_label + v_padding
                # Resize and paste thumbnail
                orig_w, orig_h = fig_img.size
                scale = thumb_width / orig_w
                thumb_h = int(orig_h * scale)
                thumb = fig_img.resize((thumb_width, thumb_h), resample=Image.Resampling.LANCZOS)
                canvas.paste(thumb, (left_margin, y))
                y += thumb_h + v_padding
                fig_counter += 1

    return canvas

def extract_diagrams_from_pdf(file_path: str, conf_threshold: float = 0.25, iou_threshold: float = 0.45) -> Tuple[List, List[List]]:
    """Extract diagram images with detected bounding boxes from a PDF file"""
    try:
        results = []
        figure_snippets = []
        
        if _model is None:
            raise RuntimeError("Model not loaded. Cannot extract diagrams.")
        
        with open(file_path, 'rb') as f:
            pages = convert_from_bytes(f.read(), dpi=300)
            
        for page in pages:
            try:
                det_res = _model.predict(
                    page,
                    imgsz=1024,
                    conf=conf_threshold,
                    device=_device,
                )[0]
                
                boxes = det_res.__dict__['boxes'].xyxy
                classes = det_res.__dict__['boxes'].cls
                scores = det_res.__dict__['boxes'].conf

                # Apply non-maximum suppression
                indices = torchvision.ops.nms(
                    boxes=torch.Tensor(boxes),
                    scores=torch.Tensor(scores),
                    iou_threshold=iou_threshold
                )
                
                b, s, c = boxes[indices], scores[indices], classes[indices]
                
                # Ensure correct shape
                if b.ndim == 1:
                    b = np.expand_dims(b, 0)
                    s = np.expand_dims(s, 0)
                    c = np.expand_dims(c, 0)

                vis = visualize_bbox(page, b, c, s, ID_TO_NAMES)
                results.append(vis)
                
                # Extract figure snippets with advanced merging logic
                fig_indices = [i for i, cls in enumerate(c) if int(cls) == 3]
                fig_boxes = [b[i] for i in fig_indices]
                n = len(fig_boxes)
                
                if n > 0:
                    # Group overlapping boxes using union-find algorithm
                    parents = list(range(n))
                    def find(i):
                        if parents[i] != i:
                            parents[i] = find(parents[i])
                        return parents[i]
                    
                    def union(i, j):
                        pi, pj = find(i), find(j)
                        if pi != pj:
                            parents[pj] = pi
                    
                    # Merge boxes that overlap vertically
                    for i1 in range(n):
                        y1_i, y2_i = fig_boxes[i1][1], fig_boxes[i1][3]
                        for j1 in range(i1 + 1, n):
                            y1_j, y2_j = fig_boxes[j1][1], fig_boxes[j1][3]
                            if y1_i < y2_j and y1_j < y2_i:
                                union(i1, j1)
                    
                    # Group boxes by their root parent
                    groups = defaultdict(list)
                    for idx in range(n):
                        root = find(idx)
                        groups[root].append(idx)
                    
                    # Merge overlapping boxes and create crops
                    merged = []
                    for grp in groups.values():
                        xs1 = [fig_boxes[i][0] for i in grp]
                        ys1 = [fig_boxes[i][1] for i in grp]
                        xs2 = [fig_boxes[i][2] for i in grp]
                        ys2 = [fig_boxes[i][3] for i in grp]
                        x1_ = min(xs1); y1_ = min(ys1)
                        x2_ = max(xs2); y2_ = max(ys2)
                        crop = page.crop((int(x1_), int(y1_), int(x2_), int(y2_)))
                        merged.append((y1_, crop))
                    
                    # Sort by vertical position
                    merged.sort(key=lambda x: x[0])
                    page_figs = [crop for _, crop in merged]
                else:
                    page_figs = []
                
                figure_snippets.append(page_figs)
                
            except Exception as e:
                print(f"Error processing page: {str(e)}")
                results.append(np.array(page))
                figure_snippets.append([])
        
        return results, figure_snippets
        
    except Exception as e:
        raise RuntimeError(f"Diagram extraction failed: {str(e)}")

# =============================================================================
# GEMINI API FUNCTIONS
# =============================================================================



def generate_diagram_mapping_internal(pdf_path: str, image_path: str, logger: UnifiedLogger, run_id: str) -> str:
    """Generate diagram mapping within an existing pipeline run"""
    try:
        logger.log_step(run_id, "Step 2: Upload Files", "Uploading PDF and image to Gemini", "Preparing files for analysis")
        
        # Use the same prompts as the original function
        system_prompt = """
You are a specialized diagram analysis assistant that maps extracted diagrams to their corresponding questions in CBSE Mathematics exam papers with 100% accuracy.

## Core Identity
You analyze image files containing extracted diagrams and PDF documents to create precise mappings between figure numbers and their corresponding question identifiers, including proper internal choice classification.

## Input Specification
- **Image file**: Contains extracted diagrams with figure numbers and page numbers
- **PDF document**: CBSE Mathematics exam paper from which diagrams were extracted

## Primary Objective
Systematically analyze both files to create accurate mappings between figure numbers and their corresponding question identifiers, focusing ONLY on questions with actual printed visual content.

## Critical Content Rules

### MUST INCLUDE (Visual Content Only):
- Questions with actual printed diagrams, figures, charts, or images
- Visual elements that can be seen and described
- Geometric shapes, graphs, illustrations that are physically present

### MUST EXCLUDE (Textual Descriptions):
- Questions with only textual descriptions like "A triangle ABC has sides 3, 4, 5..."
- Questions stating "In a circle with center O..." without actual visual circle
- Questions mentioning "Consider a function f(x)..." without actual graph
- Questions saying "In the given figure..." when no actual figure is present
- Any question that only describes mathematical objects without showing them

## Internal Choice Classification Rules
- **Case study questions**: Always `choice_location = "null"` (regardless of OR separators in subparts)
- **Regular questions with OR**: Classify as `first/second/both` based on diagram location
- **Regular questions without OR**: `choice_location = "null"`

## Output Format
```json
{
  "figure-1": {
    "question_identifier": "question_number",
    "choice_location": "first/second/null"
  },
  "figure-2": {
    "question_identifier": "question_number",
    "choice_location": "first/second/null"
  }
}
```

## Quality Standards
- **100% Visual Content Focus**: Only map to questions with actual printed diagrams
- **Complete Figure Coverage**: Every figure in the image must be mapped
- **Precise Choice Classification**: Accurate determination of internal choice locations
- **Verbatim Question Identification**: Match questions exactly as they appear in the PDF
"""

        user_prompt = """
Please analyze the provided image file containing extracted diagrams and the PDF document they came from. Follow this systematic approach:

## Step 1: Figure Image Analysis
**Parse the provided image file:**
- Identify and count all figures present in the image
- For each figure, extract:
  - Figure number/identifier (as labeled in the image)
  - Page number (as indicated in the image)
  - Generate a detailed description of each figure's visual content

**Output format for Step 1:**
```
Total figures in image: [number]
Figure-1: Page X - [Detailed visual description including diagram type, elements, labels, etc.]
Figure-2: Page Y - [Detailed visual description including diagram type, elements, labels, etc.]
...continue for all figures
```

## Step 2: PDF Document Question Analysis
**Analyze the PDF document comprehensively:**
- Count the total number of questions in the PDF
- Identify which questions contain **actual visual diagrams/figures/images** (not just textual descriptions)
- **IMPORTANT**: Only count questions with printed diagrams, figures, charts, or visual elements
- **EXCLUDE**: Questions that only contain textual descriptions of diagrams without actual visual content
- Count the total number of questions that have actual diagrams

**Output format for Step 2:**
```
Total questions in PDF: [number]
Questions with actual diagrams: [number]
Question numbers containing actual diagrams: [list of question numbers]
```

## Final Output
Present only the final mapping in JSON format:

```json
{
  "figure-1": {
    "question_identifier": "question_number",
    "choice_location": "first/second/null"
  },
  "figure-2": {
    "question_identifier": "question_number",
    "choice_location": "first/second/null"
  }
}
```
"""
        
        # Upload files to Gemini
        pdf_file = client.files.upload(file=pdf_path)
        img_file = client.files.upload(file=image_path)

        logger.log_step(run_id, "Step 2: Generate Mapping", "Processing with Gemini AI", "Analyzing diagrams and questions")

        # Safety settings
        safety_settings = [
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]

        # Generation configuration
        config = types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=60000,
            response_mime_type="text/plain",
            safety_settings=safety_settings,
            thinking_config=types.ThinkingConfig(thinking_budget=5000)
        )

        # Generate content
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[pdf_file, img_file, system_prompt, user_prompt],
            config=config,
        )

        # Clean up uploaded files
        client.files.delete(name=pdf_file.name)
        client.files.delete(name=img_file.name)

        # Parse response
        raw_text = response.text.strip() if hasattr(response, 'text') else ''
        if not raw_text:
            raise ValueError("No mapping content generated")
        
        # Extract JSON
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise ValueError("No JSON object found in mapping response")
        
        json_str = match.group(0)
        mapping_json = json.loads(json_str)

        # Upload figures to Cloudinary and update mapping with URLs
        logger.log_step(run_id, "Step 2: Upload Figures", "Starting Cloudinary uploads", f"Uploading {len(mapping_json)} figures")
        
        # Get the run directory to find the figure files
        run_dir = logger.logs_root / run_id
        step1_dir = run_dir / "step1_diagram_extraction"
        
        # Get all figure files and sort them to create sequential mapping
        figure_files = []
        for file_path in step1_dir.glob("step1_page_*_figure_*.png"):
            if "overview" not in file_path.name:  # Skip overview image
                figure_files.append(file_path)
        
        # Sort files by page and figure number
        figure_files.sort(key=lambda x: (
            int(x.name.split('_')[2]),  # page number
            int(x.name.split('_')[4].replace('.png', ''))  # figure number
        ))
        
        # Update mapping with Cloudinary URLs
        for i, figure_key in enumerate(mapping_json.keys()):
            try:
                if i < len(figure_files):
                    figure_path = figure_files[i]
                else:
                    print(f"Warning: No file found for {figure_key}")
                    mapping_json[figure_key]["cloudinary_url"] = ""
                    continue
                
                if figure_path.exists():
                    # Read the image file
                    with open(figure_path, 'rb') as f:
                        image_bytes = f.read()
                    
                    # Upload to Cloudinary
                    blob = BytesIO(image_bytes)
                    result = cloudinary.uploader.upload(
                        blob,
                        resource_type='image',
                        format='png',
                        public_id=f"diagram_mapping/{run_id}/{figure_key}"
                    )
                    
                    # Add Cloudinary URL to the mapping
                    mapping_json[figure_key]["cloudinary_url"] = result.get('secure_url', '')
                    print(f"Uploaded {figure_key} to Cloudinary: {result.get('secure_url', '')}")
                else:
                    print(f"Warning: Figure file not found: {figure_path}")
                    mapping_json[figure_key]["cloudinary_url"] = ""
                    
            except Exception as e:
                print(f"Error uploading {figure_key} to Cloudinary: {e}")
                mapping_json[figure_key]["cloudinary_url"] = ""

        # Save updated mapping with Cloudinary URLs
        output_filename = f"step2_diagram_mapping.json"
        logger.save_file(run_id, json.dumps(mapping_json, indent=2), output_filename, 'step2_diagram_mapping')
        
        logger.log_step(run_id, "Step 2: Save Results", f"Mapped {len(mapping_json)} figures with Cloudinary URLs", "Saved mapping JSON with figure URLs")
        
        return raw_text

    except Exception as e:
        # Cleanup on error
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        try:
            client.files.delete(name=img_file.name)
        except:
            pass
        raise RuntimeError(f"Diagram mapping failed: {str(e)}")

def generate_markdown_from_pdf(pdf_path: str, logger: Optional[UnifiedLogger] = None, run_id: Optional[str] = None) -> str:
    """Generate markdown from PDF using Gemini"""
    try:
        # If logger and run_id provided, use them; otherwise create new run
        if logger and run_id:
            logger.log_step(run_id, "Step 3: Upload PDF", "Uploading PDF to Gemini", "Preparing for question extraction")
        else:
            logger = UnifiedLogger()
            run_id = logger.create_run(LogType.QUESTION_EXTRACTION, "Question Extraction", {
                "pdf_file": os.path.basename(pdf_path)
            })
        # System and user prompts for question extraction
        system_prompt = """
# CBSE Mathematics Question Extraction Assistant

## Core Identity
You are a specialized question extraction assistant that converts CBSE Mathematics exam papers to clean Markdown format with 100% verbatim accuracy for questions only, excluding all instructional content and diagrams.

## Input Specification
- **Source**: CBSE Mathematics exam paper (any length, any number of questions)
- **Question Types**:
  - Multiple Choice Questions (MCQs) with options A, B, C, D
  - Assertion-Reason questions with statements A and R
  - Very Short Answer (VSA) questions with internal choices
  - Short Answer (SA) questions with internal choices
  - Long Answer (LA) questions with internal choices
  - Case-study questions with sub-parts and internal choices

## Primary Objective
Extract ONLY the questions from the exam paper, converting them to clean Markdown format while maintaining exact textual fidelity and proper question separation.

## Content Classification Rules

### MUST INCLUDE (Questions):
- All question text with question numbers (as they appear in the source)
- All answer options for MCQs (A), (B), (C), (D)
- All mathematical expressions and symbols
- All case study paragraphs and their sub-questions
- All internal choice alternatives marked with "OR"
- All sub-parts: (i), (ii), (iii), (a), (b), (c)
- All question fragments that contain subject matter content

### MUST EXCLUDE (Instructions/Metadata):
- General instructions ("Read the following instructions carefully")
- Any Table and it's content -EXCLUDE
- ALL diagram content, diagram labels, diagram annotations, figures, images, or visual elements
- Section headers ("SECTION A", "SECTION B", etc.)
- Section descriptions ("This section has X questions carrying Y marks each")
- Marking schemes and mark allocations ("[X marks]", "X×Y=Z")
- Page numbers and "P.T.O." indicators
- Assertion-Reason boilerplate instructions (when no actual A and R statements present)
- Drawing instructions unless part of the question itself
- Calculator usage instructions
- Subject names or exam metadata

## Formatting Rules

### Mathematical Expressions
- Inline math: `$expression$`
- Display math: `$$expression$$`
- Preserve all mathematical notation exactly as shown

### Structure and Tagging
- Preserve original question numbering exactly as shown in the source
- Replace internal choice indicators: "OR" becomes [%OR%]
- Add [####] immediately after each complete question ends
- Separate questions with blank lines
- Do NOT add any additional tags or formatting to question numbers

### Question Separation Logic
A question is considered "complete" when:
- All parts of an MCQ (question + options A,B,C,D) are included
- All sub-parts of a multi-part question are included
- Both alternatives of an OR question are included
- All sub-questions of a case study are included

## Diagram Handling
- **COMPLETELY IGNORE** all visual elements even if the question explicitly mentions to refer including:
  - Geometric figures and shapes
  - Graphs and charts
  - Diagrams and illustrations
  - Image annotations and labels
  - Figure captions
  - Any text that describes or references diagrams ("In the given figure...")

## Output Format Template
```markdown
1. [Complete question text]
(A) [option]
(B) [option]
(C) [option]
(D) [option]
[####]

2. [Complete question text]
[####]

15. (a) [Question part a]
[%OR%]
(b) [Question part b]
[####]

25. [Case study scenario description]
Based on the above given information, answer the following questions:
(i) [Sub-question i]
(ii) [Sub-question ii]
(iii) (a) [Sub-question iii part a]
[%OR%]
(iii) (b) [Sub-question iii part b]
[####]
```

## Quality Standards
- **Verbatim Accuracy**: Every character of question content must match the source exactly
- **Complete Extraction**: All questions must be extracted with no omissions
- **Clean Formatting**: Use proper Markdown syntax throughout
- **Consistent Tagging**: Apply [%OR%] and [####] tags uniformly
- **No Hallucinations**: Do not add, modify, or invent any content

## Verification Checklist
Before submitting, confirm:
- [ ] All questions extracted in sequential order as they appear in the source
- [ ] Each question ends with [####]
- [ ] Question numbers preserved exactly as shown (no additional tagging)
- [ ] All mathematical expressions properly formatted
- [ ] Internal choice "OR" replaced with [%OR%]
- [ ] Any table present in the question paper was excluded
- [ ] No instructional text included
- [ ] No diagram content or references included
- [ ] All case study scenarios and sub-questions included
- [ ] No marks/scoring information included
- [ ] Output is in clean Markdown format

## Critical Success Factors
1. **100% Question Coverage**: Every question must be extracted
2. **Zero Instruction Contamination**: No instructional text should appear in output
3. **Diagram Immunity**: Completely ignore all visual elements
4. **Exact Textual Fidelity**: Preserve every character of question content
5. **Proper Separation**: Each question clearly demarcated with [####]

Focus on precision, completeness, and clean Markdown output while maintaining absolute fidelity to the original question content.
"""

        user_prompt = """
# Chain of Thought Question Extraction Prompt

**TASK:** Extract ONLY the questions from a mathematics exam paper with precise formatting using systematic chain-of-thought reasoning.

**SYSTEMATIC PROCESSING APPROACH:**

## **Step 1: Initial Document Analysis**
First, analyze the overall structure: "I can see [X] total pages with [Y] distinct questions numbered from [start] to [end]. The document contains [Z] sections with [A] question types including MCQs, assertion-reason, case studies, and multi-part questions."

## **Step 2: Question Inventory and Mapping**
For comprehensive question identification: "I will now scan the entire document to create a complete question inventory:
- Questions 1-[X]: [Location/Section]
- Questions [Y]-[Z]: [Location/Section]
- Total question count: [Number]
- Question types identified: [MCQ/Long Answer/Case Study/etc.]"

## **Step 3: Element-by-Element Classification**
For each and every element from top to bottom, explicitly state: "This is [question text/instruction/header/page number] and should be [included/excluded] because [specific reason based on inclusion/exclusion criteria]."

**Inclusion Criteria Check:**
- "This element contains a question number [X] - INCLUDE"
- "This element contains question text following a number - INCLUDE"
- "This element contains answer options (A), (B), (C), (D) - INCLUDE"
- "This element contains sub-parts (i), (ii), (a), (b) - INCLUDE"
- "This element contains OR alternatives within a question - INCLUDE and TAG"
- "This element contains case study scenario for questions - INCLUDE"
- "This element contains assertion-reason statements - INCLUDE"

**Exclusion Criteria Check:**
- "This element is general instructions - EXCLUDE"
- "This element contains data tables within questions - EXCLUDE"
- "This element is section header (SECTION A/B/C) - EXCLUDE"
- "This element is marking scheme reference - EXCLUDE"
- "This element is page number/P.T.O. - EXCLUDE"
- "This element is marks allocation (2 marks, etc.) - EXCLUDE"

## **Step 4: Question-by-Question Deep Analysis**
For each identified question, perform detailed analysis:

**Question [Number] Analysis:**
"I am now processing Question [X]:
- Question identifier: [Exact format as shown]
- Question type: [MCQ/Long Answer/Case Study/Multi-part]
- Question text begins: '[First few words]'
- Question text ends: '[Last few words]'
- Contains options: [Yes/No] - If yes, options are: (A), (B), (C), (D)
- Contains sub-parts: [Yes/No] - If yes, sub-parts are: [list]
- Contains OR alternatives: [Yes/No] - If yes, mark for [%OR%] tagging
- Special mathematical notation: [List any complex symbols/equations]
- Reasoning for inclusion: [Why this entire block constitutes one complete question]"

## **Step 5: Content Boundary Determination**
For each question, clearly define boundaries: "Question [X] starts at '[exact text]' and ends at '[exact text]' before Question [X+1] begins. Everything between these boundaries belongs to Question [X], including [list specific elements like options, sub-parts, tables]."

## **Step 6: Mathematical Expression and Symbol Preservation**
For each mathematical element: "This expression '[content]' requires [specific formatting] because [reasoning]. Special characters identified: [list]. Greek letters present: [list]. Equations present: [list]. All symbols will be preserved exactly as shown."

## **Step 7: OR Alternative Identification and Tagging**
"Scanning for internal choice alternatives:
- Found 'OR' in Question [X] between '[option 1]' and '[option 2]' - Will replace with [%OR%]
- Found 'or' in Question [Y] between '[option 1]' and '[option 2]' - Will replace with [%or%]
- Total OR alternatives identified: [count]"

## **Step 8: Multi-part Question Structure Analysis**
For complex questions: "Question [X] has multiple parts:
- Main question: '[text]'
- Sub-part (a): '[text]'
- Sub-part (b): '[text]'
- Sub-part (i): '[text]'
- All parts belong to Question [X] and will be included together before [####] marker."

## **Step 9: Case Study Question Processing**
For case studies: "Case study identified for Questions [X]-[Y]:
- Scenario description: '[summary]'
- Questions based on scenario: [list]
- Will include complete scenario followed by all related questions before [####] marker."

## **Step 10: Quality Assurance Pre-Extraction**
Before extraction, verify: "I have identified [X] questions total. Each question has been analyzed for:
- ✓ Complete question text
- ✓ All options where applicable
- ✓ All sub-parts where applicable
- ✓ All OR alternatives tagged
- ✓ All mathematical symbols preserved
- ✓ All tables/data excluded
- ✓ Proper boundaries established
- ✓ No instructional content mixed in"

## **Step 11: Sequential Extraction with Verification**
"I will now extract each question in sequence, verifying accuracy:

**Extracting Question 1:**
- Question number: [as shown]
- Question text: '[complete text]'
- Options: [if applicable]
- Sub-parts: [if applicable]
- Verification: [confirms this is complete question 1]

**Extracting Question 2:**
- Question number: [as shown]
- Question text: '[complete text]'
- Options: [if applicable]
- Sub-parts: [if applicable]
- Verification: [confirms this is complete question 2]

[Continue for all questions...]"

## **Step 12: Final Verification Checklist**
Before outputting final result: "Final verification completed:
- [ ] All questions numbered sequentially from 1 to [final number]
- [ ] Each question ends with [####]
- [ ] No instructional text included
- [ ] All mathematical symbols preserved exactly
- [ ] OR alternatives tagged with [%OR%] where present
- [ ] Any table present in the question paper was excluded and not outputted
- [ ] Case study scenarios included with their questions
- [ ] No marks/scoring information included
- [ ] Question count matches initial inventory: [X] questions
- [ ] All sub-parts kept with their parent questions
- [ ] All answer options preserved exactly as shown"

## **Step 13: Final Output Generation**
"After completing the systematic analysis above, I will now provide the final extracted questions in the specified format. The output will contain ONLY the questions with their exact numbering, complete content, and proper [####] markers."

**REASONING DISPLAY REQUIREMENT:**
Present your complete step-by-step analysis and reasoning in regular text first, showing all the decision-making process, classifications, and verifications from Steps 1-12. Then, at the very end, provide only the final extracted questions in a markdown code block.

**OUTPUT FORMAT:**
```
1. [Complete question text]
(A) [option]
(B) [option]
(C) [option]
(D) [option]
[####]

2. [Complete question text]
[####]

21. (a) [Question part a]
[%OR%]
(b) [Question part b]
[####]
```

**FINAL PRESENTATION FORMAT:**
After your complete analysis, provide the final extracted questions using this exact format:

```markdown
[Place only the final extracted questions here - no steps, no reasoning, just the extracted questions with proper numbering and [####] markers]
```

**ACCURACY REQUIREMENT:** This systematic approach ensures 100% accuracy with no omissions, no additions, and no modifications to the original content. Every step must be completed before proceeding to the next, ensuring comprehensive analysis and perfect extraction. The markdown code block should contain ONLY the extracted questions, not the analysis steps.
"""
        
        # Upload file to Gemini
        pdf_file = client.files.upload(file=pdf_path)

        if logger and run_id:
            logger.log_step(run_id, "Step 3: Generate Questions", "Processing with Gemini AI", "Extracting questions from PDF")

        # Safety settings
        safety_settings = [
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]

        # Generation configuration
        config = types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=60000,
            response_mime_type="text/plain",
            safety_settings=safety_settings,
            thinking_config=types.ThinkingConfig(thinking_budget=512)
        )

        # Generate content
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=[pdf_file, system_prompt, user_prompt],
            config=config,
        )

        # Clean up uploaded file
        client.files.delete(name=pdf_file.name)

        # Parse response
        markdown_text = response.text.strip() if hasattr(response, 'text') else ''
        if not markdown_text:
            raise ValueError("No markdown content generated")

        # Save markdown
        if logger and run_id:
            # Save within existing pipeline run
            output_filename = f"step3_questions.md"
            logger.save_file(run_id, markdown_text, output_filename, 'step3_question_extraction')
            logger.log_step(run_id, "Step 3: Save Results", f"Generated {len(markdown_text)} characters", "Saved questions in markdown format")
            return markdown_text
        else:
            # Create separate run (original behavior)
            output_filename = os.path.basename(pdf_path).replace('.pdf', '.md')
            logger.save_file(run_id, markdown_text, output_filename)
            logger.complete_run(run_id, success=True)
            
            # Return the full path for compatibility
            full_path = logger.logs_root / run_id / "files" / output_filename
            return str(full_path)

    except Exception as e:
        # Cleanup on error
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        raise RuntimeError(f"Markdown generation failed: {str(e)}")


def generate_marks_mapping(pdf_path: str, logger: Optional[UnifiedLogger] = None, run_id: Optional[str] = None) -> Tuple[str, str]:
    """Generate marks mapping using Gemini"""
    try:
        # If logger and run_id provided, use them; otherwise create new run
        if logger and run_id:
            logger.log_step(run_id, "Step 4: Upload PDF", "Uploading PDF to Gemini", "Preparing for marks mapping")
        else:
            logger = UnifiedLogger()
            run_id = logger.create_run(LogType.MARKS_MAPPING, "Marks Mapping", {
                "pdf_file": os.path.basename(pdf_path)
            })
        # System and user prompts (exact from original files)
        system_prompt = """
# System Prompt: CBSE Mathematics Question Paper Marks Extraction

## Core Task
You are a specialized CBSE question paper analyzer that extracts question numbers, question types, and marks allocation from CBSE format mathematics question papers. Your primary function is to systematically identify and categorize each question with its corresponding marks.

## Key Constraints
- All questions in the paper must be identified and included in the output
- Each question must be classified by its type and marks allocation
- The JSON output length must exactly match the total number of questions in the paper
- Marks allocation must be accurate as specified in the question paper
- Question numbering must follow the exact format used in the paper

## Question Type Classification
- **MCQ**: Multiple Choice Questions with options (A), (B), (C), (D)
- **Case Study**: Questions that have subparts within them (can have internal choice in subparts)
- **Normal Subjective**: Standard subjective questions without internal choice, not MCQ, not case study
- **Internal Choice Subjective**: Questions with "OR" option where student can attempt one of two alternatives
- **Assertion Reasoning**: Questions with assertion and reasoning statements to evaluate

## Classification Priority Rules
- If a question has subparts → **Case Study** (even if subparts have internal choice)
- If a question has "OR" between just two main questions → **Internal Choice Subjective**
- If a question is multiple choice with options → **MCQ**
- If a question has assertion and reasoning format → **Assertion Reasoning**
- If a question is subjective without above features → **Normal Subjective**

## Marks Identification Rules
- Look for explicit marks mentioned in brackets like [1], (2), [3 marks], etc.
- Check section headers for marks allocation patterns
- Verify marks consistency within question types
- For Case Study questions with subparts, identify marks for each subpart and describe them in the marks field
- For questions without subparts, use numerical marks value only
- **For Internal Choice Subjective questions**: Use array format with exactly 2 elements

## Critical Instructions
- Count every main question in the paper (do not count subparts as separate questions)
- For Case Study questions with subparts, describe all subparts and their marks in the marks field
- Do not miss any question regardless of its position or format
- Ensure question numbering matches exactly with the paper format
- Verify total question count before finalizing output

## Subpart Handling Rules
- **Case Study with subparts**: Keep as single JSON entry for the main question
- **Marks field for subparts**: Write descriptive text about subparts and their individual marks
- **Format for subpart marks**: "Part (a): X marks, Part (b): Y marks, Part (c): Z marks" or similar descriptive format
- **Total marks calculation**: Include total marks for the entire question if specified

## Special Format for Internal Choice Questions
- **Internal Choice Subjective questions MUST use array format**
- **Array must have exactly 2 elements**
- **Each element format**: "This question has [X] marks"
- **Both elements should have the same marks value**

## Output Format
```
{
  "question-1": {
    "question_type": "MCQ/Case Study/Normal Subjective/Internal Choice Subjective/Assertion Reasoning/Other Subjective",
    "marks": "number OR descriptive text for subparts OR array for internal choice"
  }
}
```

## Marks Field Format Rules
- **Case Study**: Use descriptive text (e.g., "Part (a): 1 mark, Part (b): 2 marks, Total: 3 marks")
- **Internal Choice Subjective**: Use array with 2 elements (e.g., ["This question has [3] marks", "This question has [3] marks"])
"""

        user_prompt = """
# CBSE Mathematics Question Paper Marks Extraction

I need you to analyze the provided CBSE format mathematics question paper and extract the marks allocation for each question. Please follow this step-by-step approach:

## Step 1: Paper Structure Analysis
**Think through this systematically:**
- First, read through the entire question paper
- Identify the total number of main questions and their numbering system
- Note the paper format and section divisions (if any)
- Look for general instructions about marks allocation
- **Important**: Count only main questions, not subparts as separate questions

**Reasoning process:**
```
Total main questions: [Count main questions only]
Paper sections: [Section A, B, C, etc. if applicable]
Question numbering format: [1, 2, 3... etc.]
Case Study questions: [List questions with subparts like Q5: has (a), (b), (c)]
```

## Step 2: Question Type Identification
**For each question, analyze:**
- Does it have multiple choice options (A), (B), (C), (D)? → **MCQ**
- Does it have subparts (like (a), (b), (c) or (i), (ii), (iii))? → **Case Study**
- Does it have "OR" option between just two main questions? → **Internal Choice Subjective**
- Does it have assertion and reasoning format? → **Assertion Reasoning**
- Is it a regular subjective question without above features? → **Normal Subjective**

**Classification Priority:**
- Subparts present = Case Study (even if subparts have internal choice)
- "OR" between two main questions = Internal Choice Subjective
- Multiple choice options = MCQ
- Assertion-Reasoning format = Assertion Reasoning
- Regular subjective = Normal Subjective

**Reasoning process:**
```
Question 1: Has subparts? [Yes/No] → Has OR? [Yes/No] → Type = [MCQ/Case Study/Normal Subjective/Internal Choice Subjective/Assertion Reasoning/Other Subjective], Marks = [X]
Question 2: Has subparts? [Yes/No] → Has OR? [Yes/No] → Type = [MCQ/Case Study/Normal Subjective/Internal Choice Subjective/Assertion Reasoning/Other Subjective], Marks = [X]
...and so on
```

## Step 3: Marks Extraction
**For each question, identify:**
- Look for explicit marks mentioned in brackets like [1], (2), [3 marks]
- Check section headers for marks patterns
- Verify marks consistency within similar question types
- **For Case Study questions**: Identify marks for each subpart and create descriptive text
- **For simple questions**: Use numerical marks value only
- **For Internal Choice Subjective questions**: Create array with 2 identical elements
- Note any special marking schemes

**Reasoning process:**
```
Question X: Found marks indicator "[2]" → 2
Question Y (Case Study): Part (a) has "[1]", Part (b) has "[2]" → "Part (a): 1 mark, Part (b): 2 marks, Total: 3 marks"
Question Z (Internal Choice): Explicit "(5 marks)" → ["This question has [5] marks", "This question has [5] marks"]
```

## Step 4: Validation and Final Mapping
**Consolidate your findings:**
- Verify total main question count matches your analysis
- Check for any missed questions
- Ensure marks allocation is consistent with CBSE patterns
- Double-check question numbering format
- **Important**: Ensure Case Study questions have descriptive marks text including all subparts
- **Important**: Ensure Internal Choice Subjective questions use array format with exactly 2 elements

**Present your reasoning clearly before giving the final answer.**

## Expected Output Format:
The final output must be in JSON format with the following structure:
```json
{
  "question-1": {
    "question_type": "MCQ",
    "marks": [X] marks
  },
  "question-2": {
    "question_type": "Case Study", 
    "marks": "Description of marks for each subpart and it's internal choices"
  },
  "question-3": {
    "question_type": "Internal Choice Subjective",
    "marks": ["This question has [X] marks", "This question has [Y] marks"]
  },
  "question-4": {
    "question_type": "Normal Subjective",
    "marks": [X] marks
  },
  "question-5": {
    "question_type": "Assertion Reasoning",
    "marks": [X] marks
  }

}
```
## CRITICAL MARKS FORMAT RULES:
- **MCQ**: Use simple number format (e.g., [X] marks)
- **Normal Subjective**: Use simple number format (e.g., [X] marks)
- **Assertion Reasoning**: Use simple number format (e.g., [X] marks)
- **Case Study**: Use descriptive text explaining the mark distribution for each subpart and any internal choices (e.g., "Description of marks for each subpart and it's internal choices")
- **Internal Choice Subjective**: Use array with exactly 2 elements showing the marks for each choice option (e.g., ["This question has [X] marks", "This question has [Y] marks"])

"""
        
        # Upload file to Gemini
        pdf_file = client.files.upload(file=pdf_path)

        if logger and run_id:
            logger.log_step(run_id, "Step 4: Generate Marks Mapping", "Processing with Gemini AI", "Analyzing question types and marks")

        # Safety settings
        safety_settings = [
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]

        # Generation configuration
        config = types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=60000,
            response_mime_type="text/plain",
            safety_settings=safety_settings,
            thinking_config=types.ThinkingConfig(thinking_budget=512)
        )

        # Generate content
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=[pdf_file, system_prompt, user_prompt],
            config=config,
        )

        # Clean up uploaded file
        client.files.delete(name=pdf_file.name)

        # Parse response
        raw_text = response.text.strip() if hasattr(response, 'text') else ''
        if not raw_text:
            raise ValueError("No mapping content generated")
        
        # Extract JSON
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise ValueError("No JSON object found in response")
        
        json_str = match.group(0)
        mapping_json = json.loads(json_str)

        # Save mapping
        if logger and run_id:
            # Save within existing pipeline run
            output_filename = f"step4_marks_mapping.json"
            logger.save_file(run_id, json.dumps(mapping_json, indent=2), output_filename, 'step4_marks_mapping')
            
            logger.log_step(run_id, "Step 4: Save Results", f"Mapped {len(mapping_json)} questions", "Saved marks mapping JSON")
            
            return raw_text, raw_text  # Return content instead of paths for unified mode
        else:
            # Create separate run (original behavior)
            output_filename = os.path.basename(pdf_path).replace('.pdf', '_marks.json')
            marks_path = logger.save_file(run_id, json.dumps(mapping_json, indent=2), output_filename)
        
        logger.complete_run(run_id, success=True)
        
        # Return the full path for compatibility
        full_path = logger.logs_root / run_id / "files" / output_filename
        return str(full_path), raw_text

    except Exception as e:
        # Cleanup on error
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        raise RuntimeError(f"Marks mapping generation failed: {str(e)}")

# =============================================================================
# MAIN PROCESSING FUNCTIONS
# =============================================================================

def vstack_images(images: List[np.ndarray]) -> Image.Image:
    """Stack a list of numpy array images vertically into a single PIL Image."""
    if not images:
        return Image.new('RGB', (1, 1))

    pil_images = [Image.fromarray(img) for img in images]
    widths, heights = zip(*(i.size for i in pil_images))

    total_height = sum(heights)
    max_width = max(widths)

    new_im = Image.new('RGB', (max_width, total_height), color='white')

    y_offset = 0
    for im in pil_images:
        new_im.paste(im, (0, y_offset))
        y_offset += im.size[1]
    
    return new_im


async def run_end_to_end_processing(file_content: bytes, filename: str = "uploaded.pdf") -> Dict[str, Any]:
    """
    Run the complete end-to-end processing pipeline
    
    Args:
        file_content: PDF file content as bytes
        filename: Original filename for logging
    
    Returns:
        Dict containing all results and file paths
    """
    results = {
        'success': False,
        'errors': [],
        'step_results': {},
        'final_outputs': {}
    }
    
    temp_files = []  # Keep track of temporary files for cleanup
    
    # Initialize unified logger for the entire pipeline
    logger = UnifiedLogger()
    pipeline_run_id = logger.create_run(LogType.QUESTION_EXTRACTION, "Complete CBSE Processing Pipeline", {
        "filename": filename,
        "total_steps": 4
    })
    
    # Initialize database integration
    db_integration = get_db_integration()
    try:
        await db_integration.start_pipeline(
            run_id=pipeline_run_id,
            title="Complete CBSE Processing Pipeline",
            filename=filename,
            file_size=len(file_content)
        )
    except Exception as db_error:
        print(f"Warning: Failed to initialize database pipeline: {db_error}")
        # Continue with file logging even if database fails
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            temp_pdf_path = tmp_file.name
            temp_files.append(temp_pdf_path)
        
        logger.log_step(pipeline_run_id, "Step 0: File Upload", f"File: {filename}", "File uploaded successfully")
        print("Step 0: File uploaded successfully")
        
        # =====================================================================
        # STEP 1: DIAGRAM EXTRACTION
        # =====================================================================
        try:
            logger.log_step(pipeline_run_id, "Step 1: Diagram Extraction", "Starting diagram extraction", "Analyzing PDF for diagrams")
            print("Step 1: Starting diagram extraction...")
            
            parsed_images, figure_snippets = extract_diagrams_from_pdf(temp_pdf_path)
            
            # Create a single overview image for the mapping step
            preview_image_for_mapping_path = None
            if figure_snippets and any(figs for figs in figure_snippets):
                # Use the improved compose_diagram_preview function
                overview_image = compose_diagram_preview(figure_snippets, thumb_width=800)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                    overview_image.save(tmp_img, format="PNG", dpi=(300, 300))
                    preview_image_for_mapping_path = tmp_img.name
                    temp_files.append(preview_image_for_mapping_path)

            # Save figure snippets within the main pipeline run
            total_figures = sum(len(figs) for figs in figure_snippets)
            logger.log_step(pipeline_run_id, "Step 1: Processing Results", f"Total diagrams found: {total_figures}", f"Extracted {total_figures} diagrams from {len(figure_snippets)} pages")
            
            # Save each figure within the pipeline run
            for page_idx, page_figures in enumerate(figure_snippets):
                for fig_idx, figure_img in enumerate(page_figures):
                    filename = f'step1_page_{page_idx+1}_figure_{fig_idx+1}.png'
                    logger.save_image(pipeline_run_id, figure_img, filename, 'step1_diagram_extraction')
            
            # Save overview image if created
            if preview_image_for_mapping_path:
                import cv2
                overview_img = cv2.imread(preview_image_for_mapping_path)
                logger.save_image(pipeline_run_id, overview_img, 'step1_overview_image.png', 'step1_diagram_extraction')
            
            results['step_results']['step1'] = {
                'success': True,
                'total_figures': total_figures,
                'pages_processed': len(figure_snippets)
            }
            
            logger.log_step(pipeline_run_id, "Step 1: Completed", f"Success: {total_figures} diagrams", "Diagram extraction completed successfully")
            print(f"Step 1: Extracted {total_figures} diagrams")
            
            # Save to database
            figure_files = [f'step1_page_{page_idx+1}_figure_{fig_idx+1}.png' 
                          for page_idx, page_figures in enumerate(figure_snippets) 
                          for fig_idx in range(len(page_figures))]
            await db_integration.save_diagram_extraction_result(
                run_id=pipeline_run_id,
                total_figures=total_figures,
                pages_processed=len(figure_snippets),
                figure_files=figure_files,
                overview_image_path='step1_overview_image.png' if preview_image_for_mapping_path else None
            )
                
        except Exception as e:
            error_msg = f"Step 1 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step1'] = {
                'success': False,
                'error': str(e)
            }
            logger.log_error(pipeline_run_id, "Step 1: Failed", e)
            print(error_msg)
        
        # =====================================================================
        # STEP 2: DIAGRAM MAPPING
        # =====================================================================
        try:
            logger.log_step(pipeline_run_id, "Step 2: Diagram Mapping", "Starting diagram mapping", "Mapping extracted diagrams to questions")
            print("Step 2: Starting diagram mapping...")
            
            # Check if step 1 was successful AND if an overview image was created
            if results['step_results'].get('step1', {}).get('success', False) and preview_image_for_mapping_path:
                # Generate mapping within the main pipeline context
                raw_response = generate_diagram_mapping_internal(temp_pdf_path, preview_image_for_mapping_path, logger, pipeline_run_id)
                
                results['step_results']['step2'] = {
                    'success': True,
                    'mapping_generated': True
                }
                
                logger.log_step(pipeline_run_id, "Step 2: Completed", "Diagram mapping successful", "Generated diagram-to-question mapping")
                print("Step 2: Diagram mapping completed")
                
                # Save to database - read the mapping JSON file
                try:
                    mapping_file_path = Path(logger.get_run_dir(pipeline_run_id)) / "step2_diagram_mapping" / "step2_diagram_mapping.json"
                    if mapping_file_path.exists():
                        with open(mapping_file_path, 'r') as f:
                            mapping_json = json.load(f)
                        
                        # Read raw response file
                        raw_response = None
                        raw_file_path = Path(logger.get_run_dir(pipeline_run_id)) / "step2_diagram_mapping" / "step2_diagram_mapping_raw.txt"
                        if raw_file_path.exists():
                            with open(raw_file_path, 'r') as f:
                                raw_response = f.read()
                        
                        await db_integration.save_diagram_mapping_result(
                            run_id=pipeline_run_id,
                            mapping_json=mapping_json,
                            raw_response=raw_response
                        )
                except Exception as db_error:
                    print(f"Warning: Failed to save diagram mapping to database: {db_error}")
            else:
                error_reason = "No diagrams found to map" if results['step_results'].get('step1', {}).get('success', False) else "Step 1 failed"
                logger.log_step(pipeline_run_id, "Step 2: Skipped", error_reason, f"Cannot proceed: {error_reason}")
                print(f"Step 2: Skipped - {error_reason}")
                results['step_results']['step2'] = {
                    'success': False,
                    'error': error_reason
                }
                
        except Exception as e:
            error_msg = f"Step 2 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step2'] = {
                'success': False,
                'error': str(e)
            }
            logger.log_error(pipeline_run_id, "Step 2: Failed", e)
            print(error_msg)
        
        # =====================================================================
        # STEP 3: FULL PDF QUESTION EXTRACTION
        # =====================================================================
        try:
            logger.log_step(pipeline_run_id, "Step 3: Question Extraction", "Starting question extraction", "Extracting questions from PDF")
            print("Step 3: Starting full PDF question extraction...")
            
            markdown_content = generate_markdown_from_pdf(temp_pdf_path, logger, pipeline_run_id)
            
            results['step_results']['step3'] = {
                'success': True,
                'questions_generated': True
            }
            
            logger.log_step(pipeline_run_id, "Step 3: Completed", "Question extraction successful", "Generated markdown format questions")
            print("Step 3: Full PDF question extraction completed")
            
            # Save to database - read the markdown file
            try:
                markdown_file_path = Path(logger.get_run_dir(pipeline_run_id)) / "step3_question_extraction" / "step3_questions.md"
                if markdown_file_path.exists():
                    with open(markdown_file_path, 'r') as f:
                        questions_markdown = f.read()
                    
                    await db_integration.save_question_extraction_result(
                        run_id=pipeline_run_id,
                        questions_markdown=questions_markdown,
                        markdown_file_path=str(markdown_file_path)
                    )
            except Exception as db_error:
                print(f"Warning: Failed to save question extraction to database: {db_error}")
                
        except Exception as e:
            error_msg = f"Step 3 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step3'] = {
                'success': False,
                'error': str(e)
            }
            logger.log_error(pipeline_run_id, "Step 3: Failed", e)
            print(error_msg)

        # =====================================================================
        # STEP 4: MARKS MAPPING
        # =====================================================================
        try:
            logger.log_step(pipeline_run_id, "Step 4: Marks Mapping", "Starting marks mapping", "Analyzing question types and marks allocation")
            print("Step 4: Starting marks mapping...")
            
            marks_content = generate_marks_mapping(temp_pdf_path, logger, pipeline_run_id)
            
            results['step_results']['step4'] = {
                'success': True,
                'marks_generated': True
            }
            
            logger.log_step(pipeline_run_id, "Step 4: Completed", "Marks mapping successful", "Generated question types and marks allocation")
            print("Step 4: Marks mapping completed")
            
            # Save to database - read the marks mapping JSON file
            try:
                marks_file_path = Path(logger.get_run_dir(pipeline_run_id)) / "step4_marks_mapping" / "step4_marks_mapping.json"
                if marks_file_path.exists():
                    with open(marks_file_path, 'r') as f:
                        marks_json = json.load(f)
                    
                    # Read raw response file
                    raw_response = None
                    raw_file_path = Path(logger.get_run_dir(pipeline_run_id)) / "step4_marks_mapping" / "step4_marks_mapping_raw.txt"
                    if raw_file_path.exists():
                        with open(raw_file_path, 'r') as f:
                            raw_response = f.read()
                    
                    await db_integration.save_marks_mapping_result(
                        run_id=pipeline_run_id,
                        marks_json=marks_json,
                        raw_response=raw_response
                    )
            except Exception as db_error:
                print(f"Warning: Failed to save marks mapping to database: {db_error}")
                
        except Exception as e:
            error_msg = f"Step 4 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step4'] = {
                'success': False,
                'error': str(e)
            }
            logger.log_error(pipeline_run_id, "Step 4: Failed", e)
            print(error_msg)
        
        # =====================================================================
        # FINALIZATION
        # =====================================================================
        
        # Mark as successful if at least one step succeeded
        if any(step.get('success', False) for step in results['step_results'].values()):
            results['success'] = True
            logger.complete_run(pipeline_run_id, success=True)
            # Complete pipeline in database
            try:
                await db_integration.complete_pipeline(success=True)
            except Exception as db_error:
                print(f"Warning: Failed to complete pipeline in database: {db_error}")
        else:
            logger.complete_run(pipeline_run_id, success=False)
            # Mark pipeline as failed in database
            try:
                await db_integration.complete_pipeline(success=False)
            except Exception as db_error:
                print(f"Warning: Failed to mark pipeline as failed in database: {db_error}")
        
        results['final_outputs'] = {
            'total_diagrams': results['step_results'].get('step1', {}).get('total_figures', 0),
            'diagram_mapping': results['step_results'].get('step2', {}).get('mapping_generated', False),
            'questions_extracted': results['step_results'].get('step3', {}).get('questions_generated', False),
            'marks_mapping': results['step_results'].get('step4', {}).get('marks_generated', False),
            'pipeline_run_id': pipeline_run_id,
            'filename': filename
        }
        
        logger.log_step(pipeline_run_id, "Pipeline Completion", "All steps completed", f"Processing finished with success: {results['success']}")
        print("🎉 End-to-end processing completed!")
        
    except Exception as e:
        error_msg = f"Fatal error in end-to-end processing: {str(e)}"
        results['errors'].append(error_msg)
        logger.log_error(pipeline_run_id, "Fatal Pipeline Error", e)
        logger.complete_run(pipeline_run_id, success=False)
        print(error_msg)
    
    finally:
        # Cleanup temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
    
    return results

def run_diagram_extraction_only(file_content: bytes, filename: str = "uploaded.pdf") -> Dict[str, Any]:
    """Run only diagram extraction"""
    try:
        # Check dependencies first
        if not DEPENDENCIES_OK:
            return {
                'success': False,
                'error': "Missing required dependencies. Please install missing packages."
            }
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            temp_pdf_path = tmp_file.name
        
        parsed_images, figure_snippets = extract_diagrams_from_pdf(temp_pdf_path)
        images_dir, meta_path = log_diagram_snippets(figure_snippets)
        
        # Cleanup
        os.unlink(temp_pdf_path)
        
        return {
            'success': True,
            'images_dir': images_dir,
            'meta_path': meta_path,
            'total_figures': sum(len(figs) for figs in figure_snippets),
            'filename': filename
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def run_question_extraction_only(file_content: bytes, filename: str = "uploaded.pdf") -> Dict[str, Any]:
    """Run only question extraction"""
    try:
        # Check dependencies first
        if not DEPENDENCIES_OK:
            return {
                'success': False,
                'error': "Missing required dependencies. Please install missing packages."
            }
        
        if not GEMINI_CLIENT_OK:
            return {
                'success': False,
                'error': "Gemini client not initialized. Check your API key."
            }
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            temp_pdf_path = tmp_file.name
        
        questions_path = generate_markdown_from_pdf(temp_pdf_path)
        
        # Cleanup
        os.unlink(temp_pdf_path)
        
        return {
            'success': True,
            'questions_path': questions_path,
            'filename': filename
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        } 