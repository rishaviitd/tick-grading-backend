"""
Database Cleanup Script

This script deletes all documents from collections except students and teachers.
Useful for cleaning up the database for testing purposes.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import pipeline_db, initialize_database
from database.schema import COLLECTION_NAMES


async def cleanup_database():
    """Delete all documents from collections except students and teachers"""
    
    print("🧹 Database Cleanup Script")
    print("This will delete all documents from collections except students and teachers.")
    print()
    
    # Collections to clean (exclude students and teachers)
    collections_to_clean = [
        "assignments",
        "questions", 
        "diagrams",
        "tables", 
        "visual_content",
        "question_content",
        "marks_content"
    ]
    
    try:
        # Initialize database
        print("📡 Initializing database connection...")
        await initialize_database()
        print("✅ Database connection initialized")
        print()
        
        # Confirm before proceeding
        print("⚠️  WARNING: This will delete ALL documents from the following collections:")
        for collection in collections_to_clean:
            print(f"   - {collection}")
        print()
        print("Collections that will be preserved:")
        print("   - students")
        print("   - teachers")
        print()
        
        # Get confirmation
        confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("❌ Cleanup cancelled")
            return False
        
        print()
        print("🗑️  Starting cleanup...")
        
        total_deleted = 0
        
        # Clean each collection
        for collection_name in collections_to_clean:
            try:
                collection = pipeline_db.db_manager.get_collection(collection_name)
                if collection is None:
                    print(f"⚠️  Collection '{collection_name}' not found, skipping...")
                    continue
                
                # Count documents before deletion
                count_before = await collection.count_documents({})
                
                if count_before == 0:
                    print(f"✅ {collection_name}: No documents to delete")
                    continue
                
                # Delete all documents
                result = await collection.delete_many({})
                deleted_count = result.deleted_count
                
                print(f"✅ {collection_name}: Deleted {deleted_count} documents")
                total_deleted += deleted_count
                
            except Exception as e:
                print(f"❌ Error cleaning {collection_name}: {e}")
        
        print()
        print(f"🎉 Cleanup completed!")
        print(f"📊 Total documents deleted: {total_deleted}")
        
        # Verify cleanup
        print()
        print("🔍 Verifying cleanup...")
        for collection_name in collections_to_clean:
            try:
                collection = pipeline_db.db_manager.get_collection(collection_name)
                if collection is not None:
                    count_after = await collection.count_documents({})
                    print(f"   - {collection_name}: {count_after} documents remaining")
                else:
                    print(f"   - {collection_name}: Collection not found")
            except Exception as e:
                print(f"   - {collection_name}: Error checking count - {e}")
        
        # Check preserved collections
        print()
        print("📋 Preserved collections:")
        preserved_collections = ["students", "teachers"]
        for collection_name in preserved_collections:
            try:
                collection = pipeline_db.db_manager.get_collection(collection_name)
                if collection is not None:
                    count = await collection.count_documents({})
                    print(f"   - {collection_name}: {count} documents")
                else:
                    print(f"   - {collection_name}: Collection not found")
            except Exception as e:
                print(f"   - {collection_name}: Error checking count - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False


async def show_collection_counts():
    """Show current document counts for all collections"""
    
    print("📊 Current Database Collection Counts")
    print()
    
    try:
        await initialize_database()
        
        all_collections = [
            "students",
            "teachers", 
            "assignments",
            "questions",
            "diagrams",
            "tables",
            "visual_content",
            "question_content",
            "marks_content"
        ]
        
        for collection_name in all_collections:
            try:
                collection = pipeline_db.db_manager.get_collection(collection_name)
                if collection is not None:
                    count = await collection.count_documents({})
                    print(f"   - {collection_name}: {count} documents")
                else:
                    print(f"   - {collection_name}: Collection not found")
            except Exception as e:
                print(f"   - {collection_name}: Error - {e}")
        
    except Exception as e:
        print(f"❌ Error getting collection counts: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database cleanup script")
    parser.add_argument("--show-counts", action="store_true", help="Show current collection counts without cleaning")
    parser.add_argument("--cleanup", action="store_true", help="Perform cleanup (requires confirmation)")
    
    args = parser.parse_args()
    
    if args.show_counts:
        asyncio.run(show_collection_counts())
    elif args.cleanup:
        success = asyncio.run(cleanup_database())
        if not success:
            sys.exit(1)
    else:
        print("Usage:")
        print("  python testing/cleanup_database.py --show-counts  # Show current counts")
        print("  python testing/cleanup_database.py --cleanup      # Perform cleanup")
        print()
        print("Examples:")
        print("  python testing/cleanup_database.py --show-counts")
        print("  python testing/cleanup_database.py --cleanup") 