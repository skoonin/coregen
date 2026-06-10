"""
Detect Changes service implementation - Generation-based approach.

This module provides functionality to identify which configuration elements
are affected by changes between branches by comparing generated output.

Component Sorting:
    The detect-changes command sorts component output to ensure consistent
    ordering and proper context grouping. Sorting MUST happen after all
    modifications to the results are complete:

    1. Comparison phase (_compare_outputs): Detects changes by comparing
       generated outputs but does NOT sort results

    2. Cascade phase (_apply_required_cascade): Appends additional components
       to result.changes when required components change

    3. Filter phase (_apply_filters_to_results): Removes components that don't
       match filter criteria

    4. Sort phase (in detect_changes): Applies final sorting to ensure:
       - Components grouped by (workspace, context) tuple
       - Within each context: sorted by priority (0, 1, 2, ..., None)
       - Dependencies always appear before dependents
       - All three arrays sorted: changes, deleted, required_changes

    WHY SORTING MUST BE LAST:
    If sorting happened before cascade/filters, components from the same
    context would appear in multiple places in the output:
    - Direct changes would appear first (sorted)
    - Cascade changes would be appended after (unsorted)
    - This breaks the context grouping that users expect

    The required_changes array contains components marked as required=true
    that have changes and triggered cascade changes. This array appears
    separately in JSON/YAML output and is also independently sorted.
"""

import copy
import subprocess
import tarfile
from pathlib import Path
from typing import Any

from git import Repo
from git.exc import BadName, GitCommandError, GitError, InvalidGitRepositoryError

from coregen.common.component_sorter_service import ComponentSorterService
from coregen.common.path_service import PathService
from coregen.services.detect_changes.models import (
    ChangeReason,
    ChangeStatus,
    ComponentChange,
    DetectChangesResult,
)
from coregen.services.generate.gen_generate_service import GenerateService
from coregen.services.services_base import ServicesBase

# Constants for validation
COMPONENT_KEY_PARTS = 3  # Expected format: "workspace/context/component"


class DetectChangesService(ServicesBase):
    """Service for detecting changes using generation-based comparison.

    This service uses a simplified git archive approach:
    1. Validates git repository and requirements
    2. Generates all components from current branch (with unstaged changes)
    3. Extracts base branch files using git archive to temp directory
    4. Generates all components from extracted base branch files
    5. Compares generated outputs to detect changes
    6. Applies required component cascade logic
    7. Cleans up temp directories
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the detect changes service.

        Args:
            **kwargs: Keyword arguments passed to ServicesBase
        """
        super().__init__(**kwargs)

        # Store kwargs for creating GenerateService instances
        self._gen_kwargs = kwargs.copy()

        # Extract config_file from global_options if present
        if "global_options" in kwargs and hasattr(
            kwargs["global_options"], "config_file"
        ):
            config_file = getattr(kwargs["global_options"], "config_file", None)
            if config_file:
                self._gen_kwargs["config_file"] = config_file

        # Ensure quiet mode for generate service operations
        if "global_options" in self._gen_kwargs:
            global_options = self._gen_kwargs["global_options"]
            if hasattr(global_options, "quiet"):
                modified_global_options = copy.copy(global_options)
                modified_global_options.quiet = True
                self._gen_kwargs["global_options"] = modified_global_options
        else:
            self._gen_kwargs["quiet"] = True

        # Initialize path service for consistent path operations
        self._path_service = PathService()

        # Store GenerateService instances for reuse
        self._current_generate_service: GenerateService | None = None
        self._base_generate_service: GenerateService | None = None

        # Define ignore patterns for files that should be skipped during comparison
        # These are common files that don't affect functionality and don't trigger deployments
        self._ignore_patterns = [
            ".DS_Store",
            ".gitkeep",
            "*.swp",
            "*.swo",
            "*~",
            ".#*",
            "#*#",
            "Thumbs.db",
            "desktop.ini",
            "*.md",
            "*.log",
        ]

        # Initialize git repository once (lazy loading)
        self._repo: Repo | None = None
        self._repo_root: Path | None = None

    def detect_changes(
        self,
        base_branch: str = "main",
        output_dir: Path | None = None,
        filters: list[str] | None = None,
        include_inactive: bool = False,
        keep_generated: bool = False,
        verbose: bool = False,
    ) -> DetectChangesResult:
        """Detect changes between current state and base branch.

        Args:
            base_branch: Base branch to compare against
            output_dir: Custom temp directory for generated files
            filters: Filter expressions to apply
            include_inactive: Include inactive components
            keep_generated: Don't delete generated files after comparison
            verbose: Show detailed progress

        Returns:
            DetectChangesResult with all detected changes

        Raises:
            ValueError: If git validation fails or repository state is invalid
            RuntimeError: If git operations fail
        """
        # Step 0: Validate git repository and requirements
        repo_root, actual_base_ref = self._validate_git_repository(base_branch, verbose)
        self.logger.debug(
            f"Git validation passed, repo root: {repo_root}, using ref: {actual_base_ref}"
        )

        # Use the actual resolved ref for all subsequent operations
        base_branch = actual_base_ref

        if verbose:
            self.logger.debug(
                f"Repository validation passed for base branch: {base_branch}"
            )

        # Set up temp directories
        if output_dir:
            temp_base = output_dir
            temp_current = temp_base / "current"
            temp_main = temp_base / "base"
            temp_extracted = temp_base / "base_extracted"
            self.logger.debug(f"Using custom output directory: {output_dir}")
        else:
            # Use timestamped directory in .cgtmp
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_base = repo_root / ".cgtmp" / f"detect-changes-{timestamp}"
            temp_base.mkdir(parents=True, exist_ok=True)
            temp_current = temp_base / "current"
            temp_main = temp_base / "base"
            temp_extracted = temp_base / "base_extracted"
            self.logger.debug(f"Created timestamped temp directory: {temp_base}")

        self.logger.debug(
            f"Temp directories: current={temp_current}, base={temp_main}, extracted={temp_extracted}"
        )

        if verbose:
            self.console.debug(f"Comparing {base_branch} (base) vs current branch")

        try:
            # Step 1: Generate from current branch (with unstaged changes)
            if verbose:
                self.logger.debug(
                    "Generating from current branch (includes unstaged changes)"
                )

            # Prepare kwargs for current branch generation
            current_gen_kwargs = self._gen_kwargs.copy()

            # If global_options is present, make a copy to avoid modifying the original
            if "global_options" in current_gen_kwargs:
                current_gen_kwargs["global_options"] = copy.copy(
                    current_gen_kwargs["global_options"]
                )

            # Handle config file resolution
            config_file_provided = current_gen_kwargs.get("config_file")

            if config_file_provided:
                # A config file was provided, check if it needs resolution
                config_path = Path(config_file_provided)
                if not config_path.is_absolute():
                    # It's a relative path - check if it exists in current directory
                    resolved_path = Path.cwd() / config_path
                    if not resolved_path.exists():
                        # The relative path doesn't exist in current dir, search for it
                        self.logger.debug(
                            f"Config file {config_path} not found at {resolved_path}, searching..."
                        )
                        found_config = self._find_config_file_for_current_branch(
                            Path.cwd(), repo_root
                        )
                        if found_config:
                            current_gen_kwargs["config_file"] = found_config
                            # Also update global_options if present
                            if "global_options" in current_gen_kwargs and hasattr(
                                current_gen_kwargs["global_options"], "config_file"
                            ):
                                current_gen_kwargs["global_options"].config_file = (
                                    found_config
                                )
                            self.logger.debug(
                                f"Found config file for current branch: {found_config}"
                            )
                        else:
                            # Try default location at repo root
                            default_config = repo_root / config_path.name
                            if default_config.exists():
                                current_gen_kwargs["config_file"] = default_config
                                # Also update global_options if present
                                if "global_options" in current_gen_kwargs and hasattr(
                                    current_gen_kwargs["global_options"], "config_file"
                                ):
                                    current_gen_kwargs["global_options"].config_file = (
                                        default_config
                                    )
                                self.logger.debug(
                                    f"Using config file from repo root: {default_config}"
                                )
                    else:
                        # The resolved path exists, use it
                        current_gen_kwargs["config_file"] = resolved_path
                        # Also update global_options if present
                        if "global_options" in current_gen_kwargs and hasattr(
                            current_gen_kwargs["global_options"], "config_file"
                        ):
                            current_gen_kwargs["global_options"].config_file = (
                                resolved_path
                            )
                        self.logger.debug(
                            f"Using resolved config file: {resolved_path}"
                        )
            else:
                # No config file specified at all, search for it
                config_file = self._find_config_file_for_current_branch(
                    Path.cwd(), repo_root
                )
                if config_file:
                    current_gen_kwargs["config_file"] = config_file
                    # Also update global_options if present
                    if "global_options" in current_gen_kwargs and hasattr(
                        current_gen_kwargs["global_options"], "config_file"
                    ):
                        current_gen_kwargs["global_options"].config_file = config_file
                    self.logger.debug(
                        f"Found config file for current branch: {config_file}"
                    )
                else:
                    # Try default location
                    default_config = repo_root / ".cgconfig.yaml"
                    if default_config.exists():
                        current_gen_kwargs["config_file"] = default_config
                        # Also update global_options if present
                        if "global_options" in current_gen_kwargs and hasattr(
                            current_gen_kwargs["global_options"], "config_file"
                        ):
                            current_gen_kwargs["global_options"].config_file = (
                                default_config
                            )
                        self.logger.debug(
                            f"Using default config file: {default_config}"
                        )

            # Create GenerateService for current branch
            # Ensure config_file is absolute if present
            if (
                "config_file" in current_gen_kwargs
                and current_gen_kwargs["config_file"]
            ):
                config_path = Path(current_gen_kwargs["config_file"])
                if not config_path.is_absolute():
                    current_gen_kwargs["config_file"] = config_path.resolve()

            self.logger.debug(
                f"Creating GenerateService with config_file: {current_gen_kwargs.get('config_file')}"
            )
            self._current_generate_service = GenerateService(**current_gen_kwargs)

            assert self._current_generate_service is not None  # Type guard for mypy
            # Generate WITHOUT filters to see all components (for accurate comparison)
            current_components = self._generate_and_scan(
                generate_service=self._current_generate_service,
                output_dir=temp_current,
                filters=None,  # Don't apply filters during generation
                include_inactive=include_inactive,
                verbose=verbose,
            )

            # Step 2: Extract base branch files using git archive
            if verbose:
                self.logger.debug(f"Extracting base branch files: {base_branch}")

            self._extract_base_branch(base_branch, temp_extracted, verbose)
            self.logger.debug(f"Base branch extracted to: {temp_extracted}")

            # Step 3: Generate from extracted base branch files
            if verbose:
                self.logger.debug("Generating from base branch files")

            # Create a new GenerateService instance for base branch with modified config path
            base_kwargs = self._gen_kwargs.copy()

            # Determine the config file path for the extracted base branch
            original_config_path = None
            extracted_config_path = None

            # Use the resolved config file from current branch if available
            if (
                "config_file" in current_gen_kwargs
                and current_gen_kwargs["config_file"]
            ):
                original_config_path = Path(current_gen_kwargs["config_file"])
            elif "config_file" in self._gen_kwargs:
                original_config_path = Path(self._gen_kwargs["config_file"])

            if original_config_path:
                # Check if the original path is absolute or relative
                if original_config_path.is_absolute():
                    # Get relative path from repo root
                    try:
                        rel_config_path = original_config_path.relative_to(repo_root)
                        extracted_config_path = temp_extracted / rel_config_path
                    except ValueError:
                        # If config_file is not under repo_root, that's an error
                        raise ValueError(
                            f"Config file {original_config_path} is not under repository root {repo_root}"
                        )
                else:
                    # For relative paths, we need to resolve them relative to the repo root
                    # NOT the current working directory
                    # First, resolve the path relative to the current working directory
                    resolved_path = Path.cwd() / original_config_path

                    # Now check if this resolved path exists
                    if resolved_path.exists():
                        # Get the path relative to repo root
                        try:
                            rel_config_path = resolved_path.relative_to(repo_root)
                            extracted_config_path = temp_extracted / rel_config_path
                        except ValueError:
                            # Config file is outside repo - that's an error
                            raise ValueError(
                                f"Config file {resolved_path} is not under repository root {repo_root}"
                            )
                    else:
                        # If the resolved path doesn't exist, try it as-is relative to repo root
                        # This handles cases where the path is already relative to repo root
                        extracted_config_path = temp_extracted / original_config_path

                if not extracted_config_path.exists():
                    raise ValueError(
                        f"Config file not found in extracted base branch at {extracted_config_path}"
                    )
            else:
                # Look for default config file - search up from current directory to repo root
                extracted_config_path = self._find_default_config_file(
                    Path.cwd(), repo_root, temp_extracted
                )
                if not extracted_config_path:
                    raise ValueError("No config file found for base branch generation")

            # Create a new ConfigurationProvider with the extracted directory as root
            from coregen.config_model.provider import ConfigurationProvider

            base_config_provider = ConfigurationProvider(
                root_path=temp_extracted,
                skip_validation=True,  # Skip validation for base branch
                dry_run=base_kwargs.get("dry_run", False),
                quiet=base_kwargs.get("quiet", True),
                verbose=base_kwargs.get("verbose", False),
            )

            # Load the config file for base branch
            base_config_provider.load_config(extracted_config_path)

            # Now create GenerateService with the base config provider
            base_kwargs["config_provider"] = base_config_provider
            # Remove config_file since we're providing a pre-loaded provider
            base_kwargs.pop("config_file", None)

            self._base_generate_service = GenerateService(**base_kwargs)

            assert self._base_generate_service is not None  # Type guard for mypy
            # Generate WITHOUT filters to see all components (for accurate comparison)
            base_components = self._generate_and_scan(
                generate_service=self._base_generate_service,
                output_dir=temp_main,
                filters=None,  # Don't apply filters during generation
                include_inactive=include_inactive,
                verbose=verbose,
            )

            # Step 4: Compare generated outputs
            self.logger.debug(
                f"Starting comparison: {len(current_components)} current vs {len(base_components)} base components"
            )
            if verbose:
                self.logger.debug(
                    f"Comparing outputs: {len(current_components)} current vs {len(base_components)} base components"
                )

            assert self._current_generate_service is not None  # Type guard for mypy
            result = self._compare_outputs(
                current_components,
                base_components,
                temp_current,
                temp_main,
                self._current_generate_service,
                verbose=verbose,
            )
            self.logger.debug(f"Initial comparison found {len(result.changes)} changes")

            # Step 5: Apply required component cascade logic
            if verbose:
                self.logger.debug("Applying required component cascade logic")
            assert self._current_generate_service is not None  # Type guard for mypy
            result = self._apply_required_cascade(
                result, current_components, self._current_generate_service
            )
            self.logger.debug(f"After cascade: {len(result.changes)} total changes")

            # Step 6: Apply filters to the results (after comparison and cascade)
            if filters:
                initial_count = len(result.changes)
                if verbose:
                    self.logger.debug(f"Applying filters to results: {filters}")
                    self.logger.debug(f"Components before filtering: {initial_count}")

                result = self._apply_filters_to_results(result, filters, verbose)
                final_count = len(result.changes)

                self.logger.debug(f"After filtering: {final_count} changes remain")
                if verbose and initial_count > final_count:
                    filtered_out = initial_count - final_count
                    self.logger.info(
                        f"Filtered out {filtered_out} components ({filtered_out}/{initial_count} = "
                        f"{filtered_out * 100 / initial_count:.1f}%)"
                    )

            # Step 7: Sort the changes list for consistent output ordering
            # CRITICAL: This must happen AFTER cascade and filters to ensure all components
            # are present before sorting. If sorting happened earlier:
            # - Cascade would append components AFTER sorting, breaking context grouping
            # - Components from the same context would appear in multiple places:
            #   * Direct changes (sorted) would appear first
            #   * Cascade changes (unsorted) would be appended after
            # - This would violate the user expectation that components are grouped by context
            #
            # We sort THREE arrays to maintain consistency across all output formats:
            # 1. changes: All changed/deleted components (main output)
            # 2. deleted: Subset of changes with status=deleted (for --deleted-only)
            # 3. required_changes: Components that triggered cascade (appears in JSON/YAML)
            if result.changes:
                self.logger.debug(
                    "Sorting detected changes for consistent output ordering"
                )
                sorter = ComponentSorterService()

                # Sort the main changes array
                result.changes = sorter.sort_entities(
                    result.changes, entity_type="component"
                )

                # Also sort the deleted list since it's a subset of changes
                # This ensures --deleted-only flag produces sorted output
                if result.deleted:
                    result.deleted = sorter.sort_entities(
                        result.deleted, entity_type="component"
                    )

                # Also sort the required_changes list for consistent output in JSON/YAML
                # This array appears separately in structured output formats and should be
                # sorted independently since it contains a different subset of components
                if result.required_changes:
                    result.required_changes = sorter.sort_entities(
                        result.required_changes, entity_type="component"
                    )

            # Calculate statistics
            result = self._calculate_statistics(result)
            if verbose:
                self.console.debug(
                    f"Final result: {result.total_changed} changed, {result.total_deleted} deleted"
                )

            return result

        finally:
            # Clean up temp directories unless keep_generated is True
            if not keep_generated and output_dir is None:
                try:
                    # temp_base might not be defined if we fail early
                    if "temp_base" in locals() and temp_base.exists():
                        self.file_manager.remove_directory(temp_base)
                        self.logger.debug(f"Cleaned up temp directory: {temp_base}")

                    # If .cgtmp is now empty, remove it too
                    if "repo_root" in locals():
                        cgtmp_dir = repo_root / ".cgtmp"
                        if cgtmp_dir.exists() and not any(cgtmp_dir.iterdir()):
                            cgtmp_dir.rmdir()
                            self.logger.debug("Removed empty .cgtmp directory")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temp directory: {e}")

    def _safe_extract(self, tar: tarfile.TarFile, path: Path) -> None:
        """Safely extract tar members, preventing path traversal attacks.

        Args:
            tar: TarFile object to extract from
            path: Destination path

        Raises:
            RuntimeError: If unsafe paths are detected
        """
        base = path.resolve()

        # For streaming tar, we need to extract each member individually
        for member in tar:
            member_path = (path / member.name).resolve()
            if not str(member_path).startswith(str(base)):
                raise RuntimeError(f"Unsafe path in archive: {member.name}")
            tar.extract(member, path)

    def _find_config_file_for_current_branch(
        self, current_dir: Path, repo_root: Path
    ) -> Path | None:
        """Find the config file for the current branch by searching up from current directory.

        Args:
            current_dir: Current working directory
            repo_root: Repository root directory

        Returns:
            Path to config file, or None if not found
        """
        # Default config file name
        config_filename = ".cgconfig.yaml"

        # Start from current directory and search up to repo root
        search_dir = current_dir
        while True:
            # Check if config file exists at this level
            config_path = search_dir / config_filename
            if config_path.exists():
                self.logger.debug(f"Found config file at: {config_path}")
                return config_path

            # Move up one directory
            parent = search_dir.parent
            if parent == search_dir or not str(search_dir).startswith(str(repo_root)):
                # Reached root or went outside repo
                break
            search_dir = parent

        return None

    def _find_default_config_file(
        self, current_dir: Path, repo_root: Path, temp_extracted: Path
    ) -> Path | None:
        """Find the default config file by searching up from current directory.

        Args:
            current_dir: Current working directory
            repo_root: Repository root directory
            temp_extracted: Extracted base branch directory

        Returns:
            Path to config file in extracted directory, or None if not found
        """
        # Default config file name
        config_filename = ".cgconfig.yaml"

        # Start from current directory and search up to repo root
        search_dir = current_dir
        while True:
            # Check if config file exists at this level
            config_path = search_dir / config_filename
            if config_path.exists():
                # Found config file, get the relative path from repo root
                try:
                    rel_config_path = config_path.relative_to(repo_root)
                    extracted_config_path = temp_extracted / rel_config_path
                    if extracted_config_path.exists():
                        self.logger.debug(
                            f"Found config file at {config_path}, using {extracted_config_path} for base branch"
                        )
                        return extracted_config_path
                except ValueError as e:
                    # Config is outside repo, skip it
                    self.logger.debug(
                        f"Skipping config outside repo at {config_path}: {e}"
                    )

            # Move up one directory
            parent = search_dir.parent
            if parent == search_dir or not str(search_dir).startswith(str(repo_root)):
                # Reached root or went outside repo
                break
            search_dir = parent

        # If we didn't find it by searching up, try the default location at repo root
        default_path = repo_root / config_filename
        if default_path.exists():
            extracted_config_path = temp_extracted / config_filename
            if extracted_config_path.exists():
                self.logger.debug(
                    f"Using default config file from repo root: {extracted_config_path}"
                )
                return extracted_config_path

        return None

    def _extract_base_branch(
        self, base_branch: str, output_dir: Path, verbose: bool = False
    ) -> None:
        """Extract base branch files using git archive.

        Args:
            base_branch: Base branch to extract
            output_dir: Directory to extract files to
            verbose: Show detailed progress

        Raises:
            RuntimeError: If extraction fails
        """
        if verbose:
            self.logger.debug(
                f"Extracting files from ref '{base_branch}' to {output_dir}"
            )

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Use cached repository instance
            repo = self._get_repo()

            # Stream git archive directly to tar extraction (no temp file)
            proc = subprocess.Popen(
                ["git", "archive", base_branch],
                cwd=repo.working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                # Open tar stream and safely extract
                # Note: mode="r|" for streaming tar without seeking
                with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
                    self._safe_extract(tar, output_dir)

                # Wait for git archive to complete and check return code
                stderr = proc.stderr.read() if proc.stderr else b""
                rc = proc.wait()

                if rc != 0:
                    error_msg = (
                        stderr.decode("utf-8", errors="replace")
                        if stderr
                        else "Unknown error"
                    )
                    raise RuntimeError(
                        f"git archive failed with exit code {rc}: {error_msg}"
                    )

                if stderr and verbose:
                    self.logger.debug(
                        f"Git archive stderr: {stderr.decode('utf-8', errors='replace')}"
                    )

                self.logger.debug(
                    f"Successfully extracted {base_branch} to {output_dir}"
                )

            except Exception:
                # Kill the process if it's still running
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                raise

        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to extract base branch: {e}")
            raise RuntimeError(
                f"Failed to extract files from ref '{base_branch}': {e}"
            ) from e
        except Exception as e:
            self.logger.error(f"Failed to extract base branch: {e}")
            raise RuntimeError(
                f"Failed to extract files from ref '{base_branch}': {e}"
            ) from e

    def _generate_and_scan(
        self,
        generate_service: GenerateService,
        output_dir: Path,
        filters: list[str] | None = None,
        include_inactive: bool = False,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """Generate all components and scan the output directory.

        Args:
            generate_service: GenerateService instance to use
            output_dir: Directory to generate files to
            filters: Filter expressions to apply
            include_inactive: Include inactive components
            verbose: Show detailed progress

        Returns:
            Dictionary of generated components with metadata
        """
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate all components using the correct pattern
        # Use "cm/*" to generate all components
        paths = ["cm/*"]

        generate_service.generate_files(
            paths=paths,
            filters=filters,
            include_inactive=include_inactive,
            output_dir=output_dir,
            skip_commit_dir=True,  # Don't use context's commit_dir
        )

        # Extract component metadata from generation result
        # Since the actual result structure doesn't include component organization,
        # we need to scan the output directory to find what was generated
        components = {}

        # Scan the output directory for generated components
        # Structure should be: output_dir/context/component/...
        self.logger.debug(
            f"Scanning output_dir: {output_dir}, exists: {output_dir.exists()}, include_inactive: {include_inactive}"
        )
        if output_dir.exists():
            for context_dir in output_dir.iterdir():
                if context_dir.is_dir():
                    context_name = context_dir.name
                    for component_dir in context_dir.iterdir():
                        if component_dir.is_dir():
                            component_name = component_dir.name

                            # Get workspace from context directly
                            workspace = self._get_workspace_for_context(
                                context_name, generate_service
                            )

                            key = f"{workspace}/{context_name}/{component_name}"

                            # Get the list of files generated for this component
                            files = []
                            for file_path in component_dir.rglob("*"):
                                if file_path.is_file():
                                    rel_path = file_path.relative_to(output_dir)
                                    files.append(str(rel_path))

                            # Get component metadata from config - let errors propagate
                            component = generate_service.config_access.get_component(
                                workspace, context_name, component_name
                            )
                            # Use the resolved component path from config, not the temp generation path
                            component_path = (
                                str(component.resolved_paths.get("component_path"))
                                if hasattr(component, "resolved_paths")
                                and component.resolved_paths
                                and component.resolved_paths.get("component_path")
                                else str(component_dir)
                            )
                            metadata = {
                                "active": component.config.active,
                                "required": component.config.required,
                                "priority": component.config.priority,
                                "dependencies": [
                                    d.get("name") for d in component.get_dependencies()
                                ],
                                "path": component_path,
                                "environment": getattr(component, "environment", None),
                            }

                            components[key] = {
                                "workspace": workspace,
                                "context": context_name,
                                "component": component_name,
                                "files": files,
                                "metadata": metadata,
                            }
                            self.logger.debug(
                                f"Added component {key} with {len(files)} files"
                            )

        self.logger.debug(f"Total components found: {len(components)}")
        if verbose:
            self.logger.debug(f"Generated {len(components)} components")
            # Show first few components for debugging
            if components:
                comp_names = list(components.keys())[:3]
                self.logger.debug(f"Sample components: {comp_names}")

        return components

    def _get_workspace_for_context(
        self, context_name: str, generate_service: GenerateService
    ) -> str:
        """Get workspace name for a context.

        Args:
            context_name: Context name
            generate_service: GenerateService instance

        Returns:
            Workspace name
        """
        try:
            # Iterate through workspaces (it's an attribute, not a method)
            for workspace in generate_service.config_access.workspaces:
                try:
                    context = generate_service.config_access.get_context(
                        workspace.name, context_name
                    )
                    # Context model has a workspace field
                    if context.workspace:
                        return context.workspace
                    # Fallback to the workspace we found it in
                    return workspace.name
                except (ValueError, KeyError):
                    continue

            # If not found, raise an error instead of returning "unknown"
            raise ValueError(f"Context {context_name} not found in any workspace")
        except Exception as e:
            self.logger.error(
                f"Could not determine workspace for context {context_name}: {e}"
            )
            raise

    def _compare_outputs(
        self,
        current_components: dict[str, Any],
        base_components: dict[str, Any],
        current_dir: Path,
        base_dir: Path,
        generate_service: GenerateService,
        verbose: bool = False,
    ) -> DetectChangesResult:
        """Compare generated outputs to detect changes.

        This method performs the initial comparison but does NOT sort results.
        Sorting must happen later in detect_changes() after cascade and filters
        are applied to ensure proper context grouping.

        Args:
            current_components: Components from current branch
            base_components: Components from base branch
            current_dir: Directory with current branch output
            base_dir: Directory with base branch output
            generate_service: GenerateService for getting context metadata
            verbose: Show detailed progress

        Returns:
            DetectChangesResult with detected changes (unsorted)
        """
        result = DetectChangesResult()
        all_components = set(current_components.keys()) | set(base_components.keys())

        # Counter for actually analyzed components (excluding invalid component keys)
        analyzed_count = 0

        for component_key in all_components:
            parts = component_key.split("/")
            if len(parts) != COMPONENT_KEY_PARTS:
                continue

            # Count this component as analyzed since it passed validation
            analyzed_count += 1

            workspace, context, component = parts

            # Check if component exists in both branches
            in_current = component_key in current_components
            in_base = component_key in base_components

            # Get context config file path
            context_config_path = self._get_context_config_file_path(
                workspace, context, generate_service
            )

            if not in_base and in_current:
                # New component (treated as changed)
                change = self._create_component_change(
                    workspace,
                    context,
                    component,
                    status=ChangeStatus.CHANGED,
                    reason=ChangeReason.DIRECT,
                    metadata=current_components[component_key].get("metadata", {}),
                    context_config_file_path=context_config_path,
                )
                result.changes.append(change)

            elif in_base and not in_current:
                # Deleted component - use metadata from base to set active to false
                metadata = base_components[component_key].get("metadata", {})
                # Mark as inactive for deleted components
                metadata["active"] = False
                change = self._create_component_change(
                    workspace,
                    context,
                    component,
                    status=ChangeStatus.DELETED,
                    reason=ChangeReason.DELETED,
                    metadata=metadata,
                    context_config_file_path=context_config_path,
                )
                result.changes.append(change)
                result.deleted.append(change)

            elif in_base and in_current:
                # Component exists in both - compare content
                if self._has_content_changed(
                    component_key,
                    current_components[component_key],
                    base_components[component_key],
                    current_dir,
                    base_dir,
                ):
                    change = self._create_component_change(
                        workspace,
                        context,
                        component,
                        status=ChangeStatus.CHANGED,
                        reason=ChangeReason.DIRECT,
                        metadata=current_components[component_key].get("metadata", {}),
                        context_config_file_path=context_config_path,
                    )
                    result.changes.append(change)

        if verbose:
            self.console.debug(f"Found {len(result.changes)} changed components")

        # Set the total analyzed count for statistics
        result.total_analyzed = analyzed_count

        # NOTE: Sorting moved to detect_changes() method to happen AFTER
        # required_cascade and filters are applied. This ensures components
        # from the same context stay grouped together in the output.

        return result

    def _get_context_config_file_path(
        self, workspace: str, context_name: str, generate_service: GenerateService
    ) -> Path | None:
        """Get the config file path for a context.

        Args:
            workspace: Workspace name
            context_name: Context name
            generate_service: GenerateService instance

        Returns:
            Path to context config file, or None if not found
        """
        try:
            context = generate_service.config_access.get_context(
                workspace, context_name
            )
            # Use getattr inline as suggested
            config_path = getattr(context, "config_file_path", None)
            return Path(config_path) if config_path else None
        except Exception as e:
            self.logger.debug(
                f"Could not get config file path for context {workspace}/{context_name}: {e}"
            )
        return None

    def _is_binary(self, path: Path) -> bool:
        """Check if a file appears to be binary.

        Args:
            path: Path to file to check

        Returns:
            True if file appears to be binary
        """
        try:
            with open(path, "rb") as f:
                chunk = f.read(4096)
                return b"\0" in chunk
        except Exception:
            return False

    def _has_content_changed(
        self,
        component_key: str,
        current_comp: dict[str, Any],
        base_comp: dict[str, Any],
        current_dir: Path,
        base_dir: Path,
    ) -> bool:
        """Check if component content has changed.

        Compares generated files ignoring whitespace and comments.
        Skips files that match ignore patterns.

        Args:
            component_key: Component identifier
            current_comp: Current component info
            base_comp: Base component info
            current_dir: Current output directory
            base_dir: Base output directory

        Returns:
            True if content has changed
        """
        # First check if metadata has changed (especially active status)
        current_metadata = current_comp.get("metadata", {})
        base_metadata = base_comp.get("metadata", {})

        self.logger.debug(
            f"Comparing metadata for {component_key}: current.active={current_metadata.get('active', True)}, base.active={base_metadata.get('active', True)}"
        )
        # Check if active status changed - this is a significant change
        if current_metadata.get("active", True) != base_metadata.get("active", True):
            self.logger.debug(
                f"Component {component_key} active status changed: "
                f"base={base_metadata.get('active', True)} -> current={current_metadata.get('active', True)}"
            )
            return True

        # Get list of all files from both versions
        current_files = set(current_comp.get("files", []))
        base_files = set(base_comp.get("files", []))

        # Filter out ignored files
        current_files = self._filter_ignored_files(current_files)
        base_files = self._filter_ignored_files(base_files)

        # If file lists differ, content has changed
        if current_files != base_files:
            return True

        # Compare each file's content
        for file_path in current_files:
            current_file = current_dir / file_path
            base_file = base_dir / file_path

            # If either file doesn't exist, consider it changed
            if not current_file.exists() or not base_file.exists():
                return True

            # Compare file contents (ignoring whitespace and comments)
            if self._compare_file_content(current_file, base_file):
                return True

        return False

    def _compare_file_content(self, file1: Path, file2: Path) -> bool:
        """Compare two files ignoring whitespace and comments.

        Comment syntaxes handled:
        - Python/Hash (#)
        - C/C++ (// and /* */)
        - Shell (## and #)
        - HTML/XML (<!-- -->)

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            True if files are different (content has changed)
        """
        try:
            # Check if files are binary
            if self._is_binary(file1) or self._is_binary(file2):
                # For binary files, compare bytes directly
                return file1.read_bytes() != file2.read_bytes()

            # For text files, normalize and compare (pass file path for type detection)
            content1 = self._normalize_content(file1.read_text(), file1)
            content2 = self._normalize_content(file2.read_text(), file2)
            return content1 != content2
        except Exception as e:
            self.logger.warning(f"Error comparing files {file1} and {file2}: {e}")
            # If we can't compare, assume they're different
            return True

    def _normalize_content(self, content: str, file_path: Path | None = None) -> str:
        """Normalize content for comparison.

        For JSON/YAML files, parses and re-serializes to eliminate formatting differences.
        For other files, removes comments and normalizes whitespace.

        Args:
            content: File content to normalize
            file_path: Optional file path to determine file type

        Returns:
            Normalized content
        """
        # If we have a file path, check for JSON/YAML and handle specially
        if file_path:
            suffix = file_path.suffix.lower()

            # Handle JSON files - parse and re-serialize with sorted keys
            if suffix == ".json":
                try:
                    import json

                    data = json.loads(content)
                    # Re-serialize with sorted keys and consistent formatting
                    return json.dumps(data, sort_keys=True, indent=2)
                except (json.JSONDecodeError, ValueError):
                    # If parsing fails, fall through to normal processing
                    self.logger.debug(
                        f"Failed to parse {file_path} as JSON, using text normalization"
                    )

            # Handle YAML files - parse and re-serialize canonically
            elif suffix in [".yaml", ".yml"]:
                try:
                    import yaml

                    data = yaml.safe_load(content)
                    # Re-serialize with consistent formatting
                    return yaml.dump(data, default_flow_style=False, sort_keys=True)
                except yaml.YAMLError:
                    # If parsing fails, fall through to normal processing
                    self.logger.debug(
                        f"Failed to parse {file_path} as YAML, using text normalization"
                    )

        # Standard text normalization for non-JSON/YAML files or if parsing failed
        lines = []
        in_multiline_comment = False

        for line in content.splitlines():
            # Strip trailing whitespace but preserve indentation for now
            line = line.rstrip()

            # Skip empty lines
            if not line or line.isspace():
                continue

            # Handle C-style multi-line comments more carefully
            if in_multiline_comment:
                # Check if comment ends on this line
                if "*/" in line:
                    in_multiline_comment = False
                    # Keep the part after the comment ends
                    _, _, after = line.partition("*/")
                    line = after.strip()
                    if not line:
                        continue
                else:
                    # Still in multiline comment, skip entire line
                    continue

            # Check for multiline comment start
            if "/*" in line:
                # Handle single-line /* ... */ comments
                if "*/" in line:
                    # Remove just the comment part, keep rest of line
                    before, _, rest = line.partition("/*")
                    _, _, after = rest.partition("*/")
                    line = before + after
                    line = line.strip()
                    if not line:
                        continue
                else:
                    # Comment continues to next line
                    in_multiline_comment = True
                    # Keep the part before the comment
                    before, _, _ = line.partition("/*")
                    line = before.strip()
                    if not line:
                        continue

            # Strip inline comments for YAML files (but not inside quoted strings)
            # This handles comments like "key: value # comment"
            if file_path and file_path.suffix.lower() in [".yaml", ".yml"]:
                # Simple approach: if line contains # not inside quotes, remove from # onward
                if "#" in line:
                    # Check if # is inside quotes (simple check)
                    in_single_quote = False
                    in_double_quote = False
                    for i, char in enumerate(line):
                        if char == "'" and (i == 0 or line[i - 1] != "\\"):
                            in_single_quote = not in_single_quote
                        elif char == '"' and (i == 0 or line[i - 1] != "\\"):
                            in_double_quote = not in_double_quote
                        elif (
                            char == "#" and not in_single_quote and not in_double_quote
                        ):
                            # Found a comment outside quotes
                            line = line[:i].rstrip()
                            break

            # Handle line-starting comments
            line_stripped = line.lstrip()
            if line_stripped.startswith("#") or line_stripped.startswith("//"):
                continue

            # HTML/XML comments (simple handling)
            if line_stripped.startswith("<!--") and line_stripped.endswith("-->"):
                continue

            # Normalize remaining whitespace
            line = " ".join(line.split())

            # Add normalized line
            if line:
                lines.append(line)

        return "\n".join(lines)

    def _filter_ignored_files(self, file_paths: set[str]) -> set[str]:
        """Filter out files that match ignore patterns.

        Args:
            file_paths: Set of file paths to filter

        Returns:
            Filtered set of file paths with ignored files removed
        """
        import fnmatch

        filtered = set()
        for file_path in file_paths:
            file_name = Path(file_path).name

            # Check if file matches any ignore pattern
            should_ignore = False
            for pattern in self._ignore_patterns:
                if fnmatch.fnmatch(file_name, pattern):
                    should_ignore = True
                    self.logger.debug(
                        f"Ignoring file {file_path} (matches pattern {pattern})"
                    )
                    break

            if not should_ignore:
                filtered.add(file_path)

        return filtered

    def _create_component_change(
        self,
        workspace: str,
        context: str,
        component: str,
        status: ChangeStatus,
        reason: ChangeReason,
        metadata: dict[str, Any],
        context_config_file_path: Path | None = None,
    ) -> ComponentChange:
        """Create a ComponentChange object.

        Args:
            workspace: Workspace name
            context: Context name
            component: Component name
            status: Change status
            reason: Change reason
            metadata: Component metadata
            context_config_file_path: Path to context configuration file

        Returns:
            ComponentChange object
        """
        # Build the command
        command = None
        if status != ChangeStatus.DELETED:
            command = (
                f"cm/{component} --filter workspace.name={workspace} "
                f"--filter context.name={context}"
            )

        # For deleted components, ensure active is False
        component_active = (
            False if status == ChangeStatus.DELETED else metadata.get("active", True)
        )

        return ComponentChange(
            component_name=component,
            context_name=context,
            workspace_name=workspace,
            environment=metadata.get("environment"),
            status=status,
            reason=reason,
            component_active=component_active,
            component_required=metadata.get("required", False),
            component_priority=metadata.get("priority"),
            component_dependencies=metadata.get("dependencies", []),
            component_path=Path(metadata["path"]) if metadata.get("path") else None,
            context_config_file_path=context_config_file_path,
            command=command,
        )

    def _apply_required_cascade(
        self,
        result: DetectChangesResult,
        current_components: dict[str, Any],
        generate_service: GenerateService,
    ) -> DetectChangesResult:
        """Apply required component cascade logic.

        When a required component changes, all components in the same context
        are marked as changed with reason "required_cascade".

        Args:
            result: Initial detection result
            current_components: Current branch components
            generate_service: GenerateService instance for config access

        Returns:
            Updated result with cascade applied
        """
        # Find all required components that changed
        required_changes = [
            c
            for c in result.changes
            if c.component_required and c.status == ChangeStatus.CHANGED
        ]

        # Track which contexts have required changes
        affected_contexts = set()
        for change in required_changes:
            affected_contexts.add((change.workspace_name, change.context_name))
            result.required_changes.append(change)

        # Find all components in affected contexts
        for component_key, comp_info in current_components.items():
            parts = component_key.split("/")
            if len(parts) != COMPONENT_KEY_PARTS:
                continue

            workspace, context, component = parts

            # Check if this context has a required change
            if (workspace, context) in affected_contexts:
                # Check if this component is already in the changes
                already_changed = any(
                    c.workspace_name == workspace
                    and c.context_name == context
                    and c.component_name == component
                    for c in result.changes
                )

                if not already_changed:
                    # Add as cascade change
                    context_config_path = self._get_context_config_file_path(
                        workspace, context, generate_service
                    )
                    change = self._create_component_change(
                        workspace,
                        context,
                        component,
                        status=ChangeStatus.CHANGED,
                        reason=ChangeReason.REQUIRED_CASCADE,
                        metadata=comp_info.get("metadata", {}),
                        context_config_file_path=context_config_path,
                    )
                    result.changes.append(change)

        return result

    def _apply_filters_to_results(
        self, result: DetectChangesResult, filters: list[str], verbose: bool = False
    ) -> DetectChangesResult:
        """Apply filters to the detect-changes results using dynamic field access.

        This method applies filters AFTER change detection and cascade logic,
        using the same FilterService.apply_filters_complete() method that
        get/generate commands use. This ensures consistent filtering behavior
        and automatic support for all fields including custom fields.

        Args:
            result: DetectChangesResult to filter
            filters: List of filter expressions to apply
            verbose: Show detailed progress

        Returns:
            Filtered DetectChangesResult

        Raises:
            ValueError: If filter expression parsing fails
        """
        if not filters:
            return result

        # Get the complete model from config_access
        complete_model = self.config_access.get_complete_model()

        # Create a working copy to avoid modifying the original
        working_model = {
            "workspaces": complete_model.get("workspaces", {}).copy(),
            "contexts": complete_model.get("contexts", {}).copy(),
            "components": complete_model.get("components", {}).copy(),
        }

        # Temporarily add deleted components to the model for filtering
        # This allows filters to work on deleted components using their metadata
        from coregen.config_model.models.components import Component, ComponentConfig

        for change in result.changes:
            if change.status == ChangeStatus.DELETED:
                # Create a temporary Component object from ComponentChange metadata
                # Use context/component as key since context names are unique
                comp_key = f"{change.context_name}/{change.component_name}"

                # Only add if not already in the model (shouldn't happen but be safe)
                if comp_key not in working_model["components"]:
                    # Create a ComponentConfig with available metadata
                    config = ComponentConfig(
                        active=change.component_active,
                        required=change.component_required,
                        priority=change.component_priority,
                        dependencies=[],  # Empty list for deleted components
                        for_commit=False,  # Default value
                        path=None,  # Default value
                    )

                    # Create a minimal Component object with the config
                    temp_component = Component(
                        name=change.component_name, config=config
                    )
                    # Add workspace reference (Component objects have this)
                    temp_component.workspace = change.workspace_name
                    # Add context reference
                    temp_component.context = change.context_name
                    # Add environment if available
                    temp_component.environment = change.environment

                    working_model["components"][comp_key] = temp_component

        # Parse filter expressions using the inherited filter service
        parsed_filters = []
        for filter_expr in filters:
            try:
                parsed_filters.append(
                    self.filter_service.parse_filter_expression(filter_expr)
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to parse filter expression '{filter_expr}': {e}"
                )
                raise ValueError(f"Invalid filter expression: {filter_expr}") from e

        # Apply filters using FilterService.apply_filters_complete()
        # This handles all field access dynamically including custom fields
        filtered_model = self.filter_service.apply_filters_complete(
            working_model, parsed_filters
        )

        # Build set of component keys that passed the filter
        # Keys are in "context/component" format
        filtered_component_keys = set(filtered_model.get("components", {}).keys())

        if verbose:
            self.logger.debug(
                f"Components that passed filters: {len(filtered_component_keys)} "
                f"out of {len(working_model['components'])}"
            )

        # Filter the changes list to only include components that passed
        filtered_changes = []
        filtered_deleted = []

        for change in result.changes:
            # Build the key for this change (context/component format)
            change_key = f"{change.context_name}/{change.component_name}"

            # Check if this component passed the filters
            if change_key in filtered_component_keys:
                filtered_changes.append(change)
                if change.status == ChangeStatus.DELETED:
                    filtered_deleted.append(change)
            elif verbose:
                self.logger.debug(
                    f"Filtered out: {change.workspace_name}/{change.context_name}/"
                    f"{change.component_name} (status={change.status.value})"
                )

        # Update result with filtered lists
        result.changes = filtered_changes
        result.deleted = filtered_deleted

        # Update required_changes list if it exists
        if hasattr(result, "required_changes"):
            result.required_changes = [
                c for c in result.required_changes if c in filtered_changes
            ]

        return result

    def _calculate_statistics(self, result: DetectChangesResult) -> DetectChangesResult:
        """Calculate statistics for the result.

        Args:
            result: Detection result

        Returns:
            Result with statistics calculated
        """
        # Count unique contexts and workspaces
        contexts = set()
        workspaces = set()

        for change in result.changes:
            contexts.add((change.workspace_name, change.context_name))
            workspaces.add(change.workspace_name)

        result.total_changed = len(
            [c for c in result.changes if c.status == ChangeStatus.CHANGED]
        )
        result.total_deleted = len(result.deleted)
        result.total_contexts_affected = len(contexts)
        result.total_workspaces_affected = len(workspaces)

        # Calculate total_unchanged from total_analyzed (set in _compare_outputs)
        # total_unchanged = total_analyzed - (changed + deleted)
        if result.total_analyzed > 0:
            result.total_unchanged = result.total_analyzed - (
                result.total_changed + result.total_deleted
            )
        else:
            result.total_unchanged = 0

        return result

    def _validate_git_repository(
        self, base_branch: str, verbose: bool = False
    ) -> tuple[Path, str]:
        """Validate git repository state and requirements.

        Args:
            base_branch: Base branch to validate
            verbose: Show detailed progress

        Returns:
            Tuple of (repository root path, actual base ref to use)

        Raises:
            ValueError: If validation fails
        """
        # Check if we're in a git repository
        repo = self._get_repo()
        if not repo:
            raise ValueError(
                "Not in a git repository. The detect-changes command must be run from within a git repository."
            )

        repo_root = Path(repo.working_dir)

        # Note: git archive has been available since git 1.4.3, so no version check needed
        # It's much more widely available than worktree (which requires 2.5+)

        # Validate base ref exists and is accessible
        actual_base_ref = base_branch
        if not self._ref_exists(base_branch):
            # Try origin/main as fallback if main doesn't exist
            if base_branch == "main" and self._ref_exists("origin/main"):
                actual_base_ref = "origin/main"
                self.logger.info(
                    f"Using '{actual_base_ref}' as base branch since 'main' doesn't exist locally"
                )
            else:
                raise ValueError(
                    f"Base ref '{base_branch}' does not exist or is not accessible."
                )

        # Check repository health
        if not self._check_repo_health():
            raise ValueError("Repository appears to be corrupted or inaccessible.")

        self.logger.debug(
            f"Git repository validation successful: repo_root={repo_root}, base_branch={actual_base_ref}"
        )

        return repo_root, actual_base_ref

    def _get_repo(self) -> Repo | None:
        """Get or create the git repository instance.

        This method implements lazy loading and caching of the repository object
        to avoid multiple lookups.

        Returns:
            Repo instance, or None if not in a git repository
        """
        if self._repo is None:
            try:
                self._repo = Repo(search_parent_directories=True)
                self._repo_root = Path(self._repo.working_dir)
            except InvalidGitRepositoryError:
                return None
            except GitError:
                return None
        return self._repo

    def _get_git_repo_root(self) -> Path | None:
        """Get the git repository root directory.

        This method uses the cached repository instance.

        Returns:
            Path to repository root, or None if not in a git repository
        """
        repo = self._get_repo()
        if repo:
            return Path(repo.working_dir)
        return None

    def _is_safe_git_ref(self, ref: str) -> bool:
        """Validate that a git ref is safe from injection attacks.

        Args:
            ref: Git ref to validate

        Returns:
            True if the ref appears safe
        """
        if not ref:
            return False

        # Check for dangerous patterns that could lead to command injection
        dangerous_patterns = [
            "..",  # Path traversal
            ";",  # Command separator
            "|",  # Pipe
            "&",  # Background/command chaining
            "`",  # Command substitution
            "$(",  # Command substitution
            "$((",  # Arithmetic substitution
            ">",  # Redirect output
            "<",  # Redirect input
            "\\",  # Escape character
            "\n",  # Newline
            "\r",  # Carriage return
            "\0",  # Null byte
            "--",  # Could be interpreted as option (except for legitimate use)
        ]

        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in ref:
                self.logger.warning(f"Unsafe git ref rejected: contains '{pattern}'")
                return False

        # Check if ref starts with dash (could be interpreted as option)
        if ref.startswith("-"):
            self.logger.warning("Unsafe git ref rejected: starts with '-'")
            return False

        # Additional check: ref should not contain control characters
        if any(ord(c) < 32 for c in ref):
            self.logger.warning("Unsafe git ref rejected: contains control characters")
            return False

        return True

    def _ref_exists(self, ref: str) -> bool:
        """Check if a git ref exists and is accessible.

        This handles local branches, remote branches (origin/main), tags, and SHAs.

        Args:
            ref: Git ref to check (branch, tag, SHA, etc.)

        Returns:
            True if ref exists and is accessible
        """
        try:
            # Validate ref name for security
            if not self._is_safe_git_ref(ref):
                return False

            repo = self._get_repo()
            if not repo:
                return False
            # This will raise if ref doesn't resolve
            _ = repo.commit(ref)
            return True
        except (BadName, ValueError):
            # Ref simply doesn't exist - expected
            return False
        except GitCommandError as e:
            self.logger.error(f"Git command failed checking ref '{ref}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error checking ref '{ref}': {e}")
            raise

    def _check_repo_health(self) -> bool:
        """Check basic repository health.

        Returns:
            True if repository appears healthy
        """
        try:
            repo = self._get_repo()
            if not repo:
                return False

            # Check if we can access the git directory
            _ = repo.git_dir

            # Check if we can read HEAD
            _ = repo.head.commit

            return True
        except (GitError, AttributeError):
            return False
