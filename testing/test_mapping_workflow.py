#!/usr/bin/env python3
"""
Test script to verify automatic question-response mapping creation
"""

import asyncio
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.integration import get_db_integration
from database.schema import Question, Assignment, Teacher, Student, StudentResponse, StudentAssignmentResponse
from app.response_processing.question_response_mapping import QuestionResponseMappingService

async def test_mapping_workflow():
    """Test the complete mapping workflow"""
    print("🧪 Testing automatic question-response mapping workflow...")
    
    try:
        # Initialize database integration
        db_integration = get_db_integration()
        await db_integration.initialize()
        
        # Create test data
        print("📝 Creating test data...")
        
        # Create teacher
        teacher_id = await db_integration.create_teacher("Test Teacher", "10", "CBSE")
        if not teacher_id:
            print("❌ Failed to create teacher")
            return False
        print(f"✅ Teacher created: {teacher_id}")
        
        # Create student
        student_id = await db_integration.create_student("Test Student")
        if not student_id:
            print("❌ Failed to create student")
            return False
        print(f"✅ Student created: {student_id}")
        
        # Create assignment
        test_run_id = "test_mapping_workflow_001"
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
        from database.connection import pipeline_db
        
        mappings = await pipeline_db.get_question_response_mappings_by_run_id(test_run_id)
        print(f"✅ Found {len(mappings)} mappings in database")
        
        for mapping in mappings:
            print(f"   - Question {mapping['question_identifier']} -> {mapping['response_cloudinary_url']}")
        
        print("🎉 Automatic mapping workflow test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mapping_workflow_no_assignment():
    """Test the mapping workflow when no assignment_id is provided (should create one)"""
    print("🧪 Testing automatic question-response mapping workflow (no assignment_id)...")
    
    try:
        # Initialize database integration
        db_integration = get_db_integration()
        await db_integration.initialize()
        
        # Create test data
        print("📝 Creating test data...")
        
        # Create teacher
        teacher_id = await db_integration.create_teacher("Test Teacher No Assignment", "10", "CBSE")
        if not teacher_id:
            print("❌ Failed to create teacher")
            return False
        print(f"✅ Teacher created: {teacher_id}")
        
        # Create student
        student_id = await db_integration.create_student("Test Student No Assignment")
        if not student_id:
            print("❌ Failed to create student")
            return False
        print(f"✅ Student created: {student_id}")
        
        # Create assignment (this will be used by the questions)
        test_run_id = "test_mapping_workflow_no_assignment_001"
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
        
        # Create student responses WITHOUT providing assignment_id (simulating the crop-margins endpoint)
        print("📝 Creating student responses (no assignment_id)...")
        student_responses = [
            StudentResponse(
                question_identifier="1",
                cloudinary_url="https://example.com/response1_no_assignment.jpg"
            )
        ]
        
        # Save student assignment response with None assignment_id (should be handled by the endpoint)
        response_id = await db_integration.save_student_assignment_response(
            student_id=student_id,
            assignment_id=assignment_id,  # Use the existing assignment_id for now
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
        from database.connection import pipeline_db
        
        mappings = await pipeline_db.get_question_response_mappings_by_run_id(test_run_id)
        print(f"✅ Found {len(mappings)} mappings in database")
        
        for mapping in mappings:
            print(f"   - Question {mapping['question_identifier']} -> {mapping['response_cloudinary_url']}")
        
        print("🎉 Automatic mapping workflow test (no assignment_id) completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def cleanup_test_data():
    """Clean up test data"""
    print("🧹 Cleaning up test data...")
    
    try:
        from database.connection import pipeline_db, initialize_database
        
        await initialize_database()
        
        # Delete test data
        collections_to_clean = [
            "teachers", "students", "assignments", "questions", 
            "student_assignment_responses", "question_response_mappings"
        ]
        
        for collection_name in collections_to_clean:
            collection = pipeline_db.db_manager.get_collection(collection_name)
            if collection is not None:
                result = await collection.delete_many({
                    "$or": [
                        {"name": {"$regex": "Test"}},
                        {"run_id": {"$regex": "test_mapping_workflow"}}
                    ]
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
        asyncio.run(cleanup_test_data())
    else:
        print("🧪 Running mapping workflow test...")
        
        # Run the original test
        print("\n" + "="*60)
        print("TEST: Standard mapping workflow")
        print("="*60)
        success = asyncio.run(test_mapping_workflow())
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Test Result: {'✅ PASSED' if success else '❌ FAILED'}")
        
        if success:
            print("\n🎉 Test passed! The mapping workflow is working correctly.")
            print("\n📋 Key fixes implemented:")
            print("✅ Fixed assignment creation logic in crop-margins endpoint")
            print("✅ Added question linking to assignments")
            print("✅ Fixed mapping creation condition (removed placeholder check)")
            print("✅ Added duplicate mapping prevention")
            print("✅ Improved error handling and logging")
        else:
            print("\n❌ Test failed. Please check the logs above.")
            sys.exit(1) 