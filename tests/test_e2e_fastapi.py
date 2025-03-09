from fastapi.testclient import TestClient
from app import app  # Import your FastAPI app

client = TestClient(app)

def test_auth_flow():
    """Test the authentication flow."""
    # Register a new user
    register_response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "password": "Test@123",
            "email": "test@example.com",
            "role": "client"
        }
    )
    assert register_response.status_code == 200
    assert "user_id" in register_response.json()
    
    # Login with the registered user
    login_response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "Test@123"
        }
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    
    # Store the token for other tests
    token = login_response.json()["access_token"]
    return token

def test_code_execution():
    """Test code execution with E2B."""
    # First get a token
    token = test_auth_flow()
    
    # Execute a simple Python code
    headers = {"Authorization": f"Bearer {token}"}
    code_response = client.post(
        "/e2b/execute",
        headers=headers,
        json={
            "code": "print('Hello, world!')\nresult = {'message': 'Hello, world!', 'value': 42}",
            "language": "python"
        }
    )
    
    assert code_response.status_code == 200
    result = code_response.json()
    assert result["success"] is True
    assert "outputs" in result
    assert "result" in result
    
    # Check if the result contains the expected values
    assert "json" in result["result"]
    assert result["result"]["json"]["message"] == "Hello, world!"
    assert result["result"]["json"]["value"] == 42

def test_workflow_execution():
    """Test workflow execution."""
    # First get a token
    token = test_auth_flow()
    
    # Execute a workflow
    headers = {"Authorization": f"Bearer {token}"}
    workflow_response = client.post(
        "/workflows/execute",
        headers=headers,
        json={
            "workflow_id": "example",
            "parameters": {
                "param1": "value1",
                "param2": "value2"
            }
        }
    )
    
    assert workflow_response.status_code == 200
    result = workflow_response.json()
    assert "workflow_id" in result
    assert result["status"] == "completed"
    assert "result" in result
