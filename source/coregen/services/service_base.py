"""
Base class for all services.

This module provides the base class for all service implementations.
It handles common functionality such as file management, workspace initialization,
and console output.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from coregen.cli.global_options import GlobalOptions

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.console import Console
from coregen.common.file_manager import FileManager
from coregen.common.logger import Logger
from coregen.common.workspace_initializer import WorkspaceInitializer

logger = Logger(__name__)


class ServiceBase:
    """Base class for all services.

    This class provides common functionality for all services.
    It manages file operations, workspace initialization, and console output.

    Attributes:
        file_manager: Manager for file operations
        workspace_initializer: Manager for workspace initialization
        console: Console output handler
    """

    def __init__(
        self,
        console: Console | None = None,
        file_manager: FileManager | None = None,
        workspace_initializer: WorkspaceInitializer | None = None,
        global_options: Optional["GlobalOptions"] = None,
        dry_run: bool | None = None,
        file_action: FileAction | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        no_color: bool | None = None,
        config_file: Path | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            console: Optional Console instance
            file_manager: Optional FileManager instance
            workspace_initializer: Optional WorkspaceInitializer instance
            global_options: Optional GlobalOptions instance (takes precedence over individual options)
            dry_run: If True, show what would be done without making changes
            file_action: Action to take when a file exists
            quiet: If True, suppress non-essential output
            verbose: If True, show detailed output
            no_color: If True, disable colored output
            config_file: Optional path to the configuration file
        """
        self.logger = Logger(self.__class__.__name__)

        # Use GlobalOptions if provided, otherwise use individual parameters
        if global_options is not None:
            # GlobalOptions takes precedence over individual parameters
            self.dry_run = global_options.dry_run
            self.file_action = global_options.file_action
            self.quiet = global_options.quiet
            self.verbose = global_options.verbose
            self.no_color = global_options.no_color
            self.config_file = global_options.config_file
            # Store the GlobalOptions instance for reference
            self._global_options = global_options
        else:
            # Import settings for defaults
            from coregen.config_model.models.settings import get_settings

            settings = get_settings()
            cli_settings = settings.options.global_options

            self.dry_run = dry_run if dry_run is not None else cli_settings.dry_run
            self.file_action = (
                file_action if file_action is not None else cli_settings.file_action
            )
            self.quiet = quiet if quiet is not None else cli_settings.quiet
            self.verbose = verbose if verbose is not None else cli_settings.verbose
            self.no_color = no_color if no_color is not None else cli_settings.no_color
            self.config_file = config_file
            self._global_options = None

        # Initialize console consistently as an instance if provided or access class methods
        if console is not None:
            self._console = console  # Use provided console instance
        else:
            # Use the class directly (not creating an instance)
            self._console = Console

        # Initialize file manager if not provided
        self._file_manager = file_manager or FileManager(
            dry_run=self.dry_run,
            file_action=self.file_action,
            quiet=self.quiet,
            verbose=self.verbose,
        )

        # Initialize workspace initializer if not provided
        self._workspace_initializer = workspace_initializer or WorkspaceInitializer(
            path_service=None,  # This will be set by derived classes if needed
            file_manager=self._file_manager,
        )

        self.logger.debug(f"Initialized {self.__class__.__name__}")

    @property
    def console(self) -> Console:
        """Get the console output handler instance."""
        return self._console

    @property
    def file_manager(self) -> FileManager:
        """Get the file manager instance."""
        return self._file_manager

    @property
    def workspace_initializer(self) -> WorkspaceInitializer:
        """Get the workspace initializer instance."""
        return self._workspace_initializer

    @property
    def global_options(self) -> Optional["GlobalOptions"]:
        """Get the global options instance."""
        return self._global_options
