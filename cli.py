"""
Composio Framework Generator CLI

This tool generates scaffold code for integrating Composio Agent with
FastAPI or Django frameworks, including e2b code interpreter support.
"""

import os
import sys
import argparse
import logging
from typing import Dict, Any



##from composio.generators import FastAPIGenerator, DjangoGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate scaffold code for Composio Agent integration"
    )
    
    parser.add_argument(
        "--framework", 
        type=str, 
        choices=["fastapi", "django"], 
        required=True,
        help="Web framework to use (fastapi or django)"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        default="./composio_app",
        help="Output directory for the generated code"
    )
    
    parser.add_argument(
        "--name", 
        type=str, 
        default="composio_app",
        help="Name of the application"
    )
    
    parser.add_argument(
        "--vector-db", 
        type=str, 
        choices=["chroma", "pinecone"], 
        default="chroma",
        help="Vector database to use (chroma or pinecone)"
    )
    
    parser.add_argument(
        "--with-docker", 
        action="store_true",
        help="Generate Docker configuration files"
    )
    
    parser.add_argument(
        "--with-examples", 
        action="store_true",
        help="Include example code and workflows"
    )
    
    return parser.parse_args()

def main() -> int:
    """Main entry point for the CLI."""
    args = parse_args()
    
    config = {
        "app_name": args.name,
        "output_dir": args.output,
        "vector_db": args.vector_db,
        "with_docker": args.with_docker,
        "with_examples": args.with_examples,
    }
    
    try:
        if args.framework == "fastapi":
            generator = FastAPIGenerator(config)
        else:  # django
            generator = DjangoGenerator(config)
        
        generator.generate()
        
        logger.info(f"Successfully generated {args.framework} application in {args.output}")
        logger.info(f"To run the application:")
        
        if args.with_docker:
            logger.info(f"  cd {args.output}")
            logger.info(f"  docker-compose up -d")
        else:
            if args.framework == "fastapi":
                logger.info(f"  cd {args.output}")
                logger.info(f"  pip install -r requirements.txt")
                logger.info(f"  uvicorn app:app --reload")
            else:  # django
                logger.info(f"  cd {args.output}")
                logger.info(f"  pip install -r requirements.txt")
                logger.info(f"  python manage.py migrate")
                logger.info(f"  python manage.py runserver")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error generating application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())