"""
Fix Question Parsing Consolidation

This script manually reads the existing files from the failed pipeline run
and runs the consolidation process to fix the empty questions array.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.integration import get_db_integration


async def fix_consolidation():
    """Fix the consolidation for the failed run"""
    
    # Parameters for the failed run
    run_id = "d9506559abb8"
    assignment_id = "6887df9522f1d45a09db70b6"
    
    print("🔧 Fixing Question Parsing Consolidation")
    print(f"  - Run ID: {run_id}")
    print(f"  - Assignment ID: {assignment_id}")
    print()
    
    # Initialize database integration
    db_integration = get_db_integration()
    
    try:
        # Step 1: Initialize database connection
        print("📡 Initializing database connection...")
        success = await db_integration.initialize()
        if not success:
            print("❌ Failed to initialize database connection")
            return False
        print("✅ Database connection initialized")
        print()
        
        # Step 2: Read the existing files and save to database
        print("📖 Reading existing files and saving to database...")
        
        # Read question content
        question_file_path = Path(f"logs/{run_id}/step3_question_extraction/step3_questions.md")
        if question_file_path.exists():
            with open(question_file_path, 'r') as f:
                questions_markdown = f.read()
            
            print(f"  - Read question markdown: {len(questions_markdown)} characters")
            
            # Parse questions from markdown
            questions = db_integration._parse_questions_from_markdown(questions_markdown, {})
            structured_questions = db_integration._create_structured_questions_output(questions)
            
            print(f"  - Parsed {len(questions)} questions")
            
            # Save question content to database
            question_content_id = await db_integration.save_question_content_with_assignment_update(
                run_id=run_id,
                questions_markdown=questions_markdown,
                assignment_id=assignment_id,
                extraction_success=True,
                raw_response="Manually fixed from existing file",
                parsed_questions=structured_questions
            )
            
            if question_content_id:
                print(f"  ✅ Question content saved with ID: {question_content_id}")
            else:
                print("  ❌ Failed to save question content")
                return False
        else:
            print("  ❌ Question file not found")
            return False
        
        # Read marks mapping
        marks_file_path = Path(f"logs/{run_id}/step4_marks_mapping/step4_marks_mapping.json")
        if marks_file_path.exists():
            with open(marks_file_path, 'r') as f:
                marks_mapping = json.load(f)
            
            print(f"  - Read marks mapping: {len(marks_mapping)} entries")
            
            # Save marks content to database
            marks_content_id = await db_integration.save_marks_content_with_assignment_update(
                run_id=run_id,
                marks_mapping=marks_mapping,
                total_questions=len(marks_mapping),
                assignment_id=assignment_id,
                mapping_success=True,
                raw_response="Manually fixed from existing file"
            )
            
            if marks_content_id:
                print(f"  ✅ Marks content saved with ID: {marks_content_id}")
            else:
                print("  ❌ Failed to save marks content")
                return False
        else:
            print("  ❌ Marks mapping file not found")
            return False
        
        print()
        
        # Step 3: Run question parsing consolidation
        print("🔄 Running question parsing consolidation...")
        consolidation_success = await db_integration.question_parsing_consolidation(
            run_id=run_id,
            assignment_id=assignment_id
        )
        
        if consolidation_success:
            print("✅ Question parsing consolidation completed successfully!")
            print()
            
            # Step 4: Verify the results
            print("🔍 Verifying results...")
            await verify_fixed_results(run_id, assignment_id)
            
        else:
            print("❌ Question parsing consolidation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        return False
    
    return True


async def verify_fixed_results(run_id: str, assignment_id: str):
    """Verify that the consolidation process worked correctly"""
    
    db_integration = get_db_integration()
    
    try:
        # Get the updated assignment
        from database.connection import pipeline_db
        from database.schema import COLLECTION_NAMES
        
        assignments_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["assignments"])
        assignment = await assignments_collection.find_one({"_id": assignment_id})
        
        if assignment:
            print(f"✅ Assignment found: {assignment.get('title', 'Unknown')}")
            
            # Check content IDs
            question_content_id = assignment.get("question_content_id")
            marks_content_id = assignment.get("marks_content_id")
            print(f"  - Question content ID: {question_content_id}")
            print(f"  - Marks content ID: {marks_content_id}")
            
            # Check questions array
            questions = assignment.get("questions", [])
            print(f"📝 Questions array has {len(questions)} entries")
            
            for i, question_mapping in enumerate(questions[:5]):  # Show first 5
                question_identifier = question_mapping.get("question_identifier")
                question_id = question_mapping.get("question_id")
                
                if isinstance(question_id, list):
                    print(f"  - Question {question_identifier}: Internal choice with {len(question_id)} sub-questions")
                else:
                    print(f"  - Question {question_identifier}: Single question")
            
            if len(questions) > 5:
                print(f"  ... and {len(questions) - 5} more questions")
            
            # Check questions collection
            questions_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["questions"])
            questions_count = await questions_collection.count_documents({})
            print(f"📊 Questions collection has {questions_count} documents")
            
            # Show a few example questions
            cursor = questions_collection.find().limit(3)
            example_questions = await cursor.to_list(length=3)
            
            print("\n📝 Example Questions:")
            for i, question in enumerate(example_questions):
                question_text = question.get("question_text", "")[:100] + "..." if len(question.get("question_text", "")) > 100 else question.get("question_text", "")
                print(f"  {i+1}. {question_text}")
            
        else:
            print("❌ Assignment not found")
            
    except Exception as e:
        print(f"❌ Error verifying results: {e}")


if __name__ == "__main__":
    success = asyncio.run(fix_consolidation())
    if success:
        print("\n🎉 Consolidation fix completed successfully!")
    else:
        print("\n❌ Consolidation fix failed!")
        sys.exit(1) 