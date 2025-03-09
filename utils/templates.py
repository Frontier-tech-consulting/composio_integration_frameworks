"""
Template rendering utilities for Composio framework generator.
"""

import os
import jinja2
from typing import Dict, Any

# Get the directory where templates are stored
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

def render_template(template_path: str, context: Dict[str, Any]) -> str:
    """
    Render a template with the given context.
    
    Args:
        template_path: Path to the template file, relative to the templates directory
        context: Dictionary of variables to use in the template
        
    Returns:
        Rendered template as a string
    """
    # Create Jinja2 environment
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Load and render the template
    template = env.get_template(template_path)
    return template.render(**context)
