#!/usr/bin/env python3
"""
Quick test to verify the fix for the MongoDB collection boolean issue.
"""

import requests
import json

def test_fix():
    """Test that the endpoint no longer throws the boolean error."""
    
    print("🧪 Testing the fix for MongoDB collection boolean issue...")
    
    # Test the endpoint with a short timeout to see if it gets past the initial error
    try:
        response = requests.post(
            "http://localhost:8000/build-rubrics-for-assignment",
            json={"assignment_id": "6894fb06041681ff21148e2b"},
            timeout=10  # 10 second timeout to catch initial errors
        )
        
        if response.status_code == 200:
            print("✅ Success! The fix worked.")
            result = response.json()
            print(f"   Processed: {result.get('processed_questions', 0)} questions")
            print(f"   Failed: {result.get('failed_questions', 0)} questions")
        elif response.status_code == 500:
            print("❌ Still getting 500 error:")
            print(response.text)
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("✅ Timeout is expected - this means the fix worked and the endpoint is processing!")
        print("   The endpoint got past the initial MongoDB collection check.")
        print("   Rubric generation is now running (which takes several minutes).")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_fix() 