"""
Exceptions for the workflows module.
"""

from ..auth.exceptions import ComposioBaseException


class WorkflowError(ComposioBaseException):
    """Base exception for workflow-related errors."""
    pass


class WorkflowNotFoundError(WorkflowError):
    """Exception raised when a workflow is not found."""
    def __init__(self, workflow_id=None, message=None):
        self.workflow_id = workflow_id
        default_message = f"Workflow not found"
        if workflow_id:
            default_message += f": {workflow_id}"
        super().__init__(message or default_message)


class WorkflowExecutionError(WorkflowError):
    """Exception raised when a workflow execution fails."""
    def __init__(self, workflow_id=None, step_id=None, message=None, cause=None):
        self.workflow_id = workflow_id
        self.step_id = step_id
        default_message = f"Workflow execution failed"
        if workflow_id:
            default_message += f" for workflow: {workflow_id}"
        if step_id:
            default_message += f" at step: {step_id}"
        if cause:
            default_message += f" - Cause: {str(cause)}"
        super().__init__(message or default_message)
        self.__cause__ = cause


class WorkflowValidationError(WorkflowError):
    """Exception raised when workflow validation fails."""
    def __init__(self, workflow_id=None, errors=None, message=None):
        self.workflow_id = workflow_id
        self.errors = errors or []
        default_message = f"Workflow validation failed"
        if workflow_id:
            default_message += f" for workflow: {workflow_id}"
        if errors:
            default_message += f" - Errors: {', '.join(errors)}"
        super().__init__(message or default_message) 