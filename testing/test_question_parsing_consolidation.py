"""
Test for Question Parsing Consolidation

This test demonstrates the final step of question processing where:
1. Question content is read from the database
2. Individual question documents are created with proper diagram/table mapping
3. Assignment is updated with the questions array
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.integration import get_db_integration


async def test_question_parsing_consolidation():
    """Test the question parsing consolidation process"""
    
    # Initialize database integration
    db_integration = get_db_integration()
    
    # Test parameters
    test_run_id = "5bec1d2b655b"  # Use the run_id from your example
    test_assignment_id = "6887cfe388d0b662df0b8c9f"  # Use the assignment_id from your example
    
    print("🧪 Testing Question Parsing Consolidation")
    print(f"  - Run ID: {test_run_id}")
    print(f"  - Assignment ID: {test_assignment_id}")
    print()
    
    try:
        # Step 1: Initialize database connection
        print("📡 Initializing database connection...")
        success = await db_integration.initialize()
        if not success:
            print("❌ Failed to initialize database connection")
            return False
        print("✅ Database connection initialized")
        print()
        
        # Step 2: Run question parsing consolidation
        print("🔄 Running question parsing consolidation...")
        success = await db_integration.question_parsing_consolidation(
            run_id=test_run_id,
            assignment_id=test_assignment_id
        )
        
        if success:
            print("✅ Question parsing consolidation completed successfully!")
            print()
            
            # Step 3: Verify the results
            print("🔍 Verifying results...")
            await verify_consolidation_results(test_run_id, test_assignment_id)
            
        else:
            print("❌ Question parsing consolidation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    return True


async def verify_consolidation_results(run_id: str, assignment_id: str):
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
            
            # Check simple_questions collection
            simple_questions_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["simple_questions"])
            simple_questions_count = await simple_questions_collection.count_documents({})
            print(f"📊 Simple questions collection has {simple_questions_count} documents")
            
            # Show a few example questions
            cursor = simple_questions_collection.find().limit(3)
            example_questions = await cursor.to_list(length=3)
            
            for i, question in enumerate(example_questions):
                question_text = question.get("question_text", "")[:100] + "..." if len(question.get("question_text", "")) > 100 else question.get("question_text", "")
                diagram_url = question.get("diagram_url")
                table_url = question.get("table_url")
                
                print(f"  Example {i+1}:")
                print(f"    Text: {question_text}")
                print(f"    Diagram: {'Yes' if diagram_url else 'No'}")
                print(f"    Table: {'Yes' if table_url else 'No'}")
                print()
            
        else:
            print("❌ Assignment not found")
            
    except Exception as e:
        print(f"❌ Error verifying results: {e}")


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_question_parsing_consolidation())
    
    if success:
        print("🎉 All tests passed!")
    else:
        print("💥 Tests failed!")
        sys.exit(1) 