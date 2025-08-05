"""
Test script to verify Cloudinary URLs are being saved to the database correctly
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.connection import pipeline_db, initialize_database
from database.schema import VisualContent
from datetime import datetime


async def test_cloudinary_save():
    """Test that Cloudinary URLs are saved to the database correctly"""
    
    print("🧪 Testing Cloudinary URL save to database...")
    
    # Initialize database
    success = await initialize_database()
    if not success:
        print("❌ Failed to initialize database")
        return False
    
    # Test data
    test_run_id = "test_cloudinary_123"
    test_figures = [
        {
            "cloudinary_url": "https://res.cloudinary.com/test/image/upload/v1234567890/test_figure_1.png",
            "page_number": 1,
            "figure_id": 1,
            "file_name": "test_figure_1.png",
            "figure_counter": 1
        },
        {
            "cloudinary_url": "https://res.cloudinary.com/test/image/upload/v1234567890/test_figure_2.png",
            "page_number": 2,
            "figure_id": 1,
            "file_name": "test_figure_2.png",
            "figure_counter": 2
        }
    ]
    
    test_overview_url = "https://res.cloudinary.com/test/image/upload/v1234567890/test_overview_figures.png"
    
    try:
        # Create test extraction result
        extraction_result = DiagramExtractionResult(
            run_id=test_run_id,
            total_figures=2,
            pages_processed=2,
            extraction_success=True,
            figures=test_figures,
            tables=[],  # Empty for now
            overview_image_figures=test_overview_url,
            overview_image_tables=None,  # None for now
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        save_success = await pipeline_db.save_diagram_extraction(extraction_result)
        
        if not save_success:
            print("❌ Failed to save extraction result to database")
            return False
        
        print("✅ Successfully saved extraction result to database")
        
        # Retrieve and verify the saved data
        collection = pipeline_db.db_manager.get_collection("diagram_extraction_results")
        if collection is None:
            print("❌ Could not get diagram_extraction_results collection")
            return False
        
        # Find the saved document
        saved_doc = await collection.find_one({"run_id": test_run_id})
        
        if not saved_doc:
            print("❌ Could not find saved document in database")
            return False
        
        print("✅ Found saved document in database")
        
        # Verify the data structure
        print(f"📊 Document ID: {saved_doc['_id']}")
        print(f"📊 Run ID: {saved_doc['run_id']}")
        print(f"📊 Total Figures: {saved_doc['total_figures']}")
        print(f"📊 Pages Processed: {saved_doc['pages_processed']}")
        print(f"📊 Extraction Success: {saved_doc['extraction_success']}")
        
        # Verify figures array
        if 'figures' in saved_doc:
            print(f"📊 Figures count: {len(saved_doc['figures'])}")
            for i, figure in enumerate(saved_doc['figures']):
                print(f"  Figure {i+1}:")
                print(f"    URL: {figure.get('cloudinary_url', 'MISSING')}")
                print(f"    Page: {figure.get('page_number', 'MISSING')}")
                print(f"    ID: {figure.get('figure_id', 'MISSING')}")
        else:
            print("❌ Figures array not found in saved document")
            return False
        
        # Verify overview image
        if 'overview_image_figures' in saved_doc:
            print(f"📊 Overview Image URL: {saved_doc['overview_image_figures']}")
        else:
            print("❌ Overview image URL not found in saved document")
            return False
        
        # Verify tables array (should be empty)
        if 'tables' in saved_doc:
            print(f"📊 Tables count: {len(saved_doc['tables'])}")
        else:
            print("❌ Tables array not found in saved document")
            return False
        
        print("✅ All Cloudinary URLs and data structure verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup_test_data():
    """Clean up test data from database"""
    try:
        collection = pipeline_db.db_manager.get_collection("diagram_extraction_results")
        if collection:
            result = await collection.delete_one({"run_id": "test_cloudinary_123"})
            if result.deleted_count > 0:
                print("🧹 Cleaned up test data from database")
            else:
                print("🧹 No test data found to clean up")
    except Exception as e:
        print(f"⚠️ Error cleaning up test data: {str(e)}")


async def main():
    """Main test function"""
    print("🚀 Starting Cloudinary URL save test...")
    
    try:
        # Run the test
        success = await test_cloudinary_save()
        
        if success:
            print("🎉 Test completed successfully!")
        else:
            print("💥 Test failed!")
            
    finally:
        # Clean up test data
        await cleanup_test_data()
        
        # Close database connection
        await pipeline_db.db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main()) 