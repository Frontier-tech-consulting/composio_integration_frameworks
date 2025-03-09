from composio import Composio
import requests
import json
import os
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
from .exceptions import (
    AuthException, NetworkError, APIError, ConfigurationError,
    InvalidCredentialsError, TokenInvalidError, TokenExpiredError,
    UserExistsError, InvalidRegistrationDataError, AdminRequiredError,
    get_exception_for_status_code
)

class AgentAuthClient:
    """
    Client for interacting with Composio's AgentAuth API.
    
    This client provides functionality for user registration, login, and user information
    retrieval from the AgentAuth API.
    """
    
    def __init__(self, base_url: str = None, api_key: str = None):
        """
        Initialize the AgentAuth client with configuration.
        
        Args:
            base_url: The base URL for the AgentAuth API. If not provided, it will be 
                    read from the AGENTAUTH_BASE_URL environment variable.
            api_key: The API key for authentication. If not provided, it will be read 
                    from the AGENTAUTH_API_KEY environment variable.
        """
        self.base_url = base_url or os.environ.get('AGENTAUTH_BASE_URL', 'https://api.composio.dev/agentauth/')
        self.api_key = api_key or os.environ.get('AGENTAUTH_API_KEY')
        
        if not self.base_url:
            raise ConfigurationError("AgentAuth base URL is required. "
                                     "Provide it in the constructor or set AGENTAUTH_BASE_URL environment variable.")
        
        # Initialize Composio client
        try:
            self.composio_client = Composio(api_key=self.api_key)
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize Composio client: {e}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None, 
                      headers: Dict[str, str] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make an HTTP request to the AgentAuth API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint to call
            data: Request payload
            headers: HTTP headers
            params: Query parameters
            
        Returns:
            Response data as a dictionary
            
        Raises:
            AuthException: If the request fails
        """
        url = urljoin(self.base_url, endpoint)
        
        # Set default headers
        if headers is None:
            headers = {}
        
        # Add API key if available
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        # Add content type for POST/PUT requests
        if method.upper() in ['POST', 'PUT'] and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if method.upper() in ['POST', 'PUT'] else None,
                params=params
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Return response data
            return response.json()
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Connection error while connecting to {endpoint}: {str(e)}")
        except requests.exceptions.Timeout as e:
            raise NetworkError(f"Timeout while connecting to {endpoint}: {str(e)}")
        except requests.exceptions.HTTPError as e:
            # Handle error responses
            error_message = f"Request to {endpoint} failed: {str(e)}"
            status_code = e.response.status_code if hasattr(e, 'response') else None
            
            response_data = None
            if hasattr(e, 'response') and e.response is not None:
                try:
                    response_data = e.response.json()
                    if 'error' in response_data or 'message' in response_data:
                        error_message = response_data.get('error', response_data.get('message', error_message))
                except ValueError:
                    pass
            
            # Create the appropriate exception for the status code
            if status_code:
                raise get_exception_for_status_code(
                    status_code=status_code,
                    message=error_message,
                    response_data=response_data
                )
            else:
                raise APIError(error_message, response_data=response_data)
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request to {endpoint} failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise APIError(f"Failed to parse JSON response from {endpoint}: {str(e)}")
        except Exception as e:
            raise AuthException(f"Unexpected error during request to {endpoint}: {str(e)}")
    
    def register_user(self, username: str, password: str, email: str, 
                      role: str = 'client', additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Register a new user with AgentAuth.
        
        Args:
            username: User's username
            password: User's password
            email: User's email address
            role: User's role (default: 'client')
            additional_data: Any additional data to include in the registration
            
        Returns:
            User data including ID and role
            
        Raises:
            UserExistsError: If a user with the username or email already exists
            InvalidRegistrationDataError: If the registration data is invalid
            AuthException: For other registration failures
        """
        data = {
            'username': username,
            'password': password,
            'email': email,
            'role': role
        }
        
        # Add any additional data
        if additional_data:
            data.update(additional_data)
        
        try:
            return self._make_request('POST', 'register', data=data)
        except UserExistsError:
            raise UserExistsError(f"A user with the username '{username}' or email '{email}' already exists")
        except InvalidRegistrationDataError as e:
            raise InvalidRegistrationDataError(f"Invalid registration data: {e.message}", 
                                              status_code=e.status_code, 
                                              response_data=e.response_data)
    
    def login_user(self, username: str, password: str) -> str:
        """
        Authenticate a user and retrieve an access token.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Access token string
            
        Raises:
            InvalidCredentialsError: If the credentials are invalid
            AuthException: For other login failures
        """
        data = {
            'username': username,
            'password': password
        }
        
        try:
            response = self._make_request('POST', 'login', data=data)
            
            # Extract token from response
            token = response.get('access_token') or response.get('token')
            if not token:
                raise AuthException("No access token found in login response")
            
            return token
        except AuthException as e:
            if e.status_code == 401:
                raise InvalidCredentialsError("Invalid username or password", 
                                             status_code=e.status_code, 
                                             response_data=e.response_data)
            raise
    
    def get_user_info(self, token: str) -> Dict[str, Any]:
        """
        Retrieve user information using an access token.
        
        Args:
            token: The access token obtained from login
            
        Returns:
            User data including ID, username, email, and role
            
        Raises:
            TokenInvalidError: If the token is invalid
            TokenExpiredError: If the token has expired
            AuthException: For other user info retrieval failures
        """
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            return self._make_request('GET', 'user-info', headers=headers)
        except AuthException as e:
            if e.status_code == 401:
                # Check if the error indicates token expiration
                if e.response_data and 'expired' in str(e.response_data).lower():
                    raise TokenExpiredError("Access token has expired", 
                                           status_code=e.status_code, 
                                           response_data=e.response_data)
                else:
                    raise TokenInvalidError("Invalid access token", 
                                           status_code=e.status_code, 
                                           response_data=e.response_data)
            raise
    
    def validate_token(self, token: str) -> bool:
        """
        Validate if a token is still valid.
        
        Args:
            token: The access token to validate
            
        Returns:
            True if the token is valid, False otherwise
        """
        try:
            self.get_user_info(token)
            return True
        except (TokenInvalidError, TokenExpiredError):
            return False
        except AuthException:
            return False
    
    def has_role(self, token: str, required_role: str) -> bool:
        """
        Check if the user has the specified role.
        
        Args:
            token: The access token
            required_role: The role to check for (e.g., 'admin', 'client')
            
        Returns:
            True if the user has the role, False otherwise
            
        Raises:
            AuthException: If retrieving user info fails
        """
        try:
            user_info = self.get_user_info(token)
            user_role = user_info.get('role')
            
            # Check if the user has the required role
            return user_role == required_role
        except (TokenInvalidError, TokenExpiredError):
            return False
    
    def is_admin(self, token: str) -> bool:
        """
        Check if the user has admin role.
        
        Args:
            token: The access token
            
        Returns:
            True if the user is an admin, False otherwise
        """
        return self.has_role(token, 'admin')
    
    def require_admin(self, token: str) -> Dict[str, Any]:
        """
        Verify the user has admin role and return user info, or raise an exception.
        
        Args:
            token: The access token
            
        Returns:
            User information including role
            
        Raises:
            AdminRequiredError: If the user is not an admin
            AuthException: For other authentication failures
        """
        user_info = self.get_user_info(token)
        user_role = user_info.get('role')
        
        if user_role != 'admin':
            raise AdminRequiredError(user_role=user_role)
        
        return user_info

# Create a default client instance for easier imports
default_client = AgentAuthClient()

# Export common functions using the default client
def register_user(username: str, password: str, email: str, 
                 role: str = 'client', additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Register a new user with AgentAuth."""
    return default_client.register_user(username, password, email, role, additional_data)

def login_user(username: str, password: str) -> str:
    """Authenticate a user and retrieve an access token."""
    return default_client.login_user(username, password)

def get_user_info(token: str) -> Dict[str, Any]:
    """Retrieve user information using an access token."""
    return default_client.get_user_info(token)

def validate_token(token: str) -> bool:
    """Validate if a token is still valid."""
    return default_client.validate_token(token)

def has_role(token: str, required_role: str) -> bool:
    """Check if the user has the specified role."""
    return default_client.has_role(token, required_role)

def is_admin(token: str) -> bool:
    """Check if the user has admin role."""
    return default_client.is_admin(token)

def require_admin(token: str) -> Dict[str, Any]:
    """Verify the user has admin role and return user info, or raise an exception."""
    return default_client.require_admin(token)
