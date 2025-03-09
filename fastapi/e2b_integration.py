"""
E2B Code Interpreter integration with FastAPI.

This module provides FastAPI routes and dependencies for integrating
E2B Code Interpreter with FastAPI applications.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from pydantic import BaseModel, Field

# Import from auth
from ..auth.exceptions import (
    AuthException, TokenInvalidError, TokenExpiredError, PermissionError
)

# Import from discussion
from ..discussion.manager import DiscussionManager
from ..discussion.exceptions import DiscussionException

# Import from the e2b_interpreter module
from ..e2b_interpreter import (
    CodeInterpreterClient, AsyncCodeInterpreterClient,
    CodeInterpreterException, InterpreterConfigError, 
    SandboxError, ExecutionError, TimeoutError
)

# Import FastAPI security
from .security import (
    AgentAuthSecurity, get_current_user, get_admin_user, get_user_with_role
)

logger = logging.getLogger(__name__)


# Pydantic models for the API
class CodeExecutionRequest(BaseModel):
    """Request model for code execution."""
    
    code: str = Field(..., description="Code to execute")
    language: str = Field("python", description="Programming language")
    store_result: bool = Field(True, description="Whether to store the result")
    execution_id: Optional[str] = Field(None, description="Optional execution ID")
    environment_vars: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    timeout: Optional[float] = Field(None, description="Execution timeout in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "code": "print('Hello, world!')\nresult = 42",
                "language": "python",
                "store_result": True,
                "environment_vars": {"DEBUG": "true"}
            }
        }


class CodeExecutionResult(BaseModel):
    """Response model for code execution."""
    
    execution_id: str = Field(..., description="Execution ID")
    user_id: Union[str, int] = Field(..., description="User ID")
    language: str = Field(..., description="Programming language")
    success: bool = Field(..., description="Whether execution was successful")
    outputs: List[Dict[str, Any]] = Field([], description="Stdout/stderr outputs")
    errors: List[Dict[str, Any]] = Field([], description="Execution errors")
    result: Dict[str, Any] = Field({}, description="Result data")
    timestamp: str = Field(..., description="Execution timestamp")


class ExecutionQueryParams(BaseModel):
    """Query parameters for retrieving executions."""
    
    limit: int = Field(10, description="Maximum number of results")
    offset: int = Field(0, description="Result offset")
    user_id: Optional[Union[str, int]] = Field(None, description="Filter by user ID")
    language: Optional[str] = Field(None, description="Filter by programming language")
    success: Optional[bool] = Field(None, description="Filter by success status")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    detail: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")


def create_e2b_router(
    discussion_manager: Optional[DiscussionManager] = None,
    e2b_api_key: Optional[str] = None,
    auth_security: Optional[AgentAuthSecurity] = None
) -> APIRouter:
    """
    Create a FastAPI router for E2B Code Interpreter integration.
    
    Args:
        discussion_manager: DiscussionManager instance for storing results
        e2b_api_key: E2B API key (falls back to environment variable)
        auth_security: AgentAuthSecurity instance for authentication
        
    Returns:
        APIRouter instance with E2B routes
    """
    router = APIRouter(
        prefix="/e2b",
        tags=["e2b", "code-interpreter"]
    )
    
    # Create or use the provided security instance
    security = auth_security or AgentAuthSecurity()
    
    # Create background interpreter client
    interpreter = CodeInterpreterClient(
        api_key=e2b_api_key or os.environ.get("E2B_API_KEY"),
        discussion_manager=discussion_manager,
        timeout=float(os.environ.get("E2B_EXECUTION_TIMEOUT", "300"))
    )
    
    # Route for executing code
    @router.post(
        "/execute",
        response_model=CodeExecutionResult,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        }
    )
    async def execute_code(
        request: CodeExecutionRequest,
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        """
        Execute code in a secure sandbox.
        
        This endpoint allows users to execute code in various programming languages
        within a secure sandbox environment. Results can be stored in the vector
        database for later retrieval.
        
        Args:
            request: Code execution request
            user: Authenticated user (from dependency)
            
        Returns:
            Execution result
            
        Raises:
            HTTPException: For authentication or execution errors
        """
        try:
            # Run the code
            result = interpreter.execute_code(
                code=request.code,
                user_id=user["user_id"],
                language=request.language,
                store_result=request.store_result,
                execution_id=request.execution_id,
                environment_vars=request.environment_vars,
                timeout=request.timeout
            )
            
            return result
            
        except CodeInterpreterException as e:
            error_type = type(e).__name__
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
            if isinstance(e, TimeoutError):
                status_code = status.HTTP_408_REQUEST_TIMEOUT
            elif isinstance(e, ExecutionError):
                status_code = status.HTTP_400_BAD_REQUEST
                
            raise HTTPException(
                status_code=status_code,
                detail=str(e),
                headers={"Error-Type": error_type}
            )
        except Exception as e:
            logger.error(f"Unexpected error during code execution: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
                headers={"Error-Type": "ServerError"}
            )
            
    # Route for executing code in background
    @router.post(
        "/schedule",
        response_model=Dict[str, str],
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        }
    )
    async def schedule_execution(
        request: CodeExecutionRequest,
        background_tasks: BackgroundTasks,
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        """
        Schedule code execution in the background.
        
        This endpoint queues the code execution to run in the background,
        allowing the API to respond immediately while the code runs.
        
        Args:
            request: Code execution request
            background_tasks: FastAPI background tasks
            user: Authenticated user (from dependency)
            
        Returns:
            Dictionary with execution ID
            
        Raises:
            HTTPException: For authentication or scheduling errors
        """
        try:
            # Generate execution ID
            execution_id = request.execution_id or os.urandom(8).hex()
            
            # Define background task
            def execute_in_background():
                try:
                    interpreter.execute_code(
                        code=request.code,
                        user_id=user["user_id"],
                        language=request.language,
                        store_result=request.store_result,
                        execution_id=execution_id,
                        environment_vars=request.environment_vars,
                        timeout=request.timeout
                    )
                except Exception as e:
                    logger.error(f"Background execution error: {e}")
            
            # Add task to background tasks
            background_tasks.add_task(execute_in_background)
            
            return {"execution_id": execution_id}
            
        except Exception as e:
            logger.error(f"Failed to schedule code execution: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to schedule execution: {str(e)}",
                headers={"Error-Type": "SchedulingError"}
            )
    
    # Route for retrieving execution results
    @router.get(
        "/executions",
        response_model=List[CodeExecutionResult],
        responses={
            401: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        }
    )
    async def get_executions(
        query: str = Query(..., description="Search query"),
        limit: int = Query(10, description="Maximum number of results"),
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        """
        Get execution results matching a query.
        
        This endpoint searches the vector database for code executions
        matching the specified query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            user: Authenticated user (from dependency)
            
        Returns:
            List of matching execution results
            
        Raises:
            HTTPException: For authentication or database errors
        """
        try:
            if not discussion_manager:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Discussion manager not configured",
                    headers={"Error-Type": "ConfigurationError"}
                )
                
            # Get relevant discussions
            discussions = discussion_manager.get_relevant_discussions(
                user_id=user["user_id"],
                query=query,
                top_k=limit
            )
            
            # Parse JSON and filter for code executions
            results = []
            for discussion in discussions:
                try:
                    content = json.loads(discussion.get("content", "{}"))
                    if "execution_id" in content and "code" in content:
                        results.append(content)
                except (json.JSONDecodeError, AttributeError):
                    # Skip invalid entries
                    continue
                    
            return results
            
        except DiscussionException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
                headers={"Error-Type": type(e).__name__}
            )
        except Exception as e:
            logger.error(f"Failed to retrieve execution results: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve execution results: {str(e)}",
                headers={"Error-Type": "ServerError"}
            )
    
    # Route for admin to get all executions
    @router.get(
        "/admin/executions",
        response_model=List[CodeExecutionResult],
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        }
    )
    async def get_all_executions(
        query: str = Query(..., description="Search query"),
        limit: int = Query(10, description="Maximum number of results"),
        user: Dict[str, Any] = Depends(get_admin_user)
    ):
        """
        Admin route to get all execution results matching a query.
        
        This endpoint searches the vector database for all code executions
        matching the specified query, regardless of user.
        
        Args:
            query: Search query
            limit: Maximum number of results
            user: Authenticated admin user (from dependency)
            
        Returns:
            List of matching execution results
            
        Raises:
            HTTPException: For authentication, permission, or database errors
        """
        try:
            if not discussion_manager:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Discussion manager not configured",
                    headers={"Error-Type": "ConfigurationError"}
                )
                
            # Get all relevant discussions
            discussions = discussion_manager.get_all_relevant_discussions(
                query=query,
                top_k=limit
            )
            
            # Parse JSON and filter for code executions
            results = []
            for discussion in discussions:
                try:
                    content = json.loads(discussion.get("content", "{}"))
                    if "execution_id" in content and "code" in content:
                        results.append(content)
                except (json.JSONDecodeError, AttributeError):
                    # Skip invalid entries
                    continue
                    
            return results
            
        except DiscussionException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
                headers={"Error-Type": type(e).__name__}
            )
        except Exception as e:
            logger.error(f"Failed to retrieve all execution results: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve execution results: {str(e)}",
                headers={"Error-Type": "ServerError"}
            )
    
    return router 