# cli/cli_functions.py


from coregen.common.logger import Logger

logger = Logger(__name__)


def get_epilog(app_name: str, subcommand: str | None = None) -> str:
    """Get epilog text for typer application."""
    # Return empty string to remove epilog entirely
    return ""
