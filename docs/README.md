# TickAI Database Schema

This module provides MongoDB integration for storing CBSE processing pipeline results.

## Overview

The database uses **Motor** (async MongoDB driver) for optimal performance with FastAPI's async nature.
It stores results from each step of the CBSE question paper processing pipeline:

1. **Diagram Extraction** - Extracted figures and diagrams
2. **Diagram Mapping** - Mapping figures to questions with Cloudinary URLs
3. **Question Extraction** - Questions in markdown format
4. **Marks Mapping** - Question types and marks allocation

## Database Collections

### 1. `pipeline_results`

Main collection storing complete pipeline execution data.

**Schema:**

```json
{
  "_id": "ObjectId",
  "run_id": "string (unique)",
  "title": "string",
  "log_type": "string",
  "status": "string (active/completed/failed)",
  "original_filename": "string",
  "file_size": "number",
  "steps": [
    {
      "name": "string",
      "timestamp": "datetime",
      "input": "string",
      "output": "string"
    }
  ],
  "step_results": {
    "step1": {...},
    "step2": {...},
    "step3": {...},
    "step4": {...}
  },
  "final_outputs": {...},
  "errors": ["string"],
  "created_at": "datetime",
  "updated_at": "datetime",
  "completed_at": "datetime"
}
```

### 2. `visual_extraction_results`

Stores results from Step 1: Visual Content Extraction (figures and tables).

**Schema:**

```json
{
  "_id": "ObjectId",
  "run_id": "string",
  "total_figures": "number",
  "pages_processed": "number",
  "extraction_success": "boolean",
  "figures": ["string"],
  "tables": ["string"],
  "overview_image_figures": "string",
  "overview_image_tables": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 3. `visual_mapping_results`

Stores results from Step 2: Visual Content Mapping with Cloudinary URLs.

**Schema:**

```json
{
  "_id": "ObjectId",
  "run_id": "string",
  "step": "visual_mapping",
  "figures": {
    "figure-1": {
      "question_identifier": "string",
      "choice_location": "string",
      "diagram_id": "string",
      "table_id": "null"
    }
  },
  "tables": {
    "table-1": {
      "question_identifier": "string",
      "choice_location": "string",
      "diagram_id": "null",
      "table_id": "string"
    }
  },
  "total_mappings": "number",
  "mapping_success": "boolean",
  "raw_response": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 4. `question_extraction_results`

Stores results from Step 3: Question Extraction.

**Schema:**

```json
{
  "_id": "ObjectId",
  "run_id": "string",
  "step": "question_extraction",
  "questions_markdown": "string",
  "questions_count": "number",
  "content_length": "number",
  "extraction_success": "boolean",
  "raw_response": "string",
  "markdown_file_path": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Setup

### 1. Environment Variables

Add these to your `.env` file:

```env
# MongoDB Connection
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=tickai

# Cloudinary (for diagram URLs)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### 2. Install Dependencies

```bash
# Motor is already included in the main requirements.txt
pip install -r requirements.txt
```

### 3. Initialize Database

```python
from database import initialize_database

# Initialize connection
success = initialize_database()
if success:
    print("Database connected successfully")
```

## Usage

### Basic Integration

```python
from database import get_db_integration

# Get database integration instance
db = get_db_integration()

# Start a new pipeline (async)
await db.start_pipeline(
    run_id="abc123",
    title="CBSE Processing Pipeline",
    filename="maths-paper.pdf"
)

# Save step results (async)
await db.save_step_log("Step 1", "Starting extraction", "Extraction completed")

# Save diagram extraction results (async)
await db.save_diagram_extraction_result(
    run_id="abc123",
    total_figures=12,
    pages_processed=4,
    figure_files=["figure1.png", "figure2.png"]
)

# Complete pipeline (async)
await db.complete_pipeline(success=True)
```

### Querying Results

```python
from database import pipeline_db

# Get pipeline by run_id (async)
pipeline = await pipeline_db.get_pipeline_by_run_id("abc123")

# Get specific step results (async)
diagram_mapping = await pipeline_db.get_step_results_by_run_id("abc123", "diagram_mapping")

# Get all pipelines (async)
pipelines = await pipeline_db.get_all_pipelines(limit=10)
```

### Migration from File Logs

```python
from database import save_logs_to_database

# Migrate existing logs to database (async)
success = await save_logs_to_database(
    run_id="396bf503ebac",
    logs_dir="logs/396bf503ebac"
)
```

## Database Indexes

The following indexes are automatically created for optimal performance:

- **pipeline_results**: `run_id`, `status`, `created_at`, `log_type`
- **diagram_extraction_results**: `run_id`, `created_at`
- **diagram_mapping_results**: `run_id`, `created_at`
- **question_extraction_results**: `run_id`, `created_at`

## Benefits

1. **Async Performance**: Motor provides non-blocking async operations for better performance
2. **FastAPI Integration**: Perfect compatibility with FastAPI's async nature
3. **Scalability**: MongoDB can handle large volumes of processing results
4. **Queryability**: Easy to search and filter results by various criteria
5. **Reliability**: ACID transactions and data persistence
6. **Performance**: Optimized indexes for fast queries
7. **Flexibility**: Schema can evolve as requirements change
8. **Cloudinary Integration**: Direct access to figure images via URLs

## Error Handling

The database operations include comprehensive error handling:

- Connection failures are logged and handled gracefully
- Data validation using Pydantic models
- Automatic retry logic for transient failures
- Detailed error messages for debugging

## Production Considerations

1. **Connection Pooling**: Configure appropriate connection pool sizes
2. **Backup Strategy**: Implement regular database backups
3. **Monitoring**: Set up MongoDB monitoring and alerting
4. **Security**: Use authentication and network security
5. **Performance**: Monitor query performance and optimize indexes
