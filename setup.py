"""Setup script for Backup Assistant."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="backup-assistant",
    version="1.0.0",
    description="A GUI-based Backup Assistant with deduplication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Backup Assistant Team",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "backup-assistant=app:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)


