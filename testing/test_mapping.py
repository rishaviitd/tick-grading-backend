#!/usr/bin/env python3
"""
Test script for question-response mapping functionality

This script tests the mapping logic by creating sample data and running the mapping process.
"""

import asyncio
import json
from datetime import datetime

# Mock data for testing
SAMPLE_QUESTION = {
    "_id": "6881219313aa5e929c28fd0a",
    "run_id": "4e92705bd303",
    "question_identifier": "1",
    "has_internal_choice": False,
    "primary_question": "1. If two positive integers a and b are written as a = x²y² and b = xy³, where x and y are prime\nnumbers, then the HCF (a, b) is:\n(a) xy\n(b) xy²\n(c) x³y³\n(d) x2y2",
    "secondary_question": None,
    "primary_diagram_url": None,
    "secondary_diagram_url": None,
    "table_url": None,
    "primary_marks": "1 mark",
    "secondary_marks": None,
    "question_type": "MCQ",
    "created_at": {"$date": "2025-07-23T17:53:23.412Z"},
    "updated_at": {"$date": "2025-07-23T17:53:23.412Z"}
}

SAMPLE_RESPONSE = {
    "_id": "6882a1993d5428c042abbd2e",
    "run_id": "2ca2e9a229b6",
    "student_responses": [
        {
            "answer_label": "ANS-1",
            "cloudinary_url": "https://res.cloudinary.com/de19ckse5/image/upload/v1753391510/wipiwotuohhnjzysirnr.jpg"
        },
        {
            "answer_label": "ANS-15",
            "cloudinary_url": "https://res.cloudinary.com/de19ckse5/image/upload/v1753391510/ei2hpaodieiamo4kexbg.jpg"
        },
        {
            "answer_label": "ANS-30",
            "cloudinary_url": "https://res.cloudinary.com/de19ckse5/image/upload/v1753391511/cor4txnoie764vfyo99l.jpg"
        },
        {
            "answer_label": "ANS-12",
            "cloudinary_url": "https://res.cloudinary.com/de19ckse5/image/upload/v1753391512/edkxemr00oqujgsxx24s.jpg"
        }
    ],
    "created_at": {"$date": "2025-07-24T21:11:53.369Z"},
    "updated_at": {"$date": "2025-07-24T21:11:53.369Z"}
}

def test_extract_question_number():
    """Test the question number extraction function"""
    from app.response_processing.question_response_mapping import QuestionResponseMappingService
    
    # Test cases
    test_cases = [
        ("ANS-1", "1"),
        ("ANS-15", "15"),
        ("ANS-30", "30"),
        ("ANS-12", "12"),
        ("ANS-123", "123"),
        ("ans-1", None),  # Wrong case
        ("ANS1", None),   # Missing dash
        ("ANS-", None),   # No number
        ("ANS-abc", None), # Non-numeric
        ("", None),       # Empty string
        ("ABC-1", None),  # Wrong prefix
    ]
    
    print("Testing question number extraction:")
    for answer_label, expected in test_cases:
        result = QuestionResponseMappingService.extract_question_number_from_answer_label(answer_label)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{answer_label}' -> '{result}' (expected: '{expected}')")
    
    print()

def test_mapping_logic():
    """Test the mapping logic with sample data"""
    from app.response_processing.question_response_mapping import QuestionResponseMappingService
    
    # Create sample questions map
    questions = [SAMPLE_QUESTION]
    questions_map = {q["question_identifier"]: q for q in questions}
    
    # Test student responses
    student_responses = SAMPLE_RESPONSE["student_responses"]
    
    print("Testing mapping logic:")
    print(f"Available questions: {list(questions_map.keys())}")
    print()
    
    for response in student_responses:
        answer_label = response["answer_label"]
        cloudinary_url = response["cloudinary_url"]
        
        # Extract question number
        question_number = QuestionResponseMappingService.extract_question_number_from_answer_label(answer_label)
        
        if question_number:
            if question_number in questions_map:
                print(f"✓ '{answer_label}' -> Question {question_number} (MAPPED)")
                print(f"  URL: {cloudinary_url}")
            else:
                print(f"✗ '{answer_label}' -> Question {question_number} (NOT FOUND)")
        else:
            print(f"✗ '{answer_label}' -> Invalid format")
        
        print()
    
    # Test with matching run_id
    print("Testing with matching run_id:")
    sample_question_2 = SAMPLE_QUESTION.copy()
    sample_question_2["run_id"] = "2ca2e9a229b6"  # Match the response run_id
    sample_question_2["question_identifier"] = "15"  # Match ANS-15
    
    questions_2 = [sample_question_2]
    questions_map_2 = {q["question_identifier"]: q for q in questions_2}
    
    print(f"Available questions: {list(questions_map_2.keys())}")
    
    for response in student_responses:
        answer_label = response["answer_label"]
        question_number = QuestionResponseMappingService.extract_question_number_from_answer_label(answer_label)
        
        if question_number and question_number in questions_map_2:
            print(f"✓ '{answer_label}' -> Question {question_number} (MAPPED)")
        elif question_number:
            print(f"✗ '{answer_label}' -> Question {question_number} (NOT FOUND)")
        else:
            print(f"✗ '{answer_label}' -> Invalid format")

def main():
    """Run all tests"""
    print("=" * 60)
    print("QUESTION-RESPONSE MAPPING TEST")
    print("=" * 60)
    print()
    
    test_extract_question_number()
    test_mapping_logic()
    
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main() 