from setuptools import setup, find_packages
import os

# Read the README file for long description
long_description = ""
if os.path.exists("README.md"):
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()

setup(
    name="composio_integration_frameworks",
    version="0.1.0",
    description="Integrate Composio's AgentAuth with FastAPI and Django",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Dhruv Malik",
    author_email="malikdhruv1994@gmail.com",
    url="https://github.com/Frontier-tech-consulting/composio_integration_frameworks",
    packages=["auth", "discussion", "utils", "generators", "e2b_interpreter", "fastapi", "django", "workflows"],
    install_requires=[
        "requests>=2.28.0",
        "composio>=0.1.0",
    ],
    extras_require={
        "fastapi": ["fastapi>=0.100.0", "pydantic>=2.0.0", "uvicorn>=0.15.0"],
        "django": ["django>=4.0"],
        "pinecone": ["pinecone-client>=2.0.0"],
        "chroma": ["chromadb>=0.3.24"],
        "langchain": ["langchain>=0.0.248"],
        "crewai": ["crewai>=0.0.1"],
        "e2b": ["e2b-code-interpreter>=0.1.0"],
        "test": ["pytest>=7.0.0", "pytest-asyncio>=0.18.0", "httpx>=0.23.0"],
        "all": [
            "fastapi>=0.100.0", 
            "pydantic>=2.0.0",
            "uvicorn>=0.15.0",
            "django>=4.0", 
            "pinecone-client>=2.0.0", 
            "chromadb>=0.3.24", 
            "langchain>=0.0.248", 
            "crewai>=0.0.1",
            "e2b-code-interpreter>=0.1.0",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "httpx>=0.23.0"
        ],
    },
    python_requires=">=3.8,<3.11",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Framework :: Django",
        "Framework :: FastAPI",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
    ],
    keywords=["composio", "agents", "ai", "authentication", "vector database", 
              "django", "fastapi", "code interpreter", "e2b", "workflow"],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "composio-framework=cli:main",
        ],
    },
)

