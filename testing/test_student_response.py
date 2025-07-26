#!/usr/bin/env python3
"""
Test script to verify student response processing works with new schema
"""

import asyncio
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.integration import get_db_integration
from database.schema import StudentResponse, StudentAssignmentResponse

async def test_student_response_processing():
    """Test that student response processing works with the new schema"""
    print("🧪 Testing student response processing with new schema...")
    
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
        test_run_id = "test_response_run_123"
        assignment_id = await db_integration.create_assignment(test_run_id)
        if assignment_id:
            print(f"✅ Assignment created with ID: {assignment_id}")
        else:
            print("❌ Failed to create assignment")
            return False
        
        # Test creating student responses
        print("📝 Creating test student responses...")
        student_responses = [
            StudentResponse(
                question_identifier="1",
                cloudinary_url="https://example.com/response1.jpg"
            ),
            StudentResponse(
                question_identifier="2", 
                cloudinary_url="https://example.com/response2.jpg"
            )
        ]
        
        response_id = await db_integration.save_student_assignment_response(
            student_id=student_id,
            assignment_id=assignment_id,
            run_id=test_run_id,
            student_responses=student_responses
        )
        
        if response_id:
            print(f"✅ Student assignment response created with ID: {response_id}")
        else:
            print("❌ Failed to create student assignment response")
            return False
        
        # Test creating question response mappings
        print("🔗 Creating test question response mappings...")
        
        # First create a question
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
        
        # Create mapping
        mapping_id = await db_integration.create_question_response_mapping(
            student_id=student_id,
            assignment_id=assignment_id,
            run_id=test_run_id,
            question_data=question_data,
            response_url="https://example.com/response1.jpg"
        )
        
        if mapping_id:
            print(f"✅ Question response mapping created with ID: {mapping_id}")
        else:
            print("❌ Failed to create question response mapping")
            return False
        
        print("🎉 All student response processing tests passed!")
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
        success = asyncio.run(test_student_response_processing())
        if success:
            print("\n✅ Student response processing test completed successfully!")
        else:
            print("\n❌ Student response processing test failed!")
            sys.exit(1) 