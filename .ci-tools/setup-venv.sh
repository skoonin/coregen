#!/bin/bash
# Simple virtual environment setup script

set -e

# Find Python
if ! PYTHON=$(bash .ci-tools/detect-python.sh); then
    echo "Error: Could not find suitable Python"
    exit 1
fi

echo "Using Python: $PYTHON"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv .venv || { echo "Error: Failed to create virtual environment"; exit 1; }
fi

# Upgrade pip, setuptools, wheel
echo "Upgrading pip, setuptools, wheel..."
.venv/bin/pip install --upgrade pip setuptools wheel || { echo "Error: Failed to upgrade pip"; exit 1; }

# Install dependencies
echo "Installing dependencies..."
if [ -f "pyproject.toml" ]; then
    .venv/bin/pip install -e ".[dev]" || { echo "Error: Failed to install dependencies"; exit 1; }
else
    echo "Warning: pyproject.toml not found, skipping dependency installation"
fi

echo "✓ Virtual environment ready at .venv/"
