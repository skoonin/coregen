#!/bin/bash
# Simple environment validation script

ERRORS=0

# Check Python version
if bash .ci-tools/detect-python.sh >/dev/null 2>&1; then
    echo "✓ Python 3.11+ found"
else
    echo "✗ Python 3.11+ not found"
    ERRORS=$((ERRORS + 1))
fi

# Check virtual environment
if [ "$DEVCONTAINER" = "true" ]; then
    # In container - check /opt/venv
    if [ -d "/opt/venv" ] && [ -x "/opt/venv/bin/python" ]; then
        echo "✓ Virtual environment exists"
    else
        echo "✗ Virtual environment missing or corrupted"
        echo "  → Container venv should be at /opt/venv"
        ERRORS=$((ERRORS + 1))
    fi
else
    # On host - check .venv
    if [ -d ".venv" ] && [ -x ".venv/bin/python" ]; then
        echo "✓ Virtual environment exists"
    else
        echo "✗ Virtual environment missing or corrupted"
        echo "  → Run: make venv"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check if in virtual environment
if [ "$VIRTUAL_ENV" != "" ]; then
    echo "✓ Virtual environment activated"
else
    echo "✗ Virtual environment not activated"
    echo "  → Run: source .venv/bin/activate"
fi

# Check pyproject.toml
if [ -f "pyproject.toml" ]; then
    echo "✓ pyproject.toml found"
else
    echo "✗ pyproject.toml missing"
    ERRORS=$((ERRORS + 1))
fi

# Check for patchelf (required for Linux standalone builds)
if [ "$(uname -s)" = "Linux" ]; then
    if command -v patchelf >/dev/null 2>&1; then
        echo "✓ patchelf found (required for standalone builds)"
    else
        echo "⚠ patchelf not found (required for standalone builds)"
        echo "  → Install: apt-get install patchelf (or dnf/yum install patchelf)"
    fi
fi

# Exit with error count
if [ $ERRORS -eq 0 ]; then
    echo "All checks passed"
    exit 0
else
    echo "$ERRORS check(s) failed"
    exit 1
fi
