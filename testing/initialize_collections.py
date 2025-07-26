#!/usr/bin/env python3
"""
Utility script to initialize database collections and create sample data
"""

import asyncio
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import initialize_database, close_database, pipeline_db
from database.schema import Teacher, Student, Assignment, Question, StudentResponse, StudentAssignmentResponse, QuestionResponseMapping, COLLECTION_NAMES, INDEXES

async def initialize_collections():
    """Initialize all database collections and create sample data"""
    print("🚀 Initializing database collections...")
    
    try:
        # Initialize database connection
        success = await initialize_database()
        if not success:
            print("❌ Failed to initialize database connection")
            return False
        
        print("✅ Database connection established")
        
        # Create sample data
        await create_sample_data()
        
        print("🎉 Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        return False
    finally:
        await close_database()

async def create_sample_data():
    """Create sample data for testing"""
    print("📝 Creating sample data...")
    
    # Create a sample teacher
    teacher = Teacher(
        name="Rishav Kumar",
        class_name="10",
        board="CBSE"
    )
    
    teacher_id = await pipeline_db.save_teacher(teacher)
    if teacher_id:
        print(f"✅ Created teacher: {teacher.name}")
    else:
        print("❌ Failed to create teacher")
        return
    
    # Create sample students
    students_data = [
        {"name": "Shristi Jain", "id": "student_001"},
        {"name": "Prashant Goel", "id": "student_002"},
        {"name": "Darshan Kumar", "id": "student_003"},
        {"name": "Ankit Singh", "id": "student_004"},
        {"name": "Piya Maheshwari", "id": "student_005"}
    ]
    
    student_ids = []
    for student_data in students_data:
        student = Student(name=student_data["name"])
        student_id = await pipeline_db.save_student(student)
        if student_id:
            print(f"✅ Created student: {student_data['name']}")
            student_ids.append(student_id)
        else:
            print(f"❌ Failed to create student: {student_data['name']}")
    
    # Create a sample assignment
    assignment = Assignment(
        run_id="sample_assignment_001"
    )
    
    assignment_id = await pipeline_db.save_assignment(assignment)
    if assignment_id:
        print(f"✅ Created assignment with run_id: {assignment.run_id}")
    else:
        print("❌ Failed to create assignment")
        return
    
    # Create a sample question
    question = Question(
        assignment_id=assignment_id,
        run_id="sample_assignment_001",
        question_identifier="1",
        has_internal_choice=False,
        primary_question="What is 2 + 2?",
        secondary_question=None,
        primary_diagram_url=None,
        secondary_diagram_url=None,
        table_url=None,
        primary_marks="1 mark",
        secondary_marks=None,
        question_type="MCQ"
    )
    
    question_id = await pipeline_db.save_question(question)
    if question_id:
        print(f"✅ Created sample question: {question.question_identifier}")
        
        # Update assignment with question ID
        await pipeline_db.update_assignment_questions(assignment_id, [question_id])
        print(f"✅ Updated assignment with question ID")
    else:
        print("❌ Failed to create question")
    
    print("📊 Sample data creation completed!")

async def list_collections():
    """List all collections in the database"""
    print("📋 Listing database collections...")
    
    try:
        success = await initialize_database()
        if not success:
            print("❌ Failed to initialize database connection")
            return False
        
        # Get all collection names
        collections = await pipeline_db.db_manager.db.list_collection_names()
        
        print(f"Found {len(collections)} collections:")
        for collection in sorted(collections):
            print(f"  - {collection}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing collections: {e}")
        return False
    finally:
        await close_database()

async def verify_indexes():
    """Verify that indexes are created for all collections"""
    print("🔍 Verifying database indexes...")
    
    try:
        success = await initialize_database()
        if not success:
            print("❌ Failed to initialize database connection")
            return False
        
        for collection_name, indexes in INDEXES.items():
            collection = pipeline_db.db_manager.get_collection(collection_name)
            if collection is not None:
                # Get existing indexes
                existing_indexes = await collection.list_indexes().to_list(length=None)
                print(f"📊 {collection_name}: {len(existing_indexes)} indexes")
                for idx in existing_indexes:
                    print(f"    - {idx['name']}: {idx['key']}")
            else:
                print(f"⚠️  Collection {collection_name} not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying indexes: {e}")
        return False
    finally:
        await close_database()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            asyncio.run(initialize_collections())
        elif command == "list":
            asyncio.run(list_collections())
        elif command == "indexes":
            asyncio.run(verify_indexes())
        else:
            print("Usage: python initialize_collections.py [init|list|indexes]")
    else:
        print("Usage: python initialize_collections.py [init|list|indexes]")
        print("  init    - Initialize collections and create sample data")
        print("  list    - List all collections in the database")
        print("  indexes - Verify database indexes") 