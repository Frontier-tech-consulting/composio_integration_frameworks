"""
Tests for the E2B Code Interpreter integration.

This module provides test cases for the E2B Code Interpreter integration.
"""

import unittest
import os
import json
import uuid
from typing import Dict, Any, Optional

from unittest.mock import patch, MagicMock

from .client import CodeInterpreterClient, AsyncCodeInterpreterClient
from .exceptions import (
    CodeInterpreterException, InterpreterConfigError, 
    SandboxError, ExecutionError, TimeoutError
)


class MockResponse:
    """Mock response object for testing."""
    
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        
    def json(self):
        """Return mock JSON data."""
        return self._json_data


class TestCodeInterpreterClient(unittest.TestCase):
    """Test cases for the CodeInterpreterClient."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test environment
        self.api_key = "test-api-key"
        self.user_id = "test-user-123"
        self.code = "print('Hello, world!')\nresult = 42"
        
        # Create mocks
        self.discussion_manager = MagicMock()
        
        # Create a patcher for the Sandbox class
        self.sandbox_patcher = patch('e2b_interpreter.client.Sandbox')
        self.sandbox_mock = self.sandbox_patcher.start()
        
        # Set up mock instance
        self.sandbox_instance = MagicMock()
        self.sandbox_mock.return_value = self.sandbox_instance
        
    def tearDown(self):
        """Clean up after tests."""
        # Stop patchers
        self.sandbox_patcher.stop()
    
    def test_init(self):
        """Test initialization with valid parameters."""
        # Act
        client = CodeInterpreterClient(
            api_key=self.api_key,
            discussion_manager=self.discussion_manager,
            timeout=300.0
        )
        
        # Assert
        self.sandbox_mock.assert_called_once_with(api_key=self.api_key)
        self.assertEqual(client.api_key, self.api_key)
        self.assertEqual(client.discussion_manager, self.discussion_manager)
        self.assertEqual(client.timeout, 300.0)
    
    def test_init_error(self):
        """Test initialization with error."""
        # Arrange
        self.sandbox_mock.side_effect = Exception("Connection error")
        
        # Act & Assert
        with self.assertRaises(InterpreterConfigError):
            CodeInterpreterClient(api_key=self.api_key)
    
    def test_execute_code_success(self):
        """Test successful code execution."""
        # Arrange
        client = CodeInterpreterClient(
            api_key=self.api_key,
            discussion_manager=self.discussion_manager
        )
        
        # Set up mock execution
        execution_mock = MagicMock()
        self.sandbox_instance.run_code.return_value = execution_mock
        
        # Act
        result = client.execute_code(
            code=self.code,
            user_id=self.user_id,
            language="python"
        )
        
        # Assert
        self.sandbox_instance.run_code.assert_called_once()
        self.assertTrue(result['success'])
        self.assertEqual(result['user_id'], self.user_id)
        self.assertEqual(result['language'], "python")
        self.assertEqual(result['code'], self.code)
    
    def test_execute_code_with_result_storage(self):
        """Test code execution with result storage."""
        # Arrange
        client = CodeInterpreterClient(
            api_key=self.api_key,
            discussion_manager=self.discussion_manager
        )
        
        # Set up mock execution
        execution_mock = MagicMock()
        self.sandbox_instance.run_code.return_value = execution_mock
        
        # Set up outputs to trigger storage
        outputs = [{"type": "stdout", "line": "Hello, world!", "timestamp": 123456789}]
        
        # Mock the on_stdout callback
        def side_effect(code, language, on_stdout, **kwargs):
            # Call the callback with test data
            on_stdout(MagicMock(line="Hello, world!", timestamp=123456789, error=False))
            return execution_mock
            
        self.sandbox_instance.run_code.side_effect = side_effect
        
        # Act
        result = client.execute_code(
            code=self.code,
            user_id=self.user_id,
            language="python",
            store_result=True
        )
        
        # Assert
        self.discussion_manager.add_discussion.assert_called_once()
        call_args = self.discussion_manager.add_discussion.call_args[1]
        self.assertEqual(call_args['user_id'], self.user_id)
        
        # Parse the stored message
        stored_message = call_args['message']
        stored_data = json.loads(stored_message)
        
        self.assertEqual(stored_data['code'], self.code)
        self.assertEqual(stored_data['user_id'], self.user_id)
    
    @patch('e2b_interpreter.client.uuid.uuid4')
    def test_execute_code_with_execution_id(self, mock_uuid):
        """Test code execution with custom execution ID."""
        # Arrange
        client = CodeInterpreterClient(
            api_key=self.api_key,
            discussion_manager=self.discussion_manager
        )
        
        # Set up mock UUID
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        
        # Set up mock execution
        execution_mock = MagicMock()
        self.sandbox_instance.run_code.return_value = execution_mock
        
        # Act - with custom execution ID
        result_with_id = client.execute_code(
            code=self.code,
            user_id=self.user_id,
            execution_id="custom-id-123"
        )
        
        # Act - without custom execution ID
        result_without_id = client.execute_code(
            code=self.code,
            user_id=self.user_id
        )
        
        # Assert
        self.assertEqual(result_with_id['execution_id'], "custom-id-123")
        self.assertEqual(result_without_id['execution_id'], "12345678-1234-5678-1234-567812345678")
        
    def test_execution_error(self):
        """Test handling of execution errors."""
        # Arrange
        client = CodeInterpreterClient(
            api_key=self.api_key,
            discussion_manager=self.discussion_manager
        )
        
        # Create a mock error
        error = MagicMock()
        error.name = "SyntaxError"
        error.value = "invalid syntax"
        error.traceback = "Traceback (most recent call last):\n..."
        
        # Mock the on_error callback
        def side_effect(code, language, on_error, **kwargs):
            # Call the callback with test data
            on_error(error)
            return MagicMock()
            
        self.sandbox_instance.run_code.side_effect = side_effect
        
        # Act
        result = client.execute_code(
            code="print('Hello, world'",  # Syntax error
            user_id=self.user_id
        )
        
        # Assert
        self.assertFalse(result['success'])
        self.assertEqual(len(result['errors']), 1)
        self.assertEqual(result['errors'][0]['name'], "SyntaxError")
        
    def test_create_context(self):
        """Test creating a new execution context."""
        # Arrange
        client = CodeInterpreterClient(
            api_key=self.api_key,
            discussion_manager=self.discussion_manager
        )
        
        # Set up mock context
        context_mock = MagicMock()
        context_mock.id = "test-context-123"
        self.sandbox_instance.create_code_context.return_value = context_mock
        
        # Act
        context_id = client.create_context(language="python")
        
        # Assert
        self.assertEqual(context_id, "test-context-123")
        self.assertEqual(client.current_context_id, "test-context-123")
        self.sandbox_instance.create_code_context.assert_called_once_with(
            language="python",
            cwd=None
        )
        
    def test_create_context_error(self):
        """Test error handling in create_context."""
        # Arrange
        client = CodeInterpreterClient(
            api_key=self.api_key,
            discussion_manager=self.discussion_manager
        )
        
        # Set up mock error
        self.sandbox_instance.create_code_context.side_effect = Exception("Context creation failed")
        
        # Act & Assert
        with self.assertRaises(SandboxError):
            client.create_context()


class TestAsyncCodeInterpreterClient(unittest.TestCase):
    """Test cases for the AsyncCodeInterpreterClient."""
    
    def setUp(self):
        """Set up test environment."""
        # Note: These are synchronous tests for the async class
        # For proper async testing, use asynctest or pytest with async/await
        
        # Create a test environment
        self.api_key = "test-api-key"
        self.user_id = "test-user-123"
        self.code = "print('Hello, world!')\nresult = 42"
        
        # Create mocks
        self.discussion_manager = MagicMock()
        
        # Create a patcher for the AsyncSandbox class
        self.sandbox_patcher = patch('e2b_interpreter.client.AsyncSandbox')
        self.sandbox_mock = self.sandbox_patcher.start()
        
        # Set up mock instance and method
        self.sandbox_mock.create.return_value = MagicMock()
        
    def tearDown(self):
        """Clean up after tests."""
        # Stop patchers
        self.sandbox_patcher.stop()
    
    def test_init(self):
        """Test initialization with valid parameters."""
        # Act
        client = AsyncCodeInterpreterClient(
            api_key=self.api_key,
            discussion_manager=self.discussion_manager,
            timeout=300.0
        )
        
        # Assert
        self.assertEqual(client.api_key, self.api_key)
        self.assertEqual(client.discussion_manager, self.discussion_manager)
        self.assertEqual(client.timeout, 300.0)
        self.assertIsNone(client.sandbox)


# This test requires async testing framework to run properly
# @pytest.mark.asyncio
# async def test_async_execute_code():
#     """Test asynchronous code execution."""
#     client = await AsyncCodeInterpreterClient.create(api_key="test")
#     result = await client.execute_code("print('hello')", user_id="1")
#     assert result['success'] is True 