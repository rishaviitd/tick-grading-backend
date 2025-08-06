#!/usr/bin/env python3
"""
Marking Scheme Generation using LLM1 API function for text output.

This script takes JSON input, metadata, and question-type-specific guides to generate comprehensive 
marking schemes for educational questions. It automatically selects the appropriate marking guide 
based on the question type and creates detailed evaluation criteria.

Features:
- Generates comprehensive, fair marking schemes
- Automatically selects appropriate guide based on question type
- Supports image input for questions with diagrams
- Uses metadata for context-aware marking scheme generation
- Implements caching for performance optimization
- Provides detailed logging and error handling
- Command-line interface for easy usage

Supported Question Types:
- MCQ: Multiple Choice Questions
- Subjective: Open-ended questions
- Case-Study: Multi-part case study questions
- Assertion-Reason: Assertion-reason type questions
- Fill in the Blanks: Fill-in-the-blank questions
- Internal Choice: Questions with internal choice options

Usage:
    python markingscheme.py input_file.json metadata_file.json [output_file.txt] [--images image1.jpg image2.jpg]

Example:
    python markingscheme.py question.json metadata.json marking_scheme.txt --images diagram.jpg --log-level DEBUG

Dependencies:
- LLM1.py: Core API function for Gemini API calls
- .env file: Must contain GEMINI_API_KEY
- Guide files: Markdown files for each question type (guide_*.md)
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
            logging.FileHandler('markingscheme.log'),
            logging.StreamHandler()
        ]
    )

# Set up logger
logger = logging.getLogger(__name__)


# Question type to guide file mapping
QUESTION_TYPE_GUIDE_MAP = {
    "MCQ": "guide_mcq.md",
    "Subjective": "guide_subjective.md",
    "Case-Study": "guide_case_study.md",
    "Assertion-Reason": "guide_assertion_reason.md",
    "Fill in the Blanks": "guide_fill_in_the_blanks.md",
    "Internal Choice": "guide_internal_choice.md"
}


# Configuration constants
DEFAULT_MODEL = "gemini-2.5-flash-lite-preview-06-17"
DEFAULT_TEMPERATURE = 0.5  # Lower temperature for consistent marking schemes
DEFAULT_MAX_OUTPUT_TOKENS = 15000
DEFAULT_THINKING_BUDGET = 2500
DEFAULT_RESPONSE_MIME_TYPE = "text/plain"


def get_api_configuration(question_type: str) -> Dict[str, Any]:
    """
    Get API configuration parameters, ensuring JSON output for all question types.
    
    Returns:
        Dictionary containing API configuration
    """
    # Schema for MCQ and Assertion-Reasoning questions
    if question_type in ["MCQ", "Assertion-Reason"]:
        response_schema = {
            "type": "object",
            "properties": {
                "ques_identifier": {"type": "string"},
                "total_marks": {"type": "number"},
                "correct_option": {"type": "string"},
                "acceptable_answers": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "solution": {"type": "string"}
            },
            "required": ["ques_identifier", "total_marks", "correct_option", "acceptable_answers", "solution"]
        }
    elif question_type == "Case-Study":
        response_schema = {
  "type": "object",
  "properties": {
    "ques_identifier": {
      "type": "string"
    },
    "parts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "part_label": {
            "type": "string"
          },
          "methods": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "methodName": {
                  "type": "string"
                },
                "markingPoints": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "stepId": {
                        "type": "string"
                      },
                      "MarkType": {
                        "type": "string",
                        "enum": [
                          "B",
                          "M",
                          "A"
                        ]
                      },
                      "marks": {
                        "type": "string",
                        "enum": [
                          "0.5",
                          "1"
                        ]
                      },
                      "Teacher Expectation": {
                        "type": "string"
                      },
                      "Pass if": {
                        "type": "string"
                      },
                      "Fail if": {
                        "type": "string"
                      },
                      "guidance": {
                        "type": "string"
                      }
                    },
                    "propertyOrdering": [
                      "stepId",
                      "MarkType",
                      "marks",
                      "Teacher Expectation",
                      "Pass if",
                      "Fail if",
                      "guidance"
                    ],
                    "required": [
                      "stepId",
                      "MarkType",
                      "marks",
                      "Teacher Expectation",
                      "Pass if",
                      "Fail if",
                      "guidance"
                    ]
                  }
                }
              },
              "propertyOrdering": [
                "methodName",
                "markingPoints"
              ],
              "required": [
                "methodName",
                "markingPoints"
              ]
            }
          }
        },
        "propertyOrdering": [
          "part_label",
          "methods"
        ],
        "required": [
          "part_label",
          "methods"
        ]
      }
    },
    "Question_specific_notes": {
      "type": "string"
    }
  },
  "propertyOrdering": [
    "ques_identifier",
    "parts",
    "Question_specific_notes"
  ],
  "required": [
    "ques_identifier",
    "parts",
    "Question_specific_notes"
  ]
}
    else:
        response_schema = {
            "type": "object",
            "properties": {
                "ques_identifier": {"type": "string"},
                "methods": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "methodName": {"type": "string"},
                            "markingPoints": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "stepId": {"type": "string"},
                                        "MarkType": {"type": "string", "enum": ["B", "M", "A"]},
                                        "marks": {"type": "string", "enum": ["0.5", "1"]},
                                        "Teacher Expectation": {"type": "string"},
                                        "Pass if": {"type": "string"},
                                        "Fail if": {"type": "string"},
                                        "guidance": {"type": "string"}
                                    },
                                    "required": ["stepId", "MarkType", "marks", "Teacher Expectation", "Pass if", "Fail if", "guidance"]
                                }
                            }
                        },
                        "required": ["methodName", "markingPoints"]
                    }
                },
                "Question_specific_notes": {"type": "string"}
            },
            "required": ["ques_identifier", "methods", "Question_specific_notes"]
        }

    return {
        "model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
        "thinking_budget": DEFAULT_THINKING_BUDGET,
        "response_mime_type": "application/json",
        "stream": False,
        "response_schema": response_schema
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
    guide_dir = current_dir.parent / "guide"
    md_path = guide_dir / md_filename
    
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
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded input from {input_filename}")
        return data
    except Exception as e:
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


def get_guide_filename(question_type: str) -> str:
    """
    Get the appropriate guide filename for a question type.
    
    Args:
        question_type: Type of question (MCQ, Subjective, etc.)
        
    Returns:
        Filename of the corresponding guide
    """
    # guide_file = QUESTION_TYPE_GUIDE_MAP["Subjective"]
    guide_file = QUESTION_TYPE_GUIDE_MAP.get(question_type)
    if not guide_file:
        # Default to subjective guide if question type not found
        print(f"⚠ Warning: Question type '{question_type}' not found in mapping. Using subjective guide.")
        guide_file = QUESTION_TYPE_GUIDE_MAP["Subjective"]
    
    return guide_file




def create_marking_scheme_prompt(
    json_input: Dict[str, Any],
    metadata: Dict[str, Any],
    guide_content: str,
    solution_file_path: Optional[str] = None
) -> str:
    """
    Create a user prompt for marking scheme generation.
    
    Args:
        json_input: Input JSON data containing question
        metadata: Metadata JSON data
        guide_content: Content from the question-type-specific guide
        solution_file_path: Path to solution .md file
        
    Returns:
        Formatted prompt for the LLM
    """
    # Extract question information
    ques_identifier = json_input.get("ques_identifier", "")
    ques_text = json_input.get("ques_text", "")
    # marks = json_input.get("marks", "")
    question_type = json_input.get("question_type", "")
    target_class = json_input.get("target_class", "")
    marks_analysis = json_input.get("marks_analysis", "")
    
    # Extract metadata information
    assessment_intent = metadata.get("assessment_intent", "")
    bloom_level = metadata.get("bloom_taxonomy_level", "")
    
    # Load solution content if provided
    solution_content = ""
    if solution_file_path and Path(solution_file_path).exists():
        try:
            with open(solution_file_path, 'r', encoding='utf-8') as f:
                solution_content = f.read()
            logger.info(f"Loaded solution from: {solution_file_path}")
        except Exception as e:
            logger.warning(f"Could not load solution file {solution_file_path}: {e}")
    


    prompt = f"""

# Mission Objective: Generate a Precise JSON Marking Scheme via a Chain-of-Thought Workflow

Your primary goal is to transform a structured solution outline into a precise, teacher-centric JSON marking scheme. This requires a sophisticated, **chain-of-thought cognitive workflow**. You must first perform a detailed mathematical analysis to create a mark allocation plan, then justify that plan based on pedagogical intent, and only then generate the final JSON. Your final output must be a single, valid JSON object conforming to the strict schema provided.

---

# `<Core_Directives>`: Non-Negotiable Rules of Engagement

1.  **JSON Output is Absolute**: The final output **MUST** be a single, valid JSON object. No conversational text, reasoning, or apologies outside of this JSON structure.
2.  **Strict Schema Adherence**: The JSON object must strictly follow the structure and constraints defined in the `<Output_JSON_Schema>`.
3.  **Cognitive Workflow is Mandatory**: You **MUST** follow the four-phase cognitive workflow defined below. Your internal reasoning must clearly show each phase.
4.  **Mark Integrity**: The sum of marks allocated across all `markingPoints` within a single method **MUST** equal the `marks_analysis` for the question. Marks can only be "1" or "0.5".
5.  **Direct Data Transfer**: Fields like `stepId`, `MarkType`, `Teacher Expectation`, `Pass if`, and `Fail if` must be transferred directly from the input `solution_outline`.
6.  **Use `marks_analysis`**: The field for total marks is `marks_analysis`.

## CONTEXT

### 1. Question & Solution Data

*   **Question Information:**
    *   Question ID: {ques_identifier}
    *   Question Text: {ques_text}
    *   Question Type: {question_type}
    *   Grade/Class: {target_class}
    *   Marks Analysis: {marks_analysis}
*   **Assessment Context:**
    *   Assessment Intent: {assessment_intent}
    *   Bloom's Taxonomy Level: {bloom_level}
*   **Solution Reference:**
    *   {solution_content}

### 2. Marking Guidelines & Glossaries


 {guide_content}


    """
    return prompt


def generate_marking_scheme_text(
    json_input: Dict[str, Any],
    metadata: Dict[str, Any],
    stream: bool = False,
    image_paths: Optional[List[str]] = None,
    solution_file_path: Optional[str] = None
) -> Optional[tuple[Dict[str, Any], Any]]:
    """
    Generate marking scheme from JSON input and metadata.
    
    Args:
        json_input: Input JSON data
        metadata: Metadata JSON data
        stream: Whether to stream the response
        image_paths: Optional list of paths to image files
        solution_file_path: Optional path to solution .md file
        
    Returns:
        A tuple containing the generated marking scheme and usage metadata, or (None, None).
    """
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
    
    # Get question type and corresponding guide
    question_type = json_input.get("question_type", "Subjective")

    guide_filename = get_guide_filename(question_type)
    print(f"Loading guide for question type: {question_type}")
    guide_content = load_documentation(guide_filename)
    print(f"✓ Guide loaded ({len(guide_content)} characters)")
    
    # Create user prompt
    user_prompt = create_marking_scheme_prompt(
        json_input,
        metadata,
        guide_content,
        solution_file_path
    )
    print(f"✓ User prompt created ({len(user_prompt)} characters)")
    
    # Process image paths if provided
    if image_paths:
        print(f"✓ Using {len(image_paths)} image(s) as additional input")
        for img_path in image_paths:
            if not Path(img_path).exists():
                print(f"⚠ Warning: Image file not found: {img_path}")
    
    # System instruction for marking scheme generation
    system_instruction = """## Persona
You are an expert assessment designer. Your purpose is to create structured marking schemes from educational materials.

## Output Format
Your response MUST be a single, valid JSON object that conforms to the schema provided. Do not output any other text, explanation, or markdown formatting.

## Style and Tone
The tone of all generated text within the JSON, such as in the "Annotations/Guidance for grader" field, must be instructive, professional, and concise.

## Goals and Rules
Your primary goal is to accurately convert the provided context into the specified JSON format. You must follow these operational rules:
1.  The allocation of marks for each step within a method must be calculated using the algorithm provided in the user prompt.
2.  All guidance and annotation text you generate must be based on the rules and examples provided in the user prompt."""
    
    # Get API configuration
    config = get_api_configuration(question_type)
    
    max_retries = 3
    base_delay = 1  # in seconds
    
    for attempt in range(max_retries):
        try:
            print("Generating marking scheme...")
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
                try:
                    # Parse the JSON string into a dictionary
                    marking_scheme_json = json.loads(response)
                    print("✓ Marking scheme generated and parsed successfully")
                    return marking_scheme_json, usage_metadata
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse marking scheme JSON: {e}")
                    logger.error(f"Raw response from API: {response}")
                    # This is a parsing error, not a generation error, so we don't retry
                    return None, None
            else:
                # If response is empty, treat as a failure and retry
                logger.warning("Marking scheme generation returned an empty response. Retrying...")
                raise Exception("Empty response from API")

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("All retry attempts failed. Marking scheme generation failed.")
                print(f"Error generating marking scheme after {max_retries} attempts: {e}")
                return None, None
    return None, None


def save_marking_scheme(marking_scheme: Dict[str, Any], output_filename: str) -> None:
    """
    Save marking scheme to a JSON file.
    
    Args:
        marking_scheme: Marking scheme dictionary to save
        output_filename: Output file name
    """
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(marking_scheme, f, indent=2, ensure_ascii=False)
        print(f"✓ Marking scheme saved to {output_filename}")
    except Exception as e:
        print(f"Error saving marking scheme: {e}")
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
    image_files: List[str] = None,
    solution_file: str = None
) -> Optional[tuple[Dict[str, Any], Any]]:
    """
    Process JSON input file and generate marking scheme.
    
    Args:
        input_file: Path to input JSON file
        metadata_file: Path to metadata JSON file
        output_file: Path to output text file (optional)
        image_files: List of paths to image files (optional)
        solution_file: Path to solution .md file (optional)
        
    Returns:
        A tuple containing the generated marking scheme and usage metadata, or (None, None).
    """
    try:
        # Validate file existence
        if not Path(input_file).exists():
            print(f"Error: Input file '{input_file}' not found")
            return None
        
        if not Path(metadata_file).exists():
            print(f"Error: Metadata file '{metadata_file}' not found")
            return None
        
        # Validate solution file if provided
        if solution_file and not Path(solution_file).exists():
            print(f"Warning: Solution file '{solution_file}' not found")
        
        # Validate image files if provided
        if image_files:
            for img_file in image_files:
                if not Path(img_file).exists():
                    print(f"Warning: Image file '{img_file}' not found")
        
        # Load input data
        input_data = load_json_input(input_file)
        
        # Load metadata
        metadata = load_metadata_input(metadata_file)
        
        # Validate input data
        if not validate_input_data(input_data):
            return None
        
        # Validate metadata
        if not validate_metadata(metadata):
            return None
        
        # Generate marking scheme
        marking_scheme, usage_metadata = generate_marking_scheme_text(
            json_input=input_data,
            metadata=metadata,
            stream=False,
            image_paths=image_files,
            solution_file_path=solution_file
        )
        
        if marking_scheme:
            print("\n" + "="*60)
            print("GENERATED MARKING SCHEME")
            print("="*60)
            print(marking_scheme)
            print("="*60)
            
            # Save to file if specified
            if output_file:
                save_marking_scheme(marking_scheme, output_file)
            else:
                # Default output filename based on input filename
                base_name = Path(input_file).stem
                default_output = f"{base_name}_marking_scheme.json"
                save_marking_scheme(marking_scheme, default_output)
                
        return marking_scheme, usage_metadata
    
    except Exception as e:
        print(f"Error processing file input: {e}")
        return None, None


def main():
    """Main function to process input files."""
    import sys
    import argparse
    
    print("Marking Scheme Generation Tool")
    print("=" * 60)
    
    try:
        # Set up argument parser
        parser = argparse.ArgumentParser(description='Generate comprehensive marking schemes for educational questions')
        parser.add_argument('input_file', help='Input JSON file containing question data')
        parser.add_argument('metadata_file', help='Metadata JSON file containing question analysis')
        parser.add_argument('output_file', nargs='?', help='Output JSON file for marking scheme')
        parser.add_argument('--images', '-i', nargs='+', help='Image files containing question diagrams')
        parser.add_argument('--solution', '-s', help='Solution .md file for reference')
        parser.add_argument('--stream', action='store_true', help='Stream the response (default: False)')
        parser.add_argument('--log-level', '-l', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                           default='INFO', help='Set logging level (default: INFO)')
        
        args = parser.parse_args()
        
        # Set up logging
        setup_logging(args.log_level)
        logger.info("Starting marking scheme generation process")
        
        # Process input file with optional images and solution
        print(f"Processing input file: {args.input_file}")
        print(f"Using metadata file: {args.metadata_file}")
        logger.info(f"Processing input file: {args.input_file}")
        logger.info(f"Using metadata file: {args.metadata_file}")
        
        if args.images:
            print(f"Using images: {', '.join(args.images)}")
            logger.info(f"Using images: {', '.join(args.images)}")
        
        if args.solution:
            print(f"Using solution file: {args.solution}")
            logger.info(f"Using solution file: {args.solution}")
        
        marking_scheme, usage_metadata = process_file_input(
            input_file=args.input_file,
            metadata_file=args.metadata_file,
            output_file=args.output_file,
            image_files=args.images,
            solution_file=args.solution
        )
        
        if marking_scheme:
            if usage_metadata:
                logger.info(f"Token usage: {usage_metadata}")
            print("\n✓ Marking scheme generation completed successfully!")
            logger.info("Marking scheme generation completed successfully")
        else:
            print("\n✗ Marking scheme generation failed!")
            logger.error("Marking scheme generation failed")
            sys.exit(1)
        
    except Exception as e:
        logger.critical(f"Critical error in main: {e}")
        print(f"Error: {e}")
        print("\nUsage: python markingscheme.py input_file.json metadata_file.json [output_file.json] [--images image1.jpg image2.jpg] [--solution solution.md] [--log-level INFO]")
        print("Please check your API key in .env file and network connection.")
        sys.exit(1)


if __name__ == "__main__":
    main() 