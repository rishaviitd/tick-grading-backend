# New Database Schema Guide

## Overview

The TickAI backend has been updated with a new database schema that properly separates core business logic entities from pipeline processing data. This new structure makes it easier to manage teachers, students, assignments, and their relationships.

## New Schema Structure

### Core Business Logic Collections

#### 1. **Teacher Collection**

```json
{
  "_id": "teacher_001",
  "name": "Rishav Kumar",
  "class_name": "10",
  "board": "CBSE",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 2. **Student Collection**

```json
{
  "_id": "student_001",
  "name": "Shristi Jain",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 3. **Assignment Collection**

```json
{
  "_id": "assignment_001",
  "run_id": "4e92705bd303",
  "questions": ["question_001", "question_002", "question_003"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 4. **Question Collection**

```json
{
  "_id": "question_001",
  "assignment_id": "assignment_001",
  "run_id": "4e92705bd303",
  "question_identifier": "1",
  "has_internal_choice": false,
  "primary_question": "1. If two positive integers a and b are written as a = x²y² and b = xy³, where x and y are prime numbers, then the HCF (a, b) is:\n(a) xy\n(b) xy²\n(c) x³y³\n(d) x2y2",
  "secondary_question": null,
  "primary_diagram_url": null,
  "secondary_diagram_url": null,
  "table_url": null,
  "primary_marks": "1 mark",
  "secondary_marks": null,
  "question_type": "MCQ",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 5. **Student Assignment Response Collection**

```json
{
  "_id": "response_001",
  "student_id": "student_001",
  "assignment_id": "assignment_001",
  "run_id": "2ca2e9a229b6",
  "student_responses": [
    {
      "question_identifier": "1",
      "cloudinary_url": "https://res.cloudinary.com/de19ckse5/image/upload/v1753391510/wipiwotuohhnjzysirnr.jpg"
    },
    {
      "question_identifier": "15",
      "cloudinary_url": "https://res.cloudinary.com/de19ckse5/image/upload/v1753391510/ei2hpaodieiamo4kexbg.jpg"
    }
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 6. **Question Response Mapping Collection**

```json
{
  "_id": "mapping_001",
  "student_id": "student_001",
  "assignment_id": "assignment_001",
  "run_id": "2ca2e9a229b6",
  "question_identifier": "1",
  "has_internal_choice": false,
  "primary_question": "1. If two positive integers a and b are written as a = x²y² and b = xy³, where x and y are prime numbers, then the HCF (a, b) is:\n(a) xy\n(b) xy²\n(c) x³y³\n(d) x2y2",
  "primary_marks": "1 mark",
  "question_type": "MCQ",
  "response_cloudinary_url": "https://res.cloudinary.com/de19ckse5/image/upload/v1753391510/wipiwotuohhnjzysirnr.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## Key Changes

### 1. **Student Information in POST Requests**

The `/crop-margins` endpoint now accepts and stores student information:

```json
{
  "urls": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
  "assignment_id": "assignment_001",
  "student_id": "student_001",
  "student_name": "Shristi Jain"
}
```

### 2. **Assignment-Based Organization**

- Questions are now linked to assignments via `assignment_id`
- Student responses are organized by assignment
- This allows for better organization and querying

### 3. **Direct Question-Response Mapping**

- Question response mappings now use `question_identifier` instead of `answer_label`
- This provides direct mapping between questions and student responses

## Usage Examples

### Creating a Teacher

```python
from database.integration import get_db_integration

db_integration = get_db_integration()
teacher_id = await db_integration.create_teacher("Rishav Kumar", "10", "CBSE")
```

### Creating a Student

```python
student_id = await db_integration.create_student("Shristi Jain")
```

### Creating an Assignment

```python
assignment_id = await db_integration.create_assignment("run_id_123")
```

### Saving Questions with Assignment

```python
question_data = {
    "question_identifier": "1",
    "has_internal_choice": False,
    "primary_question": "What is 2 + 2?",
    "primary_marks": "1 mark",
    "question_type": "MCQ"
}

question_id = await db_integration.save_question_with_assignment(
    question_data, assignment_id, "run_id_123"
)
```

### Saving Student Responses

```python
student_responses = [
    StudentResponse(
        question_identifier="1",
        cloudinary_url="https://example.com/response.jpg"
    )
]

response_id = await db_integration.save_student_assignment_response(
    student_id, assignment_id, "run_id_456", student_responses
)
```

## Database Initialization

### Initialize Sample Data

```bash
cd app
python -m database.init_data
```

### List Sample Data

```bash
cd app
python -m database.init_data list
```

## Testing the New Schema

### Run Tests

```bash
python test_new_schema.py
```

### Cleanup Test Data

```bash
python test_new_schema.py cleanup
```

## Migration Notes

### For Existing Data

1. **Legacy pipeline processing data** is preserved in separate collections
2. **New core business logic** uses the new schema structure
3. **Gradual migration** can be done by creating assignments for existing questions

### Frontend Updates

The frontend has been updated to send `assignment_id` in POST requests to `/crop-margins`. Currently, it uses a placeholder value (`"assignment_001"`), but this should be dynamically set based on the current assignment context.

## Benefits of the New Schema

1. **Better Organization**: Clear separation between core entities and processing data
2. **Improved Querying**: Easy to find all responses for a student or assignment
3. **Scalability**: Better structure for handling multiple assignments and students
4. **Data Integrity**: Proper relationships between entities
5. **Flexibility**: Easy to extend with additional fields or relationships

## Next Steps

1. **Dynamic Assignment Management**: Create endpoints to manage assignments dynamically
2. **Student Management**: Add endpoints for student CRUD operations
3. **Teacher Dashboard**: Build interfaces for teachers to manage assignments and view results
4. **Data Migration**: Create migration scripts for existing data if needed
5. **API Documentation**: Update API documentation to reflect new endpoints and schemas
