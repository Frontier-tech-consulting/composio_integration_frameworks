"""
Example FastAPI application using Composio Agent Integration with E2B Code Interpreter.

This example demonstrates how to integrate E2B Code Interpreter with FastAPI
and Composio's AgentAuth to create a secure code execution API.
"""

import os
import logging
from typing import Dict, Any

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import components from composio_integration_frameworks
from ..auth.client import register_user, login_user
from ..discussion.manager import DiscussionManager
from ..e2b_interpreter import CodeInterpreterClient, AsyncCodeInterpreterClient

# Import FastAPI components
from .middleware import AuthenticationMiddleware
from .security import AgentAuthSecurity
from .e2b_integration import create_e2b_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a FastAPI application
app = FastAPI(
    title="E2B Code Interpreter Integration Example",
    description="An example FastAPI application that demonstrates how to use E2B Code Interpreter with Composio Agent Integration",
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

# Create a discussion manager for storing execution results
discussion_manager = DiscussionManager(
    vector_db_type=os.environ.get("VECTOR_DB_TYPE", "chroma"),
    config={
        # For Pinecone
        "api_key": os.environ.get("PINECONE_API_KEY"),
        "environment": os.environ.get("PINECONE_ENVIRONMENT"),
        "index_name": os.environ.get("PINECONE_INDEX", "composio-e2b-executions"),
        
        # For Chroma
        "persist_directory": os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db"),
        "collection_name": os.environ.get("CHROMA_COLLECTION", "e2b_executions"),
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

# Create E2B router and add it to the FastAPI app
e2b_router = create_e2b_router(
    discussion_manager=discussion_manager,
    e2b_api_key=os.environ.get("E2B_API_KEY"),
    auth_security=auth_security
)
app.include_router(e2b_router)

# Authentication routes
@app.post("/auth/register", response_model=Dict[str, Any], tags=["auth"])
async def api_register_user(user: UserRegister):
    """Register a new user."""
    result = register_user(
        username=user.username,
        password=user.password,
        email=user.email,
        role=user.role
    )
    return {"user_id": result.get("user_id"), "username": user.username, "role": user.role}

@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
async def api_login_user(user: UserLogin):
    """Login and get access token."""
    result = login_user(username=user.username, password=user.password)
    return {"access_token": result.get("token")}

# Health check route
@app.get("/health", tags=["status"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "auth": True,
            "discussion_manager": discussion_manager is not None,
            "e2b_interpreter": True
        }
    }

# Example usage
"""
Example usage of the E2B Code Interpreter API:

1. Register a user:
   ```
   curl -X POST "http://localhost:8000/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"username": "testuser", "password": "password123", "email": "test@example.com"}'
   ```

2. Login to get a token:
   ```
   curl -X POST "http://localhost:8000/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "testuser", "password": "password123"}'
   ```

3. Execute code:
   ```
   curl -X POST "http://localhost:8000/e2b/execute" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -d '{
            "code": "import numpy as np\nimport matplotlib.pyplot as plt\n\nx = np.linspace(0, 10, 100)\ny = np.sin(x)\nprint(f\"Min: {y.min()}, Max: {y.max()}\")\nresult = {\"min\": float(y.min()), \"max\": float(y.max())}",
            "language": "python"
        }'
   ```

4. Schedule code execution in the background:
   ```
   curl -X POST "http://localhost:8000/e2b/schedule" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -d '{
            "code": "import time\nprint(\"Starting long computation\")\ntime.sleep(10)\nprint(\"Completed\")\nresult = {\"status\": \"completed\"}",
            "language": "python"
        }'
   ```

5. Search for execution results:
   ```
   curl -X GET "http://localhost:8000/e2b/executions?query=numpy&limit=5" \
        -H "Authorization: Bearer YOUR_TOKEN"
   ```

6. Admin access to all executions:
   ```
   curl -X GET "http://localhost:8000/e2b/admin/executions?query=error&limit=10" \
        -H "Authorization: Bearer ADMIN_TOKEN"
   ```
"""

# Run with:
# uvicorn composio_integration_frameworks.fastapi.e2b_example:app --reload 