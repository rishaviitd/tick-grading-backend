#!/usr/bin/env python3
"""
Test script to verify automatic final consolidated JSON generation
"""

import asyncio
import sys
import os
import json

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.integration import get_db_integration
from database.schema import Question, Assignment, Teacher, Student, StudentResponse, StudentAssignmentResponse

async def test_final_json_generation():
    """Test that final consolidated JSON is automatically generated"""
    print("🧪 Testing automatic final consolidated JSON generation...")
    
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
        test_run_id = "test_final_json_001"
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
        
        # Create mappings
        from app.response_processing.question_response_mapping import QuestionResponseMappingService
        mapping_result = await QuestionResponseMappingService.create_mappings_for_run_id(test_run_id)
        
        if not mapping_result["success"]:
            print(f"❌ Failed to create mappings: {mapping_result.get('error')}")
            return False
        print(f"✅ Mappings created: {mapping_result['mappings_created']}")
        
        # Test the final JSON generation endpoint
        print("🔗 Testing final JSON generation...")
        from app.main import get_final_consolidated_json
        
        final_json_result = await get_final_consolidated_json(test_run_id)
        
        if final_json_result["success"]:
            final_json = final_json_result["data"]
            print("✅ Final consolidated JSON generated successfully!")
            
            # Print the structure
            print(f"\n📊 Final JSON Structure:")
            print(f"   - Run ID: {final_json['run_id']}")
            print(f"   - Generated at: {final_json['generated_at']}")
            print(f"   - Metadata: {final_json['metadata']}")
            
            if "teacher" in final_json:
                print(f"   - Teacher: {final_json['teacher']['name']}")
            
            if "student" in final_json:
                print(f"   - Student: {final_json['student']['name']}")
            
            if "assignment" in final_json:
                print(f"   - Assignment: {final_json['assignment']['id']}")
            
            if "questions" in final_json:
                print(f"   - Questions: {len(final_json['questions'])}")
            
            if "student_responses" in final_json:
                print(f"   - Student Responses: {len(final_json['student_responses']['responses'])}")
            
            if "question_response_mappings" in final_json:
                print(f"   - Mappings: {len(final_json['question_response_mappings'])}")
            
            # Save the JSON to a file for inspection
            with open(f"final_json_{test_run_id}.json", "w") as f:
                json.dump(final_json, f, indent=2)
            print(f"💾 Final JSON saved to: final_json_{test_run_id}.json")
            
            return True
        else:
            print(f"❌ Final JSON generation failed: {final_json_result.get('message')}")
            return False
        
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
                        {"run_id": {"$regex": "test_final_json"}}
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
        success = asyncio.run(test_final_json_generation())
        if success:
            print("\n✅ Final JSON generation test passed!")
        else:
            print("\n❌ Final JSON generation test failed!")
            sys.exit(1) 