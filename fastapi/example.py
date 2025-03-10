"""
Example FastAPI application using Composio Agent Integration.

This file demonstrates how to use the middleware and security components
with FastAPI to create a secure API that integrates with Composio's AgentAuth.
"""

import os
import logging
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import components from composio_integration_frameworks
from ..auth.client import (
    register_user, login_user, get_user_info, validate_token, is_admin
)
from ..auth.exceptions import (
    AuthException, UserExistsError, InvalidCredentialsError, 
    TokenInvalidError, TokenExpiredError
)
from ..discussion.manager import DiscussionManager
from ..discussion.exceptions import (
    DiscussionException, DiscussionNotFoundError, UserDiscussionAccessError,
    DatabaseConnectionError, TextEmbeddingError
)

# Import FastAPI components
from .middleware import AuthenticationMiddleware
from .security import (
    AgentAuthSecurity, get_current_user, get_admin_user, get_user_with_role
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a FastAPI application
app = FastAPI(
    title="Composio Agent Integration Example",
    description="An example FastAPI application that demonstrates how to use Composio Agent Integration",
    version="0.1.0"
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    exclude_paths=["/docs", "/openapi.json", "/auth/register", "/auth/login"],
)

# Create security utilities
auth_security = AgentAuthSecurity(
    exclude_paths=["/docs", "/openapi.json", "/auth/register", "/auth/login"]
)

# Create a discussion manager
discussion_manager = DiscussionManager(
    vector_db_type=os.environ.get("VECTOR_DB_TYPE", "chroma"),
    config={
        # For Pinecone
        "api_key": os.environ.get("PINECONE_API_KEY"),
        "environment": os.environ.get("PINECONE_ENVIRONMENT"),
        "index_name": os.environ.get("PINECONE_INDEX", "composio-discussions"),
        
        # For Chroma
        "persist_directory": os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db"),
        "collection_name": os.environ.get("CHROMA_COLLECTION", "agent_discussions"),
    }
)

# Define API models
class UserRegister(BaseModel):
    username: str
    password: str
    email: str
    role: str = "client"  # Default role is "client"
    
class UserLogin(BaseModel):
    username: str
    password: str
    
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class Message(BaseModel):
    content: str
    
class MessageResponse(BaseModel):
    message_id: str
    content: str
    success: bool = True
    
class DiscussionQuery(BaseModel):
    query: str
    top_k: int = 5

# Authentication endpoints
@app.post("/auth/register", response_model=Dict[str, Any])
async def api_register(user_data: UserRegister):
    """Register a new user with AgentAuth."""
    try:
        result = register_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            role=user_data.role
        )
        return result
    except UserExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username or email already exists",
        )
    except AuthException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration",
        )

@app.post("/auth/login", response_model=LoginResponse)
async def api_login(login_data: UserLogin):
    """Log in a user and get an access token."""
    try:
        token = login_user(
            username=login_data.username,
            password=login_data.password
        )
        return {"access_token": token, "token_type": "bearer"}
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    except AuthException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )

@app.get("/auth/me", response_model=Dict[str, Any])
async def api_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Get information about the current user."""
    return user

# Discussion endpoints
@app.post("/discussions", response_model=MessageResponse)
async def add_discussion(
    message: Message,
    user: Dict[str, Any] = Depends(auth_security)
):
    """Add a new discussion for the current user."""
    try:
        # Add discussion using the user_id from the authenticated user
        user_id = user.get("user_id") or user.get("id")
        discussion_manager.add_discussion(user_id, message.content)
        
        # Return success response
        return {
            "message_id": "new", # In a real implementation, return the actual ID
            "content": message.content,
            "success": True
        }
    except TextEmbeddingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process message: {e}",
        )
    except DatabaseConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {e}",
        )
    except DiscussionException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

@app.post("/discussions/search", response_model=List[Dict[str, Any]])
async def search_discussions(
    query: DiscussionQuery,
    user: Dict[str, Any] = Depends(auth_security)
):
    """
    Search for relevant discussions for the current user.
    
    This endpoint retrieves the most relevant past discussions
    based on the query and similarity matching.
    """
    try:
        # Get user_id from the authenticated user
        user_id = user.get("user_id") or user.get("id")
        
        # Get relevant discussions
        discussions = discussion_manager.get_relevant_discussions(
            user_id=user_id,
            query=query.query,
            top_k=query.top_k
        )
        
        return discussions
    except DiscussionException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Error searching discussions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while searching discussions",
        )

@app.delete("/discussions/{discussion_id}")
async def delete_discussion(
    discussion_id: str,
    user: Dict[str, Any] = Depends(auth_security)
):
    """Delete a discussion by ID."""
    try:
        # Get user_id from the authenticated user
        user_id = user.get("user_id") or user.get("id")
        
        # Try to delete the discussion
        success = discussion_manager.delete_discussion(
            discussion_id=discussion_id,
            user_id=user_id
        )
        
        if success:
            return {"message": "Discussion deleted successfully"}
        else:
            return {"message": "Discussion not found or you don't have permission to delete it"}
    except DiscussionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found",
        )
    except UserDiscussionAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this discussion",
        )
    except DiscussionException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

# Admin-only endpoints
@app.post("/admin/discussions/search", response_model=List[Dict[str, Any]])
async def admin_search_all_discussions(
    query: DiscussionQuery,
    user: Dict[str, Any] = Depends(auth_security.admin_required())
):
    """
    Search for relevant discussions across all users (admin only).
    
    This endpoint retrieves the most relevant past discussions
    from any user based on the query and similarity matching.
    """
    try:
        # Get relevant discussions across all users
        discussions = discussion_manager.get_all_relevant_discussions(
            query=query.query,
            top_k=query.top_k
        )
        
        return discussions
    except DiscussionException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Error searching all discussions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while searching all discussions",
        )

@app.get("/admin/users/{user_id}/discussions", response_model=List[Dict[str, Any]])
async def admin_get_user_discussions(
    user_id: str,
    query: str = "",
    top_k: int = 5,
    user: Dict[str, Any] = Depends(auth_security.admin_required())
):
    """
    Get discussions for a specific user (admin only).
    
    This endpoint allows admins to retrieve discussions for any user.
    """
    try:
        # Get relevant discussions for the specified user
        discussions = discussion_manager.get_relevant_discussions(
            user_id=user_id,
            query=query,
            top_k=top_k
        )
        
        return discussions
    except DiscussionException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    # Run the FastAPI application with uvicorn
    uvicorn.run(
        "example:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    ) 