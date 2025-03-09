"""
Django application generator for Composio framework.
"""

import os
import logging
import subprocess
from typing import Dict, Any

from .base import BaseGenerator
from composio_framework.utils.templates import render_template

logger = logging.getLogger(__name__)

class DjangoGenerator(BaseGenerator):
    """Generator for Django applications."""
    
    framework = "django"
    
    def _generate_framework_files(self) -> None:
        """Generate Django-specific files."""
        # Create Django project using django-admin
        project_name = self.app_name
        app_name = "composio_app"
        
        # Create requirements.txt first
        requirements_content = render_template("django/requirements.txt.template", self.config)
        with open(os.path.join(self.output_dir, "requirements.txt"), "w") as f:
            f.write(requirements_content)
        
        # Create Django project structure manually
        self._create_django_structure(project_name, app_name)
        
        # Create settings.py
        settings_content = render_template(
            "django/project/settings.py.template", 
            {**self.config, "project_name": project_name, "app_name": app_name}
        )
        with open(os.path.join(self.output_dir, project_name, "settings.py"), "w") as f:
            f.write(settings_content)
        
        # Create urls.py for project
        urls_content = render_template(
            "django/project/urls.py.template", 
            {**self.config, "project_name": project_name, "app_name": app_name}
        )
        with open(os.path.join(self.output_dir, project_name, "urls.py"), "w") as f:
            f.write(urls_content)
        
        # Create views.py for app
        views_content = render_template(
            "django/app/views.py.template", 
            {**self.config, "project_name": project_name, "app_name": app_name}
        )
        with open(os.path.join(self.output_dir, app_name, "views.py"), "w") as f:
            f.write(views_content)
        
        # Create urls.py for app
        app_urls_content = render_template(
            "django/app/urls.py.template", 
            {**self.config, "project_name": project_name, "app_name": app_name}
        )
        with open(os.path.join(self.output_dir, app_name, "urls.py"), "w") as f:
            f.write(app_urls_content)
        
        # Create models.py for app
        models_content = render_template(
            "django/app/models.py.template", 
            {**self.config, "project_name": project_name, "app_name": app_name}
        )
        with open(os.path.join(self.output_dir, app_name, "models.py"), "w") as f:
            f.write(models_content)
        
        # Create workflows directory
        workflows_dir = os.path.join(self.output_dir, app_name, "workflows")
        os.makedirs(workflows_dir, exist_ok=True)
        
        # Create base workflow file
        workflow_base_content = render_template(
            "django/app/workflows/base.py.template", 
            {**self.config, "project_name": project_name, "app_name": app_name}
        )
        with open(os.path.join(workflows_dir, "base.py"), "w") as f:
            f.write(workflow_base_content)
        
        # Create __init__.py in workflows directory
        with open(os.path.join(workflows_dir, "__init__.py"), "w") as f:
            f.write("# Workflows package\n")
    
    def _create_django_structure(self, project_name: str, app_name: str) -> None:
        """Create basic Django project structure."""
        # Create project directory
        project_dir = os.path.join(self.output_dir, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # Create __init__.py in project directory
        with open(os.path.join(project_dir, "__init__.py"), "w") as f:
            f.write("")
        
        # Create wsgi.py
        wsgi_content = f"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project_name}.settings')

application = get_wsgi_application()
"""
        with open(os.path.join(project_dir, "wsgi.py"), "w") as f:
            f.write(wsgi_content)
        
        # Create asgi.py
        asgi_content = f"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project_name}.settings')

application = get_asgi_application()
"""
        with open(os.path.join(project_dir, "asgi.py"), "w") as f:
            f.write(asgi_content)
        
        # Create app directory
        app_dir = os.path.join(self.output_dir, app_name)
        os.makedirs(app_dir, exist_ok=True)
        
        # Create __init__.py in app directory
        with open(os.path.join(app_dir, "__init__.py"), "w") as f:
            f.write("")
        
        # Create apps.py
        apps_content = f"""
from django.apps import AppConfig


class {app_name.capitalize()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{app_name}'
"""
        with open(os.path.join(app_dir, "apps.py"), "w") as f:
            f.write(apps_content)
        
        # Create migrations directory
        migrations_dir = os.path.join(app_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create __init__.py in migrations directory
        with open(os.path.join(migrations_dir, "__init__.py"), "w") as f:
            f.write("")
        
        # Create manage.py
        manage_content = f"""#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project_name}.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
"""
        manage_path = os.path.join(self.output_dir, "manage.py")
        with open(manage_path, "w") as f:
            f.write(manage_content)
        
        # Make manage.py executable
        os.chmod(manage_path, 0o755)
    
    def _generate_example_files(self) -> None:
        """Generate example files for Django."""
        if not self.with_examples:
            return
        
        app_name = "composio_app"
        
        # Create examples directory
        examples_dir = os.path.join(self.output_dir, app_name, "examples")
        os.makedirs(examples_dir, exist_ok=True)
        
        # Create example workflow
        example_workflow_content = render_template(
            "django/app/examples/data_analysis_workflow.py.template", 
            {**self.config, "app_name": app_name}
        )
        with open(os.path.join(examples_dir, "data_analysis_workflow.py"), "w") as f:
            f.write(example_workflow_content)
        
        # Create example view
        example_view_content = render_template(
            "django/app/examples/example_views.py.template", 
            {**self.config, "app_name": app_name}
        )
        with open(os.path.join(examples_dir, "example_views.py"), "w") as f:
            f.write(example_view_content)
        
        # Create example template
        templates_dir = os.path.join(self.output_dir, app_name, "templates", app_name)
        os.makedirs(templates_dir, exist_ok=True)
        
        example_template_content = render_template(
            "django/app/templates/workflow.html.template", 
            {**self.config, "app_name": app_name}
        )
        with open(os.path.join(templates_dir, "workflow.html"), "w") as f:
            f.write(example_template_content)
        
        # Create example README
        example_readme_content = render_template(
            "django/app/examples/README.md.template", 
            {**self.config, "app_name": app_name}
        )
        with open(os.path.join(examples_dir, "README.md"), "w") as f:
            f.write(example_readme_content)
