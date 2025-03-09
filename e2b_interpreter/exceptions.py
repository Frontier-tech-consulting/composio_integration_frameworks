"""
Exceptions for the E2B Code Interpreter integration.

This module provides a hierarchy of exceptions for the e2b code interpreter
integration, making it easier to handle specific error cases.
"""

from typing import Optional, Any, Dict


class CodeInterpreterException(Exception):
    """Base exception for all code interpreter errors."""
    
    def __init__(self, message: str = "Code interpreter error occurred"):
        self.message = message
        super().__init__(self.message)


class InterpreterConfigError(CodeInterpreterException):
    """Exception for configuration-related errors."""
    
    def __init__(self, message: str = "Configuration error", config: Optional[Dict[str, Any]] = None):
        self.config = config
        message = f"{message}" + (f" with config: {config}" if config else "")
        super().__init__(message)


class SandboxError(CodeInterpreterException):
    """Exception for sandbox creation or management errors."""
    
    def __init__(self, message: str = "Sandbox error", sandbox_id: Optional[str] = None):
        self.sandbox_id = sandbox_id
        message = f"{message}" + (f" for sandbox: {sandbox_id}" if sandbox_id else "")
        super().__init__(message)


class ExecutionError(CodeInterpreterException):
    """Exception for code execution errors."""
    
    def __init__(
        self, 
        message: str = "Code execution error", 
        code: Optional[str] = None,
        error_name: Optional[str] = None,
        error_value: Optional[str] = None,
        traceback: Optional[str] = None
    ):
        self.code = code
        self.error_name = error_name
        self.error_value = error_value
        self.traceback = traceback
        
        details = []
        if error_name:
            details.append(f"Error: {error_name}")
        if error_value:
            details.append(f"Value: {error_value}")
        
        message = f"{message}" + (f": {', '.join(details)}" if details else "")
        super().__init__(message)
        

class TimeoutError(CodeInterpreterException):
    """Exception for execution timeout errors."""
    
    def __init__(
        self, 
        message: str = "Execution timed out", 
        timeout_seconds: Optional[float] = None
    ):
        self.timeout_seconds = timeout_seconds
        message = f"{message}" + (f" after {timeout_seconds}s" if timeout_seconds else "")
        super().__init__(message) 