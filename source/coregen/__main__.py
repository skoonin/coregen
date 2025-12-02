#!/usr/bin/env python3
"""Entry point for standalone builds and python -m execution."""

if __name__ == "__main__":
    import sys

    # try:
    #     from .cli.cli import app
    #     from .common.logger import Logger
    # except ImportError:
    from coregen.cli.cli import app
    from coregen.common.logger import Logger

    try:
        # Initialize logger with default configuration
        logger = Logger("main")

        # Run the Typer app
        app()

    except KeyboardInterrupt:
        logger = Logger("main")
        logger.warning("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger = Logger("main")
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception(e)
        sys.exit(1)
