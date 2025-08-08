#!/usr/bin/env python3
"""
Debug script to identify the issue with bulk rubric generation.
"""

import sys
import json
import requests
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

def debug_bulk_rubric_endpoint():
    """Debug the bulk rubric generation endpoint."""
    
    base_url = "http://localhost:8000"
    
    print("🔍 Debugging Bulk Rubric Generation")
    print("=" * 50)
    
    # Step 1: Get assignments to find a valid assignment ID
    print("1. Getting assignments...")
    try:
        response = requests.get(f"{base_url}/api/assignments", timeout=10)
        if response.status_code == 200:
            assignments = response.json()
            print(f"✅ Found {len(assignments)} assignments")
            
            if not assignments:
                print("❌ No assignments found. Please create an assignment first.")
                return
            
            # Use the first assignment
            assignment = assignments[0]
            assignment_id = assignment['id']
            print(f"📋 Using assignment: {assignment['title']} (ID: {assignment_id})")
            
            # Check assignment structure
            print(f"   Questions: {assignment.get('total_questions', 0)}")
            print(f"   Question details: {len(assignment.get('question_details', []))}")
            
            # Check if questions have the expected structure
            question_details = assignment.get('question_details', [])
            if question_details:
                first_question = question_details[0]
                print(f"   First question structure:")
                print(f"     - ID: {first_question.get('id')}")
                print(f"     - Text: {first_question.get('question_text', 'N/A')[:50]}...")
                print(f"     - Type: {first_question.get('question_type', 'N/A')}")
                print(f"     - Marks: {first_question.get('question_marks', 'N/A')}")
                print(f"     - Has rubric: {bool(first_question.get('rubric'))}")
            
        else:
            print(f"❌ Failed to get assignments: {response.status_code}")
            print(f"   Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Error getting assignments: {e}")
        return
    
    # Step 2: Test the bulk rubric generation endpoint
    print(f"\n2. Testing bulk rubric generation for assignment {assignment_id}...")
    
    try:
        payload = {"assignment_id": assignment_id}
        print(f"   Request payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{base_url}/build-rubrics-for-assignment",
            json=payload,
            timeout=60  # 1 minute timeout
        )
        
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"   Total questions: {result.get('total_questions', 0)}")
            print(f"   Processed: {result.get('processed_questions', 0)}")
            print(f"   Failed: {result.get('failed_questions', 0)}")
            print(f"   Time: {result.get('total_time', 0):.2f} seconds")
            
            if result.get('errors'):
                print(f"   Errors: {result['errors']}")
                
        elif response.status_code == 500:
            print("❌ 500 Internal Server Error")
            print(f"   Response: {response.text}")
            
            # Try to parse the error response
            try:
                error_data = response.json()
                print(f"   Error detail: {error_data.get('detail', 'No detail provided')}")
            except:
                print(f"   Raw error response: {response.text}")
                
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⚠️  Request timed out (this might be expected for long operations)")
    except Exception as e:
        print(f"❌ Error testing bulk rubric generation: {e}")
        import traceback
        traceback.print_exc()

def test_single_rubric_generation():
    """Test single rubric generation to see if that works."""
    
    base_url = "http://localhost:8000"
    
    print(f"\n3. Testing single rubric generation...")
    
    # Get a sample question from assignments
    try:
        response = requests.get(f"{base_url}/api/assignments", timeout=10)
        if response.status_code == 200:
            assignments = response.json()
            if assignments:
                assignment = assignments[0]
                question_details = assignment.get('question_details', [])
                
                if question_details:
                    question = question_details[0]
                    print(f"   Testing with question: {question.get('question_text', 'N/A')[:50]}...")
                    
                    # Test single rubric generation
                    payload = {"question": question}
                    response = requests.post(
                        f"{base_url}/build-rubric",
                        json=payload,
                        timeout=60
                    )
                    
                    print(f"   Single rubric response status: {response.status_code}")
                    if response.status_code == 200:
                        print("✅ Single rubric generation works!")
                    else:
                        print(f"❌ Single rubric generation failed: {response.text}")
                        
    except Exception as e:
        print(f"❌ Error testing single rubric generation: {e}")

if __name__ == "__main__":
    debug_bulk_rubric_endpoint()
    test_single_rubric_generation() 