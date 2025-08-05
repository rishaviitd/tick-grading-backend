#!/usr/bin/env python3
"""
Test script for the enhanced question parsing logic
"""

import sys
import os
import asyncio

# Add the project root to the path
project_root = os.path.join(os.path.dirname(__file__), '..')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.integration import DatabaseIntegration

def test_question_parsing():
    """Test the enhanced question parsing logic"""
    
    # Sample markdown content with questions
    sample_markdown = """1. The LCM of two numbers is 14 times their HCF. The sum of LCM and HCF is 600. If one number is 280, then the other number is
(a) 20
(b) 28
(c) 60
(d) 80
[####]
2. When 2120 is expressed as the product of its prime factors we get
(a) 2 × 53 × 53
(b) 2³ × 5 × 53
(c) 5 × 7² × 31
(d) 52 × 7 × 33
[####]
22. Find A and B, if sin (A + 2B) = √3/2 and cos (A + B) = 1/2.
[%OR%]
If (1 + cos A) (1 – cos A) = 3/4, find the value of tan A.
[####]
25. A rope by which a cow is tethered is increased from 16m to 23m. How much additional ground does it have now to graze?
[%OR%]
In the below figure, OACB is a quadrant of a circle with centre O and radius 3.5 cm. If OD = 2 cm, find the area of the (i) quadrant OACB, (ii) shaded region.
[####]
30. Prove that: (sin θ - cos θ + 1) / (sin θ + cos θ - 1) = sec θ + tan θ
[####]"""
    
    # Create database integration instance
    db_integration = DatabaseIntegration()
    
    # Test the parsing logic
    print("Testing enhanced question parsing logic...")
    print("=" * 50)
    
    # Parse questions
    questions = db_integration._parse_questions_from_markdown(sample_markdown)
    
    print(f"Total questions parsed: {len(questions)}")
    print()
    
    # Display results
    for i, question in enumerate(questions, 1):
        print(f"Question {i}:")
        print(f"  Identifier: {question['question_identifier']}")
        print(f"  Has internal choice: {question['has_internal_choice']}")
        
        if question['has_internal_choice']:
            print(f"  Question text (array):")
            for j, text in enumerate(question['question_text']):
                print(f"    {j+1}. {text[:100]}...")
        else:
            print(f"  Question text: {question['question_text'][:100]}...")
        print()
    
    # Test structured output creation
    print("Testing structured output creation...")
    print("=" * 50)
    
    structured_output = db_integration._create_structured_questions_output(questions)
    
    print(f"Total questions: {structured_output['total_questions']}")
    print(f"Questions with internal choice: {structured_output['questions_with_internal_choice']}")
    print(f"Questions without internal choice: {structured_output['questions_without_internal_choice']}")
    print()
    
    # Display structured questions
    for question in structured_output['questions']:
        print(f"Question {question['question_identifier']}:")
        print(f"  Has internal choice: {question['has_internal_choice']}")
        if question['has_internal_choice']:
            print(f"  Array length: {len(question['question_text'])}")
        print()
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_question_parsing() 