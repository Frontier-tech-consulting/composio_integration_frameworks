"""
E2B Code Interpreter integration for Composio Agent.

This module provides integration with the E2B Code Interpreter for running
code in secure sandboxes as part of agent workflows.
"""

from .client import CodeInterpreterClient, AsyncCodeInterpreterClient
from .exceptions import (
    CodeInterpreterException, InterpreterConfigError, 
    SandboxError, ExecutionError, TimeoutError
)

__all__ = [
    'CodeInterpreterClient',
    'AsyncCodeInterpreterClient',
    'CodeInterpreterException',
    'InterpreterConfigError',
    'SandboxError',
    'ExecutionError',
    'TimeoutError',
] 