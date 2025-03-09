from django.test import TestCase, Client
from django.urls import reverse
import json

class ComposioIntegrationTest(TestCase):
    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.execute_code_url = reverse('execute_code')
        self.execute_workflow_url = reverse('execute_workflow')
        
        # Register a test user
        self.register_data = {
            "username": "testuser",
            "password": "Test@123",
            "email": "test@example.com",
            "role": "client"
        }
        self.client.post(
            self.register_url,
            data=json.dumps(self.register_data),
            content_type='application/json'
        )
        
        # Login to get a token
        login_data = {
            "username": "testuser",
            "password": "Test@123"
        }
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type='application/json'
        )
        self.token = login_response.json()['access_token']
    
    def test_code_execution(self):
        """Test code execution with E2B."""
        code_data = {
            "code": "print('Hello, world!')\nresult = {'message': 'Hello, world!', 'value': 42}",
            "language": "python"
        }
        
        response = self.client.post(
            self.execute_code_url,
            data=json.dumps(code_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        self.assertIn('outputs', result)
        self.assertIn('result', result)
        self.assertIn('json', result['result'])
        self.assertEqual(result['result']['json']['message'], 'Hello, world!')
        self.assertEqual(result['result']['json']['value'], 42)
    
    def test_workflow_execution(self):
        """Test workflow execution."""
        workflow_data = {
            "workflow_id": "example",
            "parameters": {
                "param1": "value1",
                "param2": "value2"
            }
        }
        
        response = self.client.post(
            self.execute_workflow_url,
            data=json.dumps(workflow_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('workflow_id', result)
        self.assertEqual(result['status'], 'completed')
        self.assertIn('result', result)