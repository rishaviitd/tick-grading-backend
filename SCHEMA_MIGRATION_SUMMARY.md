# Schema Migration Summary: Assignment Schema Update Fix

## Issue Identified

The `question_content_id` and `marks_content_id` fields in the assignments collection were showing as `null` because the code was using the old save methods instead of the new methods that automatically update the assignment with the content IDs.

## Root Cause

In `app/question_parsing/question_extraction.py`, the code was calling:

- `db_integration.save_question_content()` instead of `db_integration.save_question_content_with_assignment_update()`
- `db_integration.save_marks_content()` instead of `db_integration.save_marks_content_with_assignment_update()`

## Fix Applied

### Updated Method Calls in `app/question_parsing/question_extraction.py`

**Before:**

```python
# Save question content to database with parsed questions
question_content_id = await db_integration.save_question_content(
    run_id=pipeline_run_id,
    questions_markdown=questions_markdown,
    extraction_success=True,
    raw_response=markdown_content,
    parsed_questions=structured_questions
)
```

**After:**

```python
# Save question content to database with parsed questions and update assignment
question_content_id = await db_integration.save_question_content_with_assignment_update(
    run_id=pipeline_run_id,
    questions_markdown=questions_markdown,
    assignment_id=assignment_id,  # Added assignment_id parameter
    extraction_success=True,
    raw_response=markdown_content,
    parsed_questions=structured_questions
)
```

**Before:**

```python
# Save marks mapping data to database
marks_mapping_id = await db_integration.save_marks_content(
    run_id=pipeline_run_id,
    marks_mapping=marks_json,
    total_questions=len(marks_json),
    mapping_success=True,
    raw_response=raw_response
)
```

**After:**

```python
# Save marks mapping data to database and update assignment
marks_mapping_id = await db_integration.save_marks_content_with_assignment_update(
    run_id=pipeline_run_id,
    marks_mapping=marks_json,
    total_questions=len(marks_json),
    assignment_id=assignment_id,  # Added assignment_id parameter
    mapping_success=True,
    raw_response=raw_response
)
```

## Expected Result

After this fix, when a new assignment is processed:

1. **Question content** will be saved to the `question_content` collection
2. **Assignment** will be automatically updated with the `question_content_id`
3. **Marks content** will be saved to the `marks_content` collection
4. **Assignment** will be automatically updated with the `marks_content_id`

The assignment document will now have this structure:

```json
{
  "_id": "6887cfe388d0b662df0b8c9f",
  "run_id": "8fba145bb9f0",
  "title": "PAPER-4",
  "total_marks": 50,
  "visual_content_id": "6887cff888d0b662df0b8ca8",
  "question_content_id": "6887cff888d0b662df0b8ca9", // Now populated
  "marks_content_id": "6887cff888d0b662df0b8caa", // Now populated
  "created_at": "2025-07-28T19:30:43.455Z",
  "updated_at": "2025-07-28T19:31:04.681Z"
}
```

## Testing

To verify the fix works:

1. Process a new PDF through the pipeline
2. Check that the assignment document has non-null values for `question_content_id` and `marks_content_id`
3. Verify that these IDs correspond to actual documents in the `question_content` and `marks_content` collections
