"""
MongoDB Connection and Database Operations for TickAI

This module handles MongoDB connection, database operations, and data persistence
for the CBSE processing pipeline results using Motor for async operations.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from dotenv import load_dotenv
import logging

from .schema import (
    # Core business logic schemas
    Teacher, Student, Assignment, Question, StudentResponse, StudentAssignmentResponse, QuestionResponseMapping,
    Diagram, Table, VisualContent, QuestionContent,
    
    # Collection names and indexes
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
                try:
                    # Create a dummy document to ensure collection exists
                    # This will be deleted immediately after index creation
                    dummy_doc = {"_dummy": True, "created_at": datetime.utcnow()}
                    await collection.insert_one(dummy_doc)
                    
                    # Create indexes
                    for index_fields in indexes:
                        await collection.create_index(index_fields)
                    logger.info(f"Created indexes for collection: {collection_name}")
                    
                    # Remove the dummy document
                    await collection.delete_one({"_dummy": True})
                    
                except Exception as index_error:
                    # Log the error but don't fail the entire connection
                    logger.warning(f"Could not create indexes for collection {collection_name}: {index_error}")
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
    

    
    async def save_question(self, question: Question) -> Optional[str]:
        """Save a combined question to database and return the question ID"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["questions"])
            if collection is None:
                logger.error("Questions collection not found")
                return None
            
            # Convert to dict and ensure run_id is set
            data = question.dict(by_alias=True)
            if not data.get("run_id"):
                logger.error("Question must have run_id")
                return None
            
            result = await collection.insert_one(data)
            logger.info(f"Saved question with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save question: {e}")
            return None
    
    async def save_diagram(self, diagram: Diagram) -> Optional[str]:
        """Save a diagram to database and return the diagram ID"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["diagrams"])
            if collection is None:
                logger.error("Diagrams collection not found")
                return None
            
            # Convert to dict and handle ObjectId
            data = diagram.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved diagram with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save diagram: {e}")
            return None
    
    async def save_table(self, table: Table) -> Optional[str]:
        """Save a table to database and return the table ID"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["tables"])
            if collection is None:
                logger.error("Tables collection not found")
                return None
            
            # Convert to dict and handle ObjectId
            data = table.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved table with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save table: {e}")
            return None
    
    async def save_visual_content(self, visual_content: VisualContent) -> Optional[str]:
        """Save visual content to database"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["visual_content"])
            if collection is None:
                logger.error("Visual content collection not found")
                return None
            
            # Convert to dict and handle ObjectId
            data = visual_content.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            # Insert document
            result = await collection.insert_one(data)
            logger.info(f"Saved visual content with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save visual content: {e}")
            return None
    
    async def save_question_content(self, question_content: QuestionContent) -> Optional[str]:
        """Save question content to database"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["question_content"])
            if collection is None:
                logger.error("Question content collection not found")
                return None
            
            # Convert to dict and handle ObjectId
            data = question_content.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            # Insert document
            result = await collection.insert_one(data)
            logger.info(f"Saved question content with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save question content: {e}")
            return None
    

    
    async def update_diagram_mapping(self, diagram_id: str, question_identifier: str, choice_location: str) -> bool:
        """Update diagram with mapping data"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["diagrams"])
            if collection is None:
                logger.error("Diagrams collection not found")
                return False
            
            result = await collection.update_one(
                {"_id": ObjectId(diagram_id)},
                {
                    "$set": {
                        "question_identifier": question_identifier,
                        "choice_location": choice_location
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update diagram mapping: {e}")
            return False
    
    async def update_table_mapping(self, table_id: str, question_identifier: str, choice_location: str) -> bool:
        """Update table with mapping data"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["tables"])
            if collection is None:
                logger.error("Tables collection not found")
                return False
            
            result = await collection.update_one(
                {"_id": ObjectId(table_id)},
                {
                    "$set": {
                        "question_identifier": question_identifier,
                        "choice_location": choice_location
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update table mapping: {e}")
            return False
    
    async def get_diagram_by_figure_id(self, run_id: str, figure_id: int) -> Optional[Dict[str, Any]]:
        """Get diagram by run_id and figure_id"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["diagrams"])
            if collection is None:
                logger.error("Diagrams collection not found")
                return None
            
            result = await collection.find_one({
                "run_id": run_id,
                "figure_id": figure_id
            })
            return result
            
        except Exception as e:
            logger.error(f"Failed to get diagram by figure_id: {e}")
            return None
    
    async def get_table_by_table_id(self, run_id: str, table_id: int) -> Optional[Dict[str, Any]]:
        """Get table by run_id and table_id"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["tables"])
            if collection is None:
                logger.error("Tables collection not found")
                return None
            
            result = await collection.find_one({
                "run_id": run_id,
                "table_id": table_id
            })
            return result
            
        except Exception as e:
            logger.error(f"Failed to get table by table_id: {e}")
            return None
    
    async def get_diagram_by_url(self, run_id: str, cloudinary_url: str) -> Optional[Dict[str, Any]]:
        """Get diagram by run_id and cloudinary_url"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["diagrams"])
            if collection is None:
                logger.error("Diagrams collection not found")
                return None
            
            result = await collection.find_one({
                "run_id": run_id,
                "cloudinary_url": cloudinary_url
            })
            return result
            
        except Exception as e:
            logger.error(f"Failed to get diagram by URL: {e}")
            return None
    
    async def get_diagrams_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all diagrams for a specific run_id"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["diagrams"])
            if collection is None:
                logger.error("Diagrams collection not found")
                return []
            
            cursor = collection.find({"run_id": run_id}).sort("figure_id", 1)
            results = await cursor.to_list(length=None)
            return results
            
        except Exception as e:
            logger.error(f"Failed to get diagrams by run_id: {e}")
            return []
    
    async def get_tables_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all tables for a specific run_id"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["tables"])
            if collection is None:
                logger.error("Tables collection not found")
                return []
            
            cursor = collection.find({"run_id": run_id}).sort("table_id", 1)
            results = await cursor.to_list(length=None)
            return results
            
        except Exception as e:
            logger.error(f"Failed to get tables by run_id: {e}")
            return []
    
    async def get_diagram_by_identifier(self, diagram_identifier: str) -> Optional[Dict[str, Any]]:
        """Get diagram by diagram_identifier from the diagrams collection"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["diagrams"])
            if collection is None:
                logger.error("Diagrams collection not found")
                return None
            
            # Find diagram by diagram_identifier
            diagram = await collection.find_one({"diagram_identifier": diagram_identifier})
            if diagram:
                logger.info(f"Found diagram with identifier: {diagram_identifier}")
                return diagram
            else:
                logger.warning(f"No diagram found with identifier: {diagram_identifier}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get diagram by identifier: {e}")
            return None
    
    async def get_table_by_identifier(self, table_identifier: str) -> Optional[Dict[str, Any]]:
        """Get table by table_identifier from the tables collection"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["tables"])
            if collection is None:
                logger.error("Tables collection not found")
                return None
            
            # Find table by table_identifier
            table = await collection.find_one({"table_identifier": table_identifier})
            if table:
                logger.info(f"Found table with identifier: {table_identifier}")
                return table
            else:
                logger.warning(f"No table found with identifier: {table_identifier}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get table by identifier: {e}")
            return None
    

    
    async def save_question_response_mapping(self, mapping: QuestionResponseMapping) -> Optional[str]:
        """Save question-response mapping to database and return the mapping ID"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["question_response_mappings"])
            if collection is None:
                logger.error("Question response mapping collection not found")
                return None
            
            # Convert to dict and handle ObjectId
            data = mapping.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved question-response mapping with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save question-response mapping: {e}")
            return None
    
    async def get_question_response_mappings_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all question-response mappings for a specific run_id"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["question_response_mappings"])
            if collection is None:
                logger.error("Question response mapping collection not found")
                return []
            
            cursor = collection.find({"run_id": run_id})
            results = await cursor.to_list(length=None)
            return results
            
        except Exception as e:
            logger.error(f"Failed to get question-response mappings: {e}")
            return []
    
    async def get_question_response_mapping_by_question_id(self, run_id: str, question_identifier: str) -> Optional[Dict[str, Any]]:
        """Get question-response mapping for a specific question identifier"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["question_response_mappings"])
            if collection is None:
                logger.error("Question response mapping collection not found")
                return None
            
            result = await collection.find_one({
                "run_id": run_id
            })
            return result
            
        except Exception as e:
            logger.error(f"Failed to get question-response mapping: {e}")
            return None
    
    async def get_questions_by_run_id(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all questions for a specific run_id"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["questions"])
            if collection is None:
                logger.error("Questions collection not found")
                return []
            
            cursor = collection.find({"run_id": run_id})
            results = await cursor.to_list(length=None)
            return results
            
        except Exception as e:
            logger.error(f"Failed to get questions: {e}")
            return []
    
    async def get_responses_by_run_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get student assignment response for a specific run_id"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["student_assignment_responses"])
            if collection is None:
                logger.error("Student assignment responses collection not found")
                return None
            
            result = await collection.find_one({"run_id": run_id})
            return result
            
        except Exception as e:
            logger.error(f"Failed to get student assignment responses: {e}")
            return None
    


    # =============================================================================
    # CORE BUSINESS LOGIC METHODS
    # =============================================================================
    
    async def save_teacher(self, teacher: Teacher) -> bool:
        """Save teacher to database"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["teachers"])
            if collection is None:
                logger.error("Teachers collection not found")
                return False
            
            # Convert to dict and handle ObjectId
            data = teacher.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved teacher with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save teacher: {e}")
            return False
    
    async def save_student(self, student: Student) -> bool:
        """Save student to database"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["students"])
            if collection is None:
                logger.error("Students collection not found")
                return False
            
            # Convert to dict and handle ObjectId
            data = student.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved student with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save student: {e}")
            return False
    
    async def save_assignment(self, assignment: Assignment) -> Optional[str]:
        """Save assignment to database and return the assignment ID"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["assignments"])
            if collection is None:
                logger.error("Assignments collection not found")
                return None
            
            # Convert to dict and handle ObjectId
            data = assignment.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved assignment with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save assignment: {e}")
            return None
    
    async def update_assignment_questions(self, assignment_id: str, question_ids: List[str]) -> bool:
        """Update the questions array in an assignment"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["assignments"])
            if collection is None:
                logger.error("Assignments collection not found")
                return False
            
            # Try with string ID first (since our Pydantic models use string IDs)
            result = await collection.update_one(
                {"_id": assignment_id},
                {
                    "$set": {
                        "questions": question_ids,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated assignment questions for assignment_id: {assignment_id}")
                return True
            else:
                # Try with ObjectId as fallback
                try:
                    from bson import ObjectId
                    result = await collection.update_one(
                        {"_id": ObjectId(assignment_id)},
                        {
                            "$set": {
                                "questions": question_ids,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        logger.info(f"Updated assignment questions for assignment_id: {assignment_id} (ObjectId)")
                        return True
                except Exception:
                    pass
                
                logger.warning(f"No assignment found with ID: {assignment_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update assignment questions: {e}")
            return False
    
    async def update_assignment_visual_content(self, assignment_id: str, visual_content_id: str) -> bool:
        """Update the visual_content_id in an assignment"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["assignments"])
            if collection is None:
                logger.error("Assignments collection not found")
                return False
            
            # Try with string ID first (since our Pydantic models use string IDs)
            result = await collection.update_one(
                {"_id": assignment_id},
                {
                    "$set": {
                        "visual_content_id": visual_content_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated assignment visual content for assignment_id: {assignment_id}")
                return True
            else:
                # Try with ObjectId as fallback
                try:
                    from bson import ObjectId
                    result = await collection.update_one(
                        {"_id": ObjectId(assignment_id)},
                        {
                            "$set": {
                                "visual_content_id": visual_content_id,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        logger.info(f"Updated assignment visual content for assignment_id: {assignment_id} (ObjectId)")
                        return True
                except Exception:
                    pass
                
                logger.warning(f"No assignment found with ID: {assignment_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update assignment visual content: {e}")
            return False
    
    async def update_assignment_question_content(self, assignment_id: str, question_content_id: str) -> bool:
        """Update the question_content_id in an assignment"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["assignments"])
            if collection is None:
                logger.error("Assignments collection not found")
                return False
            
            # Try with string ID first (since our Pydantic models use string IDs)
            result = await collection.update_one(
                {"_id": assignment_id},
                {
                    "$set": {
                        "question_content_id": question_content_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated assignment question content for assignment_id: {assignment_id}")
                return True
            else:
                # Try with ObjectId as fallback
                try:
                    from bson import ObjectId
                    result = await collection.update_one(
                        {"_id": ObjectId(assignment_id)},
                        {
                            "$set": {
                                "question_content_id": question_content_id,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        logger.info(f"Updated assignment question content for assignment_id: {assignment_id} (ObjectId)")
                        return True
                except Exception:
                    pass
                
                logger.warning(f"No assignment found with ID: {assignment_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update assignment question content: {e}")
            return False
    
    async def update_assignment_marks_content(self, assignment_id: str, marks_content_id: str) -> bool:
        """Update the marks_content_id in an assignment"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["assignments"])
            if collection is None:
                logger.error("Assignments collection not found")
                return False
            
            # Try with string ID first (since our Pydantic models use string IDs)
            result = await collection.update_one(
                {"_id": assignment_id},
                {
                    "$set": {
                        "marks_content_id": marks_content_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated assignment marks content for assignment_id: {assignment_id}")
                return True
            else:
                # Try with ObjectId as fallback
                try:
                    from bson import ObjectId
                    result = await collection.update_one(
                        {"_id": ObjectId(assignment_id)},
                        {
                            "$set": {
                                "marks_content_id": marks_content_id,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        logger.info(f"Updated assignment marks content for assignment_id: {assignment_id} (ObjectId)")
                        return True
                except Exception:
                    pass
                
                logger.warning(f"No assignment found with ID: {assignment_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update assignment marks content: {e}")
            return False
    
    async def save_student_assignment_response(self, response: StudentAssignmentResponse) -> bool:
        """Save student assignment response to database"""
        try:
            collection = self.db_manager.get_collection(COLLECTION_NAMES["student_assignment_responses"])
            if collection is None:
                logger.error("Student assignment responses collection not found")
                return False
            
            # Convert to dict and handle ObjectId
            data = response.dict(by_alias=True)
            if data.get("_id") is None:
                data.pop("_id", None)
            
            result = await collection.insert_one(data)
            logger.info(f"Saved student assignment response with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save student assignment response: {e}")
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