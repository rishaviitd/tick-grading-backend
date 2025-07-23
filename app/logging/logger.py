"""
Unified Logger for TickAI Backend

This module provides a centralized logging system that handles all types of
processing logs in a consistent manner.
"""

import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import cv2
import numpy as np
from PIL import Image

class LogType(Enum):
    """Types of logs supported by the unified logger"""
    RESPONSE_PROCESSING = "response_processing"
    DIAGRAM_EXTRACTION = "diagram_extraction"
    DIAGRAM_MAPPING = "diagram_mapping"
    QUESTION_EXTRACTION = "question_extraction"
    MARKS_MAPPING = "marks_mapping"
    MARGIN_ANALYSIS = "margin_analysis"
    ERROR = "error"

class LogEntry:
    """Represents a single log entry with metadata"""
    
    def __init__(self, 
                 log_type: LogType, 
                 title: str, 
                 data: Dict[str, Any],
                 run_id: Optional[str] = None):
        self.log_type = log_type
        self.title = title
        self.data = data
        self.run_id = run_id or self._generate_run_id()
        self.timestamp = datetime.now().isoformat()
        
    def _generate_run_id(self) -> str:
        """Generate a unique run ID"""
        return uuid.uuid4().hex[:12]

class UnifiedLogger:
    """Centralized logging system for all TickAI backend operations"""
    
    def __init__(self, logs_root: Optional[Path] = None):
        if logs_root is None:
            # Default to project root logs directory
            self.logs_root = Path(__file__).parent.parent.parent / "logs"
        else:
            self.logs_root = Path(logs_root)
        
        self.logs_root.mkdir(parents=True, exist_ok=True)
        
    def create_run(self, log_type: LogType, title: str, data: Optional[Dict] = None) -> str:
        """Create a new logging run and return the run ID"""
        if data is None:
            data = {}
            
        run_id = uuid.uuid4().hex[:12]
        
        # Create run directory
        run_dir = self.logs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metadata
        metadata = {
            "run_id": run_id,
            "log_type": log_type.value,
            "title": title,
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "steps": [],
            "files": [],
            "data": data
        }
        
        # Save initial metadata
        self._save_metadata(run_id, metadata)
        
        return run_id
    
    def log_step(self, run_id: str, step_name: str, input_data: Any = None, output_data: Any = None):
        """Log a processing step for a run"""
        metadata = self._load_metadata(run_id)
        
        step = {
            "name": step_name,
            "timestamp": datetime.now().isoformat(),
            "input": self._serialize_data(input_data),
            "output": self._serialize_data(output_data)
        }
        
        metadata["steps"].append(step)
        self._save_metadata(run_id, metadata)
    
    def log_error(self, run_id: str, error_msg: str, exception: Optional[Exception] = None):
        """Log an error for a run"""
        metadata = self._load_metadata(run_id)
        
        error_data = {
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        
        if exception:
            error_data["exception_type"] = type(exception).__name__
            error_data["exception_details"] = str(exception)
        
        if "errors" not in metadata:
            metadata["errors"] = []
        
        metadata["errors"].append(error_data)
        metadata["status"] = "error"
        self._save_metadata(run_id, metadata)
    
    def save_image(self, run_id: str, image: Union[np.ndarray, Image.Image], 
                   filename: str, subfolder: str = "images") -> str:
        """Save an image file and return the relative path"""
        run_dir = self.logs_root / run_id
        img_dir = run_dir / subfolder
        img_dir.mkdir(parents=True, exist_ok=True)
        
        img_path = img_dir / filename
        
        if isinstance(image, np.ndarray):
            # OpenCV image (BGR)
            cv2.imwrite(str(img_path), image)
        elif isinstance(image, Image.Image):
            # PIL image
            image.save(str(img_path))
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")
        
        # Update metadata with file info
        metadata = self._load_metadata(run_id)
        file_info = {
            "filename": filename,
            "subfolder": subfolder,
            "path": f"{subfolder}/{filename}",
            "type": "image",
            "timestamp": datetime.now().isoformat()
        }
        
        metadata["files"].append(file_info)
        self._save_metadata(run_id, metadata)
        
        return f"{subfolder}/{filename}"
    
    def save_file(self, run_id: str, content: Union[str, bytes], 
                  filename: str, subfolder: str = "files") -> str:
        """Save a text or binary file and return the relative path"""
        run_dir = self.logs_root / run_id
        file_dir = run_dir / subfolder
        file_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = file_dir / filename
        
        if isinstance(content, str):
            file_path.write_text(content, encoding='utf-8')
            file_type = "text"
        else:
            file_path.write_bytes(content)
            file_type = "binary"
        
        # Update metadata with file info
        metadata = self._load_metadata(run_id)
        file_info = {
            "filename": filename,
            "subfolder": subfolder,
            "path": f"{subfolder}/{filename}",
            "type": file_type,
            "timestamp": datetime.now().isoformat()
        }
        
        metadata["files"].append(file_info)
        self._save_metadata(run_id, metadata)
        
        return f"{subfolder}/{filename}"
    
    def update_data(self, run_id: str, key: str, value: Any):
        """Update data field for a run"""
        metadata = self._load_metadata(run_id)
        metadata["data"][key] = self._serialize_data(value)
        self._save_metadata(run_id, metadata)
    
    def complete_run(self, run_id: str, success: bool = True):
        """Mark a run as completed"""
        metadata = self._load_metadata(run_id)
        metadata["status"] = "completed" if success else "failed"
        metadata["completed_at"] = datetime.now().isoformat()
        self._save_metadata(run_id, metadata)
    
    def get_all_runs(self) -> List[Dict[str, Any]]:
        """Get metadata for all runs"""
        runs = []
        
        for run_dir in self.logs_root.iterdir():
            if run_dir.is_dir():
                metadata_file = run_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        metadata = json.loads(metadata_file.read_text())
                        runs.append(metadata)
                    except json.JSONDecodeError:
                        # Skip invalid metadata files
                        continue
        
        # Sort by timestamp (newest first)
        runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return runs
    
    def get_run_metadata(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific run"""
        try:
            return self._load_metadata(run_id)
        except FileNotFoundError:
            return None
    
    def get_run_dir(self, run_id: str) -> str:
        """Get the directory path for a specific run"""
        return str(self.logs_root / run_id)
    
    def _load_metadata(self, run_id: str) -> Dict[str, Any]:
        """Load metadata for a run"""
        metadata_file = self.logs_root / run_id / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata not found for run {run_id}")
        
        return json.loads(metadata_file.read_text())
    
    def _save_metadata(self, run_id: str, metadata: Dict[str, Any]):
        """Save metadata for a run"""
        metadata_file = self.logs_root / run_id / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
    
    def _serialize_data(self, data: Any) -> Any:
        """Serialize data for JSON storage"""
        if data is None:
            return None
        elif isinstance(data, (str, int, float, bool, list, dict)):
            return data
        elif isinstance(data, bytes):
            return {"_type": "bytes", "_length": len(data)}
        elif isinstance(data, np.ndarray):
            return {"_type": "numpy_array", "_shape": data.shape, "_dtype": str(data.dtype)}
        elif hasattr(data, '__dict__'):
            return {"_type": type(data).__name__, "_repr": repr(data)}
        else:
            return str(data)

# Legacy compatibility functions for existing code
def log_diagram_snippets(figure_snippets: List[List]) -> tuple[str, str]:
    """Legacy compatibility function for diagram logging"""
    logger = UnifiedLogger()
    
    run_id = logger.create_run(
        LogType.DIAGRAM_EXTRACTION,
        "Diagram Extraction",
        {
            "total_pages": len(figure_snippets),
            "total_figures": sum(len(figs) for figs in figure_snippets)
        }
    )
    
    # Save each figure
    for page_idx, page_figures in enumerate(figure_snippets):
        for fig_idx, figure_img in enumerate(page_figures):
            filename = f'page_{page_idx+1}_figure_{fig_idx+1}.png'
            logger.save_image(run_id, figure_img, filename)
    
    logger.complete_run(run_id)
    
    run_dir = logger.logs_root / run_id
    metadata_file = run_dir / "metadata.json"
    return str(run_dir), str(metadata_file) 