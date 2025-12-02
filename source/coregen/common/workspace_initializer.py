"""
Workspace initialization manager.

This module handles the initialization of workspaces based on configuration.
It is used by CLI commands but remains separate from the configuration system.
"""

from pathlib import Path

from coregen.common.file_manager import FileManager
from coregen.common.logger import Logger
from coregen.common.path_service import PathService
from coregen.config_model.models.config import CoregenConfig
from coregen.config_model.models.settings import get_settings


class WorkspaceInitializer:
    """
    Handles workspace initialization based on configuration.

    This class is responsible for:
    - Creating required directories during init
    - Validating paths during normal operation
    - Used by CLI commands but separate from config system
    """

    def __init__(
        self,
        path_service: PathService | None = None,
        file_manager: FileManager | None = None,
        dry_run: bool | None = None,
    ):
        """
        Initialize the workspace initializer.

        Args:
            path_service: Optional PathService instance. If not provided,
                       a new one will be created.
            file_manager: Optional FileManager instance. If not provided,
                       a new one will be created with default settings.
            dry_run: If True, simulate operations without making changes.
                     None means use settings default.
        """
        # Get settings for default values
        self.settings = get_settings()
        cli_settings = self.settings.options.global_options

        # Use parameter if provided, otherwise use settings default
        use_dry_run = dry_run if dry_run is not None else cli_settings.dry_run

        self.path_service = path_service or PathService()
        self.file_manager = file_manager or FileManager(dry_run=use_dry_run)
        self.logger = Logger(self.__class__.__name__)
        self.dry_run = use_dry_run

    def validate_paths(self, config: CoregenConfig, strict: bool = True) -> bool:
        """
        Validate that all required paths exist.

        Args:
            config: The processed configuration
            strict: If True, raises error if paths don't exist
                   If False, returns False if paths invalid

        Returns:
            True if all paths are valid

        Raises:
            ValueError: If paths don't exist and strict=True
        """
        required_paths = self._get_required_paths(config)
        missing_paths = []

        # Check each required path
        for path in required_paths:
            if not path.exists():
                if strict:
                    raise ValueError(f"Required path does not exist: {path}")
                else:
                    self.logger.warning(f"Required path does not exist: {path}")
                    missing_paths.append(path)

        return len(missing_paths) == 0

    def initialize_workspace(
        self, config: CoregenConfig, create_contexts: bool = False
    ) -> None:
        """
        Initialize workspace by creating required directories.

        Args:
            config: The processed configuration
            create_contexts: If True, also creates context directories
        """
        self.logger.debug(
            f"initialize_workspace called with create_contexts={create_contexts}, dry_run={self.dry_run}"
        )
        required_paths = self._get_required_paths(
            config, include_contexts=create_contexts
        )

        self.logger.debug(
            f"Required paths to create: {[str(p) for p in required_paths]}"
        )

        # Create each required path using FileManager to respect global options
        for path in required_paths:
            try:
                if not path.exists():
                    self.logger.info(f"Creating directory: {path}")
                    # Let the file_manager handle dry_run mode - it has the logic built in
                    self.file_manager.create_directory(path)
                else:
                    self.logger.debug(f"Path already exists, skipping: {path}")
            except Exception as e:
                self.logger.error(f"Failed to create directory {path}: {str(e)}")
                raise ValueError(f"Failed to create directory {path}: {str(e)}")

    def _get_required_paths(
        self, config: CoregenConfig, include_contexts: bool = False
    ) -> set[Path]:
        """
        Get the set of required paths for the configuration.

        Args:
            config: The processed configuration
            include_contexts: If True, includes context directories
                           If False, only includes workspace and global dirs

        Returns:
            Set of required Path objects
        """
        required_paths = set()
        root_path = self.path_service.resolver.root_path

        # Always required: archive directory
        archive_dir = root_path / self.settings.workspace.archive_dir
        required_paths.add(archive_dir)

        # For each workspace
        for workspace in config.workspaces:
            # Get workspace path
            workspace_path = self.path_service.get_workspace_path(workspace)
            required_paths.add(workspace_path)

            # Add output directory for the workspace
            if hasattr(workspace, "output_dir") and workspace.output_dir:
                output_dir = root_path / workspace.output_dir
                required_paths.add(output_dir)
                self.logger.debug(f"Adding output directory: {output_dir}")

            if include_contexts:
                # Add context paths if requested
                # Use context_type from the workspace config itself (it should be there after loading)
                # This avoids trying to access context_type directly from settings
                context_type = workspace.context_type

                if context_type in workspace.contexts:
                    for context_name, context in workspace.contexts[
                        context_type
                    ].items():
                        # Add context path
                        context_path = self.path_service.get_context_path(
                            context, workspace
                        )
                        required_paths.add(context_path)
                        self.logger.debug(f"Adding context directory: {context_path}")

                        # Add commit directory for the context
                        if hasattr(context, "commit_dir") and context.commit_dir:
                            commit_dir = context_path / context.commit_dir
                            required_paths.add(commit_dir)
                            self.logger.debug(f"Adding commit directory: {commit_dir}")

        return required_paths
