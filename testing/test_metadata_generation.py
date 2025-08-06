#!/usr/bin/env python3
"""
Test file for metadata_gen.py - Testing with specific JSON input and image
This file tests the metadata generation functionality without modifying the original files.
"""

import json
import os
from pathlib import Path
from metadata_gen import generate_metadata, save_metadata

def test_metadata_generation():
    """
    Test metadata generation with the provided JSON data and image.
    """
    print("=" * 60)
    print("METADATA GENERATION TEST")
    print("=" * 60)
    
    # Test data provided by user
    test_json_data = {
        "ques_identifier": "Q1",
        "target_class": "10",
        "ques_text": "A backyard is in the shape of a triangle ABC with right angle at B . $\\mathrm{AB}=7 \\mathrm{~m}$ and $\\mathrm{BC}=15 \\mathrm{~m}$. A circular pit was dug inside it such that it touches the walls $\\mathrm{AC}, \\mathrm{BC}$ and AB at $\\mathrm{P}, \\mathrm{Q}$ and R respectively such that $\\mathrm{AP}=x \\mathrm{~m}$.\n\nBased on the above information, answer the following questions :\n(i) Find the length of AR in terms of $x$.\n(ii) Write the type of quadrilateral BQOR.",
        "marks": 4,
        "marks_analysis": "This question is a case-study-based question carrying 4 marks. It has three subparts: (i), (ii), and (iii). Subpart (i) carries 1 mark. Subpart (ii) carries 1 mark. Subpart (iii) has an internal choice between (a) and (b), both carrying 2 marks.",
        "question_type": "Case-Study"
    }
    
    # Image file path
    image_path = "2025_07_11_c38f0a0138022b907ba8g-1.jpg"
    
    # Check if image exists
    if not Path(image_path).exists():
        print(f"❌ Error: Image file not found: {image_path}")
        return None
    
    print(f"✓ Input JSON data loaded")
    print(f"✓ Image file found: {image_path}")
    print(f"✓ Question ID: {test_json_data['ques_identifier']}")
    print(f"✓ Question Type: {test_json_data['question_type']}")
    print(f"✓ Target Class: {test_json_data['target_class']}")
    print(f"✓ Marks: {test_json_data['marks']}")
    print("\n" + "=" * 60)
    print("GENERATING METADATA...")
    print("=" * 60)
    
    try:
        # Generate metadata using the metadata_gen.py function
        metadata = generate_metadata(
            json_input=test_json_data,
            md_filename="bloom_taxonomy_guide.md",
            stream=False,
            use_syllabus=True,
            image_paths=[image_path]
        )
        
        if metadata:
            print("\n" + "=" * 60)
            print("METADATA GENERATION SUCCESSFUL!")
            print("=" * 60)
            
            # Display the generated metadata
            print("\n📋 GENERATED METADATA:")
            print("-" * 40)
            print(json.dumps(metadata, indent=2, ensure_ascii=False))
            
            # Save to output file
            output_filename = "test_metadata_output.json"
            save_metadata(metadata, output_filename)
            
            print(f"\n✅ Test completed successfully!")
            print(f"✅ Results saved to: {output_filename}")
            
            return metadata
            
        else:
            print("\n❌ Error: No metadata generated")
            return None
            
    except Exception as e:
        print(f"\n❌ Error during metadata generation: {e}")
        return None


def main():
    """Main function to run the test."""
    print("Starting metadata generation test...")
    
    # Check if .env file exists or API key is set
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not found in environment variables.")
        print("   Make sure you have a .env file with GEMINI_API_KEY set.")
        print("   Example .env file:")
        print("   GEMINI_API_KEY=your_api_key_here")
        return
    
    # Run the test
    result = test_metadata_generation()
    
    if result:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")


if __name__ == "__main__":
    main() 