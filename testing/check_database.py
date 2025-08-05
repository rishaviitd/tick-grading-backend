#!/usr/bin/env python3
"""
Script to check the current state of database collections
"""

import asyncio
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import pipeline_db, initialize_database

async def check_database():
    """Check the current state of all database collections"""
    print("🔍 Checking database collections...")
    
    try:
        # Initialize database
        await initialize_database()
        
        # Collections to check
        collections_to_check = [
            "teachers", "students", "assignments", "questions", 
            "student_assignment_responses", "question_response_mappings",
            "pipeline_results", "diagram_extraction_results", 
            "question_extraction_results", 
        
        ]
        
        for collection_name in collections_to_check:
            collection = pipeline_db.db_manager.get_collection(collection_name)
            if collection is not None:
                count = await collection.count_documents({})
                print(f"📊 {collection_name}: {count} documents")
                
                # Show a few sample documents for key collections
                if count > 0 and count <= 5:
                    print(f"   Sample documents:")
                    cursor = collection.find().limit(3)
                    docs = await cursor.to_list(length=3)
                    for i, doc in enumerate(docs):
                        # Show key fields
                        if collection_name == "teachers":
                            print(f"     {i+1}. ID: {doc.get('_id')}, Name: {doc.get('name')}, Class: {doc.get('class_name')}")
                        elif collection_name == "students":
                            print(f"     {i+1}. ID: {doc.get('_id')}, Name: {doc.get('name')}")
                        elif collection_name == "assignments":
                            print(f"     {i+1}. ID: {doc.get('_id')}, Run ID: {doc.get('run_id')}")
                        elif collection_name == "questions":
                            print(f"     {i+1}. ID: {doc.get('_id')}, Question ID: {doc.get('question_identifier')}, Assignment ID: {doc.get('assignment_id')}")
                        elif collection_name == "student_assignment_responses":
                            print(f"     {i+1}. ID: {doc.get('_id')}, Student ID: {doc.get('student_id')}, Assignment ID: {doc.get('assignment_id')}")
                        elif collection_name == "question_response_mappings":
                            print(f"     {i+1}. ID: {doc.get('_id')}, Question ID: {doc.get('question_identifier')}, Student ID: {doc.get('student_id')}")
                        else:
                            print(f"     {i+1}. ID: {doc.get('_id')}")
                elif count > 5:
                    print(f"   (showing first 3 of {count} documents)")
                    cursor = collection.find().limit(3)
                    docs = await cursor.to_list(length=3)
                    for i, doc in enumerate(docs):
                        print(f"     {i+1}. ID: {doc.get('_id')}")
            else:
                print(f"❌ {collection_name}: Collection not found")
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        # Check if we have the minimum required data
        teachers_collection = pipeline_db.db_manager.get_collection("teachers")
        students_collection = pipeline_db.db_manager.get_collection("students")
        
        teachers_count = await teachers_collection.count_documents({}) if teachers_collection is not None else 0
        students_count = await students_collection.count_documents({}) if students_collection is not None else 0
        
        print(f"Teachers: {teachers_count}")
        print(f"Students: {students_count}")
        
        # Check for real teachers/students (not test data)
        if teachers_collection is not None:
            real_teachers = await teachers_collection.count_documents({"name": {"$not": {"$regex": "Test"}}})
            print(f"Real Teachers (non-test): {real_teachers}")
        
        if students_collection is not None:
            real_students = await students_collection.count_documents({"name": {"$not": {"$regex": "Test"}}})
            print(f"Real Students (non-test): {real_students}")
        
        if real_teachers == 0:
            print("⚠️  WARNING: No real teachers found in database!")
            print("   The question-response mapping workflow requires at least one real teacher.")
        if real_students == 0:
            print("⚠️  WARNING: No real students found in database!")
            print("   The question-response mapping workflow requires at least one real student.")
        
        if real_teachers == 0 or real_students == 0:
            print("\n💡 SOLUTION: You need to create at least one real teacher and one real student.")
            print("   You can use the database initialization script or create them manually.")
            print("   Test data will not work for the actual workflow.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(check_database())
    if not success:
        sys.exit(1) 