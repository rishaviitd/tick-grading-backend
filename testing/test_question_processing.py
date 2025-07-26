#!/usr/bin/env python3
"""
Test script to verify question processing works with new schema
"""

import asyncio
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.integration import get_db_integration
from database.schema import Question, Assignment, Teacher, Student

async def test_question_processing():
    """Test that question processing works with the new schema"""
    print("🧪 Testing question processing with new schema...")
    
    try:
        # Initialize database integration
        db_integration = get_db_integration()
        await db_integration.initialize()
        
        # Test creating a teacher
        print("📝 Creating test teacher...")
        teacher_id = await db_integration.create_teacher("Test Teacher", "10", "CBSE")
        if teacher_id:
            print(f"✅ Teacher created with ID: {teacher_id}")
        else:
            print("❌ Failed to create teacher")
            return False
        
        # Test creating a student
        print("👤 Creating test student...")
        student_id = await db_integration.create_student("Test Student")
        if student_id:
            print(f"✅ Student created with ID: {student_id}")
        else:
            print("❌ Failed to create student")
            return False
        
        # Test creating an assignment
        print("📚 Creating test assignment...")
        test_run_id = "test_run_123"
        assignment_id = await db_integration.create_assignment(test_run_id)
        if assignment_id:
            print(f"✅ Assignment created with ID: {assignment_id}")
        else:
            print("❌ Failed to create assignment")
            return False
        
        # Test creating a question with assignment
        print("❓ Creating test question...")
        question_data = {
            "question_identifier": "1",
            "has_internal_choice": False,
            "primary_question": "What is 2 + 2?",
            "secondary_question": None,
            "primary_diagram_url": None,
            "secondary_diagram_url": None,
            "table_url": None,
            "primary_marks": "1 mark",
            "secondary_marks": None,
            "question_type": "MCQ"
        }
        
        question_id = await db_integration.save_question_with_assignment(
            question_data, assignment_id, test_run_id
        )
        if question_id:
            print(f"✅ Question created with ID: {question_id}")
        else:
            print("❌ Failed to create question")
            return False
        
        # Test updating assignment with question IDs
        print("🔄 Updating assignment with question IDs...")
        success = await db_integration.update_assignment_questions(assignment_id, [question_id])
        if success:
            print("✅ Assignment updated with question IDs")
        else:
            print("❌ Failed to update assignment")
            return False
        
        print("🎉 All tests passed! Question processing works with new schema.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

async def cleanup_test_data():
    """Clean up test data"""
    print("🧹 Cleaning up test data...")
    # This would typically delete the test records
    # For now, we'll just print a message
    print("✅ Cleanup completed (manual cleanup may be needed)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_data())
    else:
        success = asyncio.run(test_question_processing())
        if success:
            print("\n✅ Question processing test completed successfully!")
        else:
            print("\n❌ Question processing test failed!")
            sys.exit(1) 