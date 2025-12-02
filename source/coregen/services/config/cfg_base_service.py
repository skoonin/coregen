"""
Base class for configuration services.

This module provides the base class for all configuration-related services.
It handles common functionality such as file management, workspace initialization,
and configuration provider access.
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
from coregen.config_model.models.settings import get_settings
from coregen.config_model.provider import ConfigurationProvider


class ConfigServiceBase:
    """Base class for configuration services.

    This class provides common functionality for all configuration services.
    It manages file operations, workspace initialization, and configuration access.

    Attributes:
        file_manager: Manager for file operations
        workspace_initializer: Manager for workspace initialization
        config_provider: Provider for configuration access
        console: Console output handler


    """

    def __init__(
        self,
        console: Console | None = None,
        file_manager: FileManager | None = None,
        workspace_initializer: WorkspaceInitializer | None = None,
        config_provider: ConfigurationProvider | None = None,
        global_options: Optional["GlobalOptions"] = None,
        dry_run: bool | None = None,
        file_action: FileAction | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        no_color: bool | None = None,
        config_file: Path | None = None,
    ) -> None:
        """Initialize the configuration service.

        Args:
            console: Optional Console instance
            file_manager: Optional FileManager instance
            workspace_initializer: Optional WorkspaceInitializer instance
            config_provider: Optional ConfigurationProvider instance
            global_options: Optional GlobalOptions instance (takes precedence over individual options)
            dry_run: If True, show what would be done without making changes. None means use settings default.
            file_action: Action to take when a file exists. None means use settings default.
            quiet: If True, suppress non-essential output. None means use settings default.
            verbose: If True, show detailed output. None means use settings default.
            no_color: If True, disable colored output. None means use settings default.
            config_file: Path to configuration file. None means use settings default.
        """
        self.logger = Logger(self.__class__.__name__)

        # Use GlobalOptions if provided, otherwise use individual parameters
        if global_options is not None:
            # GlobalOptions takes precedence over individual parameters
            use_dry_run = global_options.dry_run
            use_file_action = global_options.file_action
            use_quiet = global_options.quiet
            use_verbose = global_options.verbose
            use_no_color = global_options.no_color
            use_config_file = global_options.config_file
            # Store the GlobalOptions instance for reference
            self._global_options = global_options
        else:
            # Get settings for default values
            settings = get_settings()
            cli_settings = settings.options.global_options

            use_dry_run = dry_run if dry_run is not None else cli_settings.dry_run
            use_file_action = (
                file_action if file_action is not None else cli_settings.file_action
            )
            use_quiet = quiet if quiet is not None else cli_settings.quiet
            use_verbose = verbose if verbose is not None else cli_settings.verbose
            use_no_color = no_color if no_color is not None else cli_settings.no_color
            use_config_file = (
                config_file if config_file is not None else cli_settings.config_file
            )
            self._global_options = None

        # Initialize console if not provided, create an instance
        self._console = console or Console()

        # Initialize file manager if not provided
        self._file_manager = file_manager or FileManager(
            dry_run=use_dry_run,
            file_action=use_file_action,
            quiet=use_quiet,
            verbose=use_verbose,
            no_color=use_no_color,
        )

        # Initialize configuration provider if not provided
        self._config_provider = config_provider or ConfigurationProvider(
            config_mode=True,
            lenient_validation=True,
            dry_run=use_dry_run,
            file_action=use_file_action,
            quiet=use_quiet,
            verbose=use_verbose,
            no_color=use_no_color,
        )

        # Initialize workspace initializer if not provided
        self._workspace_initializer = workspace_initializer or WorkspaceInitializer(
            path_service=self._config_provider.path_service,
            file_manager=self._file_manager,
        )

        # Store the final options (either from parameters or settings)
        self.dry_run = use_dry_run
        self.file_action = use_file_action
        self.quiet = use_quiet
        self.verbose = use_verbose
        self.no_color = use_no_color
        self.config_file = use_config_file

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
    def config_provider(self) -> ConfigurationProvider:
        """Get the configuration provider instance."""
        return self._config_provider

    @property
    def global_options(self) -> Optional["GlobalOptions"]:
        """Get the global options instance."""
        return self._global_options
