# Question Parsing Consolidation - Final Implementation

## Overview

The `question_parsing_consolidation` function is the final step in the question processing pipeline. It takes the parsed question content from the database and creates individual question documents with proper diagram/table mapping, then updates the assignment with a questions array.

## Implementation Details

### 1. **Main Function: `question_parsing_consolidation`**

**Location**: `database/integration.py`

**Purpose**: Process question content and create individual question documents with proper visual content mapping.

**Parameters**:

- `run_id: str` - The unique run identifier
- `assignment_id: str` - The assignment ID to update

**Returns**: `bool` - Success status

### 2. **Processing Steps**

#### Step 1: Get Question Content

```python
question_content = await self._get_question_content_by_run_id(run_id)
```

- Retrieves the parsed question content from the `question_content` collection
- Contains the `questions` array with `has_internal_choice` flags

#### Step 2: Get Visual Content

```python
visual_content = await self._get_visual_content_by_run_id(run_id)
tables = await self._get_tables_by_run_id(run_id)
diagrams = await self._get_diagrams_by_run_id(run_id)
```

- Retrieves visual content, tables, and diagrams for URL mapping

#### Step 3: Process Each Question

For each question in the question content:

**For Internal Choice Questions** (`has_internal_choice: true`):

- Split question text by `[%OR%]` to get two sub-questions
- Create separate question documents for each sub-question
- Map diagrams/tables based on `choice_location` ("first", "second")
- Add to assignment with array of question IDs

**For Regular Questions** (`has_internal_choice: false`):

- Create single question document
- Map diagrams/tables based on `question_identifier`
- Add to assignment with single question ID

#### Step 4: Update Assignment

```python
success = await self._update_assignment_questions_array(assignment_id, assignment_questions)
```

- Updates the assignment with the questions array

### 3. **New Database Schema**

#### SimpleQuestion Schema

```python
class SimpleQuestion(BaseModel):
    question_text: str
    question_marks: str
    diagram_url: Optional[str]
    table_url: Optional[str]
    created_at: datetime
    updated_at: datetime
```

#### Updated Assignment Schema

```python
class Assignment(BaseModel):
    # ... existing fields ...
    questions: Optional[List[Dict[str, Any]]]  # New field
```

### 4. **Database Collections**

- **`simple_questions`** - Stores individual question documents
- **`assignments`** - Updated with questions array
- **`question_content`** - Source of parsed questions
- **`diagrams`** - Source of diagram URLs and mappings
- **`tables`** - Source of table URLs and mappings

## Example Output

### Assignment Document

```json
{
  "_id": "6887cfe388d0b662df0b8c9f",
  "run_id": "5bec1d2b655b",
  "title": "PAPER-4",
  "total_marks": 50,
  "visual_content_id": "6887b9194c15665baf8696fa",
  "question_content_id": "6887d0fdef19511b87547b48",
  "marks_content_id": "6887cff888d0b662df0b8caa",
  "questions": [
    {
      "question_identifier": "1",
      "question_id": "6887cff888d0b662df0b8cb0"
    },
    {
      "question_identifier": "9",
      "question_id": "6887cff888d0b662df0b8cb8"
    },
    {
      "question_identifier": "22",
      "question_id": ["6887cff888d0b662df0b8cb9", "6887cff888d0b662df0b8cba"]
    },
    {
      "question_identifier": "25",
      "question_id": ["6887cff888d0b662df0b8cbb", "6887cff888d0b662df0b8cbc"]
    }
  ]
}
```

### Simple Question Documents

```json
// Question 1 (single question)
{
  "_id": "6887cff888d0b662df0b8cb0",
  "question_text": "The LCM of two numbers is 14 times their HCF...",
  "question_marks": "1 mark",
  "diagram_url": null,
  "table_url": null
}

// Question 22a (first choice)
{
  "_id": "6887cff888d0b662df0b8cb9",
  "question_text": "Find A and B, if sin (A + 2B) = √3/2 and cos (A + B) = 1/2.",
  "question_marks": "2 marks",
  "diagram_url": null,
  "table_url": null
}

// Question 25b (second choice with diagram)
{
  "_id": "6887cff888d0b662df0b8cbc",
  "question_text": "In the below figure, OACB is a quadrant of a circle...",
  "question_marks": "2 marks",
  "diagram_url": "https://res.cloudinary.com/.../figure_25.png",
  "table_url": null
}
```

## Usage

### 1. **Call the Function**

```python
from database.integration import get_db_integration

db_integration = get_db_integration()
success = await db_integration.question_parsing_consolidation(
    run_id="5bec1d2b655b",
    assignment_id="6887cfe388d0b662df0b8c9f"
)
```

### 2. **Integration with Pipeline**

This function should be called after:

- Question content is saved (`save_question_content_with_assignment_update`)
- Marks content is saved (`save_marks_content_with_assignment_update`)
- Visual content mapping is completed (`update_visual_content_mapping`)

### 3. **Testing**

Use the test file: `testing/test_question_parsing_consolidation.py`

## Key Features

1. **Internal Choice Detection**: Automatically detects and splits questions with `[%OR%]` markers
2. **Visual Content Mapping**: Maps diagrams and tables to questions based on `question_identifier` and `choice_location`
3. **Flexible Question IDs**: Supports both single question IDs and arrays for internal choice
4. **Error Handling**: Comprehensive error handling with detailed logging
5. **Database Consistency**: Maintains referential integrity across collections

## Benefits

1. **Simplified Question Access**: Each question is a separate document with clean structure
2. **Visual Content Integration**: Direct access to diagram/table URLs for each question
3. **Internal Choice Support**: Proper handling of questions with multiple choices
4. **Scalable Architecture**: Easy to extend with additional question metadata
5. **Performance**: Efficient queries and updates with proper indexing

## Next Steps

1. **Integration**: Add this function call to the main processing pipeline
2. **Testing**: Run comprehensive tests with real question papers
3. **Optimization**: Add caching and performance optimizations if needed
4. **Monitoring**: Add metrics and monitoring for the consolidation process
