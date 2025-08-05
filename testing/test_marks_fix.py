"""
Test Marks Fix

This script tests that the consolidation now uses marks from the marks mapping instead of defaults.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.integration import get_db_integration


async def test_marks_fix():
    """Test that marks are used from marks mapping"""
    
    # Parameters for the assignment with marks mapping
    run_id = "7f52fe5c83bd"
    assignment_id = "6887e5a38c080a1c05a16877"  # This might need to be updated
    
    print("🧪 Testing Marks Fix")
    print(f"  - Run ID: {run_id}")
    print(f"  - Assignment ID: {assignment_id}")
    
    # Initialize database
    print("\n📡 Initializing database connection...")
    db_integration = get_db_integration()
    success = await db_integration.initialize()
    if not success:
        print("❌ Database initialization failed")
        return False
    
    print("✅ Database connection initialized")
    
    # First, let's check the marks mapping
    print("\n📊 Checking marks mapping...")
    marks_mapping = await db_integration._get_marks_mapping_data(run_id)
    if marks_mapping:
        print(f"✅ Marks mapping found: {len(marks_mapping)} entries")
        
        # Show a few examples
        print("\nSample marks mapping entries:")
        for i, (key, value) in enumerate(list(marks_mapping.items())[:5]):
            print(f"  {key}: {value}")
        
        # Check internal choice questions
        internal_choice_count = sum(1 for v in marks_mapping.values() if v.get('question_type') == 'Internal Choice Subjective')
        print(f"\nInternal choice questions: {internal_choice_count}")
        
        for key, value in marks_mapping.items():
            if value.get('question_type') == 'Internal Choice Subjective':
                print(f"  {key}: {value}")
                break  # Show just the first one
    else:
        print("❌ Marks mapping not found")
        return False
    
    # Test the consolidation
    print("\n🔄 Testing consolidation with marks mapping...")
    success = await db_integration.question_parsing_consolidation(run_id, assignment_id)
    
    if success:
        print("✅ Consolidation test successful!")
        
        # Verify the results
        print("\n🔍 Verifying marks in questions...")
        await verify_marks_in_questions(run_id, assignment_id, marks_mapping)
        
        return True
    else:
        print("❌ Consolidation test failed!")
        return False


async def verify_marks_in_questions(run_id: str, assignment_id: str, marks_mapping: dict):
    """Verify that questions have the correct marks from marks mapping"""
    
    from database.connection import pipeline_db
    from database.schema import COLLECTION_NAMES
    
    # Get the assignment
    assignments_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES['assignments'])
    assignment = await assignments_collection.find_one({'_id': assignment_id})
    
    if assignment and assignment.get('questions'):
        print(f"✅ Assignment has {len(assignment['questions'])} questions")
        
        # Check a few questions for correct marks
        questions_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES['questions'])
        
        for i, question_mapping in enumerate(assignment['questions'][:10]):  # Check first 10 questions
            question_identifier = question_mapping['question_identifier']
            expected_marks = marks_mapping.get(f'question-{question_identifier}', {}).get('marks', 'Unknown')
            
            if isinstance(question_mapping['question_id'], list):
                # Internal choice question
                print(f"\nQuestion {question_identifier} (Internal Choice):")
                print(f"  Expected marks: {expected_marks}")
                
                for j, question_id in enumerate(question_mapping['question_id']):
                    question = await questions_collection.find_one({'_id': question_id})
                    if question:
                        actual_marks = question.get('question_marks', 'Unknown')
                        expected_sub_marks = expected_marks[j] if isinstance(expected_marks, list) and j < len(expected_marks) else 'Unknown'
                        print(f"    Sub-question {j+1}: expected='{expected_sub_marks}', actual='{actual_marks}'")
            else:
                # Single question
                question = await questions_collection.find_one({'_id': question_mapping['question_id']})
                if question:
                    actual_marks = question.get('question_marks', 'Unknown')
                    print(f"Question {question_identifier}: expected='{expected_marks}', actual='{actual_marks}'")
    else:
        print("❌ Assignment has no questions array")


if __name__ == "__main__":
    success = asyncio.run(test_marks_fix())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1) 