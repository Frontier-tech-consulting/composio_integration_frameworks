"""
Discussion management-related exceptions for the Composio Agent Integration package.

This module defines a hierarchy of exceptions that can be raised during 
discussion management operations with vector databases.
"""

from typing import Optional, Dict, Any


class DiscussionException(Exception):
    """
    Base exception for all discussion management-related errors.
    
    This is the parent class for all discussion exceptions in the package.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception with details about the error.
        
        Args:
            message: Human-readable error message
            details: Optional additional details about the error
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the exception."""
        return self.message


class ConfigurationError(DiscussionException):
    """Exception raised when there's an error in the discussion configuration."""
    pass


class VectorDBError(DiscussionException):
    """
    Base exception for vector database-related errors.
    
    This is the parent class for all vector database exceptions.
    """
    pass


class DatabaseConnectionError(VectorDBError):
    """Exception raised when there's an error connecting to the vector database."""
    pass


class DatabaseOperationError(VectorDBError):
    """Exception raised when there's an error during a vector database operation."""
    pass


class StoreVectorError(DatabaseOperationError):
    """Exception raised when storing a vector in the database fails."""
    pass


class QueryVectorError(DatabaseOperationError):
    """Exception raised when querying vectors from the database fails."""
    pass


class DeleteVectorError(DatabaseOperationError):
    """Exception raised when deleting a vector from the database fails."""
    pass


class EmbeddingModelError(DiscussionException):
    """
    Base exception for embedding model-related errors.
    
    This is the parent class for all embedding model exceptions.
    """
    pass


class EmbeddingModelLoadError(EmbeddingModelError):
    """Exception raised when loading an embedding model fails."""
    pass


class TextEmbeddingError(EmbeddingModelError):
    """Exception raised when converting text to a vector embedding fails."""
    pass


class PermissionError(DiscussionException):
    """Exception raised when a user doesn't have permission for an operation."""
    pass


class DiscussionNotFoundError(DiscussionException):
    """Exception raised when a requested discussion cannot be found."""
    
    def __init__(self, discussion_id: str, message: Optional[str] = None, **kwargs):
        """
        Initialize the exception with the discussion ID.
        
        Args:
            discussion_id: ID of the discussion that wasn't found
            message: Custom error message
        """
        self.discussion_id = discussion_id
        if message is None:
            message = f"Discussion with ID '{discussion_id}' not found"
        super().__init__(message, **kwargs)


class UserDiscussionAccessError(PermissionError):
    """Exception raised when a user tries to access another user's discussions without permission."""
    
    def __init__(self, user_id: str, target_user_id: str, message: Optional[str] = None, **kwargs):
        """
        Initialize the exception with the user and target user IDs.
        
        Args:
            user_id: ID of the user attempting the access
            target_user_id: ID of the user whose discussions are being accessed
            message: Custom error message
        """
        self.user_id = user_id
        self.target_user_id = target_user_id
        if message is None:
            message = f"User '{user_id}' does not have permission to access discussions of user '{target_user_id}'"
        super().__init__(message, **kwargs)


class AdminRequiredError(PermissionError):
    """Exception raised when admin role is required for an operation."""
    
    def __init__(self, user_id: Optional[str] = None, message: Optional[str] = None, **kwargs):
        """
        Initialize the exception with the user ID.
        
        Args:
            user_id: ID of the user attempting the operation
            message: Custom error message
        """
        self.user_id = user_id
        if message is None:
            if user_id:
                message = f"User '{user_id}' requires admin role for this operation"
            else:
                message = "Admin role required for this operation"
        super().__init__(message, **kwargs) 