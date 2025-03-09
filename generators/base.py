"""
Base generator for scaffolding Composio applications.
"""

import os
import shutil
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from composio_framework.utils.templates import render_template

logger = logging.getLogger(__name__)

class BaseGenerator(ABC):
    """Base class for application generators."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the generator.
        
        Args:
            config: Configuration dictionary with the following keys:
                - app_name: Name of the application
                - output_dir: Output directory for the generated code
                - vector_db: Vector database to use (chroma or pinecone)
                - with_docker: Whether to generate Docker configuration
                - with_examples: Whether to include example code
        """
        self.config = config
        self.app_name = config["app_name"]
        self.output_dir = config["output_dir"]
        self.vector_db = config["vector_db"]
        self.with_docker = config["with_docker"]
        self.with_examples = config["with_examples"]
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate(self) -> None:
        """Generate the application scaffold."""
        logger.info(f"Generating application scaffold in {self.output_dir}")
        
        # Generate common files
        self._generate_common_files()
        
        # Generate framework-specific files
        self._generate_framework_files()
        
        # Generate Docker files if requested
        if self.with_docker:
            self._generate_docker_files()
        
        # Generate example files if requested
        if self.with_examples:
            self._generate_example_files()
    
    def _generate_common_files(self) -> None:
        """Generate common files for all frameworks."""
        # Create .env file
        env_content = render_template("common/env.template", self.config)
        with open(os.path.join(self.output_dir, ".env"), "w") as f:
            f.write(env_content)
        
        # Create README.md
        readme_content = render_template("common/README.md.template", self.config)
        with open(os.path.join(self.output_dir, "README.md"), "w") as f:
            f.write(readme_content)
    
    @abstractmethod
    def _generate_framework_files(self) -> None:
        """Generate framework-specific files."""
        pass
    
    def _generate_docker_files(self) -> None:
        """Generate Docker configuration files."""
        # Generate Dockerfile
        dockerfile_content = render_template(
            f"{self.framework}/Dockerfile.template", 
            self.config
        )
        with open(os.path.join(self.output_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)
        
        # Generate docker-compose.yml
        docker_compose_content = render_template(
            f"{self.framework}/docker-compose.yml.template", 
            self.config
        )
        with open(os.path.join(self.output_dir, "docker-compose.yml"), "w") as f:
            f.write(docker_compose_content)
        
        # Generate docker-entrypoint.sh
        entrypoint_content = render_template(
            f"{self.framework}/docker-entrypoint.sh.template", 
            self.config
        )
        entrypoint_path = os.path.join(self.output_dir, "docker-entrypoint.sh")
        with open(entrypoint_path, "w") as f:
            f.write(entrypoint_content)
        
        # Make entrypoint executable
        os.chmod(entrypoint_path, 0o755)
    
    @abstractmethod
    def _generate_example_files(self) -> None:
        """Generate example files."""
        pass