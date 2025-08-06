#!/usr/bin/env python3
"""
Solution Generation using LLM1 API function for text output.

This script takes JSON input, combines it with metadata, and generates detailed step-by-step solutions
for educational questions. It supports various question types and can process images as additional input.

Features:
- Generates comprehensive, educational step-by-step solutions
- Supports image input for questions with diagrams
- Uses metadata for context-aware solution generation
- Implements caching for performance optimization
- Provides detailed logging and error handling
- Command-line interface for easy usage

Usage:
    python soln_gen.py input_file.json metadata_file.json [output_file.txt] [--images image1.jpg image2.jpg]

Example:
    python soln_gen.py question.json metadata.json solution.txt --images diagram.jpg --log-level DEBUG

Dependencies:
- LLM1.py: Core API function for Gemini API calls
- .env file: Must contain GEMINI_API_KEY
- Input JSON: Must contain required fields (ques_identifier, ques_text, question_type, target_class, marks)
- Metadata JSON: Must contain required fields (ques_identifier, assessment_intent, bloom_taxonomy_level)

Author: AI Assistant
Version: 1.0
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from .LLM1 import generate_marking_scheme


# Configure logging
def setup_logging(log_level: str = "INFO") -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('soln_gen.log'),
            logging.StreamHandler()
        ]
    )

# Set up logger
logger = logging.getLogger(__name__)


# Configuration constants
DEFAULT_MODEL = "gemini-2.5-flash-lite-preview-06-17"
DEFAULT_TEMPERATURE = 0.5 
DEFAULT_MAX_OUTPUT_TOKENS = 30000
DEFAULT_THINKING_BUDGET = 8192
DEFAULT_RESPONSE_MIME_TYPE = "text/plain"


def get_api_configuration() -> Dict[str, Any]:
    """
    Get API configuration parameters.
    
    Returns:
        Dictionary containing API configuration
    """
    return {
        "model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
        "thinking_budget": DEFAULT_THINKING_BUDGET,
        "response_mime_type": DEFAULT_RESPONSE_MIME_TYPE,
        "stream": False,
        "response_schema": None
    }


# Cache for loaded documentation files
_doc_cache = {}

def load_documentation(md_filename: str) -> str:
    """
    Load a specific markdown documentation file from the same folder.
    Uses caching to avoid repeated file reads.
    
    Args:
        md_filename: Name of the markdown file to load
        
    Returns:
        Content of the markdown file
    """
    # Check cache first
    if md_filename in _doc_cache:
        logger.debug(f"Using cached version of {md_filename}")
        return _doc_cache[md_filename]
    
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    
    # Try guide directory first
    guide_dir = parent_dir / "guide"
    md_path = guide_dir / md_filename
    
    # If not found in guide, try prompt directory
    if not md_path.exists():
        prompt_dir = parent_dir / "prompt"
        md_path = prompt_dir / md_filename
    
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_filename}")
    
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cache the content
        _doc_cache[md_filename] = content
        logger.debug(f"Cached {md_filename} ({len(content)} chars)")
        print(f"✓ Loaded {md_filename}")
        return content
    except Exception as e:
        raise Exception(f"Error loading {md_filename}: {e}")


def load_json_input(input_filename: str) -> Dict[str, Any]:
    """
    Load JSON input from file.
    
    Args:
        input_filename: Input JSON file name
        
    Returns:
        Loaded JSON data
    """
    try:
        logger.info(f"Loading input file: {input_filename}")
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"✓ Loaded input from {input_filename}")
        print(f"✓ Loaded input from {input_filename}")
        return data
    except Exception as e:
        logger.error(f"Error loading input file {input_filename}: {e}")
        print(f"Error loading input file: {e}")
        raise


def load_metadata_input(metadata_filename: str) -> Dict[str, Any]:
    """
    Load metadata JSON input from file.
    
    Args:
        metadata_filename: Metadata JSON file name
        
    Returns:
        Loaded metadata JSON data
    """
    try:
        with open(metadata_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded metadata from {metadata_filename}")
        return data
    except Exception as e:
        print(f"Error loading metadata file: {e}")
        raise


def create_solution_prompt(
    json_input: Dict[str, Any],
    metadata: Dict[str, Any]
) -> str:
    """
    Create a user prompt for Part 1: solution‐outline generation.
    
    Args:
        json_input: Input JSON data containing question
        metadata: Metadata JSON data
        
    Returns:
        Formatted prompt for the LLM to draft a solution outline
    """
    # Extract question information
    ques_identifier = json_input.get("ques_identifier", "")
    ques_text       = json_input.get("ques_text", "")
    question_type   = json_input.get("question_type", "")
    target_class    = json_input.get("target_class", "")
    marks_analysis  = json_input.get("marks_analysis", "")
    
    # Extract metadata information
    assessment_intent = metadata.get("assessment_intent", "")
    bloom_level       = metadata.get("bloom_taxonomy_level", "")
    chapters          = metadata.get("tags", {}).get("chapters", [])
    
    # Format chapters and concepts
    chapters_section = ""
    if chapters:
        chapters_section = "## Related Chapters and Concepts:\n"
        for chapter in chapters:
            chapters_section += f"- **{chapter.get('chapter','')}**:\n"
            for concept in chapter.get('concepts', []):
                chapters_section += f"  - {concept.get('name','')}\n"
        chapters_section += "\n"

    # Dynamically load prompt guide based on question type
    if question_type == "Subjective":
        prompt_guide = load_documentation("prompt_subjective_no_subparts.md")
    elif question_type == "Case-Study":
        prompt_guide = load_documentation("prompt_subjective_with_subparts.md")
    else:
        prompt_guide = ""  # Default or error case

    prompt = f"""
# Mission Objective: Generate a Flawless, Teacher-Centric Solution Outline

Your primary goal is to prepare the marking scheme foundation—the step-by-step solution outline that will later be annotated with marks. This outline must be teacher-centric, objective, and grounded in the CBSE syllabus for Grade {target_class}. Your entire process must follow the rigid cognitive workflow defined below to ensure accuracy, completeness, and adherence to all constraints.

---

# `<Input_Context>`

- **ID:** {ques_identifier}
- **Text:** {ques_text}
- **Type:** {question_type}
- **Marks Analysis:** {marks_analysis}
- **Assessment Intent:** {assessment_intent}
- **Bloom's Level:** {bloom_level}
- **Chapter Info:** {chapters_section}

---

{prompt_guide}
  """
    return prompt




def generate_solution(
    json_input: Dict[str, Any],
    metadata: Dict[str, Any],
    stream: bool = False,
    image_paths: Optional[List[str]] = None
) -> (Optional[str], Optional[Dict[str, Any]]):
    """
    Generate detailed solution from JSON input and metadata.
    
    Args:
        json_input: Input JSON data
        metadata: Metadata JSON data
        stream: Whether to stream the response
        image_paths: Optional list of paths to image files
        
    Returns:
        A tuple containing the generated solution as a string and usage metadata.
        Returns (None, None) if generation fails.
    """
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
    
    # Create user prompt
    user_prompt = create_solution_prompt(json_input, metadata)
    print(f"✓ User prompt created ({len(user_prompt)} characters)")
    
    # Process image paths if provided
    if image_paths:
        print(f"✓ Using {len(image_paths)} image(s) as additional input")
        for img_path in image_paths:
            if not Path(img_path).exists():
                print(f"⚠ Warning: Image file not found: {img_path}")
    
    # System instruction for solution generation

    target_class = json_input.get("target_class", "")
    system_instruction = f"""
<Persona>
    You are an expert CBSE Grade {target_class} STEM teacher and examiner. Your role is to draft Solution Outline for a marking scheme. You must think like a teacher building a marking guide, focusing on clarity, objectivity, and alignment with the assessment intent and Bloom's level. Use age-appropriate language and precise terminology.
</Persona>

**CRITICAL RULES:**
1.  **DO NOT** assign marks or points to any step. Your task is only to create the solution structure.
2.  You must think and write from the perspective of a teacher creating a grading guide for other teachers. The language must be objective, clear, and precise.
3.  Every step you create must be objectively gradable, with a clear pass/fail condition."""


    
    # Get API configuration
    config = get_api_configuration()
    
    # Get API configuration
    config = get_api_configuration()

    # Retry logic with exponential backoff
    max_retries = 3
    base_delay = 1  # in seconds
    
    for attempt in range(max_retries):
        try:
            print("Generating solution...")
            response, usage_metadata = generate_marking_scheme(
                api_key=api_key,
                system_instruction=system_instruction,
                model=config["model"],
                temperature=config["temperature"],
                max_output_tokens=config["max_output_tokens"],
                thinking_budget=config["thinking_budget"],
                response_mime_type=config["response_mime_type"],
                response_schema=config["response_schema"],
                stream=stream,
                text_input=user_prompt,
                image_paths=image_paths
            )
            
            if response:
                print("✓ Solution generated successfully")
                return response, usage_metadata
            else:
                # If response is None, it might be a non-exception failure
                logger.warning(f"Attempt {attempt + 1} failed, response was None.")
                
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed with error: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("All retry attempts failed.")
                print(f"Error generating solution after {max_retries} attempts: {e}")
                raise
    
    return None, None


def save_solution(solution: str, output_filename: str) -> None:
    """
    Save solution to a text file.
    
    Args:
        solution: Solution text to save
        output_filename: Output file name
    """
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(solution)
        print(f"✓ Solution saved to {output_filename}")
    except Exception as e:
        print(f"Error saving solution: {e}")
        raise


def validate_input_data(input_data: Dict[str, Any]) -> bool:
    """
    Validate input JSON data for required fields.
    
    Args:
        input_data: Input JSON data to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["ques_identifier", "ques_text", "question_type", "target_class", "marks"]
    
    for field in required_fields:
        if field not in input_data:
            print(f"Error: Required field '{field}' missing from input data")
            return False
        if not input_data[field]:
            print(f"Error: Required field '{field}' is empty")
            return False
    
    return True


def validate_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Validate metadata JSON data for required fields.
    
    Args:
        metadata: Metadata JSON data to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["ques_identifier", "assessment_intent", "bloom_taxonomy_level"]
    
    for field in required_fields:
        if field not in metadata:
            print(f"Error: Required field '{field}' missing from metadata")
            return False
        if not metadata[field]:
            print(f"Error: Required field '{field}' is empty in metadata")
            return False
    
    return True


def process_file_input(
    input_file: str,
    metadata_file: str,
    output_file: str = None,
    image_files: List[str] = None
) -> (Optional[str], Optional[Dict[str, Any]]):
    """
    Process JSON input file and generate solution.
    
    Args:
        input_file: Path to input JSON file
        metadata_file: Path to metadata JSON file
        output_file: Path to output text file (optional)
        image_files: List of paths to image files (optional)
        
    Returns:
        A tuple containing the generated solution and usage metadata.
    """
    try:
        start_time = time.time()
        logger.info("Starting solution generation process")
        
        # Validate file existence
        if not Path(input_file).exists():
            print(f"Error: Input file '{input_file}' not found")
            return None, None
        
        if not Path(metadata_file).exists():
            print(f"Error: Metadata file '{metadata_file}' not found")
            return None, None
        
        # Validate image files if provided
        if image_files:
            for img_file in image_files:
                if not Path(img_file).exists():
                    print(f"Warning: Image file '{img_file}' not found")
        
        # Load input data
        load_start = time.time()
        input_data = load_json_input(input_file)
        
        # Load metadata
        metadata = load_metadata_input(metadata_file)
        load_time = time.time() - load_start
        logger.debug(f"File loading took {load_time:.2f} seconds")
        
        # Validate input data
        if not validate_input_data(input_data):
            return None, None
        
        # Validate metadata
        if not validate_metadata(metadata):
            return None, None
        
        # Generate solution
        gen_start = time.time()
        solution, usage_metadata = generate_solution(
            json_input=input_data,
            metadata=metadata,
            stream=False,
            image_paths=image_files
        )
        gen_time = time.time() - gen_start
        logger.info(f"Solution generation took {gen_time:.2f} seconds")
        
        if solution:
            print("\n" + "="*60)
            print("GENERATED SOLUTION")
            print("="*60)
            print(solution)
            print("="*60)
            
            # Save to file if specified
            if output_file:
                save_solution(solution, output_file)
            else:
                # Default output filename based on input filename
                base_name = Path(input_file).stem
                default_output = f"{base_name}_solution.txt"
                save_solution(solution, default_output)
            
            total_time = time.time() - start_time
            logger.info(f"Total processing time: {total_time:.2f} seconds")
                
        return solution, usage_metadata
    
    except Exception as e:
        logger.error(f"Error processing file input: {e}")
        print(f"Error processing file input: {e}")
        return None, None


def main():
    """Main function to process input files."""
    import sys
    import argparse
    
    print("Solution Generation Tool")
    print("=" * 60)
    
    try:
        # Set up argument parser
        parser = argparse.ArgumentParser(description='Generate detailed solutions for educational questions')
        parser.add_argument('input_file', help='Input JSON file containing question data')
        parser.add_argument('metadata_file', help='Metadata JSON file containing question analysis')
        parser.add_argument('output_file', nargs='?', help='Output text file for solution')
        parser.add_argument('--images', '-i', nargs='+', help='Image files containing question diagrams')
        parser.add_argument('--stream', '-s', action='store_true', help='Stream the response (default: False)')
        parser.add_argument('--log-level', '-l', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                           default='INFO', help='Set logging level (default: INFO)')
        
        args = parser.parse_args()
        
        # Set up logging
        setup_logging(args.log_level)
        logger.info("Starting solution generation process")
        
        # Process input file with optional images
        print(f"Processing input file: {args.input_file}")
        print(f"Using metadata file: {args.metadata_file}")
        logger.info(f"Processing input file: {args.input_file}")
        logger.info(f"Using metadata file: {args.metadata_file}")
        
        if args.images:
            print(f"Using images: {', '.join(args.images)}")
            logger.info(f"Using images: {', '.join(args.images)}")
        
        solution, usage_metadata = process_file_input(
            input_file=args.input_file,
            metadata_file=args.metadata_file,
            output_file=args.output_file,
            image_files=args.images
        )
        
        if solution:
            print("\n✓ Solution generation completed successfully!")
            logger.info("Solution generation completed successfully")
            if usage_metadata:
                logger.info(f"Token usage: {usage_metadata}")
        else:
            print("\n✗ Solution generation failed!")
            logger.error("Solution generation failed")
            sys.exit(1)
        
    except Exception as e:
        logger.critical(f"Critical error in main: {e}")
        print(f"Error: {e}")
        print("\nUsage: python soln_gen.py input_file.json metadata_file.json [output_file.txt] [--images image1.jpg image2.jpg] [--log-level INFO]")
        print("Please check your API key in .env file and network connection.")
        sys.exit(1)


if __name__ == "__main__":
    main() 