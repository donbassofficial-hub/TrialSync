"""
Setup script for HoopSync - NBA 2K Statistics Pipeline
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text()

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text().splitlines() 
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="hoopsync",
    version="0.1.0",
    author="donbassofficial-hub",
    author_email="your-email@example.com",
    description="NBA 2K Statistics Pipeline - Capture, process, and analyze basketball gameplay data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/donbassofficial-hub/TrialSync",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video :: Capture",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "hoopsync=hoopsync.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "hoopsync": [
            "config/*.yaml",
            "templates/*.html",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
    },
)
