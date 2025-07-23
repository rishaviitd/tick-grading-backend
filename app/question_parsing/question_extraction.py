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

# Load environment variables
load_dotenv()

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
        print(f"Using device: {device}")
            
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
                
                # Extract figure snippets
                fig_indices = [i for i, cls in enumerate(c) if int(cls) == 3]
                fig_boxes = [b[i] for i in fig_indices]
                
                page_figures = []
                for box in fig_boxes:
                    x1, y1, x2, y2 = box
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Extract figure from page
                    page_array = np.array(page)
                    figure_crop = page_array[y1:y2, x1:x2]
                    page_figures.append(figure_crop)
                
                figure_snippets.append(page_figures)
                
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

def generate_diagram_mapping(pdf_path: str, image_path: str) -> Tuple[str, str]:
    """Generate diagram mapping using Gemini"""
    try:
        # System and user prompts for diagram mapping
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

## Step 3: Question-wise Diagram Description
**For each question that contains actual visual diagrams:**
- Identify the question number
- Determine if it's a case study type question
- **CRITICAL**: Only analyze questions with actual printed diagrams/figures/images
- **IGNORE**: Questions that only have textual descriptions like "A triangle ABC has sides...", "In a circle with center O...", "Consider a function f(x)..." without actual visual diagrams
- Locate the actual visual diagram(s) within that question
- Generate a detailed description of the visual diagram as it appears in the question
- Note the diagram's position within the question (beginning, middle, end, or in internal choice)

**Output format for Step 3:**
```
Question X: 
- Question type: [case study/regular]
- Has actual visual diagram: [Yes - if printed diagram present]
- Diagram location: [position in question]
- Diagram description: [detailed description of the actual visual content]
- Internal choice status: [first/second/both/null]

Question Y:
- Question type: [case study/regular]
- Has actual visual diagram: [Yes - if printed diagram present]
- Diagram location: [position in question] 
- Diagram description: [detailed description of the actual visual content]
- Internal choice status: [first/second/both/null]

...continue for all questions with actual visual diagrams
```

## Step 4: Cross-Reference and Mapping
**Match figures from image to questions:**
- Compare the figure descriptions from Step 1 with question diagram descriptions from Step 3
- Match based on:
  - Visual content similarity
  - Page number correlation
  - Figure number references
  - Context alignment

**Output format for Step 4:**
```
Mapping Analysis:
Figure-1 (Page X): Matches diagram in Question Y because [detailed reasoning]
Figure-2 (Page Z): Matches diagram in Question W because [detailed reasoning]
...continue for all figures
```

## Step 5: Internal Choice Classification
**For each mapped figure:**
- First, determine if the question is a case study type question
- If it's a case study question: Classification = null (regardless of OR separators in subparts)
- If it's a regular question:
  - Determine if the question has an "OR" separator creating internal choices
  - Identify where the diagram appears relative to the "OR"
  - Classify as: first/second/both/null

**Output format for Step 5:**
```
Internal Choice Analysis:
Question Y: Case study type → Classification: null
Question W: Regular question + Has OR separator → Figure-1 appears in [first/second/both] part
Question Z: Regular question + No OR separator → Classification: null
...continue for all questions
```

## Step 6: Final Output
**Present only the final mapping in JSON format:**

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

## Critical Instructions:
- Show your complete reasoning process for each step
- **CRITICAL**: Only consider questions with actual printed diagrams/figures/images, NOT textual descriptions
- **IGNORE**: Questions like "A triangle ABC with sides 3, 4, 5..." or "In the given circle..." that only have text descriptions without visual diagrams
- **FOCUS**: Only on questions that have actual visual content (diagrams, figures, charts, images)
- Ensure every figure from the image is mapped to a question with actual visual content
- Provide detailed visual descriptions for accurate matching
- **IMPORTANT**: For case study type questions, always set choice_location to "null" regardless of any OR separators in subparts
- For regular questions with OR separators, classify as first/second/both based on diagram location
- For regular questions without OR separators, set choice_location to "null"
- Cross-verify all mappings before finalizing
- The final mappings must include ALL figures present in the provided image
- Maintain 100% accuracy in question identification and choice classification

Please follow this systematic approach and provide the comprehensive analysis with the final JSON output.
"""
        
        # Upload files to Gemini
        pdf_file = client.files.upload(file=pdf_path)
        img_file = client.files.upload(file=image_path)

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

        # Save mapping
        logger = UnifiedLogger()
        base_pdf = os.path.splitext(os.path.basename(pdf_path))[0]
        base_img = os.path.splitext(os.path.basename(image_path))[0]
        
        run_id = logger.create_run(LogType.DIAGRAM_MAPPING, "Diagram Mapping", {
            "pdf_file": os.path.basename(pdf_path),
            "image_file": os.path.basename(image_path)
        })
        
        # Save the mapping JSON file
        output_filename = f"{base_pdf}__{base_img}.json"
        mapping_path = logger.save_file(run_id, json.dumps(mapping_json, indent=2), output_filename)
        
        # Save the raw response as well
        raw_filename = f"{base_pdf}__{base_img}_raw.txt"
        logger.save_file(run_id, raw_text, raw_filename)
        
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
        try:
            client.files.delete(name=img_file.name)
        except:
            pass
        raise RuntimeError(f"Diagram mapping failed: {str(e)}")

def generate_markdown_from_pdf(pdf_path: str) -> str:
    """Generate markdown from PDF using Gemini"""
    try:
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
        logger = UnifiedLogger()
        run_id = logger.create_run(LogType.QUESTION_EXTRACTION, "Question Extraction", {
            "pdf_file": os.path.basename(pdf_path)
        })
        
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


def run_end_to_end_processing(file_content: bytes, filename: str = "uploaded.pdf") -> Dict[str, Any]:
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
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            temp_pdf_path = tmp_file.name
            temp_files.append(temp_pdf_path)
        
        print("Step 0: File uploaded successfully")
        
        # =====================================================================
        # STEP 1: DIAGRAM EXTRACTION
        # =====================================================================
        try:
            print("Step 1: Starting diagram extraction...")
            
            parsed_images, figure_snippets = extract_diagrams_from_pdf(temp_pdf_path)
            
            # Create a single overview image for the mapping step
            preview_image_for_mapping_path = None
            if parsed_images:
                overview_image = vstack_images(parsed_images)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                    overview_image.save(tmp_img, format="PNG")
                    preview_image_for_mapping_path = tmp_img.name
                    temp_files.append(preview_image_for_mapping_path)

            # Log snippets and metadata for debugging and viewing
            images_dir, meta_path = log_diagram_snippets(figure_snippets)
            
            results['step_results']['step1'] = {
                'success': True,
                'images_dir': images_dir,
                'meta_path': meta_path,
                'total_figures': sum(len(figs) for figs in figure_snippets)
            }
            
            print(f"Step 1: Extracted {results['step_results']['step1']['total_figures']} diagrams")
                
        except Exception as e:
            error_msg = f"Step 1 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step1'] = {
                'success': False,
                'error': str(e)
            }
            print(error_msg)
        
        # =====================================================================
        # STEP 2: DIAGRAM MAPPING
        # =====================================================================
        try:
            print("Step 2: Starting diagram mapping...")
            
            # Check if step 1 was successful AND if an overview image was created
            if results['step_results'].get('step1', {}).get('success', False) and preview_image_for_mapping_path:
                mapping_path, raw_response = generate_diagram_mapping(temp_pdf_path, preview_image_for_mapping_path)
                
                results['step_results']['step2'] = {
                    'success': True,
                    'mapping_path': mapping_path,
                    'raw_response': raw_response
                }
                
                print("Step 2: Diagram mapping completed")
            else:
                error_reason = "No diagrams found to map" if results['step_results'].get('step1', {}).get('success', False) else "Step 1 failed"
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
            print(error_msg)
        
        # =====================================================================
        # STEP 3: FULL PDF QUESTION EXTRACTION
        # =====================================================================
        try:
            print("Step 3: Starting full PDF question extraction...")
            
            questions_path = generate_markdown_from_pdf(temp_pdf_path)
            
            results['step_results']['step3'] = {
                'success': True,
                'questions_path': questions_path
            }
            
            print("Step 3: Full PDF question extraction completed")
                
        except Exception as e:
            error_msg = f"Step 3 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step3'] = {
                'success': False,
                'error': str(e)
            }
            print(error_msg)
        
        # =====================================================================
        # FINALIZATION
        # =====================================================================
        
        # Mark as successful if at least one step succeeded
        if any(step.get('success', False) for step in results['step_results'].values()):
            results['success'] = True
        
        results['final_outputs'] = {
            'total_diagrams': results['step_results'].get('step1', {}).get('total_figures', 0),
            'diagram_mapping': results['step_results'].get('step2', {}).get('mapping_path'),
            'questions_extracted': results['step_results'].get('step3', {}).get('questions_path'),
            'filename': filename
        }
        
        print("🎉 End-to-end processing completed!")
        
    except Exception as e:
        error_msg = f"Fatal error in end-to-end processing: {str(e)}"
        results['errors'].append(error_msg)
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