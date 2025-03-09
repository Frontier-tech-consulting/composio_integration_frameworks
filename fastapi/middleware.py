from typing import Dict, Any, Optional, Callable, Union
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..auth.client import get_user_info
from ..auth.exceptions import (
    AuthException, TokenInvalidError, TokenExpiredError, 
    InvalidCredentialsError, NetworkError, ConfigurationError
)

logger = logging.getLogger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that authenticates requests using Composio's AgentAuth.
    
    This middleware extracts the JWT token from the Authorization header,
    verifies it with the AgentAuth API, and adds the user information to
    the request state for use in route handlers.
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        exclude_paths: Optional[list] = None,
        token_header: str = "Authorization",
        token_prefix: str = "Bearer",
        error_handler: Optional[Callable[[Request, AuthException], Response]] = None
    ):
        """
        Initialize the authentication middleware.
        
        Args:
            app: The ASGI application
            exclude_paths: List of paths to exclude from authentication (e.g., ["/docs", "/health"])
            token_header: Header name for the token (default: "Authorization")
            token_prefix: Prefix for the token in the header (default: "Bearer")
            error_handler: Optional custom function to handle authentication errors
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.token_header = token_header
        self.token_prefix = token_prefix
        self.error_handler = error_handler

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request, authenticating the user if required.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler in the chain
            
        Returns:
            The response from the next middleware or route handler
        """
        # Skip authentication for excluded paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Get the token from the request
        token = self._extract_token(request)
        
        # If no token is provided, let the route handler decide if it's required
        if not token:
            # We're not raising an error here, as some routes might not require auth
            # The route handler can use the security dependency to enforce auth if needed
            request.state.user = None
            return await call_next(request)
        
        # Authenticate the token
        try:
            # Get user info from the token
            user_info = get_user_info(token)
            
            # Add the user info and token to the request state
            request.state.user = user_info
            request.state.token = token
            
            # Proceed with the request
            return await call_next(request)
            
        except (TokenInvalidError, TokenExpiredError, InvalidCredentialsError) as e:
            # Authentication error
            logger.warning(f"Authentication failed: {e}")
            if self.error_handler:
                return await self.error_handler(request, e)
            return self._create_auth_error_response(e)
            
        except (NetworkError, ConfigurationError) as e:
            # System error
            logger.error(f"Authentication system error: {e}")
            if self.error_handler:
                return await self.error_handler(request, e)
            return JSONResponse(
                status_code=500,
                content={"detail": "Authentication service unavailable"}
            )
            
        except Exception as e:
            # Unexpected error
            logger.exception(f"Unexpected error during authentication: {e}")
            if self.error_handler:
                return await self.error_handler(request, e)
            return JSONResponse(
                status_code=500, 
                content={"detail": "Internal server error during authentication"}
            )
    
    def _should_skip_auth(self, path: str) -> bool:
        """
        Check if authentication should be skipped for this path.
        
        Args:
            path: The request path
            
        Returns:
            True if authentication should be skipped, False otherwise
        """
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract the JWT token from the request headers.
        
        Args:
            request: The incoming request
            
        Returns:
            The JWT token, or None if not found
        """
        auth_header = request.headers.get(self.token_header)
        if not auth_header:
            return None
            
        # Check if the header has the expected format (e.g., "Bearer <token>")
        if self.token_prefix:
            parts = auth_header.split()
            if len(parts) != 2 or parts[0] != self.token_prefix:
                return None
            return parts[1]
        
        # If no prefix is required, return the full header value
        return auth_header
    
    def _create_auth_error_response(self, exception: AuthException) -> JSONResponse:
        """
        Create a JSON response for authentication errors.
        
        Args:
            exception: The authentication exception
            
        Returns:
            A JSON response with the error details
        """
        if isinstance(exception, TokenExpiredError):
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired", "code": "token_expired"}
            )
        elif isinstance(exception, TokenInvalidError):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token", "code": "token_invalid"}
            )
        elif isinstance(exception, InvalidCredentialsError):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid credentials", "code": "invalid_credentials"}
            )
        else:
            return JSONResponse(
                status_code=401,
                content={"detail": str(exception), "code": "authentication_failed"}
            )

# Alternative middleware implementation using a function-based approach
# This can be used with FastAPI's add_middleware method
class SimpleAuthMiddleware:
    """
    A simpler authentication middleware that can be used with FastAPI's add_middleware.
    """
    
    def __init__(
        self,
        exclude_paths: Optional[list] = None,
        token_header: str = "Authorization",
        token_prefix: str = "Bearer"
    ):
        """
        Initialize the simple authentication middleware.
        
        Args:
            exclude_paths: List of paths to exclude from authentication
            token_header: Header name for the token (default: "Authorization")
            token_prefix: Prefix for the token in the header (default: "Bearer")
        """
        self.exclude_paths = exclude_paths or []
        self.token_header = token_header
        self.token_prefix = token_prefix
    
    async def __call__(self, request: Request, call_next):
        """
        Process the request, authenticating the user if required.
        """
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Get token from header
        auth_header = request.headers.get(self.token_header)
        if not auth_header:
            request.state.user = None
            return await call_next(request)
        
        # Extract token
        token = None
        if self.token_prefix:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0] == self.token_prefix:
                token = parts[1]
        else:
            token = auth_header
        
        if not token:
            request.state.user = None
            return await call_next(request)
        
        # Authenticate
        try:
            user_info = get_user_info(token)
            request.state.user = user_info
            request.state.token = token
            return await call_next(request)
        except (TokenInvalidError, TokenExpiredError) as e:
            return JSONResponse(
                status_code=401,
                content={"detail": str(e), "code": "authentication_failed"}
            )
        except Exception as e:
            logger.exception(f"Authentication error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error during authentication"}
            )
