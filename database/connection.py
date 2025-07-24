"""
MongoDB Connection and Database Operations for TickAI

This module handles MongoDB connection, database operations, and data persistence
for the CBSE processing pipeline results using Motor for async operations.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from dotenv import load_dotenv
import logging

from .schema import (
    PipelineResult, DiagramExtractionResult, DiagramMappingResult,
    QuestionExtractionResult, MarksMappingResult, Question, ResponseProcessingResult,
    COLLECTION_NAMES, INDEXES
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connection and operations using Motor"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._collections: Dict[str, AsyncIOMotorCollection] = {}
        
    async def connect(self) -> bool:
        """Establish connection to MongoDB"""
        try:
            # Get MongoDB connection string from environment
            mongo_uri = os.getenv('MONGODB_URI')
            if not mongo_uri:
                logger.error("MONGODB_URI environment variable not set")
                return False
            
            # Get database name from environment
            db_name = os.getenv('MONGODB_DATABASE', 'tickai')
            
            # Connect to MongoDB using Motor
            self.client = AsyncIOMotorClient(mongo_uri)
            self.db = self.client[db_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB database: {db_name}")
            
            # Initialize collections and indexes
            await self._initialize_collections()
            await self._create_indexes()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    async def _initialize_collections(self):
        """Initialize database collections"""
        for collection_name in COLLECTION_NAMES.values():
            self._collections[collection_name] = self.db[collection_name]
    
    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            for collection_name, indexes in INDEXES.items():
                collection = self._collections[collection_name]
                for index_fields in indexes:
                    await collection.create_index(index_fields)
                logger.info(f"Created indexes for collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    def get_collection(self, collection_name: str) -> Optional[AsyncIOMotorCollection]:
        """Get a specific collection by name"""
        return self._collections.get(collection_name)
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.client is not None and self.db is not None


class PipelineDatabase:
    """Database operations for pipeline results using async Motor operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def save_pipeline_result(self, pipeline_result: PipelineResult) -> bool:
        """Save complete pipeline result"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["pipeline_results"])
            if collection is None:
                logger.error("Pipeline results collection not found")
                return False
            
            # Convert to dict and handle ObjectId
            data = pipeline_result.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            # Insert document
            result = await collection.insert_one(data)
            logger.info(f"Saved pipeline result with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save pipeline result: {e}")
            return False
    
    async def save_diagram_extraction(self, extraction_result: DiagramExtractionResult) -> bool:
        """Save diagram extraction results"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["diagram_extraction"])
            if collection is None:
                logger.error("Diagram extraction collection not found")
                return False
            
            data = extraction_result.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved diagram extraction result with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save diagram extraction result: {e}")
            return False
    
    async def save_diagram_mapping(self, mapping_result: DiagramMappingResult) -> bool:
        """Save diagram mapping results"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["diagram_mapping"])
            if collection is None:
                logger.error("Diagram mapping collection not found")
                return False
            
            data = mapping_result.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved diagram mapping result with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save diagram mapping result: {e}")
            return False
    
    async def save_question_extraction(self, extraction_result: QuestionExtractionResult) -> bool:
        """Save question extraction results"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["question_extraction"])
            if collection is None:
                logger.error("Question extraction collection not found")
                return False
            
            data = extraction_result.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved question extraction result with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save question extraction result: {e}")
            return False
    
    async def save_marks_mapping(self, mapping_result: MarksMappingResult) -> bool:
        """Save marks mapping results"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["marks_mapping"])
            if collection is None:
                logger.error("Marks mapping collection not found")
                return False
            
            data = mapping_result.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved marks mapping result with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save marks mapping result: {e}")
            return False
    
    async def save_question(self, question: Question) -> bool:
        """Save a combined question to database"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["questions"])
            if collection is None:
                logger.error("Questions collection not found")
                return False
            
            # Convert to dict and ensure run_id is set
            data = question.dict(by_alias=True)
            if not data.get("run_id"):
                logger.error("Question must have run_id")
                return False
            
            result = await collection.insert_one(data)
            logger.info(f"Saved question with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save question: {e}")
            return False
    
    async def save_response_processing(self, response_result: ResponseProcessingResult) -> bool:
        """Save response processing results to database"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["response_processing"])
            if collection is None:
                logger.error("Response processing collection not found")
                return False
            
            # Convert to dict and handle ObjectId
            data = response_result.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved response processing result with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save response processing result: {e}")
            return False
    
    async def get_pipeline_by_run_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get pipeline result by run_id"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["pipeline_results"])
            if collection is None:
                return None
            
            result = await collection.find_one({"run_id": run_id})
            return result
            
        except Exception as e:
            logger.error(f"Failed to get pipeline by run_id: {e}")
            return None
    
    async def get_step_results_by_run_id(self, run_id: str, step: str) -> Optional[Dict[str, Any]]:
        """Get specific step results by run_id and step name"""
        try:
            collection_name = COLLECTION_NAMES.get(step)
            if not collection_name:
                logger.error(f"Unknown step: {step}")
                return None
            
            collection = self.db_manager.get_collection(collection_name)
            if collection is None:
                return None
            
            result = await collection.find_one({"run_id": run_id})
            return result
            
        except Exception as e:
            logger.error(f"Failed to get step results: {e}")
            return None
    
    async def get_all_pipelines(self, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        """Get all pipeline results with pagination"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["pipeline_results"])
            if collection is None:
                return []
            
            cursor = collection.find().sort("created_at", -1).skip(skip).limit(limit)
            results = await cursor.to_list(length=limit)
            return results
            
        except Exception as e:
            logger.error(f"Failed to get all pipelines: {e}")
            return []
    
    async def update_pipeline_status(self, run_id: str, status: str) -> bool:
        """Update pipeline status"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["pipeline_results"])
            if collection is None:
                return False
            
            result = await collection.update_one(
                {"run_id": run_id},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow(),
                        "completed_at": datetime.utcnow() if status == "completed" else None
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated pipeline status to {status} for run_id: {run_id}")
                return True
            else:
                logger.warning(f"No pipeline found with run_id: {run_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update pipeline status: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()
pipeline_db = PipelineDatabase(db_manager)


async def initialize_database() -> bool:
    """Initialize database connection"""
    return await db_manager.connect()


async def close_database():
    """Close database connection"""
    await db_manager.disconnect() 