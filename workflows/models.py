"""
Data models for the workflows module.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class WorkflowStatus(str, Enum):
    """Status of a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Type of workflow step."""
    CODE_EXECUTION = "code_execution"
    API_CALL = "api_call"
    FUNCTION_CALL = "function_call"
    CUSTOM = "custom"


@dataclass
class WorkflowStep:
    """A step in a workflow."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    type: StepType = StepType.CUSTOM
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_delay_seconds: int = 5
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "config": self.config,
            "depends_on": self.depends_on,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create from dictionary."""
        step_data = data.copy()
        if "type" in step_data and isinstance(step_data["type"], str):
            step_data["type"] = StepType(step_data["type"])
        if "status" in step_data and isinstance(step_data["status"], str):
            step_data["status"] = WorkflowStatus(step_data["status"])
        if "started_at" in step_data and step_data["started_at"] and isinstance(step_data["started_at"], str):
            step_data["started_at"] = datetime.fromisoformat(step_data["started_at"])
        if "completed_at" in step_data and step_data["completed_at"] and isinstance(step_data["completed_at"], str):
            step_data["completed_at"] = datetime.fromisoformat(step_data["completed_at"])
        return cls(**step_data)


@dataclass
class Workflow:
    """A workflow definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: WorkflowStatus = WorkflowStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    owner_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "metadata": self.metadata,
            "owner_id": self.owner_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """Create from dictionary."""
        workflow_data = data.copy()
        if "steps" in workflow_data:
            workflow_data["steps"] = [
                WorkflowStep.from_dict(step) if isinstance(step, dict) else step
                for step in workflow_data["steps"]
            ]
        if "status" in workflow_data and isinstance(workflow_data["status"], str):
            workflow_data["status"] = WorkflowStatus(workflow_data["status"])
        if "created_at" in workflow_data and isinstance(workflow_data["created_at"], str):
            workflow_data["created_at"] = datetime.fromisoformat(workflow_data["created_at"])
        if "updated_at" in workflow_data and isinstance(workflow_data["updated_at"], str):
            workflow_data["updated_at"] = datetime.fromisoformat(workflow_data["updated_at"])
        return cls(**workflow_data)


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    workflow_id: str
    status: WorkflowStatus
    steps_results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "steps_results": self.steps_results,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowResult':
        """Create from dictionary."""
        result_data = data.copy()
        if "status" in result_data and isinstance(result_data["status"], str):
            result_data["status"] = WorkflowStatus(result_data["status"])
        if "started_at" in result_data and isinstance(result_data["started_at"], str):
            result_data["started_at"] = datetime.fromisoformat(result_data["started_at"])
        if "completed_at" in result_data and result_data["completed_at"] and isinstance(result_data["completed_at"], str):
            result_data["completed_at"] = datetime.fromisoformat(result_data["completed_at"])
        return cls(**result_data) 