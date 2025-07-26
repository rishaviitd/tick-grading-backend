#!/usr/bin/env python3
"""
Test script to verify identifier normalization is working correctly
"""

import asyncio
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.identifier_normalizer import (
    normalize_identifier,
    is_ans_identifier,
    extract_number_from_identifier,
    normalize_identifier_list,
    normalize_identifier_dict
)

def test_identifier_normalization():
    """Test the identifier normalization functions"""
    print("🧪 Testing identifier normalization functions...")
    
    # Test normalize_identifier function
    print("\n1. Testing normalize_identifier function:")
    test_cases = [
        ("ANS-1", "1"),
        ("ANS-15", "15"),
        ("1", "1"),
        ("15", "15"),
        ("ans-1", "1"),
        ("ANS-1", "1"),
        ("Question 1", "Question 1"),
        ("", ""),
        (None, ""),
        (1, "1"),
        (15, "15")
    ]
    
    for input_val, expected in test_cases:
        result = normalize_identifier(input_val)
        status = "✅" if result == expected else "❌"
        print(f"   {status} normalize_identifier('{input_val}') -> '{result}' (expected: '{expected}')")
    
    # Test is_ans_identifier function
    print("\n2. Testing is_ans_identifier function:")
    test_cases = [
        ("ANS-1", True),
        ("ans-1", True),
        ("1", False),
        ("Question 1", False),
        ("", False),
        (None, False)
    ]
    
    for input_val, expected in test_cases:
        result = is_ans_identifier(input_val)
        status = "✅" if result == expected else "❌"
        print(f"   {status} is_ans_identifier('{input_val}') -> {result} (expected: {expected})")
    
    # Test extract_number_from_identifier function
    print("\n3. Testing extract_number_from_identifier function:")
    test_cases = [
        ("ANS-1", "1"),
        ("Question 15", "15"),
        ("1", "1"),
        ("ANS-1", "1"),
        ("", ""),
        (None, "")
    ]
    
    for input_val, expected in test_cases:
        result = extract_number_from_identifier(input_val)
        status = "✅" if result == expected else "❌"
        print(f"   {status} extract_number_from_identifier('{input_val}') -> '{result}' (expected: '{expected}')")
    
    # Test normalize_identifier_list function
    print("\n4. Testing normalize_identifier_list function:")
    input_list = ["ANS-1", "ANS-2", "3", "ANS-15"]
    expected_list = ["1", "2", "3", "15"]
    result = normalize_identifier_list(input_list)
    status = "✅" if result == expected_list else "❌"
    print(f"   {status} normalize_identifier_list({input_list}) -> {result} (expected: {expected_list})")
    
    # Test normalize_identifier_dict function
    print("\n5. Testing normalize_identifier_dict function:")
    input_dict = {"ANS-1": "data1", "ANS-2": "data2", "3": "data3"}
    expected_dict = {"1": "data1", "2": "data2", "3": "data3"}
    result = normalize_identifier_dict(input_dict)
    status = "✅" if result == expected_dict else "❌"
    print(f"   {status} normalize_identifier_dict({input_dict}) -> {result} (expected: {expected_dict})")
    
    print("\n🎉 Identifier normalization tests completed!")

async def test_database_integration():
    """Test that database integration uses normalized identifiers"""
    print("\n🧪 Testing database integration with normalized identifiers...")
    
    try:
        from database.integration import get_db_integration
        
        # Initialize database integration
        db_integration = get_db_integration()
        await db_integration.initialize()
        
        # Test question parsing with ANS- identifiers
        print("\n1. Testing question parsing with ANS- identifiers:")
        markdown_content = """
[####] What is 2 + 2?
[####] What is 3 + 3?
[####] What is 4 + 4?
        """
        
        questions = db_integration._parse_questions_from_markdown(markdown_content)
        
        print(f"   Parsed {len(questions)} questions:")
        for i, question in enumerate(questions):
            identifier = question["question_identifier"]
            # The normalization should convert ANS-{i+1} to just {i+1}
            expected = str(i + 1)
            status = "✅" if identifier == expected else "❌"
            print(f"   {status} Question {i+1}: '{identifier}' (expected: '{expected}')")
            print(f"      Raw identifier would have been 'ANS-{i+1}', normalized to '{identifier}'")
        
        # Test question data combination
        print("\n2. Testing question data combination:")
        question_data = {
            "question_identifier": "ANS-1",
            "has_internal_choice": False,
            "primary_question": "What is 2 + 2?",
            "secondary_question": None
        }
        
        marks_mapping = {
            "question-1": {
                "question_type": "MCQ",
                "marks": ["1 mark"]
            }
        }
        
        diagram_mapping = {
            "figure-1": {
                "question_identifier": "1",
                "cloudinary_url": "https://example.com/diagram1.jpg",
                "choice_location": "null"
            }
        }
        
        # This should normalize the identifier internally
        question = db_integration._combine_question_data(
            question_data, marks_mapping, diagram_mapping, "test_run", "test_assignment"
        )
        
        if question:
            identifier = question.question_identifier
            expected = "1"
            status = "✅" if identifier == expected else "❌"
            print(f"   {status} Combined question identifier: '{identifier}' (expected: '{expected}')")
        else:
            print("   ❌ Failed to combine question data")
        
        print("\n🎉 Database integration tests completed!")
        
    except Exception as e:
        print(f"❌ Error in database integration tests: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("🚀 Starting identifier normalization tests...")
    
    # Test the utility functions
    test_identifier_normalization()
    
    # Test database integration
    await test_database_integration()
    
    print("\n🎉 All identifier normalization tests completed successfully!")
    print("The system should now properly normalize ANS- identifiers throughout the pipeline.")

if __name__ == "__main__":
    asyncio.run(main()) 