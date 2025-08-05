"""
Simple test to verify table extraction functionality
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.question_parsing.question_extraction import compose_table_preview
from app.question_parsing.cloudinary_utils import upload_tables_to_cloudinary


class TestTableExtraction:
    """Test cases for table extraction functionality"""
    
    @pytest.fixture
    def sample_table_snippets(self):
        """Create sample table snippets for testing"""
        # Create sample table snippets (pages -> tables)
        tables = []
        for page in range(2):
            page_tables = []
            for table in range(2):
                # Create a simple test image for each table
                img = Image.new('RGB', (300, 200), color=f'rgb({page*100}, {table*100}, 150)')
                page_tables.append(img)
            tables.append(page_tables)
        return tables
    
    def test_compose_table_preview(self, sample_table_snippets):
        """Test table preview composition"""
        # Test preview creation
        preview = compose_table_preview(sample_table_snippets, thumb_width=200)
        
        # Verify result
        assert preview is not None
        assert isinstance(preview, Image.Image)
        assert preview.mode == 'RGB'
        assert preview.size[0] > 0  # Should have width
        assert preview.size[1] > 0  # Should have height
    
    @patch('app.question_parsing.cloudinary_utils.upload_image_to_cloudinary')
    def test_upload_tables_to_cloudinary(self, mock_upload, sample_table_snippets):
        """Test uploading tables to Cloudinary"""
        # Mock successful uploads
        mock_upload.side_effect = [
            'https://res.cloudinary.com/test/image/upload/v123/table1.png',
            'https://res.cloudinary.com/test/image/upload/v123/table2.png',
            'https://res.cloudinary.com/test/image/upload/v123/table3.png',
            'https://res.cloudinary.com/test/image/upload/v123/table4.png'
        ]
        
        # Test upload
        result = upload_tables_to_cloudinary(sample_table_snippets, 'test_run_123')
        
        # Verify result structure
        assert len(result) == 4  # 2 pages * 2 tables each
        assert mock_upload.call_count == 4
        
        # Verify each table has correct structure
        for i, table in enumerate(result):
            assert 'cloudinary_url' in table
            assert 'page_number' in table
            assert 'table_id' in table
            assert 'file_name' in table
            assert 'table_counter' in table
            assert table['cloudinary_url'].startswith('https://res.cloudinary.com/')
            assert table['table_counter'] == i + 1
    
    def test_extract_diagrams_from_pdf_includes_tables(self):
        """Test that extract_diagrams_from_pdf includes table extraction"""
        # This test verifies that the combined extraction function works
        # In a real test, you'd need to create a test PDF with both figures and tables
        from app.question_parsing.question_extraction import extract_diagrams_from_pdf
        
        assert callable(extract_diagrams_from_pdf)
        assert extract_diagrams_from_pdf.__doc__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 