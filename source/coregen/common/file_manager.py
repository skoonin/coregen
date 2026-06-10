import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.console import Console
from coregen.common.logger import Logger

logger = Logger(__name__)
# Use Console class directly
console = Console


class FileManager:
    """
    Manages file system operations with optional dry-run and file action logic.

    Attributes:
        dry_run: Simulates operations if True.
        file_action: Strategy to apply for existing files.
        archive_dir: Directory to archive files.
        timeout_seconds: Seconds to wait for user input before defaulting to skip.
    """

    def __init__(
        self,
        archive_dir: Path | None = None,
        dry_run: bool | None = None,
        file_action: FileAction | None = None,
        quiet: bool | None = None,
        verbose: bool | None = None,
        no_color: bool | None = None,
        timeout_seconds: int = 30,
    ):
        """Initialize FileManager with configuration options."""
        from coregen.config_model.models.settings import get_settings

        settings = get_settings()
        self.dry_run = (
            dry_run if dry_run is not None else settings.options.global_options.dry_run
        )
        self.file_action = (
            file_action
            if file_action is not None
            else settings.options.global_options.file_action
        )
        self.quiet = (
            quiet if quiet is not None else settings.options.global_options.quiet
        )
        self.verbose = (
            verbose if verbose is not None else settings.options.global_options.verbose
        )
        self.no_color = (
            no_color
            if no_color is not None
            else settings.options.global_options.no_color
        )

        # Use archive_dir from settings if not provided
        self.archive_dir = (
            Path(settings.workspace.archive_dir) if archive_dir is None else archive_dir
        )

        # Keep timeout_seconds as is (could be moved to settings in future)
        self.timeout_seconds = timeout_seconds

        # Track created directories to avoid duplicate messages when verbose logging is enabled
        self._created_directories: set[str] = set()

        logger.debug(
            f"FileManager initialized with dry_run={dry_run}, file_action={file_action}, no_color={no_color}"
        )

    def _handle_action(self, path: Path) -> bool:
        if not path.exists():
            return True

        # Skip prompting for empty directories
        if path.is_dir() and not any(path.iterdir()):
            return True

        if self.file_action == FileAction.ASK:
            return self._prompt_action(path)
        elif self.file_action == FileAction.SKIP:
            if not self.quiet:
                console.debug(f"Skipping: {path}")
            return False
        elif self.file_action == FileAction.OVERWRITE:
            logger.debug(f"Overwriting: {path}")
            self._delete(path)
            return True
        elif self.file_action == FileAction.ARCHIVE:
            if not self.archive_dir:
                raise ValueError("archive_dir must be set for ARCHIVE action")
            console.info(f"Archiving: {path}")
            self._archive(path)
            return True
        elif self.file_action == FileAction.DELETE:
            logger.debug(f"Deleting: {path}")
            self._delete(path)
            return True

    def _prompt_action(self, path: Path) -> bool:
        if self.dry_run:
            console.info(f"Would prompt for {path}")
            return True

        # Check if we're in a TTY environment and not in quiet mode
        if not sys.stdin.isatty() or self.quiet:
            console.info(
                f"File exists: {path} - Non-interactive mode, defaulting to skip"
            )
            return False

        console.info(f"File exists: {path}")

        # Use a thread-based timeout instead of signals for better concurrency safety
        result: list[bool | None] = [
            None
        ]  # Use a list to capture result from inner scope
        timer = None
        prompt_done = threading.Event()

        def handle_timeout() -> None:
            if not prompt_done.is_set():
                console.info("\nTimed out. Defaulting to skip.")
                prompt_done.set()

        try:
            timer = threading.Timer(self.timeout_seconds, handle_timeout)
            timer.start()

            while not prompt_done.is_set():
                action = (
                    input(
                        f"({self.timeout_seconds}s timeout) [s]kip, [o]verwrite, [a]rchive, [d]elete: "
                    )
                    .lower()
                    .strip()
                )

                if action in ["s", "skip"]:
                    console.info("Skipping.")
                    result[0] = False
                    break
                elif action in ["o", "overwrite"]:
                    self._delete(path)
                    result[0] = True
                    break
                elif action in ["a", "archive"]:
                    if not self.archive_dir:
                        console.info("No archive_dir configured.")
                        continue
                    self._archive(path)
                    result[0] = True
                    break
                elif action in ["d", "delete"]:
                    self._delete(path)
                    result[0] = True
                    break
                else:
                    console.info("Invalid choice.")

            # If prompt_done is set but result is None, timeout occurred
            return False if result[0] is None else result[0]

        finally:
            prompt_done.set()
            if timer:
                timer.cancel()

    def _archive(self, path: Path) -> None:
        # Determine the workspace root (assuming it's the current working directory)
        # and calculate the relative path.
        try:
            # Ensure path is absolute before calculating relative path
            abs_path = path.resolve()
            workspace_root = Path.cwd().resolve()
            relative_path = abs_path.relative_to(workspace_root)
            timestamp_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            # Ensure archive_dir is resolved as well
            full_archive_path = (
                self.archive_dir.resolve() / timestamp_str / relative_path
            )
        except ValueError:
            # Fallback if path is not relative to CWD
            workspace_root_str = str(Path.cwd().resolve())  # For logging
            abs_path_str = str(path.resolve())  # For logging
            logger.warning(
                f"Could not determine relative path for {abs_path_str} based on CWD {workspace_root_str}. Archiving with filename only."
            )
            timestamp_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            # Use original path name for fallback, resolved archive_dir
            full_archive_path = self.archive_dir.resolve() / timestamp_str / path.name

        if self.dry_run:
            # Use str() for printing Path objects cleanly
            console.info(f"Archive {str(path)} -> {str(full_archive_path)}")
            return

        # Use the calculated full_archive_path
        archive_path = full_archive_path
        try:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            # Use resolve() to ensure paths are absolute for shutil.move
            shutil.move(str(path.resolve()), str(archive_path))
            console.info(
                f"[bright_white]Archived:[/] {str(path)} -> {str(archive_path)}"
            )
        except Exception as e:
            logger.error(f"Archiving failed: {e}")
            raise

    def _delete(self, path: Path) -> None:
        if self.dry_run:
            # Don't output twice - this gets called from _handle_action which already logs
            return

        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir() and any(path.iterdir()):  # only delete non-empty dirs
                shutil.rmtree(path)
                logger.debug(f"Deleted: {path}")
        except Exception as e:
            logger.error(f"Deletion failed: {e}")
            raise

    def copy_file(self, source: Path, destination: Path) -> list[str]:
        """Copy a file from source to destination, returning a list of error messages.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            List of error messages, empty if successful
        """
        errors = []

        try:
            if not source.exists():
                error_msg = f"Source file does not exist: {source}"
                logger.error(error_msg)
                errors.append(error_msg)
                return errors

            if not self._handle_action(destination):
                return errors  # No errors, just skipped

            if self.dry_run:
                if not self.quiet and self.verbose:
                    console.debug(f"Copied file: {source} -> {destination}")
                return errors  # No errors

            try:
                content = source.read_text()
                self.create_file(destination, content, source_perms=source)
            except Exception as e:
                error_msg = f"Reading source failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        except Exception as e:
            error_msg = f"File copy operation failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        return errors

    def create_file(
        self, path: Path, content: str = "", source_perms: Path | None = None
    ) -> None:
        if not self._handle_action(path):
            return

        if self.dry_run:
            if not self.quiet and self.verbose:
                console.debug(f"Created file: {path}")
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            path.write_text(content)

            if source_perms and source_perms.exists():
                try:
                    shutil.copymode(source_perms, path)
                    logger.debug(f"Permissions copied from {source_perms}")
                except (OSError, PermissionError) as e:
                    logger.warning(f"Permission copy failed: {e}")

            if not self.quiet and self.verbose:
                console.debug(f"Created file: {path}")
        except Exception as e:
            logger.error(f"File creation failed: {e}")
            raise

    def create_directory(self, path: Path) -> None:
        if path.exists():
            if path.is_file():
                # File exists where directory is expected — must remove
                if not self._handle_action(path):
                    return
            elif path.is_dir():
                # Already exists as a directory — just keep it
                # Mark as created for tracking but don't log
                self._created_directories.add(str(path))
                return

        # Check dry_run before attempting creation
        if self.dry_run:
            if not self.quiet and self.verbose:
                # Only show directory creation once
                if str(path) not in self._created_directories:
                    console.debug(f"Created directory: {path}")
                    self._created_directories.add(str(path))
            return

        try:
            path.mkdir(parents=True, exist_ok=True)
            if not self.quiet and self.verbose:
                # Only show directory creation once
                if str(path) not in self._created_directories:
                    console.debug(f"Created directory: {path}")
                    self._created_directories.add(str(path))
        except Exception as e:
            logger.error(f"Directory creation failed: {e}")
            raise

    def remove_directory(self, path: Path) -> None:
        """Remove a directory and all its contents.

        Args:
            path: Directory path to remove

        Raises:
            Exception: If removal fails (unless dry_run is True)
        """
        if not path.exists():
            logger.debug(f"Directory does not exist, nothing to remove: {path}")
            return

        if not path.is_dir():
            logger.warning(f"Path is not a directory: {path}")
            return

        if self.dry_run:
            if not self.quiet:
                console.info(
                    f"[bright_white]Would remove directory:[/] [cyan]{path}[/]"
                )
            return

        try:
            shutil.rmtree(path)
            if not self.quiet:
                logger.debug(f"Removed directory: {path}")
            logger.debug(f"Successfully removed directory: {path}")
        except Exception as e:
            logger.error(f"Directory removal failed: {e}")
            raise
