#!/usr/bin/env python3
"""
Test script for the /build-rubrics-for-assignment API endpoint.
This script tests the new bulk rubric generation API with a sample assignment.
"""

import sys
import json
import requests
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

def test_bulk_rubric_generation():
    """Test the /build-rubrics-for-assignment API endpoint."""
    
    # API endpoint URL (assuming server runs on localhost:8000)
    api_url = "http://localhost:8000/build-rubrics-for-assignment"
    
    # You'll need to replace this with an actual assignment ID from your database
    # You can get this by first calling the /api/assignments endpoint
    sample_assignment_id = "507f1f77bcf86cd799439011"  # Replace with real assignment ID
    
    # Prepare request payload
    payload = {
        "assignment_id": sample_assignment_id
    }
    
    print("Testing /build-rubrics-for-assignment API endpoint...")
    print(f"API URL: {api_url}")
    print(f"Assignment ID: {sample_assignment_id}")
    print()
    
    try:
        # Make the API request
        response = requests.post(api_url, json=payload, timeout=600)  # 10 minute timeout for bulk processing
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API call successful!")
            print(f"Success: {result.get('success')}")
            print(f"Assignment ID: {result.get('assignment_id')}")
            print(f"Total questions: {result.get('total_questions')}")
            print(f"Processed questions: {result.get('processed_questions')}")
            print(f"Failed questions: {result.get('failed_questions')}")
            print(f"Total time: {result.get('total_time', 'N/A')} seconds")
            
            if result.get('results'):
                print(f"\n📋 Individual Question Results:")
                for i, question_result in enumerate(result['results'], 1):
                    print(f"  {i}. Question {question_result.get('question_id', 'N/A')}")
                    print(f"     Success: {question_result.get('success')}")
                    print(f"     Text: {question_result.get('question_text', 'N/A')[:50]}...")
                    if question_result.get('success'):
                        print(f"     Processing time: {question_result.get('processing_time', 'N/A')} seconds")
                    else:
                        print(f"     Errors: {question_result.get('errors', [])}")
                    print()
            
            if result.get('errors'):
                print(f"⚠️  Overall Errors: {result['errors']}")
                
        else:
            print("❌ API call failed!")
            print(f"Error response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the server is running on localhost:8000")
    except requests.exceptions.Timeout:
        print("❌ Request timeout: The bulk rubric generation took too long")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def get_assignments():
    """Get available assignments to find a real assignment ID for testing."""
    
    api_url = "http://localhost:8000/api/assignments"
    
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            assignments = response.json()
            print("📋 Available Assignments:")
            for assignment in assignments:
                print(f"  ID: {assignment.get('id')}")
                print(f"  Title: {assignment.get('title')}")
                print(f"  Questions: {assignment.get('total_questions', 0)}")
                print()
            return assignments
        else:
            print(f"❌ Failed to get assignments: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error getting assignments: {str(e)}")
        return []

if __name__ == "__main__":
    print("🧪 Testing Bulk Rubric Generation API")
    print("=" * 50)
    
    # First, get available assignments
    assignments = get_assignments()
    
    if assignments:
        # Use the first assignment for testing
        test_assignment_id = assignments[0]['id']
        print(f"Using assignment ID: {test_assignment_id}")
        print()
        
        # Test the bulk rubric generation
        test_bulk_rubric_generation()
    else:
        print("❌ No assignments available for testing")
        print("Please create an assignment first using the question parsing pipeline.") 