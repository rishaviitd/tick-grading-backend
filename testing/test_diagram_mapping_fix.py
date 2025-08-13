#!/usr/bin/env python3
"""
Test script to verify the diagram mapping fix.
This script tests that diagrams are properly saved with run_id and can be found during mapping.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.integration import get_db_integration
from database.schema import Diagram, Table

async def test_diagram_mapping_fix():
    """Test the diagram mapping fix"""
    print("🧪 Testing diagram mapping fix...")
    
    # Initialize database integration
    db_integration = get_db_integration()
    await db_integration.initialize()
    
    # Test data
    test_run_id = "test_diagram_mapping_fix"
    test_diagram_url = "https://res.cloudinary.com/test/test_diagram.png"
    test_diagram_identifier = "figure-1"
    
    try:
        # Step 1: Save a test diagram with run_id
        print(f"📝 Saving test diagram with run_id: {test_run_id}")
        diagram_id = await db_integration.save_diagram(
            diagram_url=test_diagram_url,
            diagram_identifier=test_diagram_identifier,
            run_id=test_run_id
        )
        
        if not diagram_id:
            print("❌ Failed to save test diagram")
            return False
        
        print(f"✅ Test diagram saved with ID: {diagram_id}")
        
        # Step 2: Test mapping update
        print("🔄 Testing diagram mapping update...")
        mapping_data = {
            "figures": {
                "figure-1": {
                    "question_identifier": "19",
                    "choice_location": "null"
                }
            },
            "tables": {}
        }
        
        success = await db_integration.update_visual_content_mapping(mapping_data, test_run_id)
        
        if success:
            print("✅ Diagram mapping update successful")
        else:
            print("❌ Diagram mapping update failed")
            return False
        
        # Step 3: Verify the update worked by checking the database
        print("🔍 Verifying database update...")
        from database.connection import pipeline_db
        
        # Get the diagram from database
        diagram = await pipeline_db.get_diagram_by_identifier(test_diagram_identifier, test_run_id)
        
        if diagram:
            question_identifier = diagram.get("question_identifier")
            choice_location = diagram.get("choice_location")
            
            print(f"📊 Diagram found:")
            print(f"   - ID: {diagram.get('_id')}")
            print(f"   - Run ID: {diagram.get('run_id')}")
            print(f"   - Question Identifier: {question_identifier}")
            print(f"   - Choice Location: {choice_location}")
            
            if question_identifier == "19" and choice_location == "null":
                print("✅ Diagram mapping verification successful!")
                return True
            else:
                print("❌ Diagram mapping verification failed - values don't match expected")
                return False
        else:
            print("❌ Could not find diagram in database")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        # Clean up test data
        try:
            from database.connection import pipeline_db
            from bson import ObjectId
            
            # Delete test diagram
            if 'diagram_id' in locals():
                collection = pipeline_db.db_manager.get_collection("diagrams")
                if collection:
                    await collection.delete_one({"_id": ObjectId(diagram_id)})
                    print(f"🧹 Cleaned up test diagram: {diagram_id}")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

async def main():
    """Main test function"""
    print("🚀 Starting diagram mapping fix test...")
    
    success = await test_diagram_mapping_fix()
    
    if success:
        print("\n🎉 All tests passed! The diagram mapping fix is working correctly.")
        print("\n📋 Summary of fixes:")
        print("   ✅ Added run_id field to Diagram and Table schemas")
        print("   ✅ Updated save_diagram and save_table functions to include run_id")
        print("   ✅ Updated get_diagram_by_identifier and get_table_by_identifier to search by run_id")
        print("   ✅ Updated update_visual_content_mapping to use run_id for lookups")
        print("   ✅ Updated pipeline to pass run_id to mapping function")
    else:
        print("\n💥 Tests failed! The diagram mapping fix needs more work.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
