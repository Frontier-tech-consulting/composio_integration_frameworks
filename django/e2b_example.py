"""
Example Django application using Composio Agent Integration with E2B Code Interpreter.

This example demonstrates how to integrate E2B Code Interpreter with Django
and Composio's AgentAuth to create a secure code execution API.
"""

import os
import json
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import authenticate, login
from django.conf import settings

# Import from Composio Agent Integration
from ..auth.client import register_user, login_user, validate_token
from ..auth.exceptions import AuthException, UserExistsError, InvalidCredentialsError
from ..discussion.manager import DiscussionManager
from ..e2b_interpreter import CodeInterpreterClient, CodeInterpreterException
from ..e2b_interpreter.exceptions import SandboxError, ExecutionError, TimeoutError

# Import Django e2b integration
from .e2b_integration import execute_code, get_user_executions, get_all_executions

# This is a simplified example file - not a complete Django app
# In a real application, you would define these views in a proper app structure
# with models, templates, etc.

# Example views for authentication
@csrf_exempt
@require_POST
def register_view(request):
    """Register a new user with AgentAuth."""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'client')
        
        # Register the user with AgentAuth
        result = register_user(username, password, email, role)
        
        return JsonResponse({
            'success': True,
            'user_id': result.get('user_id'),
            'username': username,
            'role': role
        })
    except UserExistsError:
        return JsonResponse({
            'success': False,
            'error': 'A user with this username or email already exists',
            'error_type': 'UserExistsError'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)

@csrf_exempt
@require_POST
def login_view(request):
    """Login and get an access token."""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        # Login the user with AgentAuth
        result = login_user(username, password)
        token = result.get('token')
        
        # For a real Django app, you would also authenticate with Django's system
        # User = get_user_model()
        # user, created = User.objects.get_or_create(username=username)
        # login(request, user)
        
        return JsonResponse({
            'success': True,
            'access_token': token,
            'token_type': 'bearer'
        })
    except InvalidCredentialsError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid username or password',
            'error_type': 'InvalidCredentialsError'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)

# Example view for token validation
@csrf_exempt
def validate_token_view(request):
    """Validate an access token."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return JsonResponse({
            'success': False,
            'error': 'No token provided',
            'error_type': 'ValidationError'
        }, status=401)
    
    try:
        # Validate the token and get user info
        user_info = validate_token(token)
        
        return JsonResponse({
            'success': True,
            'user': user_info
        })
    except AuthException as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': 'ServerError'
        }, status=500)

# Health check endpoint
def health_check(request):
    """Health check endpoint."""
    # Get the interpreter
    from .e2b_integration import get_code_interpreter
    interpreter = get_code_interpreter()
    
    return JsonResponse({
        'status': 'healthy',
        'services': {
            'auth': True,  # Assuming auth service is available
            'e2b_interpreter': interpreter is not None
        }
    })

# Django URL patterns (for the example)
urlpatterns = [
    # Auth routes
    path('auth/register/', register_view, name='register'),
    path('auth/login/', login_view, name='login'),
    path('auth/validate/', validate_token_view, name='validate_token'),
    
    # E2B routes (these would normally be protected by Django authentication)
    path('api/execute-code/', execute_code, name='execute_code'),
    path('api/executions/', get_user_executions, name='get_user_executions'),
    path('api/admin/executions/', get_all_executions, name='get_all_executions'),
    
    # Health check
    path('health/', health_check, name='health_check'),
]

"""
Django Integration Configuration Guide:

1. Install the package:
   ```bash
   pip install composio_integration_frameworks[all]
   ```

2. Add to Django settings.py:
   ```python
   INSTALLED_APPS = [
       # ... other apps
       'composio_integration_frameworks.django',
   ]
   
   # E2B Code Interpreter configuration
   E2B_API_KEY = 'your-e2b-api-key'  # Or use environment variable
   E2B_EXECUTION_TIMEOUT = 300  # Timeout in seconds
   
   # Vector database configuration
   VECTOR_DB_TYPE = 'chroma'  # Or 'pinecone'
   VECTOR_DB_CONFIG = {
       # For Chroma
       'persist_directory': './chroma_db',
       'collection_name': 'e2b_executions',
       
       # For Pinecone
       # 'api_key': 'your-pinecone-api-key',
       # 'environment': 'your-pinecone-environment',
       # 'index_name': 'composio-e2b-executions',
   }
   ```

3. Add to Django urls.py:
   ```python
   from django.urls import path, include
   
   urlpatterns = [
       # ... other URL patterns
       path('e2b/', include('composio_integration_frameworks.django.e2b_urls')),
   ]
   ```

4. Create a simple Django template that uses the API:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>E2B Code Interpreter Demo</title>
       <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
   </head>
   <body>
       <h1>E2B Code Interpreter Demo</h1>
       
       <div>
           <h2>Login</h2>
           <form id="login-form">
               <input type="text" id="username" placeholder="Username" required><br>
               <input type="password" id="password" placeholder="Password" required><br>
               <button type="submit">Login</button>
           </form>
       </div>
       
       <div id="code-section" style="display:none;">
           <h2>Execute Code</h2>
           <select id="language">
               <option value="python">Python</option>
               <option value="javascript">JavaScript</option>
           </select><br>
           <textarea id="code" rows="10" cols="50" placeholder="Enter code here..."></textarea><br>
           <button id="execute-btn">Execute</button>
           
           <h3>Results:</h3>
           <pre id="results"></pre>
       </div>
       
       <script>
           let token = '';
           
           $('#login-form').submit(function(e) {
               e.preventDefault();
               
               $.ajax({
                   url: '/auth/login/',
                   type: 'POST',
                   contentType: 'application/json',
                   data: JSON.stringify({
                       username: $('#username').val(),
                       password: $('#password').val()
                   }),
                   success: function(data) {
                       token = data.access_token;
                       $('#login-form').hide();
                       $('#code-section').show();
                   },
                   error: function(xhr) {
                       alert('Login failed: ' + xhr.responseJSON.error);
                   }
               });
           });
           
           $('#execute-btn').click(function() {
               const code = $('#code').val();
               const language = $('#language').val();
               
               $.ajax({
                   url: '/api/execute-code/',
                   type: 'POST',
                   contentType: 'application/json',
                   headers: {
                       'Authorization': 'Bearer ' + token
                   },
                   data: JSON.stringify({
                       code: code,
                       language: language
                   }),
                   success: function(data) {
                       let output = '';
                       
                       // Show stdout/stderr
                       if (data.outputs && data.outputs.length > 0) {
                           output += "--- Outputs ---\n";
                           data.outputs.forEach(function(item) {
                               output += item.line + '\n';
                           });
                           output += '\n';
                       }
                       
                       // Show result
                       if (data.result) {
                           output += "--- Result ---\n";
                           output += JSON.stringify(data.result, null, 2);
                       }
                       
                       $('#results').text(output);
                   },
                   error: function(xhr) {
                       $('#results').text('Error: ' + JSON.stringify(xhr.responseJSON, null, 2));
                   }
               });
           });
       </script>
   </body>
   </html>
   ```
""" 