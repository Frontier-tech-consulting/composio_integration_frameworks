from typing import List, Dict, Any, Optional
import logging
import pinecone
import os
import time
import uuid
from ..exceptions import (
    ConfigurationError, DatabaseConnectionError, StoreVectorError,
    QueryVectorError, DeleteVectorError, DiscussionNotFoundError,
    UserDiscussionAccessError
)

logger = logging.getLogger(__name__)

class PineconeVectorDB:
    """
    Vector database implementation using Pinecone.
    
    This class provides methods to store and query vectors in Pinecone.
    """
    
    def __init__(self, api_key: str = None, environment: str = None, 
                 index_name: str = None, dimension: int = 16, 
                 namespace: str = 'discussions'):
        """
        Initialize the Pinecone vector database.
        
        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            environment: Pinecone environment (defaults to PINECONE_ENVIRONMENT env var)
            index_name: Name of the Pinecone index to use (defaults to PINECONE_INDEX env var)
            dimension: Vector dimension (default: 16)
            namespace: Namespace for discussions
            
        Raises:
            ConfigurationError: If required configuration is missing
            DatabaseConnectionError: If connecting to Pinecone fails
        """
        self.api_key = api_key or os.environ.get('PINECONE_API_KEY')
        self.environment = environment or os.environ.get('PINECONE_ENVIRONMENT')
        self.index_name = index_name or os.environ.get('PINECONE_INDEX', 'composio-discussions')
        self.dimension = dimension
        self.namespace = namespace
        
        if not self.api_key:
            raise ConfigurationError("Pinecone API key is required. Provide it in the constructor or set PINECONE_API_KEY environment variable.")
        
        if not self.environment:
            raise ConfigurationError("Pinecone environment is required. Provide it in the constructor or set PINECONE_ENVIRONMENT environment variable.")
        
        # Initialize Pinecone
        self._init_pinecone()
    
    def _init_pinecone(self):
        """
        Initialize the Pinecone client and ensure the index exists.
        
        Raises:
            DatabaseConnectionError: If connecting to Pinecone or creating the index fails
        """
        try:
            # Initialize Pinecone
            pinecone.init(api_key=self.api_key, environment=self.environment)
            
            # Check if index exists, if not create it
            if self.index_name not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone index: {self.index_name} with dimension {self.dimension}")
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine"
                )
                # Wait for index to be ready
                time.sleep(1)
            
            # Connect to the index
            self.index = pinecone.Index(self.index_name)
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise DatabaseConnectionError(f"Failed to initialize Pinecone: {e}")
    
    def store_vector(self, vector: List[float], metadata: Dict[str, Any]) -> None:
        """
        Store a vector and metadata in Pinecone.
        
        Args:
            vector: The vector to store
            metadata: Metadata associated with the vector
            
        Raises:
            StoreVectorError: If storing the vector fails
        """
        try:
            # Extract the discussion_id from metadata or generate one
            vector_id = metadata.get('discussion_id', str(uuid.uuid4()))
            
            # Upsert the vector into Pinecone
            self.index.upsert(
                vectors=[(vector_id, vector, metadata)],
                namespace=self.namespace
            )
        except Exception as e:
            logger.error(f"Failed to store vector in Pinecone: {e}")
            raise StoreVectorError(f"Failed to store vector in Pinecone: {e}")
    
    def query_vectors(self, query_vector: List[float], user_id: Optional[str], 
                      top_k: int) -> List[Dict[str, Any]]:
        """
        Query Pinecone for the top_k closest vectors.
        
        Args:
            query_vector: The query vector
            user_id: Filter by user ID (None for all users)
            top_k: Maximum number of results to return
            
        Returns:
            A list of dictionaries with vectors and metadata
            
        Raises:
            QueryVectorError: If querying vectors fails
        """
        try:
            # Set up filter for user_id if provided
            filter_dict = None
            if user_id:
                filter_dict = {"user_id": {"$eq": user_id}}
            
            # Query the index
            query_result = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=self.namespace,
                filter=filter_dict,
                include_metadata=True
            )
            
            # Process results
            results = []
            for match in query_result.matches:
                results.append({
                    'id': match.id,
                    'similarity': match.score,
                    'metadata': match.metadata
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query vectors from Pinecone: {e}")
            raise QueryVectorError(f"Failed to query vectors from Pinecone: {e}")
    
    def delete_vector(self, discussion_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete a vector by discussion_id.
        
        If user_id is provided, only delete if the vector belongs to that user.
        
        Args:
            discussion_id: The ID of the discussion to delete
            user_id: The ID of the user (None for admin access)
            
        Returns:
            True if the vector was deleted, False otherwise
            
        Raises:
            DeleteVectorError: If deleting the vector fails
            DiscussionNotFoundError: If the discussion doesn't exist
            UserDiscussionAccessError: If the user doesn't have permission to delete the discussion
        """
        try:
            # If user_id is provided, verify the discussion belongs to that user
            if user_id:
                # Fetch the vector metadata
                query_result = self.index.fetch(
                    ids=[discussion_id],
                    namespace=self.namespace
                )
                
                # Check if the discussion exists
                if not query_result.vectors or discussion_id not in query_result.vectors:
                    raise DiscussionNotFoundError(discussion_id)
                
                # Check if the discussion belongs to the user
                if query_result.vectors[discussion_id].metadata.get('user_id') != user_id:
                    raise UserDiscussionAccessError(
                        user_id=user_id,
                        target_user_id=query_result.vectors[discussion_id].metadata.get('user_id', 'unknown'),
                        message=f"User '{user_id}' doesn't have permission to delete discussion '{discussion_id}'"
                    )
            
            # Delete the vector
            self.index.delete(
                ids=[discussion_id],
                namespace=self.namespace
            )
            
            return True
            
        except (DiscussionNotFoundError, UserDiscussionAccessError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to delete vector from Pinecone: {e}")
            raise DeleteVectorError(f"Failed to delete vector from Pinecone: {e}") 