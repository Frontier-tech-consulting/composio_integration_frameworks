"""
E2B Code Interpreter integration with Django.

This module provides views and utilities for integrating E2B Code Interpreter
with Django applications.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings

# Import from auth
from ..auth.exceptions import AuthException, TokenInvalidError, TokenExpiredError, PermissionError

# Import from discussion
from ..discussion.manager import DiscussionManager

# Import from the e2b_interpreter module
from ..e2b_interpreter import (
    CodeInterpreterClient, AsyncCodeInterpreterClient,
    CodeInterpreterException, InterpreterConfigError, 
    SandboxError, ExecutionError, TimeoutError
)

logger = logging.getLogger(__name__)

# Initialize discussion manager if settings are configured
discussion_manager = None
try:
    vector_db_type = getattr(settings, 'VECTOR_DB_TYPE', 'chroma')
    vector_db_config = getattr(settings, 'VECTOR_DB_CONFIG', {})
    
    # Create discussion manager instance
    discussion_manager = DiscussionManager(
        vector_db_type=vector_db_type,
        config=vector_db_config
    )
except Exception as e:
    logger.warning(f"Failed to initialize discussion manager: {e}")

# Initialize code interpreter client
interpreter = None
try:
    e2b_api_key = getattr(settings, 'E2B_API_KEY', os.environ.get('E2B_API_KEY'))
    e2b_timeout = float(getattr(settings, 'E2B_EXECUTION_TIMEOUT', 
                               os.environ.get('E2B_EXECUTION_TIMEOUT', '300')))
    
    # Create code interpreter client
    interpreter = CodeInterpreterClient(
        api_key=e2b_api_key,
        discussion_manager=discussion_manager,
        timeout=e2b_timeout
    )
except Exception as e:
    logger.warning(f"Failed to initialize E2B code interpreter: {e}")

@login_required
@require_POST
def execute_code(request):
    """
    Execute code in a secure sandbox.
    
    This view requires a logged-in user and handles code execution using
    the E2B Code Interpreter.
    
    Request body:
    {
        "code": "print('Hello, world!')",
        "language": "python",  # Optional, defaults to "python"
        "store_result": true,  # Optional, defaults to true
        "execution_id": "uuid", # Optional
        "environment_vars": {"KEY": "VALUE"}, # Optional
        "timeout": 300.0  # Optional, in seconds
    }
    
    Returns:
        JsonResponse with execution results or error details
    """
    if not interpreter:
        return JsonResponse({
            'success': False,
            'error': 'E2B Code Interpreter is not configured',
            'error_type': 'ConfigurationError'
        }, status=500)
    
    try:
        # Parse request body
        data = json.loads(request.body)
        code = data.get('code')
        language = data.get('language', 'python')
        store_result = data.get('store_result', True)
        execution_id = data.get('execution_id')
        environment_vars = data.get('environment_vars')
        timeout = data.get('timeout')
        
        # Validate code parameter
        if not code:
            return JsonResponse({
                'success': False,
                'error': 'Code parameter is required',
                'error_type': 'ValidationError'
            }, status=400)
        
        # Get user ID from Django's user model
        user_id = request.user.id
        
        # Execute the code
        result = interpreter.execute_code(
            code=code,
            user_id=user_id,
            language=language,
            store_result=store_result,
            execution_id=execution_id,
            environment_vars=environment_vars,
            timeout=timeout
        )
        
        return JsonResponse(result)
        
    except CodeInterpreterException as e:
        error_type = type(e).__name__
        status_code = 500
        
        if isinstance(e, TimeoutError):
            status_code = 408  # Request Timeout
        elif isinstance(e, ExecutionError):
            status_code = 400  # Bad Request
            
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': error_type
        }, status=status_code)
        
    except Exception as e:
        logger.error(f"Unexpected error during code execution: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': 'ServerError'
        }, status=500)

@login_required
@permission_required('can_access_all_executions', raise_exception=True)
def get_all_executions(request):
    """
    Get all code execution results (admin only).
    
    This view requires a logged-in user with appropriate permissions.
    
    Query parameters:
    - query: Search query string
    - limit: Maximum number of results (default: 10)
    
    Returns:
        JsonResponse with list of execution results or error details
    """
    if not discussion_manager:
        return JsonResponse({
            'success': False,
            'error': 'Discussion manager is not configured',
            'error_type': 'ConfigurationError'
        }, status=500)
    
    try:
        # Get query parameters
        query = request.GET.get('query', '')
        limit = int(request.GET.get('limit', 10))
        
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
                
        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve execution results: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)

@login_required
def get_user_executions(request):
    """
    Get code execution results for the current user.
    
    This view requires a logged-in user.
    
    Query parameters:
    - query: Search query string
    - limit: Maximum number of results (default: 10)
    
    Returns:
        JsonResponse with list of execution results or error details
    """
    if not discussion_manager:
        return JsonResponse({
            'success': False,
            'error': 'Discussion manager is not configured',
            'error_type': 'ConfigurationError'
        }, status=500)
    
    try:
        # Get query parameters
        query = request.GET.get('query', '')
        limit = int(request.GET.get('limit', 10))
        
        # Get user ID from Django's user model
        user_id = request.user.id
        
        # Get relevant discussions for the user
        discussions = discussion_manager.get_relevant_discussions(
            user_id=user_id,
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
                
        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve execution results: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)

def get_code_interpreter():
    """
    Get the code interpreter client instance.
    
    Returns:
        CodeInterpreterClient instance or None if not initialized
    """
    return interpreter

def create_code_interpreter(
    api_key: Optional[str] = None,
    discussion_mgr: Optional[DiscussionManager] = None,
    timeout: Optional[float] = None
) -> CodeInterpreterClient:
    """
    Create a new code interpreter client.
    
    Args:
        api_key: E2B API key (falls back to settings or env variable)
        discussion_mgr: Discussion manager instance
        timeout: Execution timeout in seconds
        
    Returns:
        New CodeInterpreterClient instance
    """
    e2b_api_key = api_key or getattr(settings, 'E2B_API_KEY', 
                                    os.environ.get('E2B_API_KEY'))
    e2b_timeout = timeout or float(getattr(settings, 'E2B_EXECUTION_TIMEOUT', 
                                          os.environ.get('E2B_EXECUTION_TIMEOUT', '300')))
    
    return CodeInterpreterClient(
        api_key=e2b_api_key,
        discussion_manager=discussion_mgr or discussion_manager,
        timeout=e2b_timeout
    ) 