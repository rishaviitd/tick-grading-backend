"""
Database Initialization Script for TickAI

This script initializes the database with sample data for teachers and students
according to the new schema structure.
"""

import asyncio
import os
from typing import List
from dotenv import load_dotenv

from .connection import initialize_database, close_database, pipeline_db
from .schema import Teacher, Student

# Load environment variables
load_dotenv()


async def initialize_sample_data():
    """Initialize the database with sample teachers and students"""
    
    # Initialize database connection
    success = await initialize_database()
    if not success:
        print("Failed to initialize database connection")
        return False
    
    try:
        # Sample teacher data
        teachers_data = [
            {
                "name": "Rishav Kumar",
                "class_name": "10",
                "board": "CBSE"
            }
        ]
        
        # Sample student data
        students_data = [
            {"name": "Shristi Jain"},
            {"name": "Aarav Patel"},
            {"name": "Zara Khan"},
            {"name": "Vihaan Sharma"},
            {"name": "Anaya Singh"}
        ]
        
        # Create teachers
        print("Creating teachers...")
        for teacher_data in teachers_data:
            teacher = Teacher(
                name=teacher_data["name"],
                class_name=teacher_data["class_name"],
                board=teacher_data["board"]
            )
            
            success = await pipeline_db.save_teacher(teacher)
            if success:
                print(f"✅ Created teacher: {teacher_data['name']}")
            else:
                print(f"❌ Failed to create teacher: {teacher_data['name']}")
        
        # Create students
        print("\nCreating students...")
        for student_data in students_data:
            student = Student(
                name=student_data["name"]
            )
            
            success = await pipeline_db.save_student(student)
            if success:
                print(f"✅ Created student: {student_data['name']}")
            else:
                print(f"❌ Failed to create student: {student_data['name']}")
        
        print("\n🎉 Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during database initialization: {e}")
        return False
    
    finally:
        await close_database()


async def list_sample_data():
    """List all teachers and students in the database"""
    
    # Initialize database connection
    success = await initialize_database()
    if not success:
        print("Failed to initialize database connection")
        return False
    
    try:
        # Get teachers collection
        teachers_collection = pipeline_db.db_manager.get_collection("teachers")
        if teachers_collection:
            teachers = await teachers_collection.find().to_list(length=None)
            print(f"\n📚 Teachers ({len(teachers)}):")
            for teacher in teachers:
                print(f"  - {teacher['name']} (Class {teacher['class_name']}, {teacher['board']})")
        
        # Get students collection
        students_collection = pipeline_db.db_manager.get_collection("students")
        if students_collection:
            students = await students_collection.find().to_list(length=None)
            print(f"\n👥 Students ({len(students)}):")
            for student in students:
                print(f"  - {student['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing data: {e}")
        return False
    
    finally:
        await close_database()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        asyncio.run(list_sample_data())
    else:
        asyncio.run(initialize_sample_data()) 