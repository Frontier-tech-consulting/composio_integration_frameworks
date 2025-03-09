"""
Authentication-related exceptions for the Composio Agent Integration package.

This module defines a hierarchy of exceptions that can be raised during 
authentication operations with Composio's AgentAuth API.
"""

from typing import Optional, Dict, Any


class AuthException(Exception):
    """
    Base exception for all authentication-related errors.
    
    This is the parent class for all authentication exceptions in the package.
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception with details about the error.
        
        Args:
            message: Human-readable error message
            status_code: Optional HTTP status code if the error came from an API response
            response_data: Optional raw response data from the API
        """
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return a string representation of the exception."""
        base_msg = self.message
        if self.status_code:
            base_msg = f"[{self.status_code}] {base_msg}"
        return base_msg


class ConfigurationError(AuthException):
    """Exception raised when there's an error in the authentication configuration."""
    pass


class NetworkError(AuthException):
    """Exception raised when there's a network-related error during authentication."""
    pass


class APIError(AuthException):
    """
    Exception raised when the AgentAuth API returns an error response.
    
    This is a base class for specific API error types.
    """
    pass


class ServerError(APIError):
    """Exception raised when the AgentAuth API returns a server error (5xx status code)."""
    pass


class ClientError(APIError):
    """
    Exception raised when the AgentAuth API returns a client error (4xx status code).
    
    This is a base class for specific client error types.
    """
    pass


class RegistrationError(ClientError):
    """Exception raised when user registration fails."""
    pass


class UserExistsError(RegistrationError):
    """Exception raised when trying to register a user that already exists."""
    pass


class InvalidRegistrationDataError(RegistrationError):
    """Exception raised when registration data is invalid or incomplete."""
    pass


class AuthenticationError(ClientError):
    """Exception raised when authentication (login) fails."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Exception raised when provided credentials are invalid."""
    pass


class AccountLockedError(AuthenticationError):
    """Exception raised when the user account is locked or disabled."""
    pass


class TokenError(ClientError):
    """
    Exception raised for token-related errors.
    
    This is a base class for specific token error types.
    """
    pass


class TokenExpiredError(TokenError):
    """Exception raised when the access token has expired."""
    pass


class TokenInvalidError(TokenError):
    """Exception raised when the access token is invalid or malformed."""
    pass


class PermissionError(ClientError):
    """Exception raised when a user doesn't have permission for an operation."""
    pass


class RoleRequiredError(PermissionError):
    """
    Exception raised when a specific role is required for an operation.
    
    Args:
        message: Error message
        required_role: The role that was required for the operation
        user_role: The user's actual role
    """
    
    def __init__(self, message: str, required_role: str, user_role: Optional[str] = None, 
                 **kwargs):
        self.required_role = required_role
        self.user_role = user_role
        super().__init__(message, **kwargs)
    
    def __str__(self) -> str:
        """Return a string representation of the exception with role information."""
        base_msg = super().__str__()
        role_info = f"Required role: {self.required_role}"
        if self.user_role:
            role_info = f"{role_info}, User role: {self.user_role}"
        return f"{base_msg} ({role_info})"


class AdminRequiredError(RoleRequiredError):
    """Exception raised when admin role is required for an operation."""
    
    def __init__(self, message: str = "Admin role required for this operation", 
                 user_role: Optional[str] = None, **kwargs):
        super().__init__(message, required_role="admin", user_role=user_role, **kwargs)


class UserInfoError(ClientError):
    """Exception raised when retrieving user information fails."""
    pass


# Map HTTP status codes to exception classes for API responses
STATUS_CODE_EXCEPTIONS = {
    400: ClientError,
    401: AuthenticationError,
    403: PermissionError,
    404: ClientError,
    409: UserExistsError,
    422: InvalidRegistrationDataError,
    429: ClientError,  # Rate limiting
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}


def get_exception_for_status_code(status_code: int, message: str, 
                                 response_data: Optional[Dict[str, Any]] = None) -> AuthException:
    """
    Create an appropriate exception instance for an HTTP status code.
    
    Args:
        status_code: HTTP status code from the API response
        message: Error message
        response_data: Raw response data from the API
    
    Returns:
        An appropriate AuthException subclass instance
    """
    exception_class = STATUS_CODE_EXCEPTIONS.get(status_code, APIError)
    return exception_class(
        message=message,
        status_code=status_code,
        response_data=response_data
    )
