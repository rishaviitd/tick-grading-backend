"""
Cloudinary utilities for question parsing module

This module provides functions for uploading extracted figures and overview images
to Cloudinary and returning their URLs.
"""

import os
import io
import tempfile
from typing import List, Dict, Any, Optional
from PIL import Image
import cloudinary.uploader
import cloudinary
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)


def upload_image_to_cloudinary(image: Image.Image, filename: str, folder: str = "question_parsing") -> Optional[str]:
    """
    Upload a PIL Image to Cloudinary and return the URL
    
    Args:
        image: PIL Image object to upload
        filename: Name for the uploaded file
        folder: Cloudinary folder path (default: "question_parsing")
    
    Returns:
        Cloudinary URL if successful, None if failed
    """
    try:
        # Convert PIL Image to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG', optimize=True)
        img_buffer.seek(0)
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            img_buffer,
            public_id=f"{folder}/{filename}",
            resource_type="image",
            format="png",
            overwrite=True
        )
        
        return upload_result.get('secure_url')
        
    except Exception as e:
        print(f"Failed to upload {filename} to Cloudinary: {str(e)}")
        return None


def upload_figures_to_cloudinary(figure_snippets: List[List[Image.Image]], run_id: str) -> List[Dict[str, Any]]:
    """
    Upload all extracted figures to Cloudinary and return structured data
    
    Args:
        figure_snippets: List of lists of PIL Images (pages -> figures)
        run_id: Unique run identifier for organizing uploads
    
    Returns:
        List of dictionaries containing figure metadata and Cloudinary URLs
    """
    figures_data = []
    figure_counter = 1
    
    for page_idx, page_figures in enumerate(figure_snippets):
        for fig_idx, figure_img in enumerate(page_figures):
            # Generate filename
            filename = f"step1_page_{page_idx+1}_figure_{fig_idx+1}.png"
            
            # Upload to Cloudinary
            cloudinary_url = upload_image_to_cloudinary(
                figure_img, 
                filename, 
                folder=f"question_parsing/{run_id}/figures"
            )
            
            if cloudinary_url:
                figure_data = {
                    "cloudinary_url": cloudinary_url,
                    "page_number": page_idx + 1,
                    "figure_id": fig_idx + 1,
                    "file_name": filename,
                    "figure_counter": figure_counter
                }
                figures_data.append(figure_data)
                figure_counter += 1
            else:
                print(f"Warning: Failed to upload figure {filename}")
    
    return figures_data


def upload_tables_to_cloudinary(table_snippets: List[List[Image.Image]], run_id: str) -> List[Dict[str, Any]]:
    """
    Upload all extracted tables to Cloudinary and return structured data
    
    Args:
        table_snippets: List of lists of PIL Images (pages -> tables)
        run_id: Unique run identifier for organizing uploads
    
    Returns:
        List of dictionaries containing table metadata and Cloudinary URLs
    """
    tables_data = []
    table_counter = 1
    
    for page_idx, page_tables in enumerate(table_snippets):
        for table_idx, table_img in enumerate(page_tables):
            # Generate filename
            filename = f"step1_page_{page_idx+1}_table_{table_idx+1}.png"
            
            # Upload to Cloudinary
            cloudinary_url = upload_image_to_cloudinary(
                table_img, 
                filename, 
                folder=f"question_parsing/{run_id}/tables"
            )
            
            if cloudinary_url:
                table_data = {
                    "cloudinary_url": cloudinary_url,
                    "page_number": page_idx + 1,
                    "table_id": table_idx + 1,
                    "file_name": filename,
                    "table_counter": table_counter
                }
                tables_data.append(table_data)
                table_counter += 1
            else:
                print(f"Warning: Failed to upload table {filename}")
    
    return tables_data


def upload_overview_image_to_cloudinary(overview_image: Image.Image, run_id: str, image_type: str = "figures") -> Optional[str]:
    """
    Upload overview image to Cloudinary
    
    Args:
        overview_image: PIL Image of the overview
        run_id: Unique run identifier
        image_type: Type of overview ("figures" or "tables")
    
    Returns:
        Cloudinary URL if successful, None if failed
    """
    filename = f"step1_overview_image_{image_type}.png"
    
    return upload_image_to_cloudinary(
        overview_image,
        filename,
        folder=f"question_parsing/{run_id}/overviews"
    )


def cleanup_cloudinary_folder(folder_path: str) -> bool:
    """
    Clean up Cloudinary folder (for testing/development)
    
    Args:
        folder_path: Cloudinary folder path to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Note: This will delete all resources in the folder
        result = cloudinary.api.delete_resources_by_prefix(folder_path)
        print(f"Cleaned up Cloudinary folder: {folder_path}")
        return True
    except Exception as e:
        print(f"Failed to cleanup Cloudinary folder {folder_path}: {str(e)}")
        return False 