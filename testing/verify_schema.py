"""
Verify that the saved data has the correct new schema
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import pipeline_db, initialize_database


async def verify_schema():
    """Verify the saved data has the correct schema"""
    
    print("🔍 Verifying Schema")
    print()
    
    try:
        await initialize_database()
        
        # Check questions collection
        questions_collection = pipeline_db.db_manager.get_collection("questions")
        question = await questions_collection.find_one({})
        
        if question:
            print("✅ Found question document:")
            print(f"   - question_marks: {question.get('question_marks')} (type: {type(question.get('question_marks')).__name__})")
            print(f"   - question_marks_analysis: {question.get('question_marks_analysis')}")
            print(f"   - question_type: {question.get('question_type')}")
            print(f"   - question_text: {question.get('question_text')[:50]}...")
        else:
            print("❌ No question documents found")
        
        # Check question_response_mappings collection
        mappings_collection = pipeline_db.db_manager.get_collection("question_response_mappings")
        mapping = await mappings_collection.find_one({})
        
        if mapping:
            print("\n✅ Found question response mapping document:")
            print(f"   - question_marks: {mapping.get('question_marks')} (type: {type(mapping.get('question_marks')).__name__})")
            print(f"   - question_marks_analysis: {mapping.get('question_marks_analysis')}")
            print(f"   - question_type: {mapping.get('question_type')}")
        else:
            print("\n❌ No question response mapping documents found")
        
        print("\n🎉 Schema verification completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_schema())
    if not success:
        sys.exit(1) 