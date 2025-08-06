#!/usr/bin/env python3
"""
Metadata Generation using LLM1 API function for structured output.
This script takes JSON input, combines it with documentation, and outputs structured JSON.
"""

import os
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from .LLM1 import generate_marking_scheme
from google import genai


def load_metadata_documentation(md_filename: str) -> str:
    """
    Load a specific markdown documentation file from the guide folder.
    
    Args:
        md_filename: Name of the markdown file to load
        
    Returns:
        Content of the markdown file
    """
    current_dir = Path(__file__).parent
    guide_dir = current_dir.parent / "guide"
    md_path = guide_dir / md_filename
    
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_filename}")
    
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✓ Loaded {md_filename}")
        return content
    except Exception as e:
        raise Exception(f"Error loading {md_filename}: {e}")


def load_syllabus() -> dict:
    """
    Load the syllabus.json file containing curriculum structure.
    
    Returns:
        Dictionary containing syllabus data
    """
    current_dir = Path(__file__).parent
    syllabus_path = current_dir / "syllabus.json"
    
    if not syllabus_path.exists():
        print("⚠ Warning: syllabus.json not found. Proceeding without syllabus data.")
        return None
    
    try:
        with open(syllabus_path, 'r', encoding='utf-8') as f:
            syllabus_data = json.load(f)
        print(f"✓ Loaded syllabus.json")
        return syllabus_data
    except Exception as e:
        print(f"⚠ Warning: Error loading syllabus.json: {e}")
        return None


def get_json_schema() -> Dict[str, Any]:
    """
    Define the fixed JSON schema for the output.
    
    Returns:
        JSON schema dictionary for structured output
    """
    return {
        "type": "object",
        "properties": {
            "ques_identifier": {
                "type": "string",
                "description": "Unique identifier for the question"
            },
            "assessment_intent": {
                "type": "string",
                "description": "Detailed description of what the question aims to assess"
            },
            "bloom_taxonomy_level": {
                "type": "string",
                "description": "Bloom taxonomy level (Remembering, Understanding, Applying, Analyzing, Evaluating, Creating)"
            },
            "tags": {
                "type": "object",
                "properties": {
                    "chapters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "chapter": {
                                    "type": "string"
                                },
                                "concepts": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "description": "List of chapters related to this question"
                    }
                }
            }
        },
        "required": [
            "ques_identifier", "assessment_intent", "bloom_taxonomy_level", "tags"
        ]
    }


def create_metadata_prompt(json_input: Dict[str, Any], md_content: str, syllabus_data=None) -> str:
    """
    Create a user prompt combining JSON input, markdown content, and syllabus data for metadata generation.
    
    Args:
        json_input: Input JSON data
        md_content: Content from markdown file
        syllabus_data: Optional syllabus data from syllabus.json
        
    Returns:
        Formatted prompt for the LLM
    """
    # Extract question information
    ques_identifier = json_input.get("ques_identifier", "")
    ques_text = json_input.get("ques_text", "")
    marks = json_input.get("marks", "")
    question_type = json_input.get("question_type", "")
    target_class = json_input.get("target_class", "")
    
    # Format syllabus section
    syllabus_section = ""
    if syllabus_data:
        syllabus_section = "## Syllabus Information:\n```json\n"
        syllabus_section += json.dumps(syllabus_data, indent=2)
        syllabus_section += "\n```\n\n"
    
    schema_definition = """{
        "type": "object",
        "properties": {
            "ques_identifier": {
                "type": "string",
                "description": "Unique identifier for the question"
            },
            "assessment_intent": {
                "type": "string",
                "description": "Detailed description of what the question aims to assess"
            },
            "bloom_taxonomy_level": {
                "type": "string",
                "description": "Bloom taxonomy level (Remembering, Understanding, Applying, Analyzing, Evaluating, Creating)"
            },
            "tags": {
                "type": "object",
                "properties": {
                    "chapters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "chapter": {
                                    "type": "string"
                                },
                                "concepts": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "description": "List of chapters related to this question"
                    }
                }
            }
        },
        "required": [
            "ques_identifier", "assessment_intent", "bloom_taxonomy_level", "tags"
        ]
    }"""

    prompt = f"""
Generate metadata for the following examination question using the provided Bloom's Taxonomy guide and syllabus as reference.

## Question Information:
- Question ID: {ques_identifier}
- Question Text: {ques_text}
- Question Type: {question_type}
- Grade/Class: {target_class}
- Marks: {marks}

## Bloom's Taxonomy Reference:
{md_content}
## Syllabus Information:
{syllabus_section}
## Task:
Analyze the question and generate structured metadata that includes:

1. Assessment Intent - Remember to think and act like a teacher. Write a detailed description of what the question aims to assess, what are the most crucial parts of solution that should be given higher weightage/importance.

2. Bloom's Taxonomy Level - Identify the cognitive level being tested (Remembering, Understanding, Applying, Analyzing, Evaluating, Creating) according to the bloom_taxonomy_guide.md file. Just give one level. Only single TAG.

3. Tags:
   - Chapters: Identify the relevant chapter(s) from the syllabus that this question relates to. For each chapter, list the specific concepts being tested.
   - Concepts: List only the specific concepts being tested in this question. Each concept should be represented as an object with a "name" property.

Important Guidelines:
- Keep the assessment intent concise but comprehensive (1-2 sentences).
- Only include chapters and concepts that are directly relevant to solving the question.
- If a concept is not found in the syllabus but is clearly needed to solve the question, include it.
- Do not include too many concepts - focus only on the main concepts required to solve the question.
- Do NOT create new chapter names - only use chapters that exist in the syllabus.
- If a concept doesn't exist in the syllabus, you can add it under the appropriate existing chapter.

Generate the output as a JSON object with the following schema
{schema_definition}
"""
    return prompt


def generate_metadata(
    json_input: Dict[str, Any],
    md_filename: str = "bloom_taxonomy_guide.md",
    stream: bool = False,
    use_syllabus: bool = True,
    image_paths: Optional[List[str]] = None
) -> (Optional[Dict[str, Any]], Optional[Dict[str, Any]]):
    """
    Generate metadata from JSON input and markdown documentation.
    
    Args:
        json_input: Input JSON data
        md_filename: Name of markdown file to load
        stream: Whether to stream the response (should be False for JSON output)
        use_syllabus: Whether to include syllabus.json data in the prompt
        image_paths: Optional list of paths to image files containing question diagrams
        
    Returns:
        A tuple containing the generated metadata and usage metadata, or (None, None) on failure.
    """
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
    
    # Load markdown documentation
    print(f"Loading documentation from {md_filename}...")
    md_content = load_metadata_documentation(md_filename)
    print(f"✓ Documentation loaded ({len(md_content)} characters)")
    
    # Load syllabus data if requested
    syllabus_data = None
    if use_syllabus:
        syllabus_data = load_syllabus()
    
    # Create user prompt
    user_prompt = create_metadata_prompt(json_input, md_content, syllabus_data)
    print(f"✓ User prompt created ({len(user_prompt)} characters)")
    
    # Process image paths if provided
    if image_paths:
        print(f"✓ Using {len(image_paths)} image(s) as additional input")
        for img_path in image_paths:
            if not Path(img_path).exists():
                print(f"⚠ Warning: Image file not found: {img_path}")
    
    # Basic system instruction for metadata generation
    system_instruction = """You are an Expert Educational Metadata Generator specializing in CBSE Grade 10 and 12 STEM subjects. Your role is to analyze examination questions and generate structured metadata that helps categorize and understand the educational intent of each question.

Focus on:
- Accurate assessment of Bloom's Taxonomy level
- Precise identification of chapters and concepts from the syllabus
- Clear articulation of what the question aims to assess
- Minimal and focused concept tagging (only include concepts directly tested)
- Analyze any images/diagrams provided with the question to understand the complete context

Generate JSON output that strictly follows the specified schema without adding any additional fields or markdown text. Just give me the JSON."""
    
    # Configuration variables for JSON output
    model = "gemini-2.5-flash-lite-preview-06-17"
    temperature = 0.2  # Lower temperature for more consistent structured output
    max_output_tokens = 25000
    thinking_budget = 2048
    response_mime_type = "application/json"
    
    # Get JSON schema
    json_schema = get_json_schema()
    
    max_retries = 3
    base_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            # Call LLM1 function with JSON output
            if stream:
                print("Note: Streaming mode not recommended for JSON output. Using non-streaming mode.")
                stream = False
            
            print("Generating metadata...")
            response, usage_metadata = generate_marking_scheme(
                api_key=api_key,
                system_instruction=system_instruction,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                thinking_budget=thinking_budget,
                response_mime_type=response_mime_type,
                response_schema=json_schema,  # Pass the JSON schema to the API
                stream=stream,
                text_input=user_prompt,
                image_paths=image_paths
            )
            
            if response:
                # Clean the response to extract only the JSON object
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    try:
                        # Parse JSON response
                        metadata = json.loads(json_str)
                        print("✓ Metadata generated successfully")
                        return metadata, usage_metadata
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON response: {e}")
                        print("Problematic JSON string:", json_str)
                        # This is a parsing error, not a network error, so we don't retry
                        return None, None
                else:
                    print("Error: No JSON object found in the response.")
                    print("Raw response:", response)
                    # No JSON object, so we don't retry
                    return None, None
            else:
                # This case might indicate a failure that could be retried
                raise Exception("No response from API")

        except Exception as e:
            print(f"Error generating metadata: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print("All retry attempts failed.")
                return None, None


def update_syllabus_with_new_concepts(metadata: Dict[str, Any], syllabus_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Update syllabus data with new concepts from metadata if they don't already exist.
    
    Args:
        metadata: Generated metadata containing tags
        syllabus_data: Original syllabus data
        
    Returns:
        Updated syllabus data with new concepts added
    """
    if not metadata or not syllabus_data:
        return syllabus_data
    
    # Create a deep copy of the syllabus data to avoid modifying the original
    updated_syllabus = json.loads(json.dumps(syllabus_data))
    
    # Extract chapters and concepts from metadata
    try:
        chapters_data = metadata.get("tags", {}).get("chapters", [])
        
        # Process each chapter in metadata
        for chapter_item in chapters_data:
            chapter_name = chapter_item.get("chapter")
            concepts = chapter_item.get("concepts", [])
            
            if not chapter_name or not concepts:
                continue
                
            # Find the chapter in syllabus
            chapter_exists = False
            for syllabus_chapter in updated_syllabus:
                if syllabus_chapter.get("chapter") == chapter_name:
                    chapter_exists = True
                    existing_concepts = syllabus_chapter.get("concepts", [])
                    
                    # Check each concept and add if it doesn't exist
                    for concept in concepts:
                        concept_name = concept.get("name")
                        if concept_name and concept_name not in existing_concepts:
                            print(f"✓ Adding new concept '{concept_name}' to chapter '{chapter_name}'")
                            existing_concepts.append(concept_name)
                    
                    # Update concepts in the syllabus chapter
                    syllabus_chapter["concepts"] = existing_concepts
                    break
            
            # We don't add new chapters as per requirements
            if not chapter_exists:
                print(f"⚠ Warning: Chapter '{chapter_name}' not found in syllabus. Not adding new chapter as per requirements.")
    
    except Exception as e:
        print(f"Error updating syllabus: {e}")
    
    return updated_syllabus


def save_updated_syllabus(syllabus_data: List[Dict[str, Any]], output_file: str = "syllabus.json") -> None:
    """
    Save updated syllabus data to a file.
    
    Args:
        syllabus_data: Syllabus data to save
        output_file: Output file name (default: syllabus.json)
    """
    try:
        current_dir = Path(__file__).parent
        syllabus_path = current_dir / output_file
        
        with open(syllabus_path, 'w', encoding='utf-8') as f:
            json.dump(syllabus_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Updated syllabus saved to {output_file}")
    except Exception as e:
        print(f"Error saving syllabus: {e}")
        raise


def save_metadata(metadata: Dict[str, Any], output_filename: str) -> None:
    """
    Save metadata to a JSON file.
    
    Args:
        metadata: Metadata dictionary to save
        output_filename: Output file name
    """
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"✓ Metadata saved to {output_filename}")
    except Exception as e:
        print(f"Error saving metadata: {e}")
        raise


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


def process_file_input(input_file: str, output_file: str = None, image_files: List[str] = None, update_syllabus: bool = False):
    """
    Process a JSON input file and generate metadata.
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file (optional)
        image_files: List of paths to image files containing question diagrams (optional)
        update_syllabus: Whether to update the syllabus with new concepts
    """
    try:
        # Load input data
        input_data = load_json_input(input_file)
        
        # Load syllabus data for potential updates
        syllabus_data = load_syllabus() if update_syllabus else None
        
        # Generate metadata
        metadata, usage_metadata = generate_metadata(
            json_input=input_data,
            md_filename="bloom_taxonomy_guide.md",
            stream=False,
            use_syllabus=True,
            image_paths=image_files
        )
        
        if metadata:
            print("\n=== Generated Metadata ===")
            print(json.dumps(metadata, indent=2))
            
            # Save to file if specified
            if output_file:
                save_metadata(metadata, output_file)
            else:
                # Default output filename based on input filename
                base_name = Path(input_file).stem
                default_output = f"{base_name}_metadata.json"
                save_metadata(metadata, default_output)
            
            # Update syllabus if requested
            if update_syllabus and syllabus_data:
                updated_syllabus = update_syllabus_with_new_concepts(metadata, syllabus_data)
                if updated_syllabus != syllabus_data:
                    save_updated_syllabus(updated_syllabus)
                    print("✓ Syllabus updated with new concepts")
                else:
                    print("ℹ No new concepts to add to syllabus")
                
        return metadata, usage_metadata
    
    except Exception as e:
        print(f"Error processing file input: {e}")
        return None, None


def main():
    """Main function to process input files."""
    import sys
    import argparse
    
    print("Metadata Generation Tool")
    print("=" * 60)
    
    try:
        # Set up argument parser
        parser = argparse.ArgumentParser(description='Generate metadata for educational questions')
        parser.add_argument('input_file', help='Input JSON file containing question data')
        parser.add_argument('output_file', nargs='?', help='Output JSON file for metadata')
        parser.add_argument('--images', '-i', nargs='+', help='Image files containing question diagrams')
        parser.add_argument('--update-syllabus', '-u', action='store_true', help='Update syllabus.json with new concepts')
        
        args = parser.parse_.args()
        
        # Process input file with optional images
        print(f"Processing input file: {args.input_file}")
        process_file_input(args.input_file, args.output_file, args.images, args.update_syllabus)
        
    except Exception as e:
        print(f"Error: {e}")
        print("Usage: python metadata_gen.py input_file.json [output_file.json] [--images image1.jpg image2.jpg] [--update-syllabus]")
        print("Please check your API key in .env file and network connection.")


if __name__ == "__main__":
    main()
