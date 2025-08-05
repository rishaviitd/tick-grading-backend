"""
Verify Question Parsing Consolidation Results

This script checks the database to verify that the consolidation process worked correctly.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import pipeline_db, initialize_database
from database.schema import COLLECTION_NAMES


async def verify_results():
    """Verify the consolidation results"""
    
    print("🔍 Verifying Question Parsing Consolidation Results")
    print()
    
    try:
        # Initialize database
        await initialize_database()
        
        # Check simple_questions collection
        simple_questions_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["simple_questions"])
        simple_questions_count = await simple_questions_collection.count_documents({})
        print(f"📊 Simple questions collection has {simple_questions_count} documents")
        
        # Show some example questions
        cursor = simple_questions_collection.find().limit(5)
        example_questions = await cursor.to_list(length=5)
        
        print("\n📝 Example Questions:")
        for i, question in enumerate(example_questions):
            question_text = question.get("question_text", "")[:100] + "..." if len(question.get("question_text", "")) > 100 else question.get("question_text", "")
            diagram_url = question.get("diagram_url")
            table_url = question.get("table_url")
            
            print(f"  {i+1}. Text: {question_text}")
            print(f"     Diagram: {'Yes' if diagram_url else 'No'}")
            print(f"     Table: {'Yes' if table_url else 'No'}")
            print()
        
        # Check assignments collection for questions array
        assignments_collection = pipeline_db.db_manager.get_collection(COLLECTION_NAMES["assignments"])
        
        # Find assignments with questions array
        cursor = assignments_collection.find({"questions": {"$exists": True, "$ne": None}})
        assignments_with_questions = await cursor.to_list(length=10)
        
        print(f"📋 Found {len(assignments_with_questions)} assignments with questions array")
        
        for i, assignment in enumerate(assignments_with_questions[:3]):
            questions = assignment.get("questions", [])
            print(f"\n  Assignment {i+1}: {assignment.get('title', 'Unknown')}")
            print(f"    Questions: {len(questions)} entries")
            
            # Show first few questions
            for j, question_mapping in enumerate(questions[:5]):
                question_identifier = question_mapping.get("question_identifier")
                question_id = question_mapping.get("question_id")
                
                if isinstance(question_id, list):
                    print(f"      {j+1}. Question {question_identifier}: Internal choice ({len(question_id)} sub-questions)")
                else:
                    print(f"      {j+1}. Question {question_identifier}: Single question")
            
            if len(questions) > 5:
                print(f"      ... and {len(questions) - 5} more questions")
        
        print("\n✅ Verification completed!")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")


if __name__ == "__main__":
    asyncio.run(verify_results()) 