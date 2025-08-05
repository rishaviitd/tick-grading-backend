"""
Test consolidation for a specific assignment
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.integration import get_db_integration


async def test_consolidation_for_paper():
    """Test consolidation for PAPER-5"""
    
    # Initialize database integration
    db_integration = get_db_integration()
    
    # Test parameters for PAPER-5
    test_run_id = "5bec1d2b655b"  # This is the run_id for PAPER-5
    test_assignment_id = "6887d0c9ef19511b87547b3e"  # This is the assignment_id for PAPER-5
    
    print("🧪 Testing Question Parsing Consolidation for PAPER-5")
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
            await verify_specific_assignment(test_assignment_id)
            
        else:
            print("❌ Question parsing consolidation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    return True


async def verify_specific_assignment(assignment_id: str):
    """Verify the results for a specific assignment"""
    
    try:
        from database.connection import pipeline_db, initialize_database
        from database.schema import COLLECTION_NAMES
        
        await initialize_database()
        
        # Get the specific assignment
        assignments_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["assignments"])
        assignment = await assignments_collection.find_one({"_id": assignment_id})
        
        if assignment:
            print(f"✅ Assignment found: {assignment.get('title', 'Unknown')}")
            
            # Check questions array
            questions = assignment.get("questions", [])
            print(f"📝 Questions array has {len(questions)} entries")
            
            if len(questions) > 0:
                for i, question_mapping in enumerate(questions[:5]):  # Show first 5
                    question_identifier = question_mapping.get("question_identifier")
                    question_id = question_mapping.get("question_id")
                    
                    if isinstance(question_id, list):
                        print(f"  - Question {question_identifier}: Internal choice with {len(question_id)} sub-questions")
                    else:
                        print(f"  - Question {question_identifier}: Single question")
                
                if len(questions) > 5:
                    print(f"  ... and {len(questions) - 5} more questions")
            else:
                print("  ⚠️  Questions array is still empty!")
            
            # Check simple_questions collection
            simple_questions_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["simple_questions"])
            simple_questions_count = await simple_questions_collection.count_documents({})
            print(f"📊 Simple questions collection has {simple_questions_count} documents")
            
        else:
            print("❌ Assignment not found")
            
    except Exception as e:
        print(f"❌ Error verifying results: {e}")


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_consolidation_for_paper())
    
    if success:
        print("🎉 Test completed!")
    else:
        print("💥 Test failed!")
        sys.exit(1) 