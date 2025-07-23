"""
Configuration file for CBSE Question Paper Processing

This module contains configuration settings for the DocYOLO model and 
Gemini AI integration used in question paper processing.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# API CONFIGURATION
# =============================================================================

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set")

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# DocYOLO Model Configuration
MODEL_CONFIG = {
    'repository': 'juliozhao/DocLayout-YOLO-DocStructBench',
    'model_file': 'doclayout_yolo_docstructbench_imgsz1024.pt',
    'image_size': 1024,
    'confidence_threshold': 0.25,
    'iou_threshold': 0.45
}

# Class ID to Name Mapping for DocYOLO
CLASS_NAMES = {
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

# =============================================================================
# PROCESSING CONFIGURATION
# =============================================================================

# File Processing Settings
PROCESSING_CONFIG = {
    'max_file_size_mb': 50,
    'supported_formats': ['.pdf'],
    'pdf_dpi': 300,
    'temp_dir': '/tmp'
}

# Gemini Model Settings
GEMINI_CONFIG = {
    'model_diagram_mapping': 'gemini-2.5-flash',
    'model_question_extraction': 'gemini-2.5-flash-lite-preview-06-17',
    'temperature': 0,
    'max_output_tokens': 60000,
    'thinking_budget': 5000
}

# =============================================================================
# DIRECTORY CONFIGURATION
# =============================================================================

# Get the base directory (response_processing folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Models directory (where DocYOLO weights are stored)
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# Logs directory (where processing results are stored)
LOGS_DIR = os.path.join(BASE_DIR, '..', '..', 'logs')

# Subdirectories for different types of logs
LOG_SUBDIRS = {
    'diagrams': 'diagrams',
    'diagram_mappings': 'diagram_mappings',
    'gemini_questions': 'gemini_questions',
    'full_pdf_questions': 'full_pdf_questions'
}

# =============================================================================
# REQUIRED DEPENDENCIES
# =============================================================================

REQUIRED_PACKAGES = [
    'torch',
    'torchvision', 
    'doclayout-yolo==0.0.4',
    'google-genai',
    'huggingface_hub',
    'pdf2image==1.16.3',
    'PyMuPDF',
    'matplotlib',
    'pillow',
    'numpy',
    'opencv-python',
    'python-dotenv'
]

# System dependencies (need to be installed separately)
SYSTEM_DEPENDENCIES = [
    'poppler-utils',  # Required for pdf2image
    'tesseract-ocr'   # Optional, for OCR functionality
]

def get_model_path():
    """Get the full path to the DocYOLO model file"""
    return os.path.join(
        MODELS_DIR, 
        'DocLayout-YOLO-DocStructBench',
        MODEL_CONFIG['model_file']
    )

def get_log_dir(log_type: str):
    """Get the full path to a specific log directory"""
    if log_type not in LOG_SUBDIRS:
        raise ValueError(f"Unknown log type: {log_type}")
    
    return os.path.join(LOGS_DIR, LOG_SUBDIRS[log_type])

def ensure_directories():
    """Create all necessary directories if they don't exist"""
    directories = [
        MODELS_DIR,
        LOGS_DIR,
        *[get_log_dir(log_type) for log_type in LOG_SUBDIRS.keys()]
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True) 