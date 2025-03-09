"""
Tests for the workflow functionality.
"""

import os
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from ..workflows.manager import WorkflowManager
from ..workflows.models import Workflow, WorkflowResult, WorkflowStatus, WorkflowStep, StepType
from ..workflows.exceptions import WorkflowNotFoundError, WorkflowValidationError, WorkflowExecutionError


@pytest.fixture
def workflow_manager():
    """Create a workflow manager for testing."""
    discussion_manager = MagicMock()
    e2b_client = MagicMock()
    
    # Create a temporary directory for workflow storage
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = WorkflowManager(
            discussion_manager=discussion_manager,
            e2b_client=e2b_client,
            storage_path=temp_dir,
        )
        yield manager


@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "steps": [
            {
                "name": "Step 1",
                "description": "First step",
                "type": StepType.CUSTOM.value,
                "config": {"param": "value"},
            },
            {
                "name": "Step 2",
                "description": "Second step",
                "type": StepType.CUSTOM.value,
                "config": {"param": "value"},
                "depends_on": [],
            },
        ],
    }


def test_create_workflow(workflow_manager, sample_workflow):
    """Test creating a workflow."""
    workflow = workflow_manager.create_workflow(
        name=sample_workflow["name"],
        description=sample_workflow["description"],
        steps=sample_workflow["steps"],
    )
    
    assert workflow.id is not None
    assert workflow.name == sample_workflow["name"]
    assert workflow.description == sample_workflow["description"]
    assert len(workflow.steps) == 2
    assert workflow.steps[0].name == "Step 1"
    assert workflow.steps[1].name == "Step 2"
    assert workflow.status == WorkflowStatus.PENDING


def test_get_workflow(workflow_manager, sample_workflow):
    """Test getting a workflow."""
    workflow = workflow_manager.create_workflow(
        name=sample_workflow["name"],
        description=sample_workflow["description"],
        steps=sample_workflow["steps"],
    )
    
    retrieved_workflow = workflow_manager.get_workflow(workflow.id)
    
    assert retrieved_workflow.id == workflow.id
    assert retrieved_workflow.name == workflow.name
    assert retrieved_workflow.description == workflow.description
    assert len(retrieved_workflow.steps) == len(workflow.steps)


def test_get_workflow_not_found(workflow_manager):
    """Test getting a non-existent workflow."""
    with pytest.raises(WorkflowNotFoundError):
        workflow_manager.get_workflow("non-existent-id")


def test_update_workflow(workflow_manager, sample_workflow):
    """Test updating a workflow."""
    workflow = workflow_manager.create_workflow(
        name=sample_workflow["name"],
        description=sample_workflow["description"],
        steps=sample_workflow["steps"],
    )
    
    updated_workflow = workflow_manager.update_workflow(
        workflow.id,
        name="Updated Workflow",
        description="Updated description",
    )
    
    assert updated_workflow.id == workflow.id
    assert updated_workflow.name == "Updated Workflow"
    assert updated_workflow.description == "Updated description"
    assert len(updated_workflow.steps) == len(workflow.steps)


def test_delete_workflow(workflow_manager, sample_workflow):
    """Test deleting a workflow."""
    workflow = workflow_manager.create_workflow(
        name=sample_workflow["name"],
        description=sample_workflow["description"],
        steps=sample_workflow["steps"],
    )
    
    workflow_manager.delete_workflow(workflow.id)
    
    with pytest.raises(WorkflowNotFoundError):
        workflow_manager.get_workflow(workflow.id)


def test_validate_workflow(workflow_manager, sample_workflow):
    """Test validating a workflow."""
    workflow = workflow_manager.create_workflow(
        name=sample_workflow["name"],
        description=sample_workflow["description"],
        steps=sample_workflow["steps"],
    )
    
    errors = workflow_manager.validate_workflow(workflow)
    
    assert len(errors) == 0


def test_validate_workflow_with_errors(workflow_manager):
    """Test validating a workflow with errors."""
    # Create a workflow with a step that depends on a non-existent step
    workflow = workflow_manager.create_workflow(
        name="Invalid Workflow",
        description="A workflow with validation errors",
        steps=[
            {
                "name": "Step 1",
                "description": "First step",
                "type": StepType.CUSTOM.value,
                "config": {"param": "value"},
                "depends_on": ["non-existent-step"],
            },
        ],
    )
    
    errors = workflow_manager.validate_workflow(workflow)
    
    assert len(errors) > 0
    assert "depends on non-existent step" in errors[0]


@pytest.mark.asyncio
async def test_execute_workflow(workflow_manager, sample_workflow):
    """Test executing a workflow."""
    # Register a custom step handler
    async def custom_handler(step, context):
        return {"result": "success"}
    
    workflow_manager.register_step_handler(StepType.CUSTOM, custom_handler)
    
    # Create a workflow
    workflow = workflow_manager.create_workflow(
        name=sample_workflow["name"],
        description=sample_workflow["description"],
        steps=sample_workflow["steps"],
    )
    
    # Execute the workflow
    result = await workflow_manager.execute_workflow(workflow.id)
    
    assert result.workflow_id == workflow.id
    assert result.status == WorkflowStatus.COMPLETED
    assert len(result.steps_results) == 2
    assert result.steps_results[workflow.steps[0].id]["result"] == "success"
    assert result.steps_results[workflow.steps[1].id]["result"] == "success"


@pytest.mark.asyncio
async def test_execute_workflow_with_validation_error(workflow_manager):
    """Test executing a workflow with validation errors."""
    # Create a workflow with a step that depends on a non-existent step
    workflow = workflow_manager.create_workflow(
        name="Invalid Workflow",
        description="A workflow with validation errors",
        steps=[
            {
                "name": "Step 1",
                "description": "First step",
                "type": StepType.CUSTOM.value,
                "config": {"param": "value"},
                "depends_on": ["non-existent-step"],
            },
        ],
    )
    
    # Execute the workflow
    with pytest.raises(WorkflowValidationError):
        await workflow_manager.execute_workflow(workflow.id)


@pytest.mark.asyncio
async def test_execute_workflow_with_execution_error(workflow_manager, sample_workflow):
    """Test executing a workflow with execution errors."""
    # Register a custom step handler that raises an exception
    async def custom_handler(step, context):
        raise Exception("Test error")
    
    workflow_manager.register_step_handler(StepType.CUSTOM, custom_handler)
    
    # Create a workflow
    workflow = workflow_manager.create_workflow(
        name=sample_workflow["name"],
        description=sample_workflow["description"],
        steps=sample_workflow["steps"],
    )
    
    # Execute the workflow
    with pytest.raises(WorkflowExecutionError):
        await workflow_manager.execute_workflow(workflow.id)


@pytest.mark.asyncio
async def test_code_execution_step(workflow_manager):
    """Test executing a code execution step."""
    # Mock the E2B client
    e2b_client = MagicMock()
    e2b_client.execute_code = AsyncMock(return_value={"result": "success"})
    workflow_manager.e2b_client = e2b_client
    
    # Create a workflow with a code execution step
    workflow = workflow_manager.create_workflow(
        name="Code Execution Workflow",
        description="A workflow with a code execution step",
        steps=[
            {
                "name": "Code Step",
                "description": "Execute code",
                "type": StepType.CODE_EXECUTION.value,
                "config": {
                    "code": "print('Hello, world!')",
                    "language": "python",
                },
            },
        ],
    )
    
    # Execute the workflow
    result = await workflow_manager.execute_workflow(workflow.id)
    
    # Check that the E2B client was called
    e2b_client.execute_code.assert_called_once_with(
        "print('Hello, world!')", "python"
    )
    
    # Check the result
    assert result.workflow_id == workflow.id
    assert result.status == WorkflowStatus.COMPLETED
    assert len(result.steps_results) == 1
    assert result.steps_results[workflow.steps[0].id]["result"] == "success"


def test_workflow_result_to_dict():
    """Test converting a workflow result to a dictionary."""
    result = WorkflowResult(
        workflow_id="test-id",
        status=WorkflowStatus.COMPLETED,
        steps_results={"step-1": {"result": "success"}},
    )
    
    result_dict = result.to_dict()
    
    assert result_dict["workflow_id"] == "test-id"
    assert result_dict["status"] == "completed"
    assert result_dict["steps_results"]["step-1"]["result"] == "success"


def test_workflow_step_to_dict():
    """Test converting a workflow step to a dictionary."""
    step = WorkflowStep(
        name="Test Step",
        description="A test step",
        type=StepType.CUSTOM,
        config={"param": "value"},
    )
    
    step_dict = step.to_dict()
    
    assert step_dict["name"] == "Test Step"
    assert step_dict["description"] == "A test step"
    assert step_dict["type"] == "custom"
    assert step_dict["config"]["param"] == "value" 