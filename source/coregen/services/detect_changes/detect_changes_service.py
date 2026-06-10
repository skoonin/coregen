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
from pathlib import Path
from typing import Any

from coregen.common.component_sorter_service import ComponentSorterService
from coregen.services.detect_changes import content_diff
from coregen.services.detect_changes.git_tree_extractor import GitTreeExtractor
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
        # One extractor owns the cached Repo for both validation and extraction;
        # closed in the finally block to release git file handles/subprocesses.
        git_extractor = GitTreeExtractor(self.logger)

        # Step 0: Validate git repository and requirements
        repo_root, actual_base_ref = git_extractor.validate(base_branch)
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

            # Prepare kwargs for current branch generation. Isolate global_options
            # once so no derived dict mutates the caller's object.
            current_gen_kwargs = self._gen_kwargs.copy()
            if "global_options" in current_gen_kwargs:
                current_gen_kwargs["global_options"] = copy.copy(
                    current_gen_kwargs["global_options"]
                )

            # Resolve the config file ONCE for the live tree as an absolute path.
            # The base-branch path is later derived from this by re-rooting under
            # the extracted directory.
            resolved_config = self._resolve_live_config_path(
                current_gen_kwargs.get("config_file"), repo_root
            )
            if resolved_config is not None:
                current_gen_kwargs["config_file"] = resolved_config
                global_options = current_gen_kwargs.get("global_options")
                if global_options is not None and hasattr(
                    global_options, "config_file"
                ):
                    global_options.config_file = resolved_config

            self.logger.debug(
                f"Creating GenerateService with config_file: {current_gen_kwargs.get('config_file')}"
            )
            current_generate_service = GenerateService(**current_gen_kwargs)

            # Generate WITHOUT filters to see all components (for accurate comparison)
            current_components = self._generate_and_scan(
                generate_service=current_generate_service,
                output_dir=temp_current,
                filters=None,  # Don't apply filters during generation
                include_inactive=include_inactive,
                verbose=verbose,
            )

            # Step 2: Extract base branch files using git archive
            if verbose:
                self.logger.debug(f"Extracting base branch files: {base_branch}")

            git_extractor.extract(base_branch, temp_extracted, verbose)
            self.logger.debug(f"Base branch extracted to: {temp_extracted}")

            # Step 3: Generate from extracted base branch files
            if verbose:
                self.logger.debug("Generating from base branch files")

            # Create a new GenerateService instance for base branch with modified
            # config path. Isolate global_options once so this derived dict never
            # shares the caller's mutable GlobalOptions object.
            base_kwargs = self._gen_kwargs.copy()
            if "global_options" in base_kwargs:
                base_kwargs["global_options"] = copy.copy(base_kwargs["global_options"])

            # Derive the base-branch config path by re-rooting the live config path
            # under the extracted tree. resolved_config is absolute and under repo_root.
            if resolved_config is None:
                raise ValueError("No config file found for base branch generation")

            try:
                rel_config_path = resolved_config.relative_to(repo_root)
            except ValueError:
                raise ValueError(
                    f"Config file {resolved_config} is not under repository root {repo_root}"
                )
            extracted_config_path = temp_extracted / rel_config_path

            if not extracted_config_path.exists():
                raise ValueError(
                    f"Config file not found in extracted base branch at {extracted_config_path}"
                )

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

            base_generate_service = GenerateService(**base_kwargs)

            # Generate WITHOUT filters to see all components (for accurate comparison)
            base_components = self._generate_and_scan(
                generate_service=base_generate_service,
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

            result = self._compare_outputs(
                current_components,
                base_components,
                temp_current,
                temp_main,
                current_generate_service,
                verbose=verbose,
            )
            self.logger.debug(f"Initial comparison found {len(result.changes)} changes")

            # Step 5: Apply required component cascade logic
            if verbose:
                self.logger.debug("Applying required component cascade logic")
            result = self._apply_required_cascade(
                result, current_components, current_generate_service
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
            # Release git file handles/subprocesses held by the cached Repo.
            git_extractor.close()

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

    def _resolve_live_config_path(
        self, config_file: Any, repo_root: Path
    ) -> Path | None:
        """Resolve the config file path for the live working tree.

        Runs the standard search ladder once and returns an absolute path so the
        base-branch path can be derived by re-rooting under the extracted tree.

        Resolution order:
        - An absolute provided path is used as-is.
        - A relative provided path is tried under the current directory, then via
          the upward search, then at the repo root using the provided basename.
        - When no path is provided, the upward search (with the repo-root default)
          is used.

        Args:
            config_file: Provided config path (absolute, relative, or None)
            repo_root: Repository root directory

        Returns:
            Absolute path to the config file, or None if none was found
        """
        resolved: Path | None = None

        if config_file:
            config_path = Path(config_file)
            if config_path.is_absolute():
                resolved = config_path
            else:
                cwd_candidate = Path.cwd() / config_path
                if cwd_candidate.exists():
                    resolved = cwd_candidate
                    self.logger.debug(f"Using resolved config file: {cwd_candidate}")
                else:
                    self.logger.debug(
                        f"Config file {config_path} not found at {cwd_candidate}, searching..."
                    )
                    found = self._find_config_file(Path.cwd(), repo_root)
                    if found:
                        resolved = found
                    else:
                        # Repo-root fallback using the provided basename
                        repo_candidate = repo_root / config_path.name
                        if repo_candidate.exists():
                            resolved = repo_candidate
                            self.logger.debug(
                                f"Using config file from repo root: {repo_candidate}"
                            )
        else:
            resolved = self._find_config_file(Path.cwd(), repo_root)

        if resolved is not None and not resolved.is_absolute():
            resolved = resolved.resolve()

        return resolved

    def _find_config_file(self, current_dir: Path, repo_root: Path) -> Path | None:
        """Find the live-tree config file using the standard search ladder.

        Searches up from ``current_dir`` to the repository root for
        ``.cgconfig.yaml``; if none is found along the way, falls back to the
        default at the repository root.

        Args:
            current_dir: Directory to begin the upward search from
            repo_root: Repository root directory (search ceiling)

        Returns:
            Path to the config file, or None if not found
        """
        config_filename = ".cgconfig.yaml"

        # Start from current directory and search up to repo root
        search_dir = current_dir
        while True:
            config_path = search_dir / config_filename
            if config_path.exists():
                self.logger.debug(f"Found config file at: {config_path}")
                return config_path

            parent = search_dir.parent
            if parent == search_dir or not str(search_dir).startswith(str(repo_root)):
                # Reached filesystem root or stepped outside the repo
                break
            search_dir = parent

        # Fall back to the default location at the repository root
        default_path = repo_root / config_filename
        if default_path.exists():
            self.logger.debug(
                f"Using default config file from repo root: {default_path}"
            )
            return default_path

        return None

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

            if in_base and not in_current:
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
                continue

            # A new component (only in current) and a component present in both
            # whose content changed are recorded identically: CHANGED/DIRECT.
            is_changed = not in_base or self._has_content_changed(
                component_key,
                current_components[component_key],
                base_components[component_key],
                current_dir,
                base_dir,
            )
            if is_changed:
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
        current_files = content_diff.filter_ignored_files(current_files)
        base_files = content_diff.filter_ignored_files(base_files)

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
            if content_diff.files_differ(current_file, base_file):
                return True

        return False

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
