"""
Debug Question Parsing Consolidation

This script debugs the consolidation process step by step to find where diagram/table URL retrieval is failing.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.integration import get_db_integration


async def debug_consolidation():
    """Debug the consolidation process step by step"""
    
    # Parameters for the existing assignment
    run_id = "0843493f250f"
    assignment_id = "6887e5a38c080a1c05a16877"
    
    print("🔍 Debugging Question Parsing Consolidation")
    print(f"  - Run ID: {run_id}")
    print(f"  - Assignment ID: {assignment_id}")
    
    # Initialize database
    print("\n📡 Initializing database connection...")
    db_integration = get_db_integration()
    success = await db_integration.initialize()
    if not success:
        print("❌ Database initialization failed")
        return False
    
    print("✅ Database connection initialized")
    
    # Step 1: Get question content
    print("\n📖 Step 1: Getting question content...")
    question_content = await db_integration._get_question_content_by_run_id(run_id)
    if question_content:
        print(f"✅ Question content found: {len(question_content.get('questions', []))} questions")
    else:
        print("❌ Question content not found")
        return False
    
    # Step 2: Get marks mapping
    print("\n📊 Step 2: Getting marks mapping...")
    marks_mapping = await db_integration._get_marks_mapping_data(run_id)
    if marks_mapping:
        print(f"✅ Marks mapping found: {len(marks_mapping)} entries")
    else:
        print("❌ Marks mapping not found")
        return False
    
    # Step 3: Get visual content
    print("\n🖼️ Step 3: Getting visual content...")
    visual_content = await db_integration._get_visual_content_by_run_id(run_id)
    if visual_content:
        print(f"✅ Visual content found: {len(visual_content.get('diagrams', []))} diagrams, {len(visual_content.get('tables', []))} tables")
    else:
        print("❌ Visual content not found")
        return False
    
    # Step 4: Get diagrams
    print("\n📐 Step 4: Getting diagrams...")
    diagrams = await db_integration._get_diagrams_by_run_id(run_id)
    print(f"✅ Found {len(diagrams)} diagrams")
    
    for diagram in diagrams:
        print(f"  - {diagram['diagram_identifier']}: question_identifier={diagram.get('question_identifier')}, choice_location={diagram.get('choice_location')}")
    
    # Step 5: Get tables
    print("\n📋 Step 5: Getting tables...")
    tables = await db_integration._get_tables_by_run_id(run_id)
    print(f"✅ Found {len(tables)} tables")
    
    for table in tables:
        print(f"  - {table['table_identifier']}: question_identifier={table.get('question_identifier')}, choice_location={table.get('choice_location')}")
    
    # Step 6: Test URL retrieval for specific questions
    print("\n🔗 Step 6: Testing URL retrieval...")
    
    # Test question 21 (should have figure-1)
    diagram_url_21 = await db_integration._get_diagram_url_for_question("21", None, diagrams)
    table_url_21 = await db_integration._get_table_url_for_question("21", None, tables)
    print(f"Question 21: diagram_url={diagram_url_21}, table_url={table_url_21}")
    
    # Test question 9 (should have table-1)
    diagram_url_9 = await db_integration._get_diagram_url_for_question("9", None, diagrams)
    table_url_9 = await db_integration._get_table_url_for_question("9", None, tables)
    print(f"Question 9: diagram_url={diagram_url_9}, table_url={table_url_9}")
    
    # Test question 25 (should have figure-3 with choice_location=second)
    diagram_url_25 = await db_integration._get_diagram_url_for_question("25", "second", diagrams)
    table_url_25 = await db_integration._get_table_url_for_question("25", "second", tables)
    print(f"Question 25 (second choice): diagram_url={diagram_url_25}, table_url={table_url_25}")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(debug_consolidation())
    if success:
        print("\n🎉 Debug completed successfully!")
    else:
        print("\n❌ Debug failed!")
        sys.exit(1) 