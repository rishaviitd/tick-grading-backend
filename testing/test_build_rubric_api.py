#!/usr/bin/env python3
"""
Test script for the /build-rubric API endpoint.
This script tests the new API with a sample question from the current schema.
"""

import sys
import json
import requests
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

def test_build_rubric_api():
    """Test the /build-rubric API endpoint with a sample question."""
    
    # Sample question data from current schema
    sample_question = {
        "_id": "507f1f77bcf86cd799439011",  # Valid MongoDB ObjectId
        "run_id": "test_run_001",
        "question_text": "1. What is the capital of France?",
        "question_marks": 2,
        "question_marks_analysis": "2 marks for correct answer",
        "question_type": "MCQ",
        "diagram_url": None,
        "table_url": None,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    # API endpoint URL (assuming server runs on localhost:8000)
    api_url = "http://localhost:8000/build-rubric"
    
    # Prepare request payload
    payload = {
        "question": sample_question
    }
    
    print("Testing /build-rubric API endpoint...")
    print(f"API URL: {api_url}")
    print(f"Sample question type: {sample_question['question_type']}")
    print(f"Question text: {sample_question['question_text']}")
    print()
    
    try:
        # Make the API request
        response = requests.post(api_url, json=payload, timeout=300)  # 5 minute timeout
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API call successful!")
            print(f"Success: {result.get('success')}")
            print(f"Total time: {result.get('total_time', 'N/A')} seconds")
            print(f"Token counts: {result.get('token_counts', 'N/A')}")
            
            if result.get('rubric'):
                print("✅ Rubric generated successfully!")
                print(f"Rubric keys: {list(result['rubric'].keys())}")
            else:
                print("❌ No rubric generated")
            
            if result.get('metadata'):
                print("✅ Metadata generated successfully!")
                print(f"Metadata keys: {list(result['metadata'].keys())}")
            else:
                print("❌ No metadata generated")
            
            if result.get('solution'):
                print("✅ Solution generated successfully!")
                print(f"Solution keys: {list(result['solution'].keys())}")
            else:
                print("❌ No solution generated")
            
            if result.get('errors'):
                print(f"⚠️  Warnings/Errors: {result['errors']}")
                
        else:
            print("❌ API call failed!")
            print(f"Error response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the server is running on localhost:8000")
    except requests.exceptions.Timeout:
        print("❌ Request timeout: The rubric generation took too long")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_with_different_question_types():
    """Test with different question types."""
    
    question_types = [
        {
            "name": "MCQ",
            "question": {
                "_id": "507f1f77bcf86cd799439012",
                "run_id": "test_run_001",
                "question_text": "1. Which of the following is a programming language?",
                "question_marks": 1,
                "question_marks_analysis": "1 mark for correct option",
                "question_type": "MCQ",
                "diagram_url": None,
                "table_url": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        },
        {
            "name": "Subjective",
            "question": {
                "_id": "507f1f77bcf86cd799439013",
                "run_id": "test_run_001",
                "question_text": "2. Explain the concept of object-oriented programming.",
                "question_marks": 5,
                "question_marks_analysis": "5 marks for comprehensive explanation",
                "question_type": "Subjective",
                "diagram_url": None,
                "table_url": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        },
        {
            "name": "Internal Choice",
            "question": {
                "_id": "507f1f77bcf86cd799439014",
                "run_id": "test_run_001",
                "question_text": "3. Answer any one of the following questions:",
                "question_marks": 5,
                "question_marks_analysis": "5 marks for either option chosen",
                "question_type": "Internal Choice",
                "diagram_url": None,
                "table_url": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        },
        {
            "name": "Case-Study",
            "question": {
                "_id": "507f1f77bcf86cd799439015",
                "run_id": "test_run_001",
                "question_text": "4. Read the following case study and answer the questions below:",
                "question_marks": 4,
                "question_marks_analysis": "Part (i): 1 mark, Part (ii): 1 mark, Part (iii): 2 marks",
                "question_type": "Case-Study",
                "diagram_url": None,
                "table_url": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    ]
    
    api_url = "http://localhost:8000/build-rubric"
    
    for test_case in question_types:
        print(f"\n{'='*50}")
        print(f"Testing {test_case['name']} question type...")
        print(f"{'='*50}")
        
        payload = {"question": test_case["question"]}
        
        try:
            response = requests.post(api_url, json=payload, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {test_case['name']} - Success: {result.get('success')}")
                print(f"⏱️  Time: {result.get('total_time', 'N/A')} seconds")
                
                if result.get('rubric'):
                    print(f"📋 Rubric generated: {len(result['rubric'])} fields")
                if result.get('metadata'):
                    print(f"📊 Metadata generated: {len(result['metadata'])} fields")
                if result.get('solution'):
                    print(f"💡 Solution generated: {len(result['solution'])} fields")
                    
            else:
                print(f"❌ {test_case['name']} - Failed: {response.status_code}")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ {test_case['name']} - Error: {str(e)}")

if __name__ == "__main__":
    print("🧪 Testing /build-rubric API endpoint")
    print("Make sure the server is running with: uvicorn app.main:app --reload")
    print()
    
    # Test basic functionality
    test_build_rubric_api()
    
    # Test different question types
    test_with_different_question_types()
    
    print("\n🎉 Test completed!") 