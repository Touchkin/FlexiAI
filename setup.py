"""Setup configuration for FlexiAI package."""

from pathlib import Path

from setuptools import find_packages, setup

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (
    (this_directory / "README.md").read_text(encoding="utf-8")
    if (this_directory / "README.md").exists()
    else ""
)

setup(
    name="flexiai",
    version="0.3.0",
    author="FlexiAI Contributors",
    author_email="",
    description="A unified interface for multiple GenAI providers with automatic failover",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/flexiai",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/flexiai/issues",
        "Documentation": "https://github.com/yourusername/flexiai/blob/main/README.md",
        "Source Code": "https://github.com/yourusername/flexiai",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai>=1.0.0",
        "google-genai>=0.1.0",
        "anthropic>=0.7.0",
        "pydantic>=2.0.0",
        "tenacity>=8.0.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
        ],
    },
    keywords=[
        "ai",
        "genai",
        "openai",
        "gemini",
        "claude",
        "anthropic",
        "llm",
        "failover",
        "circuit-breaker",
        "multi-provider",
    ],
    license="MIT",
    include_package_data=True,
)
