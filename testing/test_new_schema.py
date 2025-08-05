"""
Test script to verify the new schema works correctly
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.integration import DatabaseIntegration
from database.schema import Question, QuestionResponseMapping


async def test_new_schema():
    """Test the new schema with sample data"""
    
    print("🧪 Testing New Schema")
    print()
    
    try:
        # Initialize database integration
        db_integration = DatabaseIntegration()
        await db_integration.initialize()
        
        print("✅ Database integration initialized")
        
        # Test creating a question document with new schema
        question_id = await db_integration._create_question_document(
            question_text="Test question text",
            question_marks=5,  # Numerical value
            question_marks_analysis="5 marks",  # Descriptive string
            question_type="Normal Subjective",
            diagram_url=None,
            table_url=None
        )
        
        if question_id:
            print(f"✅ Successfully created question with new schema: {question_id}")
        else:
            print("❌ Failed to create question with new schema")
            return False
        
        # Test creating a question response mapping with new schema
        question_data = {
            "question_text": "Test question text",
            "question_marks": 3,  # Numerical value
            "question_marks_analysis": "3 marks",  # Descriptive string
            "question_type": "MCQ",
            "diagram_url": None,
            "table_url": None
        }
        
        mapping_id = await db_integration.create_question_response_mapping(
            student_id="test_student",
            assignment_id="test_assignment", 
            run_id="test_run",
            question_data=question_data,
            response_url="https://example.com/response.jpg"
        )
        
        if mapping_id:
            print(f"✅ Successfully created question response mapping with new schema: {mapping_id}")
        else:
            print("❌ Failed to create question response mapping with new schema")
            return False
        
        print()
        print("🎉 All schema tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing schema: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_new_schema())
    if not success:
        sys.exit(1) 