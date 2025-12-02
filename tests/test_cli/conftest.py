"""Test fixtures for CLI testing.

This conftest provides CLI-specific fixtures. Common fixtures like cli_runner,
cli_app_mocked, mock_logger, mock_console, and global_options are now available
from the root conftest.py and do not need to be redefined here.
"""

import sys
from pathlib import Path

# Add the source directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "source"))

# Note: cli_runner, cli_app (now cli_app_mocked), mock_logger, mock_console,
# and global_options are now provided by the root conftest.py
# If you need the CLI app without mocking, use the cli_app_raw fixture from root

# CLI-specific fixtures can be added here in the future
