# Build Rubric API

## Overview

The `/build-rubric` API endpoint generates rubrics for individual questions using the current Question schema. This endpoint leverages the existing rubric generation pipeline but accepts input in the simplified current schema format.

## Endpoint

```
POST /build-rubric
```

## Request Format

### Request Body

```json
{
  "question": {
    "_id": "question_id",
    "run_id": "run_identifier",
    "question_text": "1. What is the capital of France?",
    "question_marks": 2,
    "question_marks_analysis": "2 marks for correct answer",
    "question_type": "MCQ",
    "diagram_url": "https://example.com/diagram.png",
    "table_url": "https://example.com/table.png",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### Question Schema Fields

| Field                     | Type   | Required | Description                                                                          |
| ------------------------- | ------ | -------- | ------------------------------------------------------------------------------------ |
| `_id`                     | string | Yes      | Unique question identifier                                                           |
| `run_id`                  | string | Yes      | Run identifier                                                                       |
| `question_text`           | string | Yes      | The question text (should start with number)                                         |
| `question_marks`          | number | Yes      | Total marks for the question                                                         |
| `question_marks_analysis` | string | Yes      | Analysis of mark distribution                                                        |
| `question_type`           | string | Yes      | Type of question (MCQ, Subjective, Case-Study, Assertion Reasoning, Internal Choice) |
| `diagram_url`             | string | No       | URL to diagram image                                                                 |
| `table_url`               | string | No       | URL to table image                                                                   |
| `created_at`              | string | Yes      | Creation timestamp                                                                   |
| `updated_at`              | string | Yes      | Last update timestamp                                                                |

## Response Format

### Success Response

```json
{
  "success": true,
  "rubric": {
    "correct_option": "A",
    "acceptable_answers": ["A", "a"],
    "solution": "Paris is the capital of France..."
  },
  "metadata": {
    "subject": "Geography",
    "topic": "World Capitals",
    "difficulty": "Easy"
  },
  "solution": {
    "solution_text": "Detailed solution explanation...",
    "key_points": ["Point 1", "Point 2"]
  },
  "marking_scheme": {
    "correct_option": "A",
    "acceptable_answers": ["A", "a"],
    "solution": "Paris is the capital of France..."
  },
  "output_dir": "/tmp/tmpxxx",
  "errors": [],
  "total_time": 45.2,
  "token_counts": {
    "prompt": 1500,
    "thoughts": 300,
    "output": 800
  }
}
```

### Error Response

```json
{
  "success": false,
  "rubric": null,
  "metadata": null,
  "solution": null,
  "marking_scheme": null,
  "output_dir": null,
  "errors": ["Metadata generation failed for question_1"],
  "total_time": 12.5,
  "token_counts": {
    "prompt": 500,
    "thoughts": 100,
    "output": 200
  }
}
```

## Response Fields

| Field            | Type    | Description                                  |
| ---------------- | ------- | -------------------------------------------- |
| `success`        | boolean | Whether the rubric generation was successful |
| `rubric`         | object  | Generated rubric (same as marking_scheme)    |
| `metadata`       | object  | Generated metadata about the question        |
| `solution`       | object  | Generated solution (for non-MCQ questions)   |
| `marking_scheme` | object  | Generated marking scheme                     |
| `output_dir`     | string  | Temporary output directory path              |
| `errors`         | array   | List of errors encountered during processing |
| `total_time`     | number  | Total processing time in seconds             |
| `token_counts`   | object  | Token usage statistics                       |

## Question Types and Rubric Formats

### MCQ Questions

```json
{
  "correct_option": "A",
  "acceptable_answers": ["A", "a"],
  "solution": "Detailed explanation of why A is correct"
}
```

### Subjective Questions

```json
{
  "methods": [
    {
      "methodName": "Method 1",
      "markingPoints": [
        {
          "stepId": "1",
          "MarkType": "B",
          "marks": "1",
          "Teacher_Expectation": "Student should understand the concept",
          "Pass_if": "Student demonstrates basic understanding",
          "Fail_if": "Student shows no understanding",
          "guidance": "Look for key terms in the answer"
        }
      ]
    }
  ],
  "Question_specific_notes": "Additional marking guidance"
}
```

### Case Study Questions

```json
{
  "ques_identifier": "30",
  "parts": [
    {
      "part_label": "a",
      "methods": [
        {
          "methodName": "Analysis Method",
          "markingPoints": [...]
        }
      ]
    }
  ],
  "Question_specific_notes": "Case study specific guidance"
}
```

## Usage Examples

### Python Example

```python
import requests

# Sample question data
question_data = {
    "_id": "test_001",
    "run_id": "run_001",
    "question_text": "1. What is the capital of France?",
    "question_marks": 2,
    "question_marks_analysis": "2 marks for correct answer",
    "question_type": "MCQ",
    "diagram_url": None,
    "table_url": None,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}

# Make API request
response = requests.post(
    "http://localhost:8000/build-rubric",
    json={"question": question_data}
)

if response.status_code == 200:
    result = response.json()
    if result["success"]:
        print("Rubric generated successfully!")
        print(f"Rubric: {result['rubric']}")
    else:
        print(f"Errors: {result['errors']}")
else:
    print(f"API call failed: {response.text}")
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/build-rubric" \
  -H "Content-Type: application/json" \
  -d '{
    "question": {
      "_id": "test_001",
      "run_id": "run_001",
      "question_text": "1. What is the capital of France?",
      "question_marks": 2,
      "question_marks_analysis": "2 marks for correct answer",
      "question_type": "MCQ",
      "diagram_url": null,
      "table_url": null,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  }'
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK`: Request processed successfully
- `400 Bad Request`: Invalid question data format
- `500 Internal Server Error`: Server-side processing error

## Notes

1. **Image Downloads**: The API automatically downloads images from `diagram_url` and `table_url` for processing with Gemini models.

2. **Question Identifier**: The question identifier is automatically extracted from the question text (e.g., "1" from "1. What is the capital of France?").

3. **Processing Time**: Rubric generation can take 30-60 seconds depending on question complexity and image processing requirements.

4. **Token Usage**: The response includes token usage statistics for monitoring API costs.

5. **Temporary Files**: All generated files are stored in temporary directories and cleaned up automatically.

## Testing

Use the provided test script to verify the API functionality:

```bash
cd testing
python test_build_rubric_api.py
```

Make sure the server is running before executing the test script.
