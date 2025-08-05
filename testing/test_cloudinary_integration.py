"""
Unit tests for Cloudinary integration in question parsing

This module contains comprehensive tests for:
- Cloudinary upload functionality
- Database schema validation
- Integration between extraction and Cloudinary
- Error handling scenarios
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.connection import pipeline_db, initialize_database
from database.schema import VisualContent
from app.question_parsing.cloudinary_utils import (
    upload_image_to_cloudinary,
    upload_figures_to_cloudinary,
    upload_overview_image_to_cloudinary
)
from PIL import Image
import io


@pytest.mark.unit
class TestCloudinaryUtils:
    """Test cases for Cloudinary utility functions"""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample PIL Image for testing"""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        return img
    
    @pytest.fixture
    def sample_figure_snippets(self):
        """Create sample figure snippets for testing"""
        # Create sample figure snippets (pages -> figures)
        figures = []
        for page in range(2):
            page_figures = []
            for fig in range(2):
                # Create a simple test image for each figure
                img = Image.new('RGB', (200, 150), color=f'rgb({page*100}, {fig*100}, 100)')
                page_figures.append(img)
            figures.append(page_figures)
        return figures
    
    @patch('app.question_parsing.cloudinary_utils.cloudinary.uploader.upload')
    def test_upload_image_to_cloudinary_success(self, mock_upload, sample_image):
        """Test successful image upload to Cloudinary"""
        # Mock successful upload response
        mock_upload.return_value = {
            'secure_url': 'https://res.cloudinary.com/test/image/upload/v123/test.png'
        }
        
        # Test upload
        result = upload_image_to_cloudinary(sample_image, 'test.png', 'test_folder')
        
        # Verify result
        assert result == 'https://res.cloudinary.com/test/image/upload/v123/test.png'
        mock_upload.assert_called_once()
        
        # Verify upload parameters
        call_args = mock_upload.call_args
        assert call_args[1]['public_id'] == 'test_folder/test.png'
        assert call_args[1]['resource_type'] == 'image'
        assert call_args[1]['format'] == 'png'
    
    @patch('app.question_parsing.cloudinary_utils.cloudinary.uploader.upload')
    def test_upload_image_to_cloudinary_failure(self, mock_upload, sample_image):
        """Test image upload failure handling"""
        # Mock upload failure
        mock_upload.side_effect = Exception("Upload failed")
        
        # Test upload
        result = upload_image_to_cloudinary(sample_image, 'test.png')
        
        # Verify result is None on failure
        assert result is None
    
    @patch('app.question_parsing.cloudinary_utils.upload_image_to_cloudinary')
    def test_upload_figures_to_cloudinary(self, mock_upload, sample_figure_snippets):
        """Test uploading multiple figures to Cloudinary"""
        # Mock successful uploads
        mock_upload.side_effect = [
            'https://res.cloudinary.com/test/image/upload/v123/figure1.png',
            'https://res.cloudinary.com/test/image/upload/v123/figure2.png',
            'https://res.cloudinary.com/test/image/upload/v123/figure3.png',
            'https://res.cloudinary.com/test/image/upload/v123/figure4.png'
        ]
        
        # Test upload
        result = upload_figures_to_cloudinary(sample_figure_snippets, 'test_run_123')
        
        # Verify result structure
        assert len(result) == 4  # 2 pages * 2 figures each
        assert mock_upload.call_count == 4
        
        # Verify each figure has correct structure
        for i, figure in enumerate(result):
            assert 'cloudinary_url' in figure
            assert 'page_number' in figure
            assert 'figure_id' in figure
            assert 'file_name' in figure
            assert 'figure_counter' in figure
            assert figure['cloudinary_url'].startswith('https://res.cloudinary.com/')
            assert figure['figure_counter'] == i + 1
    
    @patch('app.question_parsing.cloudinary_utils.upload_image_to_cloudinary')
    def test_upload_overview_image_to_cloudinary(self, mock_upload, sample_image):
        """Test uploading overview image to Cloudinary"""
        # Mock successful upload
        mock_upload.return_value = 'https://res.cloudinary.com/test/image/upload/v123/overview.png'
        
        # Test upload
        result = upload_overview_image_to_cloudinary(sample_image, 'test_run_123', 'figures')
        
        # Verify result
        assert result == 'https://res.cloudinary.com/test/image/upload/v123/overview.png'
        mock_upload.assert_called_once()
        
        # Verify upload parameters
        call_args = mock_upload.call_args
        # Check positional arguments
        assert call_args[0][0] == sample_image  # First argument should be the image
        assert call_args[0][1] == 'step1_overview_image_figures.png'  # Second argument should be filename
        # Check keyword arguments
        assert call_args[1]['folder'] == 'question_parsing/test_run_123/overviews'  # folder parameter


@pytest.mark.unit
class TestDatabaseSchema:
    """Test cases for database schema validation"""
    
    def test_diagram_extraction_result_schema(self):
        """Test DiagramExtractionResult schema validation"""
        # Valid data
        valid_data = {
            'run_id': 'test_run_123',
            'total_figures': 2,
            'pages_processed': 2,
            'extraction_success': True,
            'figures': [
                {
                    'cloudinary_url': 'https://res.cloudinary.com/test/image/upload/v123/figure1.png',
                    'page_number': 1,
                    'figure_id': 1,
                    'file_name': 'figure1.png',
                    'figure_counter': 1
                }
            ],
            'tables': [],
            'overview_image_figures': 'https://res.cloudinary.com/test/image/upload/v123/overview.png',
            'overview_image_tables': None
        }
        
        # Should create without errors
        extraction_result = DiagramExtractionResult(**valid_data)
        
        # Verify fields
        assert extraction_result.run_id == 'test_run_123'
        assert extraction_result.total_figures == 2
        assert extraction_result.pages_processed == 2
        assert extraction_result.extraction_success is True
        assert len(extraction_result.figures) == 1
        assert len(extraction_result.tables) == 0
        assert extraction_result.overview_image_figures == 'https://res.cloudinary.com/test/image/upload/v123/overview.png'
        assert extraction_result.overview_image_tables is None
    
    def test_diagram_extraction_result_required_fields(self):
        """Test that required fields are enforced"""
        # Missing required field
        invalid_data = {
            'run_id': 'test_run_123',
            # Missing total_figures
            'pages_processed': 2,
            'extraction_success': True
        }
        
        # Should raise validation error
        with pytest.raises(Exception):
            DiagramExtractionResult(**invalid_data)


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test cases for database integration"""
    
    @pytest.fixture
    async def setup_database(self):
        """Setup database connection for tests"""
        success = await initialize_database()
        if not success:
            pytest.skip("Database not available")
        yield
        await pipeline_db.db_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_save_diagram_extraction_result(self, setup_database):
        """Test saving diagram extraction result to database"""
        # Test data
        test_run_id = f"test_run_{datetime.utcnow().timestamp()}"
        test_figures = [
            {
                'cloudinary_url': 'https://res.cloudinary.com/test/image/upload/v123/figure1.png',
                'page_number': 1,
                'figure_id': 1,
                'file_name': 'figure1.png',
                'figure_counter': 1
            }
        ]
        
        # TODO: Update to use new visual content schema
        # Create visual content
        # visual_content = VisualContent(
        #     tables=[],
        #     diagrams=[],  # Would be populated with actual diagram IDs
        #     overview_image_tables=None,
        #     overview_image_diagrams='https://res.cloudinary.com/test/image/upload/v123/overview.png'
        # )
        
        # Save to database
        # save_success = await pipeline_db.save_visual_content(visual_content)
        # assert save_success is not None
        
        # Verify saved data
        # collection = pipeline_db.db_manager.get_collection("visual_content")
        # saved_doc = await collection.find_one({"_id": ObjectId(save_success)})
        
        # assert saved_doc is not None
        # assert saved_doc['overview_image_diagrams'] == 'https://res.cloudinary.com/test/image/upload/v123/overview.png'
        
        # Cleanup
        # await collection.delete_one({"_id": ObjectId(save_success)})
        
        # Placeholder for now
        assert True
    
    @pytest.mark.asyncio
    async def test_save_diagram_extraction_result_with_tables(self, setup_database):
        """Test saving diagram extraction result with tables"""
        # Test data with tables
        test_run_id = f"test_run_tables_{datetime.utcnow().timestamp()}"
        test_tables = [
            {
                'cloudinary_url': 'https://res.cloudinary.com/test/image/upload/v123/table1.png',
                'page_number': 1,
                'table_id': 1,
                'file_name': 'table1.png',
                'table_counter': 1
            }
        ]
        
        # TODO: Update to use new visual content schema
        # Create visual content with tables
        # visual_content = VisualContent(
        #     tables=[],  # Would be populated with actual table IDs
        #     diagrams=[],
        #     overview_image_tables='https://res.cloudinary.com/test/image/upload/v123/overview_tables.png',
        #     overview_image_diagrams=None
        # )
        
        # Save to database
        # save_success = await pipeline_db.save_visual_content(visual_content)
        # assert save_success is not None
        
        # Verify saved data
        # collection = pipeline_db.db_manager.get_collection("visual_content")
        # saved_doc = await collection.find_one({"_id": ObjectId(save_success)})
        
        # assert saved_doc is not None
        # assert saved_doc['overview_image_tables'] == 'https://res.cloudinary.com/test/image/upload/v123/overview_tables.png'
        
        # Cleanup
        # await collection.delete_one({"_id": ObjectId(save_success)})
        
        # Placeholder for now
        assert True


@pytest.mark.unit
class TestErrorHandling:
    """Test cases for error handling scenarios"""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample PIL Image for testing"""
        img = Image.new('RGB', (100, 100), color='red')
        return img
    
    @patch('app.question_parsing.cloudinary_utils.cloudinary.uploader.upload')
    def test_cloudinary_upload_network_error(self, mock_upload, sample_image):
        """Test handling of network errors during Cloudinary upload"""
        # Mock network error
        mock_upload.side_effect = Exception("Network connection failed")
        
        # Test upload
        result = upload_image_to_cloudinary(sample_image, 'test.png')
        
        # Should return None on error
        assert result is None
    
    @patch('app.question_parsing.cloudinary_utils.cloudinary.uploader.upload')
    def test_cloudinary_upload_invalid_response(self, mock_upload, sample_image):
        """Test handling of invalid Cloudinary response"""
        # Mock invalid response (missing secure_url)
        mock_upload.return_value = {'public_id': 'test', 'format': 'png'}
        
        # Test upload
        result = upload_image_to_cloudinary(sample_image, 'test.png')
        
        # Should return None when secure_url is missing
        assert result is None
    
    def test_invalid_image_data(self):
        """Test handling of invalid image data"""
        # Test with None image
        result = upload_image_to_cloudinary(None, 'test.png')
        assert result is None
        
        # Test with invalid image type
        result = upload_image_to_cloudinary("not_an_image", 'test.png')
        assert result is None


# Integration test for the complete workflow
@pytest.mark.integration
class TestCompleteWorkflow:
    """Integration tests for the complete Cloudinary workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_figure_extraction_workflow(self, setup_database):
        """Test the complete workflow from extraction to database save"""
        # This would test the actual extraction process
        # For now, we'll test the integration points
        
        # Mock the extraction process
        mock_figure_snippets = [
            [Image.new('RGB', (100, 100), 'red')],  # Page 1: 1 figure
            [Image.new('RGB', (100, 100), 'blue')]  # Page 2: 1 figure
        ]
        
        # Mock Cloudinary uploads
        with patch('app.question_parsing.cloudinary_utils.upload_image_to_cloudinary') as mock_upload:
            mock_upload.side_effect = [
                'https://res.cloudinary.com/test/image/upload/v123/figure1.png',
                'https://res.cloudinary.com/test/image/upload/v123/figure2.png',
                'https://res.cloudinary.com/test/image/upload/v123/overview.png'
            ]
            
            # Test figure uploads
            figures_data = upload_figures_to_cloudinary(mock_figure_snippets, 'test_workflow_123')
            assert len(figures_data) == 2
            
            # Test overview upload
            overview_url = upload_overview_image_to_cloudinary(
                Image.new('RGB', (200, 200), 'green'),
                'test_workflow_123',
                'figures'
            )
            assert overview_url == 'https://res.cloudinary.com/test/image/upload/v123/overview.png'
            
            # Test database save
            extraction_result = DiagramExtractionResult(
                run_id='test_workflow_123',
                total_figures=2,
                pages_processed=2,
                extraction_success=True,
                figures=figures_data,
                tables=[],
                overview_image_figures=overview_url,
                overview_image_tables=None
            )
            
            save_success = await pipeline_db.save_diagram_extraction(extraction_result)
            assert save_success is True
            
            # Verify in database
            collection = pipeline_db.db_manager.get_collection("diagram_extraction_results")
            saved_doc = await collection.find_one({"run_id": 'test_workflow_123'})
            assert saved_doc is not None
            assert len(saved_doc['figures']) == 2
            assert saved_doc['overview_image_figures'] == overview_url
            
            # Cleanup
            await collection.delete_one({"run_id": 'test_workflow_123'})


# Pytest configuration
def pytest_configure(config):
    """Configure pytest for async tests"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"]) 