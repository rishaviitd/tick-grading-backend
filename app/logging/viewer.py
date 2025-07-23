"""
Log Viewer for Unified Logging System

This module handles the presentation and rendering of logs through web interfaces.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
from .logger import LogType, UnifiedLogger

class LogViewer:
    """Handles the viewing and presentation of unified logs"""
    
    def __init__(self, logger: Optional[UnifiedLogger] = None):
        self.logger = logger or UnifiedLogger()
    
    def get_runs_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all runs organized by log type category"""
        all_runs = self.logger.get_all_runs()
        
        categories = {
            "response_processing": [],
            "diagram_extraction": [],
            "diagram_mapping": [],
            "question_extraction": [],
            "margin_analysis": [],
            "error": [],
            "other": []
        }
        
        for run in all_runs:
            log_type = run.get("log_type", "other")
            if log_type in categories:
                categories[log_type].append(run)
            else:
                categories["other"].append(run)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def generate_runs_index_context(self) -> Dict[str, Any]:
        """Generate context for the runs index template"""
        categorized_runs = self.get_runs_by_category()
        
        # Add display metadata for each category
        category_info = {
            "response_processing": {
                "title": "📋 Response Processing",
                "description": "Student response analysis and margin cropping"
            },
            "diagram_extraction": {
                "title": "🎨 Diagram Extraction", 
                "description": "Document diagram detection and extraction"
            },
            "diagram_mapping": {
                "title": "🔗 Diagram Mapping",
                "description": "Mapping diagrams to questions"
            },
            "question_extraction": {
                "title": "📝 Question Extraction",
                "description": "Question text extraction and formatting"
            },
            "margin_analysis": {
                "title": "📊 Margin Analysis",
                "description": "Margin detection and answer parsing"
            },
            "error": {
                "title": "❌ Error Logs",
                "description": "Failed processing attempts"
            },
            "other": {
                "title": "📁 Other Logs",
                "description": "Miscellaneous processing logs"
            }
        }
        
        return {
            "categories": categorized_runs,
            "category_info": category_info,
            "total_runs": sum(len(runs) for runs in categorized_runs.values())
        }
    
    def generate_run_detail_context(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Generate context for a specific run detail view"""
        metadata = self.logger.get_run_metadata(run_id)
        if not metadata:
            return None
        
        log_type = metadata.get("log_type", "other")
        
        # Generate appropriate context based on log type
        context = {
            "metadata": metadata,
            "run_id": run_id,
            "log_type": log_type,
            "static_url": f"/logs/static/{run_id}/"
        }
        
        # Add type-specific context
        if log_type == "response_processing":
            context.update(self._generate_response_processing_context(metadata))
        elif log_type == "diagram_extraction":
            context.update(self._generate_diagram_extraction_context(metadata))
        elif log_type in ["diagram_mapping", "question_extraction"]:
            context.update(self._generate_file_listing_context(metadata))
        
        return context
    
    def _generate_response_processing_context(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate context specific to response processing logs"""
        return {
            "template_type": "response_processing",
            "pages": metadata.get("pages", []),
            "merged": metadata.get("merged", []),
            "urls": metadata.get("urls", [])
        }
    
    def _generate_diagram_extraction_context(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate context specific to diagram extraction logs"""
        # Organize files by page for diagram extraction
        files_by_page = {}
        for file_info in metadata.get("files", []):
            if file_info.get("type") == "image":
                # Extract page number from filename (e.g., page_1_figure_1.png)
                filename = file_info["filename"]
                if filename.startswith("page_"):
                    try:
                        page_num = int(filename.split("_")[1])
                        if page_num not in files_by_page:
                            files_by_page[page_num] = []
                        files_by_page[page_num].append(file_info)
                    except (IndexError, ValueError):
                        # Handle malformed filenames
                        if "other" not in files_by_page:
                            files_by_page["other"] = []
                        files_by_page["other"].append(file_info)
        
        return {
            "template_type": "diagram_extraction",
            "files_by_page": files_by_page,
            "total_figures": metadata.get("data", {}).get("total_figures", 0),
            "total_pages": metadata.get("data", {}).get("total_pages", 0)
        }
    
    def _generate_file_listing_context(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate context for file listing (mappings, questions, etc.)"""
        return {
            "template_type": "file_listing",
            "files": metadata.get("files", [])
        }

    def get_template_name(self, log_type: str) -> str:
        """Get the appropriate template name for a log type"""
        template_mapping = {
            "response_processing": "unified_log.html",
            "diagram_extraction": "unified_log.html", 
            "diagram_mapping": "unified_log.html",
            "question_extraction": "unified_log.html",
            "margin_analysis": "unified_log.html",
            "error": "unified_log.html",
            "other": "unified_log.html"
        }
        
        return template_mapping.get(log_type, "unified_log.html") 