# Visual Content Extraction Schema Changes

## Changes Made

**Removed:**

- `step` - Collection name already indicates step
- `figure_files` - Replaced with Cloudinary URLs in figures array
- `overview_image_path` - Replaced with Cloudinary URL

**Added:**

- `overview_image_figures` - Cloudinary URL for figures overview image
- `overview_image_tables` - Cloudinary URL for tables overview image
- `tables` - List of extracted tables with Cloudinary URLs

**Modified:**

- `figures` - Now contains only diagram object IDs (strings) from diagrams collection
- `tables` - Now contains only table object IDs (strings) from tables collection

## Reason for Changes

**Separate Overview Images:**

- Better organization of extracted content
- Easier to distinguish between figures and tables
- Allows independent processing and display of each type
- Supports future features like separate mapping workflows

**Table Extraction:**

- CBSE papers contain both figures and tables
- Tables need separate processing from figures
- Enables table-to-question mapping similar to figures
- Provides complete content extraction coverage

**Object ID References:**

- Store only object IDs in extraction results for cleaner data structure
- Full diagram/table data available in separate collections
- Reduces data duplication and improves maintainability
- Enables efficient querying and relationship management

## Files to Update

1. ✅ `question_extraction.py` - Add Cloudinary uploads during extraction
2. ✅ `integration.py` - Update save method signature to store object IDs only
3. ✅ `main.py` - Update API response format
4. ✅ `cloudinary_utils.py` - New utility module for Cloudinary uploads
5. ✅ `extract_tables_from_pdf()` - New table extraction function
6. ✅ `compose_table_preview()` - New table preview function
7. ✅ `upload_tables_to_cloudinary()` - New table upload function
8. ✅ Pipeline integration - Added Step 1.5 for table extraction
9. ✅ `schema.py` - Updated to use object ID references

## Data Structure

**Visual Extraction Result:**

```json
{
  "figures": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"],
  "tables": ["507f1f77bcf86cd799439013"],
  "overview_image_figures": "https://res.cloudinary.com/...",
  "overview_image_tables": "https://res.cloudinary.com/..."
}
```

**Visual Mapping Result:**

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

**Note:** In the mapping results, figures only contain `diagram_id` (with `table_id` as null), and tables only contain `table_id` (with `diagram_id` as null). This ensures clean separation and eliminates redundant fields.

**Benefits of Object ID References:**

- **Cleaner Data Structure**: Extraction results contain only essential metadata
- **No Duplication**: Full diagram/table data stored once in dedicated collections
- **Efficient Queries**: Can fetch specific diagrams/tables by ID when needed
- **Better Relationships**: Clear references between extraction, mapping, and actual content
- **Scalability**: Easier to manage large numbers of diagrams and tables
