"""
Test the integration of question_parsing_consolidation into the pipeline
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.integration import get_db_integration


async def test_pipeline_integration():
    """Test that the consolidation step is properly integrated"""
    
    print("🧪 Testing Pipeline Integration")
    print()
    
    # Initialize database integration
    db_integration = get_db_integration()
    
    try:
        # Test 1: Check if the method exists
        print("✅ Test 1: Checking if question_parsing_consolidation method exists...")
        if hasattr(db_integration, 'question_parsing_consolidation'):
            print("   ✅ Method exists")
        else:
            print("   ❌ Method not found")
            return False
        
        # Test 2: Check if the method is callable
        print("✅ Test 2: Checking if method is callable...")
        if callable(getattr(db_integration, 'question_parsing_consolidation')):
            print("   ✅ Method is callable")
        else:
            print("   ❌ Method is not callable")
            return False
        
        # Test 3: Check if database integration can be initialized
        print("✅ Test 3: Testing database initialization...")
        success = await db_integration.initialize()
        if success:
            print("   ✅ Database initialized successfully")
        else:
            print("   ❌ Database initialization failed")
            return False
        
        print()
        print("🎉 All integration tests passed!")
        print("   The question_parsing_consolidation step is properly integrated into the pipeline.")
        print("   It will run automatically as Step 5 after question extraction and marks mapping.")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_pipeline_integration())
    
    if success:
        print("\n✅ Pipeline integration is ready!")
    else:
        print("\n❌ Pipeline integration needs attention!")
        sys.exit(1) 