"""
Django example for workflow functionality.
"""

import json
import os
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..auth.client import AgentAuthClient
from ..discussion.manager import DiscussionManager
from ..django.middleware import AuthenticationMiddleware
from ..e2b_interpreter.client import E2BClient
from ..workflows.manager import WorkflowManager
from ..workflows.models import Workflow, WorkflowResult, WorkflowStep, StepType


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


# Helper functions
def get_json_body(request: HttpRequest) -> Dict[str, Any]:
    """Get JSON body from request.

    Args:
        request: HTTP request

    Returns:
        JSON body
    """
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


def get_current_user(request: HttpRequest) -> Dict[str, Any]:
    """Get current user from request.

    Args:
        request: HTTP request

    Returns:
        User data

    Raises:
        JsonResponse: If user is not authenticated
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return JsonResponse(
            {"error": "Authentication required"},
            status=401,
        )
    return user


# Views
@csrf_exempt
def root(request: HttpRequest) -> JsonResponse:
    """Root endpoint.

    Args:
        request: HTTP request

    Returns:
        JSON response
    """
    return JsonResponse({"message": "Welcome to the Composio Workflow API"})


@csrf_exempt
@require_http_methods(["POST"])
async def create_workflow(request: HttpRequest) -> JsonResponse:
    """Create a new workflow.

    Args:
        request: HTTP request

    Returns:
        JSON response
    """
    user = get_current_user(request)
    data = get_json_body(request)
    
    name = data.get("name")
    description = data.get("description", "")
    steps = data.get("steps", [])
    
    if not name:
        return JsonResponse(
            {"error": "Name is required"},
            status=400,
        )
    
    try:
        workflow = workflow_manager.create_workflow(
            name=name,
            description=description,
            steps=steps,
            owner_id=getattr(user, "id", None),
        )
        return JsonResponse(workflow.to_dict())
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
async def list_workflows(request: HttpRequest) -> JsonResponse:
    """List all workflows.

    Args:
        request: HTTP request

    Returns:
        JSON response
    """
    user = get_current_user(request)
    
    try:
        workflows = list(workflow_manager.workflows.values())
        return JsonResponse([w.to_dict() for w in workflows], safe=False)
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
async def get_workflow(request: HttpRequest, workflow_id: str) -> JsonResponse:
    """Get a workflow by ID.

    Args:
        request: HTTP request
        workflow_id: Workflow ID

    Returns:
        JSON response
    """
    user = get_current_user(request)
    
    try:
        workflow = workflow_manager.get_workflow(workflow_id)
        return JsonResponse(workflow.to_dict())
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=404,
        )


@csrf_exempt
@require_http_methods(["PUT"])
async def update_workflow(request: HttpRequest, workflow_id: str) -> JsonResponse:
    """Update a workflow.

    Args:
        request: HTTP request
        workflow_id: Workflow ID

    Returns:
        JSON response
    """
    user = get_current_user(request)
    data = get_json_body(request)
    
    try:
        updated_workflow = workflow_manager.update_workflow(
            workflow_id, **data
        )
        return JsonResponse(updated_workflow.to_dict())
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=404,
        )


@csrf_exempt
@require_http_methods(["DELETE"])
async def delete_workflow(request: HttpRequest, workflow_id: str) -> JsonResponse:
    """Delete a workflow.

    Args:
        request: HTTP request
        workflow_id: Workflow ID

    Returns:
        JSON response
    """
    user = get_current_user(request)
    
    try:
        workflow_manager.delete_workflow(workflow_id)
        return JsonResponse({"message": f"Workflow {workflow_id} deleted"})
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=404,
        )


@csrf_exempt
@require_http_methods(["POST"])
async def execute_workflow(request: HttpRequest, workflow_id: str) -> JsonResponse:
    """Execute a workflow.

    Args:
        request: HTTP request
        workflow_id: Workflow ID

    Returns:
        JSON response
    """
    user = get_current_user(request)
    data = get_json_body(request)
    
    inputs = data.get("inputs", {})
    
    try:
        result = await workflow_manager.execute_workflow(
            workflow_id, inputs
        )
        return JsonResponse(result.to_dict())
    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
async def get_workflow_result(request: HttpRequest, workflow_id: str) -> JsonResponse:
    """Get the result of a workflow execution.

    Args:
        request: HTTP request
        workflow_id: Workflow ID

    Returns:
        JSON response
    """
    user = get_current_user(request)
    
    result = workflow_manager.get_workflow_result(workflow_id)
    if not result:
        return JsonResponse(
            {"error": f"No result found for workflow {workflow_id}"},
            status=404,
        )
    return JsonResponse(result.to_dict())


# URL patterns
urlpatterns = [
    path("", root, name="root"),
    path("workflows", create_workflow, name="create_workflow"),
    path("workflows", list_workflows, name="list_workflows"),
    path("workflows/<str:workflow_id>", get_workflow, name="get_workflow"),
    path("workflows/<str:workflow_id>", update_workflow, name="update_workflow"),
    path("workflows/<str:workflow_id>", delete_workflow, name="delete_workflow"),
    path("workflows/<str:workflow_id>/execute", execute_workflow, name="execute_workflow"),
    path("workflows/<str:workflow_id>/result", get_workflow_result, name="get_workflow_result"),
] 