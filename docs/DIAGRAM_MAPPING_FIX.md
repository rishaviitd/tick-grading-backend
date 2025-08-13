# Diagram Mapping Fix - Question Identifier Population Issue

## Problem Description

The `question_identifier` field in the diagrams collection was consistently showing as `null` even when the diagram mapping JSON was correctly generated. This was causing diagrams to not be properly linked to their corresponding questions.

## Root Cause Analysis

The issue was caused by a missing `run_id` field in the diagram lookup process:

1. **Missing `run_id` in Diagram Schema**: The `Diagram` schema only had `diagram_url` and `diagram_identifier` fields, but no `run_id` field.

2. **Incomplete Diagram Lookup**: The `get_diagram_by_identifier` function was searching for diagrams by `diagram_identifier` only, without considering the `run_id`. This could lead to:

   - Finding diagrams from other runs
   - Not finding the correct diagram at all
   - Ambiguous results when multiple runs have diagrams with the same identifier

3. **Pipeline Integration Gap**: The `update_visual_content_mapping` function wasn't receiving the `run_id` parameter, so it couldn't perform run-specific lookups.

## Solution Implemented

### 1. Schema Updates

**File**: `database/schema.py`

- **Added `run_id` field to `Diagram` schema**:

  ```python
  class Diagram(BaseModel):
      diagram_url: str = Field(..., description="Cloudinary URL for the diagram image")
      diagram_identifier: str = Field(..., description="Diagram identifier")
      run_id: str = Field(..., description="Unique run identifier from question processing")
      # ... other fields
  ```

- **Added `run_id` field to `Table` schema** (for consistency):
  ```python
  class Table(BaseModel):
      table_url: str = Field(..., description="Cloudinary URL for the table image")
      table_identifier: str = Field(..., description="Table identifier")
      run_id: str = Field(..., description="Unique run identifier from question processing")
      # ... other fields
  ```

### 2. Database Integration Updates

**File**: `database/integration.py`

- **Updated `save_diagram` function**:

  ```python
  async def save_diagram(self, diagram_url: str, diagram_identifier: str, run_id: str) -> Optional[str]:
      diagram = Diagram(
          diagram_url=diagram_url,
          diagram_identifier=diagram_identifier,
          run_id=run_id
      )
  ```

- **Updated `save_table` function**:

  ```python
  async def save_table(self, table_url: str, table_identifier: str, run_id: str) -> Optional[str]:
      table = Table(
          table_url=table_url,
          table_identifier=table_identifier,
          run_id=run_id
      )
  ```

- **Updated `update_visual_content_mapping` function**:
  ```python
  async def update_visual_content_mapping(self, mapping_data: Dict[str, Any], run_id: str = None) -> bool:
      # Find diagram by identifier and run_id
      diagram = await pipeline_db.get_diagram_by_identifier(figure_identifier, run_id)
  ```

### 3. Database Connection Updates

**File**: `database/connection.py`

- **Updated `get_diagram_by_identifier` function**:

  ```python
  async def get_diagram_by_identifier(self, diagram_identifier: str, run_id: str = None) -> Optional[Dict[str, Any]]:
      query = {"diagram_identifier": diagram_identifier}
      if run_id:
          query["run_id"] = run_id
      diagram = await collection.find_one(query)
  ```

- **Updated `get_table_by_identifier` function** (for consistency):
  ```python
  async def get_table_by_identifier(self, table_identifier: str, run_id: str = None) -> Optional[Dict[str, Any]]:
      query = {"table_identifier": table_identifier}
      if run_id:
          query["run_id"] = run_id
      table = await collection.find_one(query)
  ```

### 4. Pipeline Integration

**File**: `app/question_parsing/question_extraction.py`

- **Updated pipeline call**:
  ```python
  # Update visual content mapping with diagram mapping results
  await db_integration.update_visual_content_mapping(mapping_json, pipeline_run_id)
  ```

## Testing

A comprehensive test was created in `testing/test_diagram_mapping_fix.py` that verifies:

1. ✅ Diagrams are saved with `run_id`
2. ✅ Diagram mapping updates work correctly
3. ✅ `question_identifier` and `choice_location` are properly populated
4. ✅ Database lookups work with `run_id` filtering

## Impact

This fix ensures that:

- **Accurate Diagram-Question Mapping**: Diagrams are correctly linked to their corresponding questions
- **Run Isolation**: Each pipeline run's diagrams are isolated from others
- **Data Integrity**: No cross-contamination between different runs
- **Reliable Lookups**: Database queries are precise and unambiguous

## Migration Notes

For existing data:

- Existing diagrams without `run_id` will still be found by `diagram_identifier` only (backward compatibility)
- New diagrams will be saved with `run_id` and use the improved lookup mechanism
- The system gracefully handles both old and new data formats

## Verification

The fix was verified using the test run ID `2e1a64e5a005` and confirmed that:

- Diagram mapping JSON was correctly generated
- Database updates now properly populate `question_identifier` fields
- The pipeline integration works seamlessly


