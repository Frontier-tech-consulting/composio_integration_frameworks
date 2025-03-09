from typing import List, Dict, Any, Optional, Union
import datetime
import uuid
from importlib import import_module
import logging
from .exceptions import (
    DiscussionException, ConfigurationError, VectorDBError, DatabaseConnectionError,
    DatabaseOperationError, StoreVectorError, QueryVectorError, DeleteVectorError,
    EmbeddingModelError, EmbeddingModelLoadError, TextEmbeddingError,
    PermissionError, DiscussionNotFoundError, UserDiscussionAccessError, AdminRequiredError
)

logger = logging.getLogger(__name__)

class DiscussionManager:
    """
    Manager for user-agent discussions using vector databases.
    
    This class provides functionality for storing and retrieving discussions
    using vector databases like Pinecone or Chroma.
    """
    
    def __init__(self, vector_db_type: str = 'chroma', config: Dict[str, Any] = None):
        """
        Initialize the discussion manager with a vector database.
        
        Args:
            vector_db_type: The type of vector database to use ('chroma', 'pinecone')
            config: Configuration for the vector database
            
        Raises:
            ConfigurationError: If the configuration is invalid
        """
        self.vector_db_type = vector_db_type
        self.config = config or {}
        
        # Initialize the vector database
        self._init_vector_db()
    
    def _init_vector_db(self):
        """
        Initialize the vector database based on the specified type.
        
        Raises:
            ConfigurationError: If the vector database type is not supported
            DatabaseConnectionError: If connecting to the vector database fails
        """
        try:
            if self.vector_db_type == 'pinecone':
                # Import the Pinecone vector database module
                module = import_module('..discussion.vector_db.pinecone', __package__)
                self.vector_db = module.PineconeVectorDB(**self.config)
            elif self.vector_db_type == 'chroma':
                # Import the Chroma vector database module
                module = import_module('..discussion.vector_db.chroma', __package__)
                self.vector_db = module.ChromaVectorDB(**self.config)
            else:
                raise ConfigurationError(f"Unsupported vector database type: {self.vector_db_type}")
            
            # Initialize the embedding model
            self._init_embedding_model()
            
        except ImportError as e:
            raise ConfigurationError(f"Failed to import vector database module: {e}")
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise DatabaseConnectionError(f"Failed to initialize vector database: {e}")
    
    def _init_embedding_model(self):
        """
        Initialize the embedding model for vectorizing text.
        
        This method sets up the embedding model based on configuration.
        Default to a simple model if no specific model is configured.
        
        Raises:
            EmbeddingModelLoadError: If loading the embedding model fails
        """
        # Use the embedding model specified in config or default
        embedding_model = self.config.get('embedding_model', 'default')
        
        if embedding_model == 'default':
            # Simple embedding function for demonstration
            # In a real application, use a proper embedding model
            self.embed_text = self._default_embedding
        else:
            # Import and initialize the specified embedding model
            try:
                # This is a placeholder - in a real application, 
                # you would load an actual embedding model
                self.embed_text = self._default_embedding
                logger.warning(f"Using default embedding model instead of {embedding_model}")
            except Exception as e:
                logger.error(f"Failed to load embedding model {embedding_model}: {e}")
                raise EmbeddingModelLoadError(f"Failed to load embedding model {embedding_model}: {e}")
    
    def _default_embedding(self, text: str) -> List[float]:
        """
        Default simple embedding function for demonstration.
        
        In a real application, this would be replaced with a proper embedding model.
        
        Args:
            text: The text to convert to a vector
            
        Returns:
            A vector representation of the text
            
        Raises:
            TextEmbeddingError: If converting the text to a vector fails
        """
        try:
            import hashlib
            import numpy as np
            
            # Create a simple hash-based embedding (NOT FOR PRODUCTION USE)
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()
            
            # Convert to vector of floats (dimension 16)
            vector = [float(b) / 255.0 for b in hash_bytes]
            
            # Normalize to unit length
            norm = sum(v**2 for v in vector) ** 0.5
            if norm > 0:
                vector = [v / norm for v in vector]
            
            return vector
        except Exception as e:
            raise TextEmbeddingError(f"Failed to embed text: {e}")
    
    def add_discussion(self, user_id: Union[int, str], message: str) -> None:
        """
        Store a new user-agent interaction in the vector database.
        
        Args:
            user_id: The ID of the user
            message: The message content to store
            
        Raises:
            TextEmbeddingError: If converting the message to a vector fails
            StoreVectorError: If storing the discussion in the vector database fails
        """
        try:
            # Generate a unique ID for the discussion
            discussion_id = str(uuid.uuid4())
            
            # Convert the message to a vector
            vector = self.embed_text(message)
            
            # Create metadata for the discussion
            metadata = {
                'user_id': str(user_id),
                'message': message,
                'timestamp': datetime.datetime.now().isoformat(),
                'discussion_id': discussion_id
            }
            
            # Store the vector and metadata in the vector database
            self.vector_db.store_vector(vector, metadata)
            
        except TextEmbeddingError:
            # Re-raise embedding errors
            raise
        except Exception as e:
            logger.error(f"Failed to add discussion: {e}")
            raise StoreVectorError(f"Failed to add discussion: {e}")
    
    def get_relevant_discussions(self, user_id: Union[int, str], query: str, 
                                top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant discussions for a user based on a query.
        
        Args:
            user_id: The ID of the user to get discussions for
            query: The query to use for finding relevant discussions
            top_k: Maximum number of discussions to return
            
        Returns:
            A list of relevant discussions with their metadata
            
        Raises:
            TextEmbeddingError: If converting the query to a vector fails
            QueryVectorError: If querying the vector database fails
        """
        try:
            # Convert the query to a vector
            query_vector = self.embed_text(query)
            
            # Query the vector database for discussions from this user
            results = self.vector_db.query_vectors(query_vector, str(user_id), top_k)
            
            # Extract and format the results
            discussions = []
            for result in results:
                discussions.append({
                    'message': result.get('metadata', {}).get('message', ''),
                    'timestamp': result.get('metadata', {}).get('timestamp', ''),
                    'discussion_id': result.get('metadata', {}).get('discussion_id', ''),
                    'user_id': result.get('metadata', {}).get('user_id', ''),
                    'similarity': result.get('similarity', 0.0)
                })
            
            return discussions
            
        except TextEmbeddingError:
            # Re-raise embedding errors
            raise
        except Exception as e:
            logger.error(f"Failed to get relevant discussions: {e}")
            raise QueryVectorError(f"Failed to get relevant discussions: {e}")
    
    def get_all_relevant_discussions(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant discussions across all users.
        
        This method is intended for admin users only.
        
        Args:
            query: The query to use for finding relevant discussions
            top_k: Maximum number of discussions to return
            
        Returns:
            A list of relevant discussions with their metadata
            
        Raises:
            TextEmbeddingError: If converting the query to a vector fails
            QueryVectorError: If querying the vector database fails
        """
        try:
            # Convert the query to a vector
            query_vector = self.embed_text(query)
            
            # Query the vector database for discussions across all users
            results = self.vector_db.query_vectors(query_vector, None, top_k)
            
            # Extract and format the results
            discussions = []
            for result in results:
                discussions.append({
                    'message': result.get('metadata', {}).get('message', ''),
                    'timestamp': result.get('metadata', {}).get('timestamp', ''),
                    'discussion_id': result.get('metadata', {}).get('discussion_id', ''),
                    'user_id': result.get('metadata', {}).get('user_id', ''),
                    'similarity': result.get('similarity', 0.0)
                })
            
            return discussions
            
        except TextEmbeddingError:
            # Re-raise embedding errors
            raise
        except Exception as e:
            logger.error(f"Failed to get all relevant discussions: {e}")
            raise QueryVectorError(f"Failed to get all relevant discussions: {e}")
    
    def delete_discussion(self, discussion_id: str, user_id: Optional[Union[int, str]] = None) -> bool:
        """
        Delete a discussion by ID.
        
        If user_id is provided, the discussion will only be deleted if it belongs to that user.
        If user_id is None, it assumes the caller has admin privileges.
        
        Args:
            discussion_id: The ID of the discussion to delete
            user_id: The ID of the user (None for admin access)
            
        Returns:
            True if the discussion was deleted, False otherwise
            
        Raises:
            DeleteVectorError: If deleting the discussion from the vector database fails
            DiscussionNotFoundError: If the discussion doesn't exist
            UserDiscussionAccessError: If the user doesn't have permission to delete the discussion
        """
        try:
            result = self.vector_db.delete_vector(discussion_id, str(user_id) if user_id else None)
            if not result:
                # If user_id is provided and deletion failed, it could be because:
                # 1. The discussion doesn't exist
                # 2. The discussion exists but belongs to another user
                # We'll assume it's a permission issue as that's more secure
                if user_id:
                    raise UserDiscussionAccessError(
                        user_id=str(user_id),
                        target_user_id="unknown",
                        message=f"User '{user_id}' doesn't have permission to delete discussion '{discussion_id}'"
                    )
                else:
                    raise DiscussionNotFoundError(discussion_id)
            return True
        except (UserDiscussionAccessError, DiscussionNotFoundError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to delete discussion: {e}")
            raise DeleteVectorError(f"Failed to delete discussion: {e}")

# Create a default manager instance for easier imports
default_manager = DiscussionManager()

# Export common functions using the default manager
def add_discussion(user_id: Union[int, str], message: str) -> None:
    """Store a new user-agent interaction in the vector database."""
    return default_manager.add_discussion(user_id, message)

def get_relevant_discussions(user_id: Union[int, str], query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve the most relevant discussions for a user based on a query."""
    return default_manager.get_relevant_discussions(user_id, query, top_k)

def get_all_relevant_discussions(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve the most relevant discussions across all users (admin only)."""
    return default_manager.get_all_relevant_discussions(query, top_k)

def delete_discussion(discussion_id: str, user_id: Optional[Union[int, str]] = None) -> bool:
    """Delete a discussion by ID."""
    return default_manager.delete_discussion(discussion_id, user_id) 