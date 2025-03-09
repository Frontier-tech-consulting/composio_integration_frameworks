"""
FastAPI application generator for Composio framework.
"""

import os
import logging
from typing import Dict, Any

from composio_framework.generators.base import BaseGenerator
from composio_framework.utils.templates import render_template

logger = logging.getLogger(__name__)

class FastAPIGenerator(BaseGenerator):
    """Generator for FastAPI applications."""
    
    framework = "fastapi"
    
    def _generate_framework_files(self) -> None:
        """Generate FastAPI-specific files."""
        # Create app.py
        app_content = render_template("fastapi/app.py.template", self.config)
        with open(os.path.join(self.output_dir, "app.py"), "w") as f:
            f.write(app_content)
        
        # Create requirements.txt
        requirements_content = render_template("fastapi/requirements.txt.template", self.config)
        with open(os.path.join(self.output_dir, "requirements.txt"), "w") as f:
            f.write(requirements_content)
        
        # Create workflows directory
        workflows_dir = os.path.join(self.output_dir, "workflows")
        os.makedirs(workflows_dir, exist_ok=True)
        
        # Create base workflow file
        workflow_base_content = render_template("fastapi/workflows/base.py.template", self.config)
        with open(os.path.join(workflows_dir, "base.py"), "w") as f:
            f.write(workflow_base_content)
        
        # Create __init__.py in workflows directory
        with open(os.path.join(workflows_dir, "__init__.py"), "w") as f:
            f.write("# Workflows package\n")
    
    def _generate_example_files(self) -> None:
        """Generate example files for FastAPI."""
        if not self.with_examples:
            return
        
        # Create examples directory
        examples_dir = os.path.join(self.output_dir, "examples")
        os.makedirs(examples_dir, exist_ok=True)
        
        # Create example workflow
        example_workflow_content = render_template(
            "fastapi/examples/data_analysis_workflow.py.template", 
            self.config
        )
        with open(os.path.join(examples_dir, "data_analysis_workflow.py"), "w") as f:
            f.write(example_workflow_content)
        
        # Create example test script
        test_script_content = render_template(
            "fastapi/examples/test_workflow.py.template", 
            self.config
        )
        with open(os.path.join(examples_dir, "test_workflow.py"), "w") as f:
            f.write(test_script_content)
            
        # Create example README
        example_readme_content = render_template(
            "fastapi/examples/README.md.template", 
            self.config
        )
        with open(os.path.join(examples_dir, "README.md"), "w") as f:
            f.write(example_readme_content)