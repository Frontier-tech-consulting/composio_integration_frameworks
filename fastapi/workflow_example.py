"""
FastAPI example for workflow functionality.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..auth.client import AgentAuthClient
from ..discussion.manager import DiscussionManager
from ..e2b_interpreter.client import E2BClient
from ..fastapi.middleware import AuthenticationMiddleware
from ..fastapi.security import AgentAuthSecurity
from ..workflows.manager import WorkflowManager
from ..workflows.models import Workflow, WorkflowResult, WorkflowStep, StepType


# Initialize FastAPI app
app = FastAPI(
    title="Composio Workflow API",
    description="API for managing and executing workflows with Composio",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients and managers
auth_client = AgentAuthClient(
    api_key=os.environ.get("COMPOSIO_API_KEY"),
    api_url=os.environ.get("COMPOSIO_API_URL"),
)

discussion_manager = DiscussionManager(auth_client=auth_client)

e2b_client = E2BClient(
    api_key=os.environ.get("E2B_API_KEY"),
)

workflow_manager = WorkflowManager(
    discussion_manager=discussion_manager,
    e2b_client=e2b_client,
    storage_path=os.environ.get("WORKFLOW_STORAGE_PATH", "./workflows"),
)

# Initialize security
security = AgentAuthSecurity(auth_client=auth_client)

# Add authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    auth_client=auth_client,
    exclude_paths=["/docs", "/redoc", "/openapi.json"],
)


# Models
class WorkflowStepCreate(BaseModel):
    """Model for creating a workflow step."""
    name: str
    description: Optional[str] = None
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    timeout_seconds: Optional[int] = None
    retry_count: Optional[int] = None
    retry_delay_seconds: Optional[int] = None


class WorkflowCreate(BaseModel):
    """Model for creating a workflow."""
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStepCreate] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    """Model for updating a workflow."""
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[WorkflowStepCreate]] = None


class WorkflowExecute(BaseModel):
    """Model for executing a workflow."""
    inputs: Dict[str, Any] = Field(default_factory=dict)


# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Composio Workflow API"}


@app.post("/workflows", response_model=Dict[str, Any])
async def create_workflow(
    workflow: WorkflowCreate,
    user: Dict[str, Any] = Depends(security.get_current_user),
):
    """Create a new workflow."""
    steps = []
    for step_data in workflow.steps:
        step_dict = step_data.dict()
        steps.append(step_dict)
    
    created_workflow = workflow_manager.create_workflow(
        name=workflow.name,
        description=workflow.description or "",
        steps=steps,
        owner_id=user.get("id"),
    )
    
    return created_workflow.to_dict()


@app.get("/workflows", response_model=List[Dict[str, Any]])
async def list_workflows(
    user: Dict[str, Any] = Depends(security.get_current_user),
):
    """List all workflows."""
    workflows = list(workflow_manager.workflows.values())
    return [w.to_dict() for w in workflows]


@app.get("/workflows/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow(
    workflow_id: str,
    user: Dict[str, Any] = Depends(security.get_current_user),
):
    """Get a workflow by ID."""
    try:
        workflow = workflow_manager.get_workflow(workflow_id)
        return workflow.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/workflows/{workflow_id}", response_model=Dict[str, Any])
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    user: Dict[str, Any] = Depends(security.get_current_user),
):
    """Update a workflow."""
    try:
        update_data = workflow_update.dict(exclude_unset=True)
        
        if "steps" in update_data:
            steps = []
            for step_data in update_data["steps"]:
                steps.append(step_data)
            update_data["steps"] = steps
        
        updated_workflow = workflow_manager.update_workflow(
            workflow_id, **update_data
        )
        return updated_workflow.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    user: Dict[str, Any] = Depends(security.get_current_user),
):
    """Delete a workflow."""
    try:
        workflow_manager.delete_workflow(workflow_id)
        return {"message": f"Workflow {workflow_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/workflows/{workflow_id}/execute", response_model=Dict[str, Any])
async def execute_workflow(
    workflow_id: str,
    execution: WorkflowExecute,
    user: Dict[str, Any] = Depends(security.get_current_user),
):
    """Execute a workflow."""
    try:
        result = await workflow_manager.execute_workflow(
            workflow_id, execution.inputs
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{workflow_id}/result", response_model=Dict[str, Any])
async def get_workflow_result(
    workflow_id: str,
    user: Dict[str, Any] = Depends(security.get_current_user),
):
    """Get the result of a workflow execution."""
    result = workflow_manager.get_workflow_result(workflow_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No result found for workflow {workflow_id}",
        )
    return result.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 