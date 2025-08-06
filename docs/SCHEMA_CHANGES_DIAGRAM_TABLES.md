# Visual Content Schema Changes - Object ID References

## Overview

Updated the visual content extraction and mapping schemas to use object ID references instead of storing full diagram/table data in arrays. This provides a cleaner, more efficient data structure.

## Changes Made

### 1. Visual Extraction Result Schema

**Before:**

```json
{
  "figures": [
    {
      "diagram_id": "507f1f77bcf86cd799439011",
      "page_number": 1,
      "figure_id": 1
    }
  ],
  "tables": [
    {
      "table_id": "507f1f77bcf86cd799439012",
      "page_number": 1,
      "table_id": 1
    }
  ]
}
```

**After:**

```json
{
  "figures": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"],
  "tables": ["507f1f77bcf86cd799439013"]
}
```

### 2. Visual Mapping Result Schema

**Before:**

```json
{
  "figures": {
    "figure-1": {
      "question_identifier": "1",
      "choice_location": "null",
      "diagram_id": "507f1f77bcf86cd799439011",
      "table_id": null
    }
  }
}
```

**After:**

```json
{
  "figures": {
    "figure-1": {
      "question_identifier": "1",
      "choice_location": "null",
      "diagram_id": "507f1f77bcf86cd799439011",
      "table_id": null
    }
  },
  "tables": {
    "table-1": {
      "question_identifier": "3",
      "choice_location": "null",
      "diagram_id": null,
      "table_id": "507f1f77bcf86cd799439013"
    }
  }
}
```

**Note:** Figures only contain `diagram_id` (with `table_id` as null), and tables only contain `table_id` (with `diagram_id` as null). This ensures clean separation and eliminates redundant fields.

## Reasons for Changes

### 1. **Cleaner Data Structure**

- Extraction results contain only essential metadata
- Full diagram/table data available in separate collections
- Reduces complexity in extraction result documents

### 2. **No Data Duplication**

- Diagram and table data stored once in dedicated collections
- References point to the actual data
- Easier to maintain consistency

### 3. **Efficient Querying**

- Can fetch specific diagrams/tables by ID when needed
- Better performance for large datasets
- Clear separation of concerns

### 4. **Better Relationships**

- Clear references between extraction, mapping, and actual content
- Easier to understand data flow
- More maintainable codebase

### 5. **Scalability**

- Easier to manage large numbers of diagrams and tables
- Reduced document size in extraction results
- Better database performance

## Implementation Details

### Database Integration Changes

**`save_visual_extraction_result()` Method:**

- Now saves diagrams and tables to separate collections
- Returns only object IDs for the extraction result
- Maintains full data in dedicated collections

**`save_visual_mapping_result()` Method:**

- Works with object ID references
- Resolves diagram/table IDs from mapping data
- Maintains backward compatibility

### Schema Updates

**`VisualExtractionResult`:**

- `figures`: `List[str]` - Object IDs only
- `tables`: `List[str]` - Object IDs only

**`VisualMappingResult`:**

- `figures`: `Dict[str, DiagramMappingEntry]` - Uses object ID references
- `tables`: `Dict[str, DiagramMappingEntry]` - Uses object ID references

## Benefits

1. **Reduced Complexity**: Simpler extraction result documents
2. **Better Performance**: Smaller documents, faster queries
3. **Data Integrity**: Single source of truth for diagram/table data
4. **Maintainability**: Easier to update and manage
5. **Scalability**: Better handling of large datasets
6. **Clear Relationships**: Explicit references between collections

## Migration Notes

- Existing data will continue to work with backward compatibility
- New extractions will use the simplified object ID structure
- Full diagram/table data remains accessible via separate collections
- API responses include complete data when needed
