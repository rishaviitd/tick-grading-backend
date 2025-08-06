#!/usr/bin/env python3
"""
Test script for validating the updated rubric schemas against example files.

This script tests each question category to ensure the schema changes are working correctly.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# Add the root directory to the path to import the schema
sys.path.append(str(Path(__file__).parent.parent))

from database.schema import (
    MCQRubric, 
    AssertionReasonRubric, 
    SubjectiveRubric, 
    CaseStudyRubric, 
    InternalChoiceRubric,
    MarkingPoint,
    Method,
    CaseStudyPart
)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and return JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return None


def test_mcq_rubric():
    """Test MCQ rubric schema validation."""
    print("\n🧪 Testing MCQ Rubric Schema...")
    
    # Load the example MCQ marking scheme
    mcq_file = "app/rubric_generation/example/8-MCQ_example/marking_scheme/8_marking_scheme.json"
    data = load_json_file(mcq_file)
    
    if not data:
        return False
    
    try:
        # Validate against MCQ rubric schema
        mcq_rubric = MCQRubric(**data)
        print(f"✅ MCQ Rubric validation successful!")
        print(f"   - Correct option: {mcq_rubric.correct_option}")
        print(f"   - Acceptable answers: {mcq_rubric.acceptable_answers}")
        print(f"   - Solution length: {len(mcq_rubric.solution)} characters")
        return True
    except Exception as e:
        print(f"❌ MCQ Rubric validation failed: {e}")
        return False


def test_assertion_reason_rubric():
    """Test Assertion-Reason rubric schema validation."""
    print("\n🧪 Testing Assertion-Reason Rubric Schema...")
    
    # Load the example Assertion-Reason marking scheme
    ar_file = "app/rubric_generation/example/19 (A-R)/marking_scheme/19_marking_scheme.json"
    data = load_json_file(ar_file)
    
    if not data:
        return False
    
    try:
        # Validate against Assertion-Reason rubric schema
        ar_rubric = AssertionReasonRubric(**data)
        print(f"✅ Assertion-Reason Rubric validation successful!")
        print(f"   - Correct option: {ar_rubric.correct_option}")
        print(f"   - Acceptable answers: {ar_rubric.acceptable_answers}")
        print(f"   - Solution length: {len(ar_rubric.solution)} characters")
        return True
    except Exception as e:
        print(f"❌ Assertion-Reason Rubric validation failed: {e}")
        return False


def test_subjective_rubric():
    """Test Subjective rubric schema validation."""
    print("\n🧪 Testing Subjective Rubric Schema...")
    
    # Load the example Subjective marking scheme
    subj_file = "app/rubric_generation/example/32-Subjective/marking_scheme/32_marking_scheme.json"
    data = load_json_file(subj_file)
    
    if not data:
        return False
    
    try:
        # Validate against Subjective rubric schema
        subj_rubric = SubjectiveRubric(**data)
        print(f"✅ Subjective Rubric validation successful!")
        print(f"   - Number of methods: {len(subj_rubric.methods)}")
        print(f"   - Method names: {[method.methodName for method in subj_rubric.methods]}")
        print(f"   - Total marking points: {sum(len(method.markingPoints) for method in subj_rubric.methods)}")
        print(f"   - Notes length: {len(subj_rubric.Question_specific_notes)} characters")
        return True
    except Exception as e:
        print(f"❌ Subjective Rubric validation failed: {e}")
        return False


def test_case_study_rubric():
    """Test Case Study rubric schema validation."""
    print("\n🧪 Testing Case Study Rubric Schema...")
    
    # Load the example Case Study marking scheme
    case_file = "app/rubric_generation/example/30- Case-Study/marking_scheme/30_marking_scheme.json"
    data = load_json_file(case_file)
    
    if not data:
        return False
    
    try:
        # Validate against Case Study rubric schema
        case_rubric = CaseStudyRubric(**data)
        print(f"✅ Case Study Rubric validation successful!")
        print(f"   - Number of parts: {len(case_rubric.parts)}")
        print(f"   - Part labels: {[part.part_label for part in case_rubric.parts]}")
        print(f"   - Total methods across parts: {sum(len(part.methods) for part in case_rubric.parts)}")
        print(f"   - Notes length: {len(case_rubric.Question_specific_notes)} characters")
        return True
    except Exception as e:
        print(f"❌ Case Study Rubric validation failed: {e}")
        return False


def test_internal_choice_rubric():
    """Test Internal Choice rubric schema validation."""
    print("\n🧪 Testing Internal Choice Rubric Schema...")
    
    # Load both primary and secondary marking schemes
    primary_file = "app/rubric_generation/example/23-internal_choice/marking_scheme/23_primary_marking_scheme.json"
    secondary_file = "app/rubric_generation/example/23-internal_choice/marking_scheme/23_secondary_marking_scheme.json"
    
    primary_data = load_json_file(primary_file)
    secondary_data = load_json_file(secondary_file)
    
    if not primary_data or not secondary_data:
        return False
    
    try:
        # Create subjective rubrics for both choices
        primary_rubric = SubjectiveRubric(**primary_data)
        secondary_rubric = SubjectiveRubric(**secondary_data)
        
        # Create internal choice rubric
        ic_rubric = InternalChoiceRubric(
            primary_rubric=primary_rubric,
            secondary_rubric=secondary_rubric
        )
        
        print(f"✅ Internal Choice Rubric validation successful!")
        print(f"   - Primary methods: {len(ic_rubric.primary_rubric.methods)}")
        print(f"   - Secondary methods: {len(ic_rubric.secondary_rubric.methods)}")
        print(f"   - Primary method names: {[m.methodName for m in ic_rubric.primary_rubric.methods]}")
        print(f"   - Secondary method names: {[m.methodName for m in ic_rubric.secondary_rubric.methods]}")
        return True
    except Exception as e:
        print(f"❌ Internal Choice Rubric validation failed: {e}")
        return False


def test_marking_point_schema():
    """Test individual MarkingPoint schema validation."""
    print("\n🧪 Testing MarkingPoint Schema...")
    
    # Create a sample marking point
    sample_marking_point = {
        "stepId": "test_1",
        "MarkType": "B",
        "marks": "0.5",
        "Teacher_Expectation": "Test expectation",
        "Pass_if": "Test pass criteria",
        "Fail_if": "Test fail criteria",
        "guidance": "Test guidance"
    }
    
    try:
        marking_point = MarkingPoint(**sample_marking_point)
        print(f"✅ MarkingPoint validation successful!")
        print(f"   - Step ID: {marking_point.stepId}")
        print(f"   - Mark Type: {marking_point.MarkType}")
        print(f"   - Marks: {marking_point.marks}")
        return True
    except Exception as e:
        print(f"❌ MarkingPoint validation failed: {e}")
        return False


def test_method_schema():
    """Test Method schema validation."""
    print("\n🧪 Testing Method Schema...")
    
    # Create a sample method with marking points
    sample_method = {
        "methodName": "Test Method",
        "markingPoints": [
            {
                "stepId": "1",
                "MarkType": "B",
                "marks": "0.5",
                "Teacher_Expectation": "Test expectation 1",
                "Pass_if": "Test pass criteria 1",
                "Fail_if": "Test fail criteria 1",
                "guidance": "Test guidance 1"
            },
            {
                "stepId": "2",
                "MarkType": "M",
                "marks": "1",
                "Teacher_Expectation": "Test expectation 2",
                "Pass_if": "Test pass criteria 2",
                "Fail_if": "Test fail criteria 2",
                "guidance": "Test guidance 2"
            }
        ]
    }
    
    try:
        method = Method(**sample_method)
        print(f"✅ Method validation successful!")
        print(f"   - Method name: {method.methodName}")
        print(f"   - Number of marking points: {len(method.markingPoints)}")
        return True
    except Exception as e:
        print(f"❌ Method validation failed: {e}")
        return False


def test_schema_compatibility():
    """Test that the schema is compatible with the Question model."""
    print("\n🧪 Testing Schema Compatibility with Question Model...")
    
    try:
        from database.schema import Question
        
        # Test MCQ question with rubric
        mcq_data = load_json_file("app/rubric_generation/example/8-MCQ_example/marking_scheme/8_marking_scheme.json")
        mcq_rubric = MCQRubric(**mcq_data)
        
        question = Question(
            question_text="8. If tangents PA and PB drawn from an external point P...",
            question_marks=1.0,
            question_marks_analysis="[1] mark",
            question_type="MCQ",
            rubric=mcq_rubric
        )
        
        print(f"✅ Question with MCQ rubric validation successful!")
        print(f"   - Question type: {question.question_type}")
        print(f"   - Rubric type: {type(question.rubric).__name__}")
        print(f"   - Rubric validation: {question.validate_rubric_type()}")
        
        # Test Subjective question with rubric
        subj_data = load_json_file("app/rubric_generation/example/32-Subjective/marking_scheme/32_marking_scheme.json")
        subj_rubric = SubjectiveRubric(**subj_data)
        
        question2 = Question(
            question_text="32. The perimeter of an isosceles triangle...",
            question_marks=5.0,
            question_marks_analysis="[5] marks",
            question_type="Normal Subjective",
            rubric=subj_rubric
        )
        
        print(f"✅ Question with Subjective rubric validation successful!")
        print(f"   - Question type: {question2.question_type}")
        print(f"   - Rubric type: {type(question2.rubric).__name__}")
        print(f"   - Rubric validation: {question2.validate_rubric_type()}")
        
        return True
    except Exception as e:
        print(f"❌ Schema compatibility test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Rubric Schema Tests...")
    print("=" * 50)
    
    test_results = []
    
    # Test individual schemas
    test_results.append(("MarkingPoint", test_marking_point_schema()))
    test_results.append(("Method", test_method_schema()))
    test_results.append(("MCQ", test_mcq_rubric()))
    test_results.append(("Assertion-Reason", test_assertion_reason_rubric()))
    test_results.append(("Subjective", test_subjective_rubric()))
    test_results.append(("Case Study", test_case_study_rubric()))
    test_results.append(("Internal Choice", test_internal_choice_rubric()))
    test_results.append(("Schema Compatibility", test_schema_compatibility()))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Schema validation is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the schema implementation.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 