"""
Test Question Parsing Consolidation Fix

This script tests the consolidation fix with an existing assignment that has visual content.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.integration import get_db_integration


async def test_consolidation_fix():
    """Test the consolidation fix with existing assignment"""
    
    # Parameters for the existing assignment
    run_id = "0843493f250f"
    assignment_id = "6887e5a38c080a1c05a16877"
    
    print("🧪 Testing Question Parsing Consolidation Fix")
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
    
    # Test the consolidation
    print("\n🔄 Testing question parsing consolidation...")
    success = await db_integration.question_parsing_consolidation(run_id, assignment_id)
    
    if success:
        print("✅ Consolidation test successful!")
        
        # Verify the results
        print("\n🔍 Verifying results...")
        await verify_consolidation_results(run_id, assignment_id)
        
        return True
    else:
        print("❌ Consolidation test failed!")
        return False


async def verify_consolidation_results(run_id: str, assignment_id: str):
    """Verify the consolidation results"""
    
    # Get the assignment to check the questions array
    from database.connection import pipeline_db
    from database.schema import COLLECTION_NAMES
    
    assignments_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES['assignments'])
    assignment = await assignments_collection.find_one({'_id': assignment_id})
    
    if assignment and assignment.get('questions'):
        print(f"✅ Assignment has {len(assignment['questions'])} questions")
        
        # Check a few questions for diagram/table URLs
        questions_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES['questions'])
        
        for i, question_mapping in enumerate(assignment['questions'][:5]):  # Check first 5 questions
            question_identifier = question_mapping['question_identifier']
            
            if isinstance(question_mapping['question_id'], list):
                # Internal choice question
                for j, question_id in enumerate(question_mapping['question_id']):
                    question = await questions_collection.find_one({'_id': question_id})
                    if question:
                        print(f"  - Question {question_identifier}{'a' if j == 0 else 'b'}: diagram_url={question.get('diagram_url') is not None}, table_url={question.get('table_url') is not None}")
            else:
                # Single question
                question = await questions_collection.find_one({'_id': question_mapping['question_id']})
                if question:
                    print(f"  - Question {question_identifier}: diagram_url={question.get('diagram_url') is not None}, table_url={question.get('table_url') is not None}")
    else:
        print("❌ Assignment has no questions array")


if __name__ == "__main__":
    success = asyncio.run(test_consolidation_fix())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1) 