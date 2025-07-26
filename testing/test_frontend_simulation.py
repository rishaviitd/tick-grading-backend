#!/usr/bin/env python3
"""
Test script to simulate frontend behavior and identify the 422 error
"""

import asyncio
import sys
import os
import httpx
import tempfile

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_frontend_simulation():
    """Simulate exactly what the frontend does"""
    print("🧪 Simulating frontend behavior...")
    
    try:
        # Create a simple test PDF file (just for testing)
        test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"
        
        # Create a temporary file to simulate file upload
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(test_pdf_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Test the endpoint with file upload (simulating frontend)
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Open the file and create form data exactly like the frontend
                with open(tmp_file_path, 'rb') as f:
                    files = {"pdf_file": ("test.pdf", f.read(), "application/pdf")}
                    data = {
                        "assignment_title": "Test Assignment",
                        "assignment_marks": "100"  # String from form input
                    }
                    
                    print("📤 Sending request to /process-cbse-paper (frontend simulation)...")
                    response = await client.post("http://localhost:8000/process-cbse-paper", files=files, data=data)
                    
                    print(f"📥 Response status: {response.status_code}")
                    print(f"📥 Response headers: {dict(response.headers)}")
                    
                    if response.status_code == 422:
                        print("❌ Still getting 422 Unprocessable Entity error")
                        print(f"Response body: {response.text}")
                        return False
                    elif response.status_code == 200:
                        print("✅ Frontend simulation successful!")
                        result = response.json()
                        print(f"Response: {result}")
                        return True
                    else:
                        print(f"⚠️ Unexpected status code: {response.status_code}")
                        print(f"Response body: {response.text}")
                        return False
                        
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
                
    except Exception as e:
        print(f"❌ Error in frontend simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_different_content_types():
    """Test different content type scenarios"""
    print("\n🧪 Testing different content type scenarios...")
    
    try:
        test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test 1: With explicit content type
            print("Test 1: With explicit content type...")
            files = {"pdf_file": ("test.pdf", test_pdf_content, "application/pdf")}
            data = {"assignment_title": "Test 1", "assignment_marks": "100"}
            
            response = await client.post("http://localhost:8000/process-cbse-paper", files=files, data=data)
            print(f"Status: {response.status_code}")
            
            # Test 2: Without content type
            print("Test 2: Without content type...")
            files = {"pdf_file": ("test.pdf", test_pdf_content)}
            data = {"assignment_title": "Test 2", "assignment_marks": "100"}
            
            response = await client.post("http://localhost:8000/process-cbse-paper", files=files, data=data)
            print(f"Status: {response.status_code}")
            
            # Test 3: With different filename
            print("Test 3: With different filename...")
            files = {"pdf_file": ("document.pdf", test_pdf_content, "application/pdf")}
            data = {"assignment_title": "Test 3", "assignment_marks": "100"}
            
            response = await client.post("http://localhost:8000/process-cbse-paper", files=files, data=data)
            print(f"Status: {response.status_code}")
            
            return True
                
    except Exception as e:
        print(f"❌ Error in content type tests: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting frontend simulation tests...")
    
    # Test frontend simulation
    success1 = await test_frontend_simulation()
    
    # Test different content types
    success2 = await test_different_content_types()
    
    if success1 and success2:
        print("\n🎉 All frontend simulation tests passed!")
        print("The issue might be in the browser's file handling or a different part of the frontend.")
    else:
        print("\n❌ Some tests failed. The issue might be in the API endpoint.")
    
    return success1 and success2

if __name__ == "__main__":
    asyncio.run(main()) 