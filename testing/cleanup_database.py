#!/usr/bin/env python3
"""
Script to clean up database by deleting assignments, questions, diagram mapping, and marks mapping data.
This will help reset the database state for testing purposes.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import pipeline_db, COLLECTION_NAMES
from database.integration import get_db_integration

async def cleanup_database():
    """Clean up all data from the database except teachers and students collections"""
    print("🧹 Starting database cleanup...")
    
    try:
        # Initialize database connection
        await pipeline_db.db_manager.connect()
        print("✅ Connected to database")
        
        # Get all collections except teachers and students
        collections_to_clean = [
            "assignments",
            "questions", 
            "student_assignment_responses",
            "question_response_mappings",
            "diagram_mapping_results",
            "marks_mapping_results",
            "pipeline_results",
            "diagram_extraction_results",
            "question_extraction_results"
        ]
        
        total_deleted = 0
        
        for collection_name in collections_to_clean:
            try:
                collection = pipeline_db.db_manager.get_collection(collection_name)
                if collection is None:
                    print(f"⚠️  Collection '{collection_name}' not found, skipping...")
                    continue
                
                # Count documents before deletion
                count_before = await collection.count_documents({})
                
                if count_before == 0:
                    print(f"📭 Collection '{collection_name}' is already empty")
                    continue
                
                # Delete all documents in the collection
                result = await collection.delete_many({})
                deleted_count = result.deleted_count
                total_deleted += deleted_count
                
                print(f"🗑️  Deleted {deleted_count} documents from '{collection_name}' (was {count_before})")
                
            except Exception as e:
                print(f"❌ Error cleaning collection '{collection_name}': {e}")
        
        print(f"\n🎉 Database cleanup completed!")
        print(f"📊 Total documents deleted: {total_deleted}")
        
        # Show remaining data
        print(f"\n📋 Remaining data summary:")
        remaining_collections = [
            "teachers",
            "students"
        ]
        
        for collection_name in remaining_collections:
            try:
                collection = pipeline_db.db_manager.get_collection(collection_name)
                if collection is not None:
                    count = await collection.count_documents({})
                    print(f"   📁 {collection_name}: {count} documents")
            except Exception as e:
                print(f"   ❌ Error checking {collection_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during database cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close database connection
        await pipeline_db.db_manager.disconnect()
        print("🔌 Database connection closed")

async def cleanup_specific_run(run_id: str):
    """Clean up data for a specific run_id"""
    print(f"🧹 Cleaning up data for run_id: {run_id}")
    
    try:
        # Initialize database connection
        await pipeline_db.db_manager.connect()
        print("✅ Connected to database")
        
        collections_to_clean = [
            "assignments",
            "questions",
            "student_assignment_responses", 
            "question_response_mappings",
            "diagram_mapping_results",
            "marks_mapping_results",
            "pipeline_results",
            "diagram_extraction_results",
            "question_extraction_results"
        ]
        
        total_deleted = 0
        
        for collection_name in collections_to_clean:
            try:
                collection = pipeline_db.db_manager.get_collection(collection_name)
                if collection is None:
                    print(f"⚠️  Collection '{collection_name}' not found, skipping...")
                    continue
                
                # Count documents before deletion
                count_before = await collection.count_documents({"run_id": run_id})
                
                if count_before == 0:
                    print(f"📭 No documents found in '{collection_name}' for run_id '{run_id}'")
                    continue
                
                # Delete documents for this run_id
                result = await collection.delete_many({"run_id": run_id})
                deleted_count = result.deleted_count
                total_deleted += deleted_count
                
                print(f"🗑️  Deleted {deleted_count} documents from '{collection_name}' for run_id '{run_id}'")
                
            except Exception as e:
                print(f"❌ Error cleaning collection '{collection_name}': {e}")
        
        print(f"\n🎉 Run-specific cleanup completed!")
        print(f"📊 Total documents deleted: {total_deleted}")
        return True
        
    except Exception as e:
        print(f"❌ Error during run-specific cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close database connection
        await pipeline_db.db_manager.disconnect()
        print("🔌 Database connection closed")

async def show_database_status():
    """Show current database status"""
    print("📊 Database Status Report")
    print("=" * 50)
    
    try:
        # Initialize database connection
        await pipeline_db.db_manager.connect()
        print("✅ Connected to database")
        
        all_collections = [
            "pipeline_results",
            "assignments",
            "questions",
            "student_assignment_responses",
            "question_response_mappings",
            "diagram_extraction_results",
            "diagram_mapping_results", 
            "question_extraction_results",
            "marks_mapping_results",
            "teachers",
            "students"
        ]
        
        total_documents = 0
        
        for collection_name in all_collections:
            try:
                collection = pipeline_db.db_manager.get_collection(collection_name)
                if collection is not None:
                    count = await collection.count_documents({})
                    total_documents += count
                    
                    if count > 0:
                        print(f"📁 {collection_name}: {count} documents")
                        
                        # Show sample data for non-empty collections
                        if count <= 5:
                            cursor = collection.find().limit(3)
                            docs = await cursor.to_list(length=3)
                            for i, doc in enumerate(docs):
                                run_id = doc.get('run_id', 'N/A')
                                created_at = doc.get('created_at', 'N/A')
                                if isinstance(created_at, datetime):
                                    created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
                                print(f"     {i+1}. run_id: {run_id}, created: {created_at}")
                        else:
                            print(f"     (showing first 3 of {count} documents)")
                            cursor = collection.find().limit(3)
                            docs = await cursor.to_list(length=3)
                            for i, doc in enumerate(docs):
                                run_id = doc.get('run_id', 'N/A')
                                created_at = doc.get('created_at', 'N/A')
                                if isinstance(created_at, datetime):
                                    created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
                                print(f"     {i+1}. run_id: {run_id}, created: {created_at}")
                    else:
                        print(f"📁 {collection_name}: 0 documents")
                        
            except Exception as e:
                print(f"❌ Error checking {collection_name}: {e}")
        
        print(f"\n📊 Total documents across all collections: {total_documents}")
        
    except Exception as e:
        print(f"❌ Error getting database status: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connection
        await pipeline_db.db_manager.disconnect()
        print("🔌 Database connection closed")

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database cleanup utility")
    parser.add_argument("--action", choices=["cleanup", "status", "cleanup-run"], 
                       default="cleanup", help="Action to perform")
    parser.add_argument("--run-id", help="Specific run_id to clean up (for cleanup-run action)")
    
    args = parser.parse_args()
    
    if args.action == "cleanup":
        print("🚀 Starting full database cleanup...")
        success = await cleanup_database()
        if success:
            print("\n✅ Database cleanup completed successfully!")
        else:
            print("\n❌ Database cleanup failed!")
    
    elif args.action == "cleanup-run":
        if not args.run_id:
            print("❌ Please provide a run_id with --run-id")
            return
        print(f"🚀 Starting cleanup for run_id: {args.run_id}")
        success = await cleanup_specific_run(args.run_id)
        if success:
            print(f"\n✅ Cleanup for run_id '{args.run_id}' completed successfully!")
        else:
            print(f"\n❌ Cleanup for run_id '{args.run_id}' failed!")
    
    elif args.action == "status":
        print("🚀 Getting database status...")
        await show_database_status()
    
    else:
        print("❌ Invalid action specified")

if __name__ == "__main__":
    asyncio.run(main()) 