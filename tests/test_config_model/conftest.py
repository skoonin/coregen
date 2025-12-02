"""Test fixtures for config model tests.

All common fixtures are now available from the root conftest.py.
This file is kept for future config-model-specific fixtures if needed.
"""

import sys
from pathlib import Path

# Add the source directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "source"))
