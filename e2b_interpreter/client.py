"""
Client for the E2B Code Interpreter integration.

This module provides client classes for interacting with the E2B Code Interpreter
allowing for code execution in secure sandboxes.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Awaitable
from datetime import datetime
import asyncio

# Import e2b
from e2b_code_interpreter import Sandbox, AsyncSandbox
from e2b_code_interpreter.models import (
    OutputMessage, ExecutionError as E2BExecutionError, Result
)

# Import local exceptions
from .exceptions import (
    CodeInterpreterException, InterpreterConfigError, 
    SandboxError, ExecutionError, TimeoutError
)

# Import vector database functionality 
from ..discussion.manager import DiscussionManager

# Type alias for output handler
T = TypeVar('T')
OutputHandler = Union[Callable[[T], Any], Callable[[T], Awaitable[Any]]]

logger = logging.getLogger(__name__)


class CodeInterpreterClient:
    """
    Client for running code in a secure E2B sandbox.
    
    This class provides a high-level interface for executing code and 
    managing execution contexts in isolated sandboxes.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        discussion_manager: Optional[DiscussionManager] = None,
        timeout: float = 300.0,
        **kwargs
    ):
        """
        Initialize the code interpreter client.
        
        Args:
            api_key: E2B API key (falls back to environment variable)
            discussion_manager: Optional discussion manager for saving results
            timeout: Default execution timeout in seconds
            **kwargs: Additional configuration options for the E2B sandbox
            
        Raises:
            InterpreterConfigError: If configuration is invalid
        """
        self.api_key = api_key
        self.discussion_manager = discussion_manager
        self.timeout = timeout
        self.sandbox = None
        self.current_context_id = None
        self.config = kwargs or {}
        
        try:
            # Create the sandbox
            self.sandbox = Sandbox(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize E2B sandbox: {e}")
            raise InterpreterConfigError(f"Failed to initialize E2B sandbox: {e}")
            
    def execute_code(
        self,
        code: str,
        user_id: Union[str, int],
        language: Optional[str] = "python",
        store_result: bool = True,
        execution_id: Optional[str] = None,
        context_id: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute code in the sandbox.
        
        Args:
            code: Code to execute
            user_id: ID of the user executing the code
            language: Programming language (python, javascript, etc.)
            store_result: Whether to store the result in the vector DB
            execution_id: Optional execution ID (generates a UUID if not provided)
            context_id: Optional context ID for continuing a previous execution
            environment_vars: Optional environment variables
            timeout: Execution timeout in seconds (overrides default)
            
        Returns:
            Dict with execution results including outputs, errors, and result data
            
        Raises:
            SandboxError: If sandbox operations fail
            ExecutionError: If code execution fails
            TimeoutError: If execution times out
        """
        execution_id = execution_id or str(uuid.uuid4())
        timeout = timeout or self.timeout
        outputs = []
        errors = []
        result_data = {}
        
        def on_stdout(message: OutputMessage):
            """Handle stdout messages."""
            outputs.append({
                "type": "stdout",
                "line": message.line,
                "timestamp": message.timestamp
            })
            
        def on_stderr(message: OutputMessage):
            """Handle stderr messages."""
            outputs.append({
                "type": "stderr",
                "line": message.line,
                "timestamp": message.timestamp
            })
            
        def on_result(result: Result):
            """Handle result data."""
            nonlocal result_data
            
            # Extract available formats
            formats = list(result.formats())
            
            # Store the result data
            result_dict = {
                "formats": formats
            }
            
            # Include text representation if available
            if result.text:
                result_dict["text"] = result.text
                
            # Include JSON data if available
            if result.json:
                result_dict["json"] = result.json
                
            # Include chart data if available
            if result.chart:
                result_dict["chart"] = {
                    "type": result.chart.type,
                    "data": result.chart.__dict__
                }
                
            # Include any other available data
            for fmt in formats:
                if fmt not in ["text", "json", "chart"]:
                    result_dict[fmt] = getattr(result, fmt, None)
                    
            result_data = result_dict
            
        def on_error(error: E2BExecutionError):
            """Handle execution errors."""
            errors.append({
                "name": error.name,
                "value": error.value,
                "traceback": error.traceback
            })
        
        try:
            # Execute the code
            execution = self.sandbox.run_code(
                code=code,
                language=language,
                on_stdout=on_stdout,
                on_stderr=on_stderr,
                on_result=on_result,
                on_error=on_error,
                envs=environment_vars,
                timeout=timeout
            )
            
            # Prepare the result
            result = {
                "execution_id": execution_id,
                "user_id": user_id,
                "language": language,
                "code": code,
                "outputs": outputs,
                "errors": errors,
                "result": result_data,
                "success": len(errors) == 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store the result if requested
            if store_result and self.discussion_manager and len(outputs) > 0:
                result_str = json.dumps(result)
                try:
                    self.discussion_manager.add_discussion(
                        user_id=user_id,
                        message=result_str
                    )
                except Exception as e:
                    logger.warning(f"Failed to store execution result: {e}")
                    
            return result
            
        except E2BExecutionError as e:
            raise ExecutionError(
                message="Code execution failed",
                code=code,
                error_name=e.name,
                error_value=e.value,
                traceback=e.traceback
            )
        except Exception as e:
            if "timeout" in str(e).lower():
                raise TimeoutError(
                    message="Execution timed out",
                    timeout_seconds=timeout
                )
            raise SandboxError(f"Sandbox operation failed: {e}")
            
    def create_context(
        self,
        language: Optional[str] = "python",
        working_dir: Optional[str] = None
    ) -> str:
        """
        Create a new execution context.
        
        Args:
            language: Programming language for the context
            working_dir: Working directory for the context
            
        Returns:
            Context ID string
            
        Raises:
            SandboxError: If context creation fails
        """
        try:
            context = self.sandbox.create_code_context(
                language=language,
                cwd=working_dir
            )
            self.current_context_id = context.id
            return context.id
        except Exception as e:
            raise SandboxError(f"Failed to create execution context: {e}")
            
    def __del__(self):
        """Clean up resources."""
        if self.sandbox:
            try:
                self.sandbox.close()
            except Exception as e:
                logger.warning(f"Failed to close sandbox: {e}")


class AsyncCodeInterpreterClient:
    """
    Asynchronous client for running code in a secure E2B sandbox.
    
    This class provides a high-level interface for executing code and
    managing execution contexts in isolated sandboxes asynchronously.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        discussion_manager: Optional[DiscussionManager] = None,
        timeout: float = 300.0,
        **kwargs
    ):
        """
        Initialize the async code interpreter client.
        
        Args:
            api_key: E2B API key (falls back to environment variable)
            discussion_manager: Optional discussion manager for saving results
            timeout: Default execution timeout in seconds
            **kwargs: Additional configuration options for the E2B sandbox
            
        Raises:
            InterpreterConfigError: If configuration is invalid
        """
        self.api_key = api_key
        self.discussion_manager = discussion_manager
        self.timeout = timeout
        self.sandbox = None
        self.current_context_id = None
        self.config = kwargs or {}
        
    async def initialize(self):
        """
        Initialize the sandbox asynchronously.
        
        Raises:
            InterpreterConfigError: If configuration is invalid
        """
        try:
            # Create the sandbox
            self.sandbox = await AsyncSandbox.create(api_key=self.api_key)
            return self
        except Exception as e:
            logger.error(f"Failed to initialize E2B sandbox: {e}")
            raise InterpreterConfigError(f"Failed to initialize E2B sandbox: {e}")
    
    @classmethod
    async def create(
        cls,
        api_key: Optional[str] = None,
        discussion_manager: Optional[DiscussionManager] = None,
        timeout: float = 300.0,
        **kwargs
    ):
        """
        Create and initialize an AsyncCodeInterpreterClient.
        
        Args:
            api_key: E2B API key (falls back to environment variable)
            discussion_manager: Optional discussion manager for saving results
            timeout: Default execution timeout in seconds
            **kwargs: Additional configuration options for the E2B sandbox
            
        Returns:
            Initialized AsyncCodeInterpreterClient instance
            
        Raises:
            InterpreterConfigError: If configuration is invalid
        """
        client = cls(
            api_key=api_key,
            discussion_manager=discussion_manager,
            timeout=timeout,
            **kwargs
        )
        await client.initialize()
        return client
            
    async def execute_code(
        self,
        code: str,
        user_id: Union[str, int],
        language: Optional[str] = "python",
        store_result: bool = True,
        execution_id: Optional[str] = None,
        context_id: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute code in the sandbox asynchronously.
        
        Args:
            code: Code to execute
            user_id: ID of the user executing the code
            language: Programming language (python, javascript, etc.)
            store_result: Whether to store the result in the vector DB
            execution_id: Optional execution ID (generates a UUID if not provided)
            context_id: Optional context ID for continuing a previous execution
            environment_vars: Optional environment variables
            timeout: Execution timeout in seconds (overrides default)
            
        Returns:
            Dict with execution results including outputs, errors, and result data
            
        Raises:
            SandboxError: If sandbox operations fail
            ExecutionError: If code execution fails
            TimeoutError: If execution times out
        """
        if not self.sandbox:
            await self.initialize()
            
        execution_id = execution_id or str(uuid.uuid4())
        timeout = timeout or self.timeout
        outputs = []
        errors = []
        result_data = {}
        
        async def on_stdout(message: OutputMessage):
            """Handle stdout messages."""
            outputs.append({
                "type": "stdout",
                "line": message.line,
                "timestamp": message.timestamp
            })
            
        async def on_stderr(message: OutputMessage):
            """Handle stderr messages."""
            outputs.append({
                "type": "stderr",
                "line": message.line,
                "timestamp": message.timestamp
            })
            
        async def on_result(result: Result):
            """Handle result data."""
            nonlocal result_data
            
            # Extract available formats
            formats = list(result.formats())
            
            # Store the result data
            result_dict = {
                "formats": formats
            }
            
            # Include text representation if available
            if result.text:
                result_dict["text"] = result.text
                
            # Include JSON data if available
            if result.json:
                result_dict["json"] = result.json
                
            # Include chart data if available
            if result.chart:
                result_dict["chart"] = {
                    "type": result.chart.type,
                    "data": result.chart.__dict__
                }
                
            # Include any other available data
            for fmt in formats:
                if fmt not in ["text", "json", "chart"]:
                    result_dict[fmt] = getattr(result, fmt, None)
                    
            result_data = result_dict
            
        async def on_error(error: E2BExecutionError):
            """Handle execution errors."""
            errors.append({
                "name": error.name,
                "value": error.value,
                "traceback": error.traceback
            })
        
        try:
            # Execute the code
            execution = await self.sandbox.run_code(
                code=code,
                language=language,
                on_stdout=on_stdout,
                on_stderr=on_stderr,
                on_result=on_result,
                on_error=on_error,
                envs=environment_vars,
                timeout=timeout
            )
            
            # Prepare the result
            result = {
                "execution_id": execution_id,
                "user_id": user_id,
                "language": language,
                "code": code,
                "outputs": outputs,
                "errors": errors,
                "result": result_data,
                "success": len(errors) == 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store the result if requested
            if store_result and self.discussion_manager and len(outputs) > 0:
                result_str = json.dumps(result)
                try:
                    self.discussion_manager.add_discussion(
                        user_id=user_id,
                        message=result_str
                    )
                except Exception as e:
                    logger.warning(f"Failed to store execution result: {e}")
                    
            return result
            
        except E2BExecutionError as e:
            raise ExecutionError(
                message="Code execution failed",
                code=code,
                error_name=e.name,
                error_value=e.value,
                traceback=e.traceback
            )
        except Exception as e:
            if "timeout" in str(e).lower():
                raise TimeoutError(
                    message="Execution timed out",
                    timeout_seconds=timeout
                )
            raise SandboxError(f"Sandbox operation failed: {e}")
            
    async def create_context(
        self,
        language: Optional[str] = "python",
        working_dir: Optional[str] = None
    ) -> str:
        """
        Create a new execution context asynchronously.
        
        Args:
            language: Programming language for the context
            working_dir: Working directory for the context
            
        Returns:
            Context ID string
            
        Raises:
            SandboxError: If context creation fails
        """
        if not self.sandbox:
            await self.initialize()
            
        try:
            context = await self.sandbox.create_code_context(
                language=language,
                cwd=working_dir
            )
            self.current_context_id = context.id
            return context.id
        except Exception as e:
            raise SandboxError(f"Failed to create execution context: {e}")
            
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.sandbox:
            await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.sandbox:
            try:
                await self.sandbox.close()
            except Exception as e:
                logger.warning(f"Failed to close sandbox: {e}")
            
    async def close(self):
        """Clean up resources asynchronously."""
        if self.sandbox:
            try:
                await self.sandbox.close()
                self.sandbox = None
            except Exception as e:
                logger.warning(f"Failed to close sandbox: {e}") 