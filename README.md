# Composio Agent Integration

A comprehensive Python package for integrating Composio's AgentAuth architecture with FastAPI and Django web frameworks, along with vector database support for efficient discussion management in AI agent applications.

## Key Features

- **AgentAuth Integration**: Seamlessly integrate with Composio's AgentAuth for secure user authentication
- **Framework Support**: Dedicated modules for both FastAPI and Django
- **Discussion Management**: Store and retrieve user-agent discussions using vector databases (Pinecone, Chroma)
- **Role-Based Access Control**: Built-in support for user roles (client, admin) to control access
- **Agent Framework Support**: Integrations with LangChain and CrewAI
- **Comprehensive Exception Handling**: Detailed exception hierarchy for robust error handling

## Installation

```bash
# Basic installation
pip install composio_agent_integration

# With FastAPI support
pip install composio_agent_integration[fastapi]

# With Django support
pip install composio_agent_integration[django]

# With vector database support
pip install composio_agent_integration[pinecone]  # or [chroma]

# With agent framework support
pip install composio_agent_integration[langchain]  # or [crewai]

# Complete installation with all optional dependencies
pip install composio_agent_integration[all]
```

## Environment Setup

The package requires several environment variables to be set based on your configuration:

```bash
# AgentAuth configuration
export AGENTAUTH_BASE_URL="https://staging-backend.composio.dev/api/v1/"
export AGENTAUTH_API_KEY="your-api-key"

# Vector database configuration (if using Pinecone)
export PINECONE_API_KEY="your-pinecone-api-key"
export PINECONE_ENVIRONMENT="your-pinecone-environment"
export PINECONE_INDEX="composio-discussions"
```

## Usage Examples

### Basic Authentication

```python
from composio_agent_integration.auth.client import register_user, login_user, get_user_info
from composio_agent_integration.auth.exceptions import UserExistsError, InvalidCredentialsError

try:
    # Register a new user
    user_data = register_user(
        username="john_doe",
        password="secure_password",
        email="john@example.com",
        role="client"
    )
    
    # Login to get a token
    token = login_user("john_doe", "secure_password")
    
    # Get user information
    user_info = get_user_info(token)
    print(f"Logged in as: {user_info['username']} (Role: {user_info['role']})")
    
except UserExistsError:
    print("A user with this username or email already exists")
except InvalidCredentialsError:
    print("Invalid username or password")
except Exception as e:
    print(f"An error occurred: {e}")
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, HTTPException
from composio_agent_integration.fastapi.security import AgentAuthSecurity
from composio_agent_integration.discussion.manager import DiscussionManager
from composio_agent_integration.discussion.exceptions import QueryVectorError

app = FastAPI()
auth_security = AgentAuthSecurity()
discussion_mgr = DiscussionManager(vector_db_type="pinecone")

@app.post("/chat")
async def chat(message: str, query: str = "", user=Depends(auth_security)):
    try:
        # Store the user's message
        discussion_mgr.add_discussion(user["user_id"], message)
        
        # Get relevant past discussions
        relevant_discussions = discussion_mgr.get_relevant_discussions(
            user["user_id"], query, top_k=5
        )
        
        return {
            "status": "success",
            "message": "Message stored",
            "relevant_discussions": relevant_discussions
        }
    except QueryVectorError as e:
        return {"status": "error", "message": f"Failed to retrieve discussions: {e}"}
```

### Django Integration

```python
# In views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from composio_agent_integration.django.discussion import add_discussion, get_relevant_discussions
from composio_agent_integration.auth.exceptions import AuthAdminRequiredError
from composio_agent_integration.discussion.exceptions import DiscussionPermissionError

@login_required
@require_POST
def chat_view(request):
    try:
        message = request.POST.get("message", "")
        query = request.POST.get("query", "")
        
        # Store the user's message
        add_discussion(request, message)
        
        # Get relevant past discussions
        relevant_discussions = get_relevant_discussions(request, query, top_k=5)
        
        return JsonResponse({
            "status": "success",
            "message": "Message stored",
            "relevant_discussions": relevant_discussions
        })
    except DiscussionPermissionError:
        return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
```

For admin users, you can access discussions across all users:

```python
try:
    # Only works for admin users
    all_discussions = get_all_relevant_discussions(request, query, top_k=10)
except AuthAdminRequiredError:
    # Handle the case when a non-admin tries to access admin features
    return JsonResponse({"status": "error", "message": "Admin privileges required"}, status=403)
```

### LangChain Integration

```python
from langchain.agents import initialize_agent
from langchain.llms import OpenAI
from composio_agent_integration.frameworks.langchain.memory import VectorDBMemory

# Initialize LangChain with vector database memory
memory = VectorDBMemory(user_id="user123", vector_db_type="pinecone")

# Create an agent with the memory
llm = OpenAI(temperature=0)
agent = initialize_agent(
    tools=[],
    llm=llm,
    memory=memory,
    verbose=True
)

# The agent will now use the vector database for conversation history
agent.run("Hello, can you help me with something?")
```

## Exception Handling

The package provides a comprehensive exception hierarchy for robust error handling:

### Authentication Exceptions

```python
from composio_agent_integration.auth.exceptions import (
    AuthException,                # Base exception for all auth errors
    ConfigurationError,           # Configuration issues
    NetworkError,                 # Network connectivity problems
    APIError,                     # General API errors
    
    # Client error categories
    ClientError,                  # 4xx client errors
    RegistrationError,            # Registration issues
    UserExistsError,              # User already exists
    InvalidRegistrationDataError, # Invalid registration data
    
    # Authentication error categories
    AuthenticationError,          # Auth failures
    InvalidCredentialsError,      # Wrong username/password
    TokenError,                   # Token issues
    TokenExpiredError,            # Expired token
    TokenInvalidError,            # Invalid token
    
    # Permission errors
    PermissionError,              # Permission denied
    RoleRequiredError,            # Specific role required
    AdminRequiredError            # Admin role required
)

# Example usage:
try:
    token = login_user("username", "password")
except InvalidCredentialsError:
    print("Wrong username or password")
except TokenExpiredError:
    print("Your session has expired, please login again")
except NetworkError:
    print("Network connectivity issue, please check your connection")
```

### Discussion Management Exceptions

```python
from composio_agent_integration.discussion.exceptions import (
    DiscussionException,         # Base exception for all discussion errors
    ConfigurationError,          # Configuration issues
    
    # Vector database errors
    VectorDBError,               # Base for all vector DB errors
    DatabaseConnectionError,     # Connection issues
    DatabaseOperationError,      # Operation failures
    StoreVectorError,            # Failed to store vector
    QueryVectorError,            # Failed to query vectors
    DeleteVectorError,           # Failed to delete vector
    
    # Embedding model errors
    EmbeddingModelError,         # Base for all embedding errors
    EmbeddingModelLoadError,     # Failed to load model
    TextEmbeddingError,          # Failed to convert text to vector
    
    # Permission and access errors
    PermissionError,             # Permission denied
    DiscussionNotFoundError,     # Discussion not found
    UserDiscussionAccessError,   # User can't access another's discussions
    AdminRequiredError           # Admin role required
)

# Example usage:
try:
    discussions = discussion_manager.get_relevant_discussions(user_id, query)
except TextEmbeddingError:
    print("Failed to process your query text")
except DatabaseConnectionError:
    print("Vector database is currently unavailable")
except UserDiscussionAccessError:
    print("You don't have permission to access these discussions")
```

## Vector Database Configuration

### Pinecone

```python
from composio_agent_integration.discussion.manager import DiscussionManager
from composio_agent_integration.discussion.exceptions import ConfigurationError

try:
    # Configure with API key directly
    discussion_mgr = DiscussionManager(
        vector_db_type="pinecone",
        config={
            "api_key": "your-pinecone-api-key",
            "environment": "your-pinecone-environment",
            "index_name": "composio-discussions",
            "dimension": 16,
            "namespace": "my-app-discussions"
        }
    )
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

### Chroma

```python
from composio_agent_integration.discussion.manager import DiscussionManager

# Configure with path to persist directory
discussion_mgr = DiscussionManager(
    vector_db_type="chroma",
    config={
        "persist_directory": "./chroma_db",
        "collection_name": "agent_discussions"
    }
)
```

## Role-Based Access Control

The package provides built-in support for role-based access control. By default, it supports two roles:

- **client**: Regular users who can only access their own discussions
- **admin**: Admin users who can access discussions for all users

In Django, you can link the AgentAuth user with the Django user model:

```python
from django.contrib.auth.models import User
from composio_agent_integration.django.discussion import link_user_with_agentauth
from composio_agent_integration.auth.exceptions import TokenInvalidError

try:
    # After authenticating with AgentAuth
    user = User.objects.get(username="john_doe")
    link_user_with_agentauth(user, token)
except TokenInvalidError:
    print("Your token is invalid or has expired")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Composio](https://composio.dev/) for their AgentAuth framework
- [FastAPI](https://fastapi.tiangolo.com/) and [Django](https://www.djangoproject.com/) for their web frameworks
- [Pinecone](https://www.pinecone.io/) and [Chroma](https://www.trychroma.com/) for vector database technologies
- [LangChain](https://langchain.readthedocs.io/) and [CrewAI](https://github.com/crewai/crewai) for agent frameworks

## E2B Code Interpreter Integration

The package includes a seamless integration with E2B Code Interpreter to execute code in secure sandboxes as part of your agent workflows.

### Installation

To use the E2B Code Interpreter functionality, install the package with the e2b extra:

```bash
# With E2B Code Interpreter support
pip install composio_agent_integration[e2b]

# For full installation including E2B Code Interpreter
pip install composio_agent_integration[all]
```

### Environment Setup

Set the following environment variables for E2B Code Interpreter:

```bash
# E2B API key
export E2B_API_KEY="your-e2b-api-key"

# Optional: Custom execution timeout
export E2B_EXECUTION_TIMEOUT="300"  # in seconds
```

### Basic Usage

```python
from composio_agent_integration.e2b_interpreter import CodeInterpreterClient, SandboxError
from composio_agent_integration.discussion.manager import DiscussionManager

# Initialize a vector database for storing results
discussion_manager = DiscussionManager(vector_db_type="chroma")

# Create a code interpreter client
interpreter = CodeInterpreterClient(
    api_key="your-e2b-api-key",  # Optional, falls back to env variable
    discussion_manager=discussion_manager,  # Optional, for storing results
    timeout=300.0  # Default timeout in seconds
)

try:
    # Execute Python code
    result = interpreter.execute_code(
        code="import numpy as np\nx = np.array([1, 2, 3])\nprint(x.mean())\nresult = {'mean': float(x.mean())}",
        user_id="user123",
        language="python",
        store_result=True  # Store in vector database
    )
    
    # Access execution results
    print(f"Execution successful: {result['success']}")
    print(f"Outputs: {result['outputs']}")
    print(f"Result data: {result['result']}")
    
except SandboxError as e:
    print(f"Sandbox error: {e}")
```

### Async Usage

```python
import asyncio
from composio_agent_integration.e2b_interpreter import AsyncCodeInterpreterClient

async def main():
    # Create an async interpreter client
    interpreter = await AsyncCodeInterpreterClient.create(
        api_key="your-e2b-api-key",
        timeout=300.0
    )
    
    try:
        # Execute JavaScript code
        result = await interpreter.execute_code(
            code="const data = [1, 2, 3, 4, 5];\nconst sum = data.reduce((a, b) => a + b, 0);\nconsole.log(`Sum: ${sum}`);\nresult = { sum };",
            user_id="user123",
            language="javascript"
        )
        
        print(f"JavaScript result: {result['result']}")
        
    finally:
        # Clean up resources
        await interpreter.close()

# Run the async example
asyncio.run(main())
```

### FastAPI Integration

Integrate code execution into your FastAPI application:

```python
import os
from fastapi import FastAPI, Depends
from composio_agent_integration.fastapi.security import AgentAuthSecurity
from composio_agent_integration.discussion.manager import DiscussionManager
from composio_agent_integration.fastapi.e2b_integration import create_e2b_router

app = FastAPI()

# Set up auth security
auth_security = AgentAuthSecurity(
    exclude_paths=["/docs", "/openapi.json", "/auth/register", "/auth/login"]
)

# Set up discussion manager for storing results
discussion_manager = DiscussionManager(vector_db_type="chroma")

# Create and include the E2B router
e2b_router = create_e2b_router(
    discussion_manager=discussion_manager,
    e2b_api_key=os.environ.get("E2B_API_KEY"),
    auth_security=auth_security
)
app.include_router(e2b_router)
```

This provides the following endpoints:

- `POST /e2b/execute`: Execute code synchronously
- `POST /e2b/schedule`: Schedule code execution in the background
- `GET /e2b/executions`: Retrieve execution results for the current user
- `GET /e2b/admin/executions`: Admin-only endpoint to retrieve results for all users

Example FastAPI request:

```bash
# Execute code
curl -X POST "http://localhost:8000/e2b/execute" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
         "code": "import numpy as np\nx = np.linspace(0, 10, 100)\ny = np.sin(x)\nprint(f\"Min: {y.min()}, Max: {y.max()}\")\nresult = {\"min\": float(y.min()), \"max\": float(y.max())}",
         "language": "python"
     }'
```

### Django Integration

For Django applications, integrate with a custom view:

```python
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json

from composio_agent_integration.e2b_interpreter import CodeInterpreterClient, CodeInterpreterException
from composio_agent_integration.discussion.manager import DiscussionManager

# Create a discussion manager for storing results
discussion_manager = DiscussionManager(vector_db_type="chroma")

# Create a code interpreter client
interpreter = CodeInterpreterClient(
    discussion_manager=discussion_manager
)

@login_required
@require_POST
def execute_code_view(request):
    try:
        # Parse the request body
        data = json.loads(request.body)
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        # Get user ID from Django's user model
        user_id = request.user.id
        
        # Execute the code
        result = interpreter.execute_code(
            code=code,
            user_id=user_id,
            language=language,
            store_result=True
        )
        
        return JsonResponse(result)
        
    except CodeInterpreterException as e:
        # Handle specific interpreter errors
        return JsonResponse({
            'error': str(e),
            'error_type': type(e).__name__
        }, status=400)
        
    except Exception as e:
        # Handle other errors
        return JsonResponse({
            'error': str(e),
            'error_type': 'ServerError'
        }, status=500)
```

In your Django URLs:

```python
from django.urls import path
from .views import execute_code_view

urlpatterns = [
    path('api/execute-code/', execute_code_view, name='execute_code'),
]
```

### Testing the Integration

To test the E2B Code Interpreter integration, follow these steps:

#### FastAPI Testing

1. Install required dependencies:
   ```bash
   pip install composio_agent_integration[all]
   ```

2. Set environment variables:
   ```bash
   export E2B_API_KEY="your-e2b-api-key"
   export AGENTAUTH_BASE_URL="https://api.composio.dev/agentauth/"
   export AGENTAUTH_API_KEY="your-api-key"
   ```

3. Run the example FastAPI app:
   ```bash
   uvicorn composio_agent_integration.fastapi.e2b_example:app --reload
   ```

4. Register a test user:
   ```bash
   curl -X POST "http://localhost:8000/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"username": "testuser", "password": "password123", "email": "test@example.com"}'
   ```

5. Login to obtain a token:
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "testuser", "password": "password123"}'
   ```

6. Execute code:
   ```bash
   curl -X POST "http://localhost:8000/e2b/execute" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -d '{
            "code": "print(\"Hello, world!\")\nresult = 42",
            "language": "python"
        }'
   ```

7. Retrieve execution results:
   ```bash
   curl -X GET "http://localhost:8000/e2b/executions?query=python&limit=5" \
        -H "Authorization: Bearer YOUR_TOKEN"
   ```

#### Django Testing

1. Configure Django settings:
   ```python
   # In settings.py
   INSTALLED_APPS = [
       # ... existing apps
       'composio_agent_integration.django',
   ]
   
   # E2B Configuration
   E2B_API_KEY = "your-e2b-api-key"
   E2B_EXECUTION_TIMEOUT = 300  # in seconds
   ```

2. Run tests:
   ```bash
   # Install test dependencies
   pip install pytest pytest-django
   
   # Create a test file (test_e2b.py)
   """
   from composio_agent_integration.e2b_interpreter import CodeInterpreterClient
   
   def test_code_execution():
       interpreter = CodeInterpreterClient()
       result = interpreter.execute_code(
           code="print('Hello, test!')\nresult = {'success': True}",
           user_id=1,
           language="python"
       )
       assert result['success'] == True
       assert any('Hello, test!' in output.get('line', '') 
                 for output in result['outputs'] if output.get('type') == 'stdout')
   """
   
   # Run the test
   pytest test_e2b.py -v
   ```

### E2B Code Interpreter Exceptions

The package provides a comprehensive exception hierarchy for E2B Code Interpreter:

```python
from composio_agent_integration.e2b_interpreter.exceptions import (
    CodeInterpreterException,    # Base exception for all interpreter errors
    InterpreterConfigError,      # Configuration issues
    SandboxError,                # Sandbox creation or management errors
    ExecutionError,              # Code execution errors
    TimeoutError                 # Execution timeout errors
)

# Example usage:
try:
    result = interpreter.execute_code(code, user_id)
except InterpreterConfigError:
    print("E2B configuration error - check your API key")
except SandboxError as e:
    print(f"Sandbox error: {e}")
except ExecutionError as e:
    print(f"Code execution failed: {e.error_name} - {e.error_value}")
    print(f"Traceback: {e.traceback}")
except TimeoutError as e:
    print(f"Execution timed out after {e.timeout_seconds} seconds")
```

## Comprehensive Exception Handling

## Workflow Management

The Composio Agent Integration package includes a powerful workflow management system that allows you to create, execute, and manage workflows with code execution capabilities. Workflows are composed of steps that can be executed in sequence or in parallel, with dependencies between steps.

### Features

- Create and manage workflows with multiple steps
- Execute code in secure sandboxes using E2B
- Define dependencies between steps
- Execute steps in parallel when possible
- Store and retrieve workflow results
- Integrate with FastAPI and Django applications

### Installation

To use the workflow functionality, install the package with the E2B extras:

```bash
pip install composio-agent-integration[e2b]
```

### Usage with FastAPI

```python
from fastapi import FastAPI, Depends
from composio_agent_integration.auth.client import AgentAuthClient
from composio_agent_integration.discussion.manager import DiscussionManager
from composio_agent_integration.e2b_interpreter.client import E2BClient
from composio_agent_integration.workflows.manager import WorkflowManager
from composio_agent_integration.fastapi.security import AgentAuthSecurity

# Initialize clients and managers
auth_client = AgentAuthClient(api_key="your-api-key")
discussion_manager = DiscussionManager(auth_client=auth_client)
e2b_client = E2BClient(api_key="your-e2b-api-key")
workflow_manager = WorkflowManager(
    discussion_manager=discussion_manager,
    e2b_client=e2b_client,
    storage_path="./workflows",
)

# Initialize FastAPI app
app = FastAPI()
security = AgentAuthSecurity(auth_client=auth_client)

# Create a workflow
@app.post("/workflows")
async def create_workflow(
    name: str,
    description: str = "",
    user = Depends(security.get_current_user),
):
    workflow = workflow_manager.create_workflow(
        name=name,
        description=description,
        owner_id=user.get("id"),
    )
    return workflow.to_dict()

# Execute a workflow
@app.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    inputs: dict = {},
    user = Depends(security.get_current_user),
):
    result = await workflow_manager.execute_workflow(
        workflow_id, inputs
    )
    return result.to_dict()
```

### Usage with Django

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from composio_agent_integration.auth.client import AgentAuthClient
from composio_agent_integration.discussion.manager import DiscussionManager
from composio_agent_integration.e2b_interpreter.client import E2BClient
from composio_agent_integration.workflows.manager import WorkflowManager

# Initialize clients and managers
auth_client = AgentAuthClient(api_key="your-api-key")
discussion_manager = DiscussionManager(auth_client=auth_client)
e2b_client = E2BClient(api_key="your-e2b-api-key")
workflow_manager = WorkflowManager(
    discussion_manager=discussion_manager,
    e2b_client=e2b_client,
    storage_path="./workflows",
)

# Create a workflow
@csrf_exempt
def create_workflow(request):
    user = request.user
    data = json.loads(request.body)
    
    workflow = workflow_manager.create_workflow(
        name=data.get("name"),
        description=data.get("description", ""),
        owner_id=user.id,
    )
    return JsonResponse(workflow.to_dict())

# Execute a workflow
@csrf_exempt
async def execute_workflow(request, workflow_id):
    user = request.user
    data = json.loads(request.body)
    
    result = await workflow_manager.execute_workflow(
        workflow_id, data.get("inputs", {})
    )
    return JsonResponse(result.to_dict())
```

### Creating a Workflow with Steps

```python
from composio_agent_integration.workflows.models import StepType

# Create a workflow with steps
workflow = workflow_manager.create_workflow(
    name="Data Analysis Workflow",
    description="Analyze data with Python",
    steps=[
        {
            "name": "Load Data",
            "description": "Load data from CSV",
            "type": StepType.CODE_EXECUTION.value,
            "config": {
                "code": """
                import pandas as pd
                
                # Load data
                data = pd.read_csv('https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv')
                
                # Return first 5 rows
                data.head()
                """,
                "language": "python",
            },
        },
        {
            "name": "Analyze Data",
            "description": "Perform data analysis",
            "type": StepType.CODE_EXECUTION.value,
            "config": {
                "code": """
                import pandas as pd
                import matplotlib.pyplot as plt
                
                # Load data
                data = pd.read_csv('https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv')
                
                # Analyze survival by gender
                survival_by_gender = data.groupby('Sex')['Survived'].mean()
                
                # Create a bar chart
                plt.figure(figsize=(8, 6))
                survival_by_gender.plot(kind='bar')
                plt.title('Survival Rate by Gender')
                plt.ylabel('Survival Rate')
                plt.xlabel('Gender')
                plt.xticks(rotation=0)
                plt.tight_layout()
                
                # Show the plot
                plt.show()
                
                # Return the survival rates
                survival_by_gender
                """,
                "language": "python",
            },
            "depends_on": ["load-data"],
        },
    ],
)

# Execute the workflow
result = await workflow_manager.execute_workflow(workflow.id)
```

### Command-Line Interface

The package includes a command-line interface for managing workflows:

```bash
# Create a workflow
composio-framework workflow create --name "My Workflow" --description "My workflow description"

# List workflows
composio-framework workflow list

# Execute a workflow
composio-framework workflow execute --id "workflow-id" --inputs '{"param1": "value1"}'

# Get workflow result
composio-framework workflow get --id "workflow-id"
```

### Environment Variables

The workflow functionality uses the following environment variables:

- `COMPOSIO_API_KEY`: Your Composio API key
- `COMPOSIO_API_URL`: The Composio API URL (optional)
- `E2B_API_KEY`: Your E2B API key
- `WORKFLOW_STORAGE_PATH`: Path to store workflow files (optional, defaults to "./workflows")