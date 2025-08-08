# Bulk Rubric Generation API

## Overview

The `/build-rubrics-for-assignment` API endpoint generates rubrics for all questions in an assignment in a single request. This endpoint leverages the existing single-question rubric generation pipeline but processes multiple questions sequentially and updates the database with the generated rubrics.

## Endpoint

```
POST /build-rubrics-for-assignment
```

## Request Format

### Request Body

```json
{
  "assignment_id": "assignment_id_string"
}
```

### Request Parameters

| Field           | Type   | Required | Description                        |
| --------------- | ------ | -------- | ---------------------------------- |
| `assignment_id` | string | Yes      | MongoDB ObjectId of the assignment |

## Response Format

### Success Response

```json
{
  "success": true,
  "assignment_id": "assignment_id_string",
  "total_questions": 5,
  "processed_questions": 4,
  "failed_questions": 1,
  "results": [
    {
      "question_id": "question_id_1",
      "question_text": "1. What is the capital of France?",
      "success": true,
      "rubric": {
        "correct_option": "A",
        "acceptable_answers": ["A", "a", "Paris"],
        "solution": "Paris is the capital of France..."
      },
      "metadata": {
        "assessment_intent": "...",
        "bloom_taxonomy_level": "Remembering",
        "tags": {...}
      },
      "solution": "Detailed solution in markdown format...",
      "processing_time": 45.2
    },
    {
      "question_id": "question_id_2",
      "question_text": "2. Solve the equation...",
      "success": false,
      "errors": ["Failed to process question due to invalid format"]
    }
  ],
  "errors": [
    "Failed to process question question_id_2: Failed to process question due to invalid format"
  ],
  "total_time": 180.5
}
```

### Error Response

```json
{
  "detail": "Assignment assignment_id not found"
}
```

## Response Fields

| Field                 | Type    | Description                                     |
| --------------------- | ------- | ----------------------------------------------- |
| `success`             | boolean | Overall success status                          |
| `assignment_id`       | string  | The assignment ID that was processed            |
| `total_questions`     | integer | Total number of questions in the assignment     |
| `processed_questions` | integer | Number of questions successfully processed      |
| `failed_questions`    | integer | Number of questions that failed to process      |
| `results`             | array   | Array of individual question processing results |
| `errors`              | array   | List of error messages                          |
| `total_time`          | float   | Total processing time in seconds                |

### Individual Question Result Fields

| Field             | Type    | Description                                      |
| ----------------- | ------- | ------------------------------------------------ |
| `question_id`     | string  | MongoDB ObjectId of the question                 |
| `question_text`   | string  | The question text                                |
| `success`         | boolean | Whether this question was processed successfully |
| `rubric`          | object  | Generated rubric (if successful)                 |
| `metadata`        | object  | Generated metadata (if successful)               |
| `solution`        | string  | Generated solution in markdown (if successful)   |
| `processing_time` | float   | Time taken to process this question              |
| `errors`          | array   | List of errors for this question (if failed)     |

## Usage Examples

### Python Example

```python
import requests

# Sample request
payload = {
    "assignment_id": "507f1f77bcf86cd799439011"
}

# Make API request
response = requests.post(
    "http://localhost:8000/build-rubrics-for-assignment",
    json=payload,
    timeout=600  # 10 minute timeout for bulk processing
)

if response.status_code == 200:
    result = response.json()
    if result["success"]:
        print(f"✅ Successfully processed {result['processed_questions']} out of {result['total_questions']} questions")
        print(f"⏱️  Total time: {result['total_time']} seconds")

        # Print individual results
        for question_result in result['results']:
            if question_result['success']:
                print(f"✅ Question {question_result['question_id']}: Rubric generated")
            else:
                print(f"❌ Question {question_result['question_id']}: Failed")
    else:
        print(f"❌ Failed to process questions: {result['errors']}")
else:
    print(f"❌ API call failed: {response.text}")
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/build-rubrics-for-assignment" \
  -H "Content-Type: application/json" \
  -d '{
    "assignment_id": "507f1f77bcf86cd799439011"
  }'
```

### JavaScript Example

```javascript
async function buildRubricsForAssignment(assignmentId) {
  try {
    const response = await fetch("/build-rubrics-for-assignment", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        assignment_id: assignmentId,
      }),
    });

    const result = await response.json();

    if (result.success) {
      console.log(
        `✅ Processed ${result.processed_questions} out of ${result.total_questions} questions`
      );
      console.log(`⏱️ Total time: ${result.total_time} seconds`);

      // Handle individual results
      result.results.forEach((questionResult) => {
        if (questionResult.success) {
          console.log(
            `✅ Question ${questionResult.question_id}: Rubric generated`
          );
        } else {
          console.log(`❌ Question ${questionResult.question_id}: Failed`);
        }
      });
    } else {
      console.error("❌ Failed to process questions:", result.errors);
    }
  } catch (error) {
    console.error("❌ Network error:", error);
  }
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK`: Request processed successfully (may have partial failures)
- `404 Not Found`: Assignment not found
- `500 Internal Server Error`: Server-side processing error

## Database Updates

When rubrics are successfully generated, the questions in the database are automatically updated with the generated rubric data. The `rubric` field in each question document is populated with the generated rubric.

## Performance Considerations

1. **Processing Time**: Bulk rubric generation can take several minutes depending on the number of questions and their complexity.

2. **Timeout**: The API has a 10-minute timeout for bulk processing.

3. **Memory Usage**: Each question is processed sequentially to manage memory usage.

4. **Error Handling**: If individual questions fail, the process continues with the remaining questions.

## Frontend Integration

The frontend automatically calls this endpoint when the "Build Rubrics" button is clicked. The button shows:

- "Build Rubrics" if no rubrics exist for the assignment
- "Rebuild Rubrics" if some rubrics already exist

The frontend also displays:

- Loading state during processing
- Success/error notifications
- Rubric status indicators for each question
- Automatic refresh of the assignments list after completion

## Testing

Use the test script `testing/test_bulk_rubric_generation.py` to verify the functionality:

```bash
cd testing
python test_bulk_rubric_generation.py
```

This script will:

1. Get available assignments from the database
2. Test the bulk rubric generation with the first available assignment
3. Display detailed results and timing information
