#!/usr/bin/env python3
"""
Test script to verify the API fix for assignment_marks parameter
"""

import asyncio
import sys
import os
import httpx

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_api_endpoint():
    """Test the /process-cbse-paper endpoint with the fixed assignment_marks parameter"""
    print("🧪 Testing /process-cbse-paper endpoint with fixed assignment_marks parameter...")
    
    try:
        # Create a simple test PDF file (just for testing the endpoint)
        test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"
        
        # Test the endpoint with assignment_marks as string (simulating form data)
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create form data
            files = {"pdf_file": ("test.pdf", test_pdf_content, "application/pdf")}
            data = {
                "assignment_title": "Test Assignment",
                "assignment_marks": "100"  # This should now work as a string
            }
            
            print("📤 Sending request to /process-cbse-paper...")
            response = await client.post("http://localhost:8000/process-cbse-paper", files=files, data=data)
            
            print(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 422:
                print("❌ Still getting 422 Unprocessable Entity error")
                print(f"Response body: {response.text}")
                return False
            elif response.status_code == 200:
                print("✅ API endpoint is working correctly!")
                result = response.json()
                print(f"Response: {result}")
                return True
            else:
                print(f"⚠️ Unexpected status code: {response.status_code}")
                print(f"Response body: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing API endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_server_health():
    """Test if the server is running and healthy"""
    print("🏥 Testing server health...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/")
            
            if response.status_code == 200:
                print("✅ Server is healthy and running")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Server health check error: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting API fix verification tests...")
    
    # First check if server is running
    if not await test_server_health():
        print("❌ Server is not running. Please start the server first.")
        return False
    
    # Test the API endpoint
    success = await test_api_endpoint()
    
    if success:
        print("\n🎉 All tests passed! The API fix is working correctly.")
        print("The assignment_marks parameter now accepts string values from form data.")
    else:
        print("\n❌ Tests failed. The API fix may not be working correctly.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main()) 