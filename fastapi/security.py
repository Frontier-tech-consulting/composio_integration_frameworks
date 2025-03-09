from typing import Dict, Any, Optional, List, Union, Callable
import logging
from fastapi import Depends, HTTPException, Security, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..auth.client import get_user_info, validate_token, has_role, is_admin
from ..auth.exceptions import (
    AuthException, TokenInvalidError, TokenExpiredError, 
    AdminRequiredError, RoleRequiredError
)

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme for API docs
oauth2_scheme = HTTPBearer(auto_error=False)

class AgentAuthSecurity:
    """
    Security utilities for FastAPI that integrate with Composio's AgentAuth.
    
    This class provides dependencies that can be used to secure FastAPI routes,
    ensuring users are authenticated and have the appropriate roles.
    """
    
    def __init__(
        self, 
        auto_error: bool = True,
        exclude_paths: Optional[List[str]] = None
    ):
        """
        Initialize the security utilities.
        
        Args:
            auto_error: Whether to automatically raise an HTTPException on auth failure
            exclude_paths: Optional list of path prefixes to exclude from authentication
        """
        self.auto_error = auto_error
        self.exclude_paths = exclude_paths or []
        self.http_bearer = HTTPBearer(auto_error=False)

    async def __call__(
        self, 
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme)
    ) -> Optional[Dict[str, Any]]:
        """
        Dependency that verifies the user is authenticated.
        
        This can be used directly in route definitions:
        @app.get("/secure", dependencies=[Depends(auth_security)])
        
        Or to get the user info:
        @app.get("/me")
        async def me(user = Depends(auth_security)):
            return user
        
        Args:
            request: The HTTP request
            credentials: HTTP Bearer credentials from the Authorization header
            
        Returns:
            User information if authenticated, or None if auto_error is False
            
        Raises:
            HTTPException: If authentication fails and auto_error is True
        """
        # Check if this path should be excluded
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return None
            
        # First, try to get the user from request state (set by middleware)
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user
            
        # If no middleware is active, extract and verify the token ourselves
        token = None
        
        # Try to get token from the credentials (if used with Depends)
        if credentials:
            token = credentials.credentials
            
        # No credentials, check for a token in the header directly
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                
        # Still no token? Fail if auto_error is True, otherwise return None
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None
            
        # Validate the token and get user info
        try:
            user_info = get_user_info(token)
            
            # Store the user info in the request state for future use
            request.state.user = user_info
            request.state.token = token
            
            return user_info
            
        except (TokenInvalidError, TokenExpiredError) as e:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(e),
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None
            
        except Exception as e:
            logger.exception(f"Authentication error: {e}")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error during authentication"
                )
            return None

    def role_required(self, required_role: str) -> Callable:
        """
        Create a dependency that requires a specific role.
        
        Usage:
        @app.get("/admin-only")
        async def admin_page(user = Depends(auth_security.role_required("admin"))):
            return {"message": "You are an admin!"}
        
        Args:
            required_role: The role required to access the route
            
        Returns:
            A dependency function that validates the user has the required role
        """
        async def role_dependency(user: Dict[str, Any] = Depends(self)) -> Dict[str, Any]:
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
            user_role = user.get("role")
            if user_role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{required_role}' required",
                    headers={"X-Required-Role": required_role}
                )
                
            return user
            
        return role_dependency

    def admin_required(self) -> Callable:
        """
        Create a dependency that requires the admin role.
        
        Usage:
        @app.get("/admin-only")
        async def admin_page(user = Depends(auth_security.admin_required())):
            return {"message": "You are an admin!"}
            
        Returns:
            A dependency function that validates the user is an admin
        """
        return self.role_required("admin")
        
    def get_token(self, request: Request) -> Optional[str]:
        """
        Get the authentication token from the request.
        
        Args:
            request: The HTTP request
            
        Returns:
            The token if found, or None
        """
        # First, try to get from request state
        if hasattr(request.state, "token") and request.state.token:
            return request.state.token
            
        # Try from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "")
            
        return None

    
# Standalone utility functions for simple use cases

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """
    Dependency that gets the current authenticated user.
    
    This can be used directly in route definitions:
    @app.get("/me")
    async def me(user = Depends(get_current_user)):
        return user
        
    Args:
        request: The HTTP request
        credentials: HTTP Bearer credentials from the Authorization header
        
    Returns:
        User information
        
    Raises:
        HTTPException: If authentication fails
    """
    # Try to get user from request state (set by middleware)
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user
        
    # Get token from credentials or header
    token = None
    if credentials:
        token = credentials.credentials
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    try:
        user_info = get_user_info(token)
        
        # Store for future use
        request.state.user = user_info
        request.state.token = token
        
        return user_info
    except (TokenInvalidError, TokenExpiredError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.exception(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )

async def get_admin_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that verifies the user is an admin.
    
    Usage:
    @app.get("/admin-only")
    async def admin_page(user = Depends(get_admin_user)):
        return {"message": "You are an admin!"}
        
    Args:
        user: The authenticated user
        
    Returns:
        User information if the user is an admin
        
    Raises:
        HTTPException: If the user is not an admin
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
            headers={"X-Required-Role": "admin"}
        )
        
    return user

async def get_user_with_role(
    role: str, 
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency that verifies the user has a specific role.
    
    Usage:
    @app.get("/client-only")
    async def client_page(user = Depends(lambda: get_user_with_role("client"))):
        return {"message": "You are a client!"}
        
    Args:
        role: The required role
        user: The authenticated user
        
    Returns:
        User information if the user has the required role
        
    Raises:
        HTTPException: If the user does not have the required role
    """
    if user.get("role") != role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' required",
            headers={"X-Required-Role": role}
        )
        
    return user
