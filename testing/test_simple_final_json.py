#!/usr/bin/env python3
"""
Simple test for final JSON generation
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

async def test_simple_final_json():
    """Test simple final JSON generation"""
    print("🧪 Testing simple final JSON generation...")
    
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
        test_run_id = "test_simple_final_json_001"
        assignment_id = await db_integration.create_assignment(test_run_id)
        if not assignment_id:
            print("❌ Failed to create assignment")
            return False
        print(f"✅ Assignment created: {assignment_id}")
        
        # Create a simple question
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
            print(f"✅ Question created: {question_id}")
        else:
            print("❌ Failed to create question")
            return False
        
        # Update assignment with question ID
        await db_integration.update_assignment_questions(assignment_id, [question_id])
        print(f"✅ Assignment updated with question")
        
        # Create student response
        student_responses = [
            StudentResponse(
                question_identifier="1",
                cloudinary_url="https://example.com/response1.jpg"
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
        
        # Create mapping
        from app.response_processing.question_response_mapping import QuestionResponseMappingService
        mapping_result = await QuestionResponseMappingService.create_mappings_for_run_id(test_run_id)
        
        if not mapping_result["success"]:
            print(f"❌ Failed to create mappings: {mapping_result.get('error')}")
            return False
        print(f"✅ Mappings created: {mapping_result['mappings_created']}")
        
        # Manually create final JSON (simulating what the endpoint should do)
        print("🔗 Creating final JSON manually...")
        
        from database.connection import pipeline_db
        
        final_json = {
            "run_id": test_run_id,
            "generated_at": "2024-01-01T00:00:00Z",
            "metadata": {
                "total_questions": 1,
                "total_responses": 1,
                "total_mappings": 1
            }
        }
        
        # Get teacher info
        teachers_collection = pipeline_db.db_manager.get_collection("teachers")
        if teachers_collection is not None:
            teacher = await teachers_collection.find_one()
            if teacher:
                final_json["teacher"] = {
                    "id": str(teacher["_id"]),
                    "name": teacher["name"],
                    "class_name": teacher["class_name"],
                    "board": teacher["board"]
                }
        
        # Get student info
        students_collection = pipeline_db.db_manager.get_collection("students")
        if students_collection is not None:
            student = await students_collection.find_one({"_id": student_id})
            if student:
                final_json["student"] = {
                    "id": str(student["_id"]),
                    "name": student["name"]
                }
        
        # Get assignment info
        assignments_collection = pipeline_db.db_manager.get_collection("assignments")
        if assignments_collection is not None:
            assignment = await assignments_collection.find_one({"_id": assignment_id})
            if assignment:
                final_json["assignment"] = {
                    "id": str(assignment["_id"]),
                    "run_id": assignment["run_id"],
                    "questions": assignment.get("questions", [])
                }
        
        # Get questions
        questions = await pipeline_db.get_questions_by_run_id(test_run_id)
        if questions:
            final_json["questions"] = []
            for question in questions:
                question_data = {
                    "id": str(question["_id"]),
                    "assignment_id": question["assignment_id"],
                    "question_identifier": question["question_identifier"],
                    "has_internal_choice": question["has_internal_choice"],
                    "primary_question": question["primary_question"],
                    "secondary_question": question.get("secondary_question"),
                    "primary_diagram_url": question.get("primary_diagram_url"),
                    "secondary_diagram_url": question.get("secondary_diagram_url"),
                    "table_url": question.get("table_url"),
                    "primary_marks": question["primary_marks"],
                    "secondary_marks": question.get("secondary_marks"),
                    "question_type": question["question_type"]
                }
                final_json["questions"].append(question_data)
        
        # Get student responses
        responses_data = await pipeline_db.get_responses_by_run_id(test_run_id)
        if responses_data:
            final_json["student_responses"] = {
                "id": str(responses_data["_id"]),
                "student_id": responses_data["student_id"],
                "assignment_id": responses_data["assignment_id"],
                "run_id": responses_data["run_id"],
                "responses": responses_data.get("student_responses", [])
            }
        
        # Get mappings
        mappings = await pipeline_db.get_question_response_mappings_by_run_id(test_run_id)
        if mappings:
            final_json["question_response_mappings"] = []
            for mapping in mappings:
                mapping_data = {
                    "id": str(mapping["_id"]),
                    "student_id": mapping["student_id"],
                    "assignment_id": mapping["assignment_id"],
                    "run_id": mapping["run_id"],
                    "question_identifier": mapping["question_identifier"],
                    "has_internal_choice": mapping["has_internal_choice"],
                    "primary_question": mapping["primary_question"],
                    "secondary_question": mapping.get("secondary_question"),
                    "primary_diagram_url": mapping.get("primary_diagram_url"),
                    "secondary_diagram_url": mapping.get("secondary_diagram_url"),
                    "table_url": mapping.get("table_url"),
                    "primary_marks": mapping["primary_marks"],
                    "secondary_marks": mapping.get("secondary_marks"),
                    "question_type": mapping["question_type"],
                    "response_cloudinary_url": mapping["response_cloudinary_url"]
                }
                final_json["question_response_mappings"].append(mapping_data)
        
        print("✅ Final JSON created successfully!")
        
        # Print structure
        print(f"\n📊 Final JSON Structure:")
        print(f"   - Run ID: {final_json['run_id']}")
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
        
        # Save to file
        with open(f"final_json_{test_run_id}.json", "w") as f:
            json.dump(final_json, f, indent=2)
        print(f"💾 Final JSON saved to: final_json_{test_run_id}.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_final_json())
    if success:
        print("\n✅ Simple final JSON test passed!")
    else:
        print("\n❌ Simple final JSON test failed!")
        sys.exit(1) 