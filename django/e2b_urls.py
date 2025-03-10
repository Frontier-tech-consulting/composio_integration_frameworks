"""
URL patterns for E2B Code Interpreter integration with Django.

This module provides URL patterns for E2B Code Interpreter views.
"""

from django.urls import path
from . import e2b_integration

urlpatterns = [
    path('execute/', e2b_integration.execute_code, name='e2b_execute_code'),
    path('executions/', e2b_integration.get_user_executions, name='e2b_get_user_executions'),
    path('admin/executions/', e2b_integration.get_all_executions, name='e2b_get_all_executions'),
]

# Usage in main urls.py:
# from django.urls import path, include
#
# urlpatterns = [
#     # ... other URL patterns
#     path('e2b/', include('composio_integration_frameworks.django.e2b_urls')),
# ] 