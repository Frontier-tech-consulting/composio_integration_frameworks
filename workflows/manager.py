"""
Workflow manager for executing and managing workflows.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from ..discussion.manager import DiscussionManager
from ..e2b_interpreter.client import E2BClient
from .exceptions import (
    WorkflowError,
    WorkflowExecutionError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from .models import Workflow, WorkflowResult, WorkflowStatus, WorkflowStep, StepType

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manager for executing and managing workflows."""

    def __init__(
        self,
        discussion_manager: Optional[DiscussionManager] = None,
        e2b_client: Optional[E2BClient] = None,
        storage_path: Optional[str] = None,
        custom_step_handlers: Optional[Dict[str, Callable]] = None,
    ):
        """Initialize the workflow manager.

        Args:
            discussion_manager: Optional discussion manager for storing results
            e2b_client: Optional E2B client for code execution
            storage_path: Optional path to store workflows
            custom_step_handlers: Optional dictionary of custom step handlers
        """
        self.discussion_manager = discussion_manager
        self.e2b_client = e2b_client
        self.storage_path = storage_path
        self.workflows: Dict[str, Workflow] = {}
        self.results: Dict[str, WorkflowResult] = {}
        self.custom_step_handlers = custom_step_handlers or {}
        
        # Register default step handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default step handlers."""
        self.register_step_handler(StepType.CODE_EXECUTION, self._handle_code_execution)
        
    def register_step_handler(self, step_type: Union[StepType, str], handler: Callable) -> None:
        """Register a step handler.

        Args:
            step_type: Type of step to handle
            handler: Handler function
        """
        if isinstance(step_type, str):
            step_type = StepType(step_type)
        self.custom_step_handlers[step_type.value] = handler

    def create_workflow(
        self, name: str, description: str = "", steps: List[Dict[str, Any]] = None, owner_id: Optional[str] = None
    ) -> Workflow:
        """Create a new workflow.

        Args:
            name: Name of the workflow
            description: Description of the workflow
            steps: List of step configurations
            owner_id: ID of the workflow owner

        Returns:
            Created workflow
        """
        workflow = Workflow(
            name=name,
            description=description,
            steps=[WorkflowStep.from_dict(step) for step in (steps or [])],
            owner_id=owner_id,
        )
        self.workflows[workflow.id] = workflow
        
        if self.storage_path:
            self._save_workflow(workflow)
            
        return workflow

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Get a workflow by ID.

        Args:
            workflow_id: ID of the workflow

        Returns:
            Workflow

        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        if workflow_id not in self.workflows:
            # Try to load from storage
            if self.storage_path:
                try:
                    self._load_workflow(workflow_id)
                except Exception as e:
                    raise WorkflowNotFoundError(workflow_id) from e
            else:
                raise WorkflowNotFoundError(workflow_id)
                
        return self.workflows[workflow_id]

    def update_workflow(self, workflow_id: str, **kwargs) -> Workflow:
        """Update a workflow.

        Args:
            workflow_id: ID of the workflow
            **kwargs: Fields to update

        Returns:
            Updated workflow

        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        workflow = self.get_workflow(workflow_id)
        
        for key, value in kwargs.items():
            if key == "steps" and isinstance(value, list):
                workflow.steps = [
                    WorkflowStep.from_dict(step) if isinstance(step, dict) else step
                    for step in value
                ]
            elif hasattr(workflow, key):
                setattr(workflow, key, value)
                
        workflow.updated_at = datetime.now()
        
        if self.storage_path:
            self._save_workflow(workflow)
            
        return workflow

    def delete_workflow(self, workflow_id: str) -> None:
        """Delete a workflow.

        Args:
            workflow_id: ID of the workflow

        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        if workflow_id not in self.workflows:
            raise WorkflowNotFoundError(workflow_id)
            
        del self.workflows[workflow_id]
        
        if self.storage_path:
            self._delete_workflow_file(workflow_id)

    def validate_workflow(self, workflow: Union[Workflow, str]) -> List[str]:
        """Validate a workflow.

        Args:
            workflow: Workflow or workflow ID

        Returns:
            List of validation errors

        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        if isinstance(workflow, str):
            workflow = self.get_workflow(workflow)
            
        errors = []
        
        # Check for cycles in dependencies
        step_ids = {step.id for step in workflow.steps}
        for step in workflow.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    errors.append(f"Step {step.id} depends on non-existent step {dep_id}")
        
        # Check for unsupported step types
        for step in workflow.steps:
            if step.type.value not in self.custom_step_handlers and step.type != StepType.CUSTOM:
                errors.append(f"Unsupported step type: {step.type.value} for step {step.id}")
        
        # Check for required handlers
        if any(step.type == StepType.CODE_EXECUTION for step in workflow.steps) and not self.e2b_client:
            errors.append("E2B client is required for code execution steps")
            
        return errors

    async def execute_workflow(
        self, workflow: Union[Workflow, str], inputs: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """Execute a workflow.

        Args:
            workflow: Workflow or workflow ID
            inputs: Optional inputs for the workflow

        Returns:
            Workflow result

        Raises:
            WorkflowNotFoundError: If workflow not found
            WorkflowValidationError: If workflow validation fails
            WorkflowExecutionError: If workflow execution fails
        """
        if isinstance(workflow, str):
            workflow = self.get_workflow(workflow)
            
        # Validate workflow
        errors = self.validate_workflow(workflow)
        if errors:
            raise WorkflowValidationError(workflow.id, errors)
            
        # Create result object
        result = WorkflowResult(
            workflow_id=workflow.id,
            status=WorkflowStatus.RUNNING,
        )
        self.results[workflow.id] = result
        
        # Update workflow status
        workflow.status = WorkflowStatus.RUNNING
        if self.storage_path:
            self._save_workflow(workflow)
            
        # Execute workflow
        try:
            start_time = time.time()
            
            # Reset step statuses
            for step in workflow.steps:
                step.status = WorkflowStatus.PENDING
                step.result = None
                step.error = None
                step.started_at = None
                step.completed_at = None
            
            # Execute steps
            await self._execute_steps(workflow, inputs or {}, result)
            
            # Update result
            result.status = WorkflowStatus.COMPLETED
            result.completed_at = datetime.now()
            result.execution_time_seconds = time.time() - start_time
            
            # Update workflow status
            workflow.status = WorkflowStatus.COMPLETED
            if self.storage_path:
                self._save_workflow(workflow)
                
            return result
            
        except Exception as e:
            logger.exception(f"Error executing workflow {workflow.id}")
            
            # Update result
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now()
            result.execution_time_seconds = time.time() - start_time
            
            # Update workflow status
            workflow.status = WorkflowStatus.FAILED
            if self.storage_path:
                self._save_workflow(workflow)
                
            raise WorkflowExecutionError(workflow.id, None, cause=e) from e

    async def _execute_steps(
        self, workflow: Workflow, inputs: Dict[str, Any], result: WorkflowResult
    ) -> None:
        """Execute workflow steps.

        Args:
            workflow: Workflow to execute
            inputs: Inputs for the workflow
            result: Result object to update
        """
        # Create context with inputs
        context = {
            "inputs": inputs,
            "results": {},
            "workflow": workflow.to_dict(),
        }
        
        # Find steps with no dependencies
        ready_steps = [
            step for step in workflow.steps
            if not step.depends_on and step.status == WorkflowStatus.PENDING
        ]
        
        # Execute steps until all are completed
        while ready_steps:
            # Execute ready steps in parallel
            tasks = [
                self._execute_step(step, context, result)
                for step in ready_steps
            ]
            await asyncio.gather(*tasks)
            
            # Find next ready steps
            ready_steps = []
            for step in workflow.steps:
                if step.status == WorkflowStatus.PENDING:
                    # Check if all dependencies are completed
                    deps_completed = all(
                        any(dep_step.id == dep_id and dep_step.status == WorkflowStatus.COMPLETED
                            for dep_step in workflow.steps)
                        for dep_id in step.depends_on
                    )
                    if deps_completed:
                        ready_steps.append(step)

    async def _execute_step(
        self, step: WorkflowStep, context: Dict[str, Any], result: WorkflowResult
    ) -> None:
        """Execute a workflow step.

        Args:
            step: Step to execute
            context: Execution context
            result: Result object to update
        """
        step.status = WorkflowStatus.RUNNING
        step.started_at = datetime.now()
        
        try:
            # Get step handler
            handler = self.custom_step_handlers.get(step.type.value)
            if not handler:
                raise WorkflowExecutionError(
                    result.workflow_id, step.id, f"No handler for step type: {step.type.value}"
                )
                
            # Execute step
            step_result = await handler(step, context)
            
            # Update step
            step.status = WorkflowStatus.COMPLETED
            step.result = step_result
            step.completed_at = datetime.now()
            
            # Update context
            context["results"][step.id] = step_result
            
            # Update result
            result.steps_results[step.id] = step_result
            
        except Exception as e:
            logger.exception(f"Error executing step {step.id}")
            
            # Update step
            step.status = WorkflowStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.now()
            
            # Update result
            result.steps_results[step.id] = {"error": str(e)}
            
            # Propagate error
            raise WorkflowExecutionError(
                result.workflow_id, step.id, cause=e
            ) from e

    async def _handle_code_execution(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle code execution step.

        Args:
            step: Step to execute
            context: Execution context

        Returns:
            Step result

        Raises:
            WorkflowExecutionError: If code execution fails
        """
        if not self.e2b_client:
            raise WorkflowExecutionError(
                None, step.id, "E2B client is required for code execution steps"
            )
            
        # Get code and language from step config
        code = step.config.get("code")
        language = step.config.get("language", "python")
        
        if not code:
            raise WorkflowExecutionError(
                None, step.id, "Code is required for code execution step"
            )
            
        # Execute code
        try:
            result = await self.e2b_client.execute_code(code, language)
            return result
        except Exception as e:
            raise WorkflowExecutionError(
                None, step.id, f"Code execution failed: {str(e)}"
            ) from e

    def _save_workflow(self, workflow: Workflow) -> None:
        """Save workflow to storage.

        Args:
            workflow: Workflow to save
        """
        if not self.storage_path:
            return
            
        try:
            import os
            import json
            
            os.makedirs(self.storage_path, exist_ok=True)
            
            file_path = os.path.join(self.storage_path, f"{workflow.id}.json")
            with open(file_path, "w") as f:
                json.dump(workflow.to_dict(), f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving workflow {workflow.id}: {str(e)}")

    def _load_workflow(self, workflow_id: str) -> None:
        """Load workflow from storage.

        Args:
            workflow_id: ID of the workflow to load

        Raises:
            WorkflowNotFoundError: If workflow file not found
        """
        if not self.storage_path:
            raise WorkflowNotFoundError(workflow_id)
            
        try:
            import os
            import json
            
            file_path = os.path.join(self.storage_path, f"{workflow_id}.json")
            if not os.path.exists(file_path):
                raise WorkflowNotFoundError(workflow_id)
                
            with open(file_path, "r") as f:
                workflow_data = json.load(f)
                
            workflow = Workflow.from_dict(workflow_data)
            self.workflows[workflow_id] = workflow
            
        except Exception as e:
            logger.error(f"Error loading workflow {workflow_id}: {str(e)}")
            raise WorkflowNotFoundError(workflow_id) from e

    def _delete_workflow_file(self, workflow_id: str) -> None:
        """Delete workflow file from storage.

        Args:
            workflow_id: ID of the workflow to delete
        """
        if not self.storage_path:
            return
            
        try:
            import os
            
            file_path = os.path.join(self.storage_path, f"{workflow_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                
        except Exception as e:
            logger.error(f"Error deleting workflow file {workflow_id}: {str(e)}")

    def get_workflow_result(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Get workflow result.

        Args:
            workflow_id: ID of the workflow

        Returns:
            Workflow result or None if not found
        """
        return self.results.get(workflow_id) 