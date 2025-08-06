#!/usr/bin/env python3
"""
New Full Paper Marking Scheme Generation Pipeline

This script orchestrates the marking scheme generation from a full paper JSON file.
It processes each question in the paper and generates the complete set of outputs,
including metadata, solution, and the final marking scheme.

Usage:
    python full_paper_pipeline.py <path_to_paper.json> --output-dir <results_folder>
"""

import os
import json
import logging
import tempfile
from pathlib import Path
import argparse
import sys
from datetime import datetime

import shutil
import time
from typing import Dict, List, Optional, Any
import requests

# Import the pipeline components
import metadata_gen
import soln_gen
import markingscheme

def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Set up logging configuration for the pipeline.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def create_output_directory(base_dir: str, question_id: str, paper_name: Optional[str] = None) -> Path:
    """
    Create organized output directory structure.
    
    Args:
        base_dir: Base directory for outputs
        question_id: Question identifier for naming
        paper_name: Optional name of the question paper. If provided, a nested
                    directory structure will be created.
        
    Returns:
        Path to the created output directory
    """
    # Ensure the base directory is inside Gemini_test/results
    base_dir = Path("Gemini_test") / "results"
    
    if paper_name:
        output_dir = base_dir / paper_name / f"{question_id}"
    else:
        output_dir = base_dir / f"{question_id}"

    # Create directory structure
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metadata").mkdir(exist_ok=True)
    (output_dir / "solution").mkdir(exist_ok=True)
    (output_dir / "marking_scheme").mkdir(exist_ok=True)
    (output_dir / "logs").mkdir(exist_ok=True)
    (output_dir / "source").mkdir(exist_ok=True)
    
    logging.info(f"Created output directory: {output_dir}")
    return output_dir

def run_metadata_generation(
    question_file: str,
    image_paths: Optional[List[str]] = None,
    output_dir: Path = None
) -> Optional[str]:
    """
    Run metadata generation step.
    
    Args:
        question_file: Path to question JSON file
        image_paths: Optional list of image file paths
        output_dir: Output directory for metadata file
        
    Returns:
        Path to generated metadata file or None if failed
    """
    try:
        logging.info("Starting metadata generation...")
        
        # Load question data to get identifier
        with open(question_file, 'r', encoding='utf-8') as f:
            question_data = json.load(f)
        
        question_id = question_data.get("ques_identifier", "unknown")
        
        # Set up output file path
        if output_dir:
            metadata_file = output_dir / "metadata" / f"{question_id}_metadata.json"
        else:
            metadata_file = Path(f"{question_id}_metadata.json")
        
        # Generate metadata using metadata_gen.py
        metadata, usage_metadata = metadata_gen.generate_metadata(
            json_input=question_data,
            md_filename="bloom_taxonomy_guide.md",
            stream=False,
            use_syllabus=True,
            image_paths=image_paths
        )
        
        if metadata:
            # Save metadata to file
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Metadata generated successfully: {metadata_file}")
            return str(metadata_file), usage_metadata
        else:
            logging.error("Metadata generation failed")
            return None, None
            
    except Exception as e:
        logging.error(f"Error in metadata generation: {e}")
        return None, None

def run_solution_generation(
    question_file: str,
    metadata_file: str,
    image_paths: Optional[List[str]] = None,
    output_dir: Path = None
) -> Optional[str]:
    """
    Run solution generation step.
    
    Args:
        question_file: Path to question JSON file
        metadata_file: Path to metadata JSON file
        image_paths: Optional list of image file paths
        output_dir: Output directory for solution file
        
    Returns:
        Path to generated solution .md file or None if failed
    """
    try:
        logging.info("Starting solution generation...")
        
        # Load question data to get identifier
        with open(question_file, 'r', encoding='utf-8') as f:
            question_data = json.load(f)
        
        # Load metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        question_id = question_data.get("ques_identifier", "unknown")
        
        # Set up output file path
        if output_dir:
            solution_file = output_dir / "solution" / f"{question_id}_solution.md"
        else:
            solution_file = Path(f"{question_id}_solution.md")
        
        # Generate solution using soln_gen.py
        solution, usage_metadata = soln_gen.generate_solution(
            json_input=question_data,
            metadata=metadata,
            stream=False,
            image_paths=image_paths
        )
        
        if solution:
            # Save solution as markdown file
            with open(solution_file, 'w', encoding='utf-8') as f:
                f.write(f"# Solution for {question_id}\n\n")
                f.write(f"**Question:** {question_data.get('ques_text', 'N/A')}\n\n")
                f.write(f"**Question Type:** {question_data.get('question_type', 'N/A')}\n\n")
                f.write("---\n\n")
                f.write(solution)
            
            logging.info(f"Solution generated successfully: {solution_file}")
            return str(solution_file), usage_metadata
        else:
            logging.error("Solution generation failed")
            return None, None
            
    except Exception as e:
        logging.error(f"Error in solution generation: {e}")
        return None, None

def run_marking_scheme_generation(
    question_file: str,
    metadata_file: str,
    solution_file: str,
    image_paths: Optional[List[str]] = None,
    output_dir: Path = None
) -> Optional[Dict[str, Any]]:
    """
    Run marking scheme generation step with solution and CIE glossary.
    
    Args:
        question_file: Path to question JSON file
        metadata_file: Path to metadata JSON file
        solution_file: Path to solution .md file
        image_paths: Optional list of image file paths
        output_dir: Output directory for marking scheme file
        
    Returns:
        A dictionary containing the generated marking scheme, or None if failed.
    """
    try:
        logging.info("Starting marking scheme generation...")
        
        # Load question data
        with open(question_file, 'r', encoding='utf-8') as f:
            question_data = json.load(f)
        
        # Load metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        question_id = question_data.get("ques_identifier", "unknown")
        
        # Set up output file path
        if output_dir:
            marking_scheme_file = output_dir / "marking_scheme" / f"{question_id}_marking_scheme.json"
        else:
            marking_scheme_file = Path(f"{question_id}_marking_scheme.json")
        
        # Generate marking scheme using markingscheme.py with solution file path
        marking_scheme, usage_metadata = markingscheme.generate_marking_scheme_text(
            json_input=question_data,
            metadata=metadata,
            stream=False,
            image_paths=image_paths,
            solution_file_path=solution_file
        )
        
        if marking_scheme:
            # Save marking scheme as json file
            with open(marking_scheme_file, 'w', encoding='utf-8') as f:
                json.dump(marking_scheme, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Marking scheme generated successfully: {marking_scheme_file}")
            return marking_scheme, usage_metadata
        else:
            logging.error("Marking scheme generation failed")
            return None, None
            
    except Exception as e:
        logging.error(f"Error in marking scheme generation: {e}")
        return None, None

def copy_source_files(
    original_question_file: str,
    image_paths: Optional[List[str]],
    output_dir: Path,
    configs: List[Dict[str, Any]],
    is_internal_choice: bool,
    total_marks: Optional[float] = None
) -> None:
    """
    Copies source files to the output directory.
    - For internal choice, it copies the original file and the two processed files (primary/secondary).
    - For other types, it copies the original and one processed file.
    """
    try:
        source_dir = output_dir / "source"
        source_dir.mkdir(exist_ok=True)

        # 1. Copy original, unmodified question file
        original_dest_path = source_dir / "source.json"
        if not original_dest_path.exists():
            shutil.copy(original_question_file, original_dest_path)
            logging.debug(f"Copied original source file to: {original_dest_path}")

        # 2. Copy processed question JSON files from configs
        for config in configs:
            temp_path = config['question_file']
            with open(temp_path, 'r', encoding='utf-8') as f:
                question_data = json.load(f)

            # For non-internal choice, we add the aggregated total marks to the single processed file.
            # For internal choice, we add the total_marks to each of the processed files.
            if total_marks is not None:
                question_data['total_marks'] = float(total_marks)

            processed_filename = f"{question_data.get('ques_identifier')}.json"
            processed_dest_path = source_dir / processed_filename
            with open(processed_dest_path, 'w', encoding='utf-8') as f:
                json.dump(question_data, f, indent=2, ensure_ascii=False)
            logging.debug(f"Saved processed source file to: {processed_dest_path}")

        # 3. Copy image files
        if image_paths:
            for image_path in image_paths:
                dest_image_path = source_dir / Path(image_path).name
                if not dest_image_path.exists() and os.path.exists(image_path):
                    shutil.copy2(image_path, dest_image_path)
                    logging.debug(f"Copied image file to: {source_dir}")

    except Exception as e:
        logging.warning(f"Could not copy or update source files: {e}")

def create_summary_report(results: Dict[str, Any], output_dir: Path) -> None:
    """
    Create a summary report of the pipeline execution.
    
    Args:
        results: Dictionary containing pipeline results
        output_dir: Output directory
    """
    try:
        summary_file = output_dir / "pipeline_summary.md"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# Pipeline Execution Summary\n\n")
            f.write(f"**Execution Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Question ID:** {results.get('question_id', 'N/A')}\n\n")
            f.write(f"**Total Processing Time:** {results.get('total_time', 'N/A'):.2f} seconds\n\n")
            
            f.write("## Pipeline Steps\n\n")
            f.write("| Step | Status | Output File | Time (s) |\n")
            f.write("|------|--------|-------------|----------|\n")
            
            steps = results.get('steps', {})
            for step_name, step_info in steps.items():
                status = "✅ Success" if step_info.get('success') else "❌ Failed"
                output_file = step_info.get('output_file', 'N/A')
                step_time = step_info.get('time', 'N/A')
                f.write(f"| {step_name} | {status} | {output_file} | {step_time} |\n")
            
            f.write("\n## Generated Files\n\n")
            if results.get('metadata_file'):
                f.write(f"- **Metadata:** `{results['metadata_file']}`\n")
            if results.get('solution_file'):
                f.write(f"- **Solution:** `{results['solution_file']}`\n")
            if results.get('marking_scheme_file'):
                f.write(f"- **Marking Scheme:** `{results['marking_scheme_file']}`\n")

            if results.get('total_token_counts'):
                f.write("\n## Token Usage\n\n")
                f.write(f"- **Prompt Tokens:** {results['total_token_counts']['prompt']}\n")
                f.write(f"- **Thoughts Tokens:** {results['total_token_counts']['thoughts']}\n")
                f.write(f"- **Output Tokens:** {results['total_token_counts']['output']}\n")
            
            if results.get('errors'):
                f.write("\n## Errors\n\n")
                for error in results['errors']:
                    f.write(f"- {error}\n")
        
        logging.info(f"Summary report created: {summary_file}")
        
    except Exception as e:
        logging.error(f"Could not create summary report: {e}")

def preprocess_input(new_format_json_path: str, temp_dir: str, target_class: Optional[str]) -> Dict[str, Any]:
    
    with open(new_format_json_path, 'r') as f:
        data = json.load(f)

    image_files = []
    for url_key in ['primary_diagram_url', 'secondary_diagram_url']:
        if data.get(url_key):
            try:
                response = requests.get(data[url_key], stream=True, timeout=60)
                response.raise_for_status()
                
                img_path = os.path.join(temp_dir, os.path.basename(data[url_key]))
                with open(img_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                image_files.append(img_path)
            except requests.exceptions.RequestException as e:
                logging.warning(f"Could not download image from {data[url_key]}: {e}")

    question_type_mapping = {
        "MCQ": "MCQ",
        "Assertion Reasoning": "Assertion-Reason",
        "Internal Choice Subjective": "Internal Choice",
        "Normal Subjective": "Subjective",
        "Case Study": "Case-Study"
    }
    question_type = question_type_mapping.get(data.get("question_type"), "Subjective")

    # This will store the path to the final, processed JSON that should be saved in 'source'
    temp_processed_json_path = os.path.join(temp_dir, "tmp.json")

    if question_type == "Internal Choice":
        # For internal choice, we create two separate configs for processing
        # but the final source JSON will be a single file combining results.
        # This part of the logic might need further refinement based on how you want to store internal choice results.
        # For now, we'll just process them separately.
        configs = []
        original_identifier = data.get("question_identifier")
        
        primary_config = {
            "_id": data.get("_id"), "run_id": data.get("run_id"),
            "ques_identifier": f"{original_identifier}_primary",
            "ques_text": data.get("primary_question"),
            "marks_analysis": data.get("primary_marks"), "question_type": "Subjective",
        }
        if target_class:
            primary_config["target_class"] = target_class
        primary_file_path = os.path.join(temp_dir, f"{primary_config['ques_identifier']}.json")
        with open(primary_file_path, 'w') as f: json.dump(primary_config, f)
        configs.append({'question_file': primary_file_path, 'image_paths': image_files, 'question_type': "Subjective"})

        secondary_config = {
            "_id": data.get("_id"), "run_id": data.get("run_id"),
            "ques_identifier": f"{original_identifier}_secondary",
            "ques_text": data.get("secondary_question"),
            "marks_analysis": data.get("secondary_marks"), "question_type": "Subjective",
        }
        if target_class:
            secondary_config["target_class"] = target_class
        secondary_file_path = os.path.join(temp_dir, f"{secondary_config['ques_identifier']}.json")
        with open(secondary_file_path, 'w') as f: json.dump(secondary_config, f)
        configs.append({'question_file': secondary_file_path, 'image_paths': image_files, 'question_type': "Subjective"})
        
        # Create the base structure for the final combined source file
        final_source_data = data.copy()
        with open(temp_processed_json_path, 'w') as f:
            json.dump(final_source_data, f)

        return {'configs': configs, 'temp_processed_json_path': temp_processed_json_path, 'is_internal_choice': True}

    else:
        # For all other types, create a single config and the final source JSON is based on this.
        config = {
            "_id": data.get("_id"), "run_id": data.get("run_id"),
            "ques_identifier": data.get("question_identifier"),
            "ques_text": data.get("primary_question"),
            "marks_analysis": data.get("primary_marks"), "question_type": question_type,
        }
        if target_class:
            config["target_class"] = target_class
        # This file is used for processing by metadata, solution, etc.
        processing_file_path = os.path.join(temp_dir, f"{config['ques_identifier']}.json")
        with open(processing_file_path, 'w') as f:
            json.dump(config, f)
        
        # This file will be the basis for the final <id>.json in the source folder
        with open(temp_processed_json_path, 'w') as f:
            json.dump(data, f)

        return {
            'configs': [{
                'question_file': processing_file_path,
                'image_paths': image_files,
                'question_type': question_type
            }],
            'temp_processed_json_path': temp_processed_json_path,
            'is_internal_choice': False
        }

def run_complete_pipeline(
    question_file: str,
    output_dir: str,
    update_syllabus: bool,
    target_class: Optional[str] = None,
) -> Dict[str, Any]:
    
    start_time = time.time()
    results = {'success': False, 'steps': {}, 'errors': [], 'temp_files': []}
    total_token_counts = {'prompt': 0, 'thoughts': 0, 'output': 0}
    
    try:
        output_path = Path(output_dir)
        results['output_dir'] = str(output_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            preprocess_result = preprocess_input(question_file, temp_dir, target_class)
            configs = preprocess_result['configs']
            is_internal_choice = preprocess_result.get('is_internal_choice', False)
            
            # Keep track of total marks for all parts (especially for internal choice)
            total_marks_agg = 0.0
            all_image_paths = []

            for config in configs:
                question_file_old_format = config['question_file']
                image_paths = config['image_paths']
                question_type = config['question_type']
                all_image_paths.extend(image_paths)

                with open(question_file_old_format, 'r', encoding='utf-8') as f:
                    question_data = json.load(f)
                
                question_id = question_data.get("ques_identifier", "unknown")
                results['question_id'] = question_id
                
                step_start = time.time()
                metadata_file, usage_metadata = run_metadata_generation(
                    question_file=question_file_old_format, image_paths=image_paths, output_dir=output_path
                )
                if usage_metadata:
                    total_token_counts['prompt'] += usage_metadata.prompt_token_count
                    total_token_counts['thoughts'] += usage_metadata.thoughts_token_count
                    total_token_counts['output'] += usage_metadata.candidates_token_count

                step_time = time.time() - step_start
                results['steps'][f'metadata_{question_id}'] = {'success': metadata_file is not None, 'output_file': metadata_file, 'time': f"{step_time:.2f}"}
                
                if not metadata_file:
                    results['errors'].append(f"Metadata generation failed for {question_id}")
                    continue
                results['metadata_file'] = metadata_file
                
                solution_file = None
                if question_type not in ["MCQ", "Assertion-Reason"]:
                    step_start = time.time()
                    solution_file, usage_metadata = run_solution_generation(
                        question_file=question_file_old_format, metadata_file=metadata_file,
                        image_paths=image_paths, output_dir=output_path
                    )
                    if usage_metadata:
                        total_token_counts['prompt'] += usage_metadata.prompt_token_count
                        total_token_counts['thoughts'] += usage_metadata.thoughts_token_count
                        total_token_counts['output'] += usage_metadata.candidates_token_count

                    step_time = time.time() - step_start
                    results['steps'][f'solution_{question_id}'] = {'success': solution_file is not None, 'output_file': solution_file, 'time': f"{step_time:.2f}"}
                    
                    if not solution_file:
                        results['errors'].append(f"Solution generation failed for {question_id}")
                        continue
                    results['solution_file'] = solution_file
                
                step_start = time.time()
                marking_scheme_json, usage_metadata = run_marking_scheme_generation(
                    question_file=question_file_old_format, metadata_file=metadata_file,
                    solution_file=solution_file, image_paths=image_paths, output_dir=output_path
                )
                if usage_metadata:
                    total_token_counts['prompt'] += usage_metadata.prompt_token_count
                    total_token_counts['thoughts'] += usage_metadata.thoughts_token_count
                    total_token_counts['output'] += usage_metadata.candidates_token_count

                step_time = time.time() - step_start
                
                marking_scheme_file_path = output_path / "marking_scheme" / f"{question_id}_marking_scheme.json"
                results['steps'][f'marking_scheme_{question_id}'] = {'success': marking_scheme_json is not None, 'output_file': str(marking_scheme_file_path), 'time': f"{step_time:.2f}"}
                
                if not marking_scheme_json:
                    results['errors'].append(f"Marking scheme generation failed for {question_id}")
                    continue
                results['marking_scheme_file'] = str(marking_scheme_file_path)

                if marking_scheme_json and 'total_marks' in marking_scheme_json:
                    total_marks_agg = float(marking_scheme_json['total_marks'])
                    # if not is_internal_choice:
                    #     total_marks_agg += float(marking_scheme_json['total_marks'])
                    # elif total_marks_agg == 0.0:  # For internal choice, only assign once
                    #     total_marks_agg = float(marking_scheme_json['total_marks'])

            # After processing all parts, copy the source files correctly
            copy_source_files(
                original_question_file=question_file,
                image_paths=list(set(all_image_paths)),
                output_dir=output_path,
                configs=configs,
                is_internal_choice=is_internal_choice,
                total_marks=total_marks_agg if total_marks_agg > 0 else None
            )

        total_time = time.time() - start_time
        results['total_time'] = total_time
        results['success'] = not results['errors']
        results['total_token_counts'] = total_token_counts
        
        create_summary_report(results, Path(results['output_dir']))
        
        logging.info(f"Pipeline completed successfully in {total_time:.2f} seconds")
        
    except Exception as e:
        results['errors'].append(f"Pipeline error: {str(e)}")
        logging.error(f"Pipeline failed: {e}", exc_info=True)
    
    finally:
        if results.get('temp_files'):
            cleanup_temp_files(results['temp_files'])
    
    return results

def process_full_paper(
    paper_file: str,
    output_dir: str,
    update_syllabus: bool,
    target_class: Optional[str] = None
) -> None:
    """
    Processes a full question paper JSON file, generating outputs for each question.

    Args:
        paper_file: Path to the full paper JSON file.
        output_dir: The base directory where results will be saved.
        update_syllabus: Flag to indicate whether to update the syllabus.
        target_class: The target class for the questions.
    """
    try:
        with open(paper_file, 'r', encoding='utf-8') as f:
            paper_data = json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: Paper file not found at {paper_file}")
        return
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {paper_file}")
        return

    paper_name = Path(paper_file).stem
    paper_output_dir = Path(output_dir) / paper_name
    paper_output_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"Processing paper: {paper_name}")
    
    paper_total_token_counts = {'prompt': 0, 'thoughts': 0, 'output': 0}

    for i, question_data in enumerate(paper_data):
        question_id = question_data.get("question_identifier") or question_data.get("ques_identifier") or f"q_{i+1}"
        
        logging.info(f"--- Processing Question: {question_id} ---")

        # Create a temporary file for the individual question JSON
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json", dir=paper_output_dir) as temp_f:
            json.dump(question_data, temp_f, indent=2)
            temp_question_file = temp_f.name

        try:
            # Each question gets its own sub-directory in the main results folder
            question_output_dir = create_output_directory(output_dir, question_id, paper_name=paper_name)

            results = run_complete_pipeline(
                question_file=temp_question_file,
                output_dir=str(question_output_dir),
                update_syllabus=update_syllabus,
                target_class=target_class
            )
            
            if results and results.get('total_token_counts'):
                paper_total_token_counts['prompt'] += results['total_token_counts'].get('prompt', 0)
                paper_total_token_counts['thoughts'] += results['total_token_counts'].get('thoughts', 0)
                paper_total_token_counts['output'] += results['total_token_counts'].get('output', 0)

        finally:
            # Clean up the temporary file
            os.remove(temp_question_file)

    logging.info(f"--- Total Token Usage for Paper: {paper_name} ---")
    logging.info(f"Prompt Tokens: {paper_total_token_counts['prompt']}")
    logging.info(f"Thoughts Tokens: {paper_total_token_counts['thoughts']}")
    logging.info(f"Output Tokens: {paper_total_token_counts['output']}")

def main():
    """Main function to run the full paper pipeline."""
    parser = argparse.ArgumentParser(
        description='Run the complete marking scheme generation pipeline for a full paper.'
    )
    parser.add_argument('paper_file', help='Input JSON file for the full question paper')
    parser.add_argument('--output-dir', '-o', default='Gemini_test/results',
                        help='Output directory for all results (default: Gemini_test/results)')
    parser.add_argument('--log-level', '-l',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Set the logging level (default: INFO)')
    parser.add_argument('--no-syllabus-update', action='store_true',
                        help='Disable automatic updates to syllabus.json')
    parser.add_argument('--target-class', default=None,
                        help='The target class for the questions (e.g., 10, 12)')

    args = parser.parse_args()

    if not Path(args.paper_file).exists():
        print(f"Error: Input paper file not found: {args.paper_file}")
        sys.exit(1)

    log_file = f"full_paper_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    setup_logging(args.log_level, log_file)

    logging.info("Starting full paper marking scheme generation pipeline...")
    
    process_full_paper(
        paper_file=args.paper_file,
        output_dir=args.output_dir,
        update_syllabus=not args.no_syllabus_update,
        target_class=args.target_class
    )

    logging.info("Full paper processing complete.")

if __name__ == "__main__":
    main()