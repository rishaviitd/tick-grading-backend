#!/usr/bin/env python3
"""
Test script for the new database schema

This script tests the new database schema structure with core business logic entities.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from database.connection import initialize_database, close_database, pipeline_db
from database.integration import get_db_integration
from database.schema import Teacher, Student, Assignment, Question, StudentResponse, StudentAssignmentResponse, QuestionResponseMapping
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_new_schema():
    """Test the new database schema"""
    
    print("🧪 Testing new database schema...")
    
    # Initialize database connection
    success = await initialize_database()
    if not success:
        print("❌ Failed to initialize database connection")
        return False
    
    try:
        db_integration = get_db_integration()
        
        # Test 1: Create a teacher
        print("\n1. Testing teacher creation...")
        teacher_id = await db_integration.create_teacher("Test Teacher", "10", "CBSE")
        if teacher_id:
            print(f"✅ Teacher created with ID: {teacher_id}")
        else:
            print("❌ Failed to create teacher")
            return False
        
        # Test 2: Create a student
        print("\n2. Testing student creation...")
        student_id = await db_integration.create_student("Test Student")
        if student_id:
            print(f"✅ Student created with ID: {student_id}")
        else:
            print("❌ Failed to create student")
            return False
        
        # Test 3: Create an assignment
        print("\n3. Testing assignment creation...")
        assignment_id = await db_integration.create_assignment("test_run_123")
        if assignment_id:
            print(f"✅ Assignment created with ID: {assignment_id}")
        else:
            print("❌ Failed to create assignment")
            return False
        
        # Test 4: Create a question
        print("\n4. Testing question creation...")
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
        
        question_id = await db_integration.save_question_with_assignment(question_data, assignment_id, "test_run_123")
        if question_id:
            print(f"✅ Question created with ID: {question_id}")
        else:
            print("❌ Failed to create question")
            return False
        
        # Test 5: Update assignment with question
        print("\n5. Testing assignment update...")
        update_success = await db_integration.update_assignment_questions(assignment_id, [question_id])
        if update_success:
            print("✅ Assignment updated with question")
        else:
            print("❌ Failed to update assignment")
            return False
        
        # Test 6: Create student responses
        print("\n6. Testing student response creation...")
        student_responses = [
            StudentResponse(
                question_identifier="1",
                cloudinary_url="https://example.com/test_response.jpg"
            )
        ]
        
        response_id = await db_integration.save_student_assignment_response(
            student_id, assignment_id, "test_run_456", student_responses
        )
        if response_id:
            print(f"✅ Student response created with ID: {response_id}")
        else:
            print("❌ Failed to create student response")
            return False
        
        # Test 7: Create question response mapping
        print("\n7. Testing question response mapping creation...")
        mapping_id = await db_integration.create_question_response_mapping(
            student_id, assignment_id, "test_run_456", question_data, "https://example.com/test_response.jpg"
        )
        if mapping_id:
            print(f"✅ Question response mapping created with ID: {mapping_id}")
        else:
            print("❌ Failed to create question response mapping")
            return False
        
        print("\n🎉 All tests passed! New schema is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await close_database()


async def cleanup_test_data():
    """Clean up test data from the database"""
    
    print("\n🧹 Cleaning up test data...")
    
    success = await initialize_database()
    if not success:
        print("❌ Failed to initialize database connection")
        return False
    
    try:
        # Delete test data from all collections
        collections_to_clean = [
            "teachers", "students", "assignments", "questions", 
            "student_assignment_responses", "question_response_mappings"
        ]
        
        for collection_name in collections_to_clean:
            collection = pipeline_db.db_manager.get_collection(collection_name)
            if collection:
                # Delete documents with test data
                result = await collection.delete_many({
                    "$or": [
                        {"name": {"$regex": "Test"}},
                        {"run_id": {"$regex": "test_run"}}
                    ]
                })
                print(f"✅ Cleaned {result.deleted_count} documents from {collection_name}")
        
        print("🎉 Cleanup completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False
    
    finally:
        await close_database()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_data())
    else:
        asyncio.run(test_new_schema()) 