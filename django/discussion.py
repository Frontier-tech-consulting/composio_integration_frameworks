from typing import List, Dict, Any, Optional
from ..discussion.manager import DiscussionManager
from ..discussion.exceptions import (
    DiscussionException, PermissionError as DiscussionPermissionError,
    UserDiscussionAccessError, DiscussionNotFoundError, AdminRequiredError as DiscussionAdminRequiredError
)
from ..auth.client import is_admin, get_user_info
from ..auth.exceptions import (
    AuthException, TokenInvalidError, TokenExpiredError, AdminRequiredError as AuthAdminRequiredError
)
from django.http import HttpRequest
from django.contrib.auth.models import User
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DjangoDiscussionManager:
    """
    Django-specific integration for discussion management.
    
    This class provides methods to integrate the discussion manager with
    Django's user model and provides role-based access control.
    """
    
    def __init__(self, discussion_manager: Optional[DiscussionManager] = None, 
                 vector_db_type: str = None):
        """
        Initialize the Django discussion manager.
        
        Args:
            discussion_manager: An existing DiscussionManager instance or None to create a new one
            vector_db_type: The vector database type to use if creating a new DiscussionManager
            
        Raises:
            DiscussionException: If initializing the discussion manager fails
        """
        if discussion_manager:
            self.discussion_manager = discussion_manager
        else:
            # Get the vector_db_type from settings if not provided
            if vector_db_type is None:
                vector_db_type = getattr(settings, 'COMPOSIO_VECTOR_DB', 'chroma')
            
            self.discussion_manager = DiscussionManager(vector_db_type=vector_db_type)
    
    def add_discussion(self, request: HttpRequest, message: str, user_id: Optional[int] = None) -> None:
        """
        Add a user-agent discussion to the vector database.
        
        Args:
            request: The Django HTTP request object with authenticated user
            message: The message content to store
            user_id: Optional user ID to store the message for (admin only)
            
        Raises:
            DiscussionPermissionError: If the user is not authenticated
            AuthAdminRequiredError: If a non-admin user tries to add a discussion for another user
            DiscussionException: If adding the discussion fails
        """
        if not request.user.is_authenticated:
            raise DiscussionPermissionError("User must be authenticated to add discussions")
        
        # Get the token from session
        token = request.session.get('agentauth_token')
        
        # If user_id is specified, check if current user is admin
        if user_id and user_id != request.user.id:
            # Verify admin role using token or user.is_superuser
            is_user_admin = request.user.is_superuser
            if token:
                try:
                    is_user_admin = is_user_admin or is_admin(token)
                except AuthException as e:
                    logger.warning(f"Failed to verify admin role with token: {e}")
                    # Continue with Django's superuser check only
            
            if not is_user_admin:
                raise AuthAdminRequiredError(
                    message="Only admins can add discussions for other users",
                    user_role=getattr(request.user, 'role', None)
                )
        else:
            # Use the authenticated user's ID if no specific user_id is provided
            user_id = request.user.id
        
        # Add the discussion using the discussion manager
        self.discussion_manager.add_discussion(user_id, message)
    
    def get_relevant_discussions(self, request: HttpRequest, query: str, 
                                user_id: Optional[int] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Get relevant discussions based on the query.
        
        Args:
            request: The Django HTTP request object with authenticated user
            query: The query to find relevant discussions
            user_id: Optional user ID to get discussions for (admin only)
            top_k: Maximum number of discussions to return
            
        Returns:
            A list of relevant discussions
            
        Raises:
            DiscussionPermissionError: If the user is not authenticated
            AuthAdminRequiredError: If a non-admin user tries to get discussions for another user
            DiscussionException: If retrieving discussions fails
        """
        if not request.user.is_authenticated:
            raise DiscussionPermissionError("User must be authenticated to retrieve discussions")
        
        # Get the token from session
        token = request.session.get('agentauth_token')
        
        # If user_id is specified and different from current user, check if admin
        if user_id and user_id != request.user.id:
            # Verify admin role using token or user.is_superuser
            is_user_admin = request.user.is_superuser
            if token:
                try:
                    is_user_admin = is_user_admin or is_admin(token)
                except AuthException as e:
                    logger.warning(f"Failed to verify admin role with token: {e}")
                    # Continue with Django's superuser check only
            
            if not is_user_admin:
                raise AuthAdminRequiredError(
                    message="Only admins can access discussions for other users",
                    user_role=getattr(request.user, 'role', None)
                )
            
            # Use the specified user_id for admin
            return self.discussion_manager.get_relevant_discussions(user_id, query, top_k)
        else:
            # Use the authenticated user's ID
            return self.discussion_manager.get_relevant_discussions(request.user.id, query, top_k)
    
    def get_all_relevant_discussions(self, request: HttpRequest, query: str, 
                                    top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Get relevant discussions across all users (admin only).
        
        Args:
            request: The Django HTTP request object with authenticated user
            query: The query to find relevant discussions
            top_k: Maximum number of discussions to return
            
        Returns:
            A list of relevant discussions from all users
            
        Raises:
            DiscussionPermissionError: If the user is not authenticated
            AuthAdminRequiredError: If a non-admin user tries to access this function
            DiscussionException: If retrieving discussions fails
        """
        if not request.user.is_authenticated:
            raise DiscussionPermissionError("User must be authenticated to retrieve discussions")
        
        # Get the token from session
        token = request.session.get('agentauth_token')
        
        # Verify admin role using token or user.is_superuser
        is_user_admin = request.user.is_superuser
        if token:
            try:
                is_user_admin = is_user_admin or is_admin(token)
            except AuthException as e:
                logger.warning(f"Failed to verify admin role with token: {e}")
                # Continue with Django's superuser check only
        
        if not is_user_admin:
            raise AuthAdminRequiredError(
                message="Only admins can access discussions for all users",
                user_role=getattr(request.user, 'role', None)
            )
        
        # Get discussions across all users
        return self.discussion_manager.get_all_relevant_discussions(query, top_k)
    
    def link_user_with_agentauth(self, user: User, token: str) -> None:
        """
        Link a Django user with AgentAuth user information.
        
        This method retrieves user information from AgentAuth and updates
        the Django user model with additional attributes.
        
        Args:
            user: The Django user model instance
            token: The AgentAuth token
            
        Raises:
            TokenInvalidError: If the token is invalid
            TokenExpiredError: If the token has expired
            AuthException: If retrieving user info fails
        """
        try:
            # Get user info from AgentAuth
            user_info = get_user_info(token)
            
            # Store token in session for future requests
            # Note: In a real application, consider using a more secure storage
            # or refreshing tokens through middleware
            user.session = getattr(user, 'session', {})
            user.session['agentauth_token'] = token
            
            # Update user model with AgentAuth role if available
            if 'role' in user_info:
                # Use Django's model to store the role
                # This assumes you've added a custom user model or profile with a 'role' field
                if hasattr(user, 'profile') and hasattr(user.profile, 'role'):
                    user.profile.role = user_info['role']
                    user.profile.save()
                # Or you could use a custom attribute manager
                elif hasattr(user, 'attributes'):
                    user.attributes.update_or_create(
                        name='agentauth_role',
                        defaults={'value': user_info['role']}
                    )
                
                # Sync with Django superuser for admin role
                if user_info['role'] == 'admin' and not user.is_superuser:
                    user.is_superuser = True
                    user.is_staff = True
                    user.save()
            
        except (TokenInvalidError, TokenExpiredError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            logger.error(f"Error linking user with AgentAuth: {e}")
            raise

# Create a default manager instance for easier imports
default_manager = DjangoDiscussionManager()

# Export common functions using the default manager
def add_discussion(request: HttpRequest, message: str, user_id: Optional[int] = None) -> None:
    """Add a user-agent discussion to the vector database."""
    return default_manager.add_discussion(request, message, user_id)

def get_relevant_discussions(request: HttpRequest, query: str, 
                            user_id: Optional[int] = None, top_k: int = 5) -> List[Dict[str, Any]]:
    """Get relevant discussions based on the query."""
    return default_manager.get_relevant_discussions(request, query, user_id, top_k)

def get_all_relevant_discussions(request: HttpRequest, query: str, 
                                top_k: int = 5) -> List[Dict[str, Any]]:
    """Get relevant discussions across all users (admin only)."""
    return default_manager.get_all_relevant_discussions(request, query, top_k)

def link_user_with_agentauth(user: User, token: str) -> None:
    """Link a Django user with AgentAuth user information."""
    return default_manager.link_user_with_agentauth(user, token) 