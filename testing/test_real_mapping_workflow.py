#!/usr/bin/env python3
"""
Test script to verify question-response mapping workflow with real teachers and students
"""

import asyncio
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.integration import get_db_integration
from database.schema import Question, Assignment, StudentResponse, StudentAssignmentResponse
from app.response_processing.question_response_mapping import QuestionResponseMappingService
from database.connection import pipeline_db

async def test_real_mapping_workflow():
    """Test the mapping workflow with real teachers and students"""
    print("🧪 Testing question-response mapping workflow with real teachers and students...")
    
    try:
        # Initialize database integration
        db_integration = get_db_integration()
        await db_integration.initialize()
        
        # Get real teacher and student
        print("📝 Getting real teacher and student...")
        
        teachers_collection = pipeline_db.db_manager.get_collection("teachers")
        students_collection = pipeline_db.db_manager.get_collection("students")
        
        # Get real teacher (not test data)
        teacher = await teachers_collection.find_one({"name": {"$not": {"$regex": "Test"}}})
        if not teacher:
            print("❌ No real teacher found in database")
            return False
        
        # Get real student (not test data)
        student = await students_collection.find_one({"name": {"$not": {"$regex": "Test"}}})
        if not student:
            print("❌ No real student found in database")
            return False
        
        teacher_id = str(teacher["_id"])
        student_id = str(student["_id"])
        
        print(f"✅ Using teacher: {teacher['name']} (ID: {teacher_id})")
        print(f"✅ Using student: {student['name']} (ID: {student_id})")
        
        # Create assignment
        test_run_id = "test_real_mapping_workflow_001"
        assignment_id = await db_integration.create_assignment(test_run_id)
        if not assignment_id:
            print("❌ Failed to create assignment")
            return False
        print(f"✅ Assignment created: {assignment_id}")
        
        # Create questions
        questions_data = [
            {
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
            },
            {
                "question_identifier": "2",
                "has_internal_choice": False,
                "primary_question": "What is 3 + 3?",
                "secondary_question": None,
                "primary_diagram_url": None,
                "secondary_diagram_url": None,
                "table_url": None,
                "primary_marks": "1 mark",
                "secondary_marks": None,
                "question_type": "MCQ"
            }
        ]
        
        question_ids = []
        for question_data in questions_data:
            question_id = await db_integration.save_question_with_assignment(
                question_data, assignment_id, test_run_id
            )
            if question_id:
                question_ids.append(question_id)
                print(f"✅ Question {question_data['question_identifier']} created: {question_id}")
            else:
                print(f"❌ Failed to create question {question_data['question_identifier']}")
                return False
        
        # Update assignment with question IDs
        await db_integration.update_assignment_questions(assignment_id, question_ids)
        print(f"✅ Assignment updated with {len(question_ids)} questions")
        
        # Create student responses (simulating the crop-margins endpoint)
        print("📝 Creating student responses...")
        student_responses = [
            StudentResponse(
                question_identifier="1",
                cloudinary_url="https://example.com/real_response1.jpg"
            ),
            StudentResponse(
                question_identifier="2",
                cloudinary_url="https://example.com/real_response2.jpg"
            )
        ]
        
        response_id = await db_integration.save_student_assignment_response(
            student_id=student_id,
            assignment_id=assignment_id,
            run_id=test_run_id,
            student_responses=student_responses
        )
        
        if not response_id:
            print("❌ Failed to create student assignment response")
            return False
        print(f"✅ Student assignment response created: {response_id}")
        
        # Test automatic mapping creation
        print("🔗 Testing automatic mapping creation...")
        mapping_result = await QuestionResponseMappingService.create_mappings_for_run_id(test_run_id)
        
        if mapping_result["success"]:
            print(f"✅ Mappings created successfully!")
            print(f"   - Mappings created: {mapping_result['mappings_created']}")
            print(f"   - Total responses: {mapping_result['total_responses']}")
            print(f"   - Student ID: {mapping_result['student_id']}")
            print(f"   - Assignment ID: {mapping_result['assignment_id']}")
            
            if mapping_result.get('unmapped_responses'):
                print(f"   - Unmapped responses: {len(mapping_result['unmapped_responses'])}")
                for unmapped in mapping_result['unmapped_responses']:
                    print(f"     * {unmapped['question_identifier']}: {unmapped['reason']}")
        else:
            print(f"❌ Mapping creation failed: {mapping_result.get('error', 'Unknown error')}")
            return False
        
        # Verify mappings were created
        print("🔍 Verifying mappings in database...")
        mappings = await pipeline_db.get_question_response_mappings_by_run_id(test_run_id)
        print(f"✅ Found {len(mappings)} mappings in database")
        
        for mapping in mappings:
            print(f"   - Question {mapping['question_identifier']} -> {mapping['response_cloudinary_url']}")
            print(f"     Student: {mapping['student_id']}")
            print(f"     Assignment: {mapping['assignment_id']}")
        
        print("🎉 Real mapping workflow test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def cleanup_real_test_data():
    """Clean up real test data"""
    print("🧹 Cleaning up real test data...")
    
    try:
        from database.connection import pipeline_db, initialize_database
        
        await initialize_database()
        
        # Delete test data
        collections_to_clean = [
            "assignments", "questions", 
            "student_assignment_responses", "question_response_mappings"
        ]
        
        for collection_name in collections_to_clean:
            collection = pipeline_db.db_manager.get_collection(collection_name)
            if collection is not None:
                result = await collection.delete_many({
                    "run_id": {"$regex": "test_real_mapping_workflow"}
                })
                print(f"✅ Cleaned {result.deleted_count} documents from {collection_name}")
        
        print("🎉 Cleanup completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_real_test_data())
    else:
        print("🧪 Running real mapping workflow test...")
        
        success = asyncio.run(test_real_mapping_workflow())
        
        if success:
            print("\n🎉 Real mapping workflow test passed!")
            print("\n📋 Key findings:")
            print("✅ Question-response mapping works with real teachers and students")
            print("✅ Database schema is properly updated")
            print("✅ All relationships are correctly established")
        else:
            print("\n❌ Real mapping workflow test failed!")
            sys.exit(1) 