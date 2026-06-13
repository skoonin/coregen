"""
Generate service implementation.

This module provides the service implementation for the generate subcommand.
It handles file generation based on configuration elements.
"""

import os
import shutil
from pathlib import Path
from typing import Any

from coregen.cli.enums.enum_file_action import FileAction
from coregen.common.generator import Generator
from coregen.common.inactive_filter_service import InactiveFilterService
from coregen.common.type_filter_service import TypeFilterService
from coregen.config_model import TemplateContextAdapter
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.services.services_base import ServicesBase


class GenerateService(ServicesBase):
    """Service for generating files based on configuration.

    This service handles:
    - Processing path patterns to identify contexts and components
    - Filtering elements based on properties
    - Generating files to output locations
    - Processing templates using Jinja2
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the generate service.

        Args:
            **kwargs: Keyword arguments passed to parent constructor
        """
        super().__init__(**kwargs)
        # Store a reference to the config provider for easy access
        # Initialize filter services
        self.type_filter_service = TypeFilterService()
        self.inactive_filter_service = InactiveFilterService()
        # Track components per context for verbose mode summary
        # Single debug log with essential service initialization info
        self.logger.debug(
            f"Initialized GenerateService with provider={hasattr(self, 'provider')}, "
            f"path_service={hasattr(self.provider, 'path_service') if hasattr(self, 'provider') else False}"
        )

    def generate_files(
        self,
        paths: list[str],
        filters: list[str] | None = None,
        include_inactive: bool = False,
        type: str | None = None,
        skip_commit_dir: bool = False,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Generate files based on configuration.

        Args:
            paths: List of paths or patterns to generate files for
            filters: Optional list of filter expressions
            include_inactive: If True, include inactive components/contexts
            type: Optional entity type filter ('all', 'workspace', 'context', 'component')
            skip_commit_dir: If True, skip generating to context's commit_dir
            output_dir: Optional override for output directory

        Returns:
            Dictionary with results of generation
        """
        # Consolidated debug log for generation parameters
        self.logger.debug(
            f"Generating files for paths: {paths}, filters: {filters}, include_inactive: {include_inactive}, "
            f"skip_commit_dir: {skip_commit_dir}, output_dir: {output_dir}"
        )

        try:
            return self._generate_files_impl(
                paths, filters, include_inactive, type, skip_commit_dir, output_dir
            )
        except Exception as e:
            import traceback

            self.logger.error(f"Exception in generate_files: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _generate_files_impl(
        self,
        paths: list[str],
        filters: list[str] | None = None,
        include_inactive: bool = False,
        type: str | None = None,
        skip_commit_dir: bool = False,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:

        # Process path patterns to get matched elements
        self.console.debug(f"Processing path patterns: {paths}")
        matched_elements = self.process_path_patterns(paths)

        self.logger.debug(
            f"Matched elements after process_path_patterns: contexts={len(matched_elements.get('contexts', {}))}, components={len(matched_elements.get('components', {}))}"
        )

        # Check if we got any matches
        if not matched_elements or (
            len(matched_elements.get("workspaces", {})) == 0
            and len(matched_elements.get("contexts", {})) == 0
            and len(matched_elements.get("components", {})) == 0
        ):
            # The pattern matcher already warned about failed patterns; the
            # empty-result error below is what the CLI renders
            self.logger.debug(
                "Try using different patterns or check your configuration"
            )
            # Return empty results
            return {
                "generated_files": [],
                "skipped_files": [],
                "errors": [
                    "No matching contexts or components found for the specified patterns"
                ],
                "component_details": [],  # Added for table output
            }

        # Developer debug info
        self.logger.debug(f"Matched elements: {matched_elements.keys()}")
        if "components" in matched_elements:
            self.logger.debug(
                f"Matched components: {list(matched_elements['components'].keys())}"
            )

        if "components" in matched_elements:
            self.console.debug(
                f"Found {len(matched_elements['components'])} components matching patterns"
            )
            component_names = {
                comp.name for comp in matched_elements["components"].values()
            }
            self.logger.debug(f"Component names: {sorted(list(component_names))}")

        # Parse filters
        parsed_filters = []
        if filters:
            self.logger.debug(f"Applying filters: {filters}")
            for filter_expr in filters:
                self.logger.debug(f"Parsing filter expression: {filter_expr}")
                parsed_filters.append(self.parse_filter_expression(filter_expr))

        # Apply filters to matched elements
        if parsed_filters:
            filtered_elements = self.apply_filters(matched_elements, parsed_filters)
        else:
            filtered_elements = matched_elements

        # Apply inactive filtering
        filtered_elements = self.inactive_filter_service.filter_inactive(
            filtered_elements, include_inactive
        )

        # Entity type filtering is already handled by entity resolution service
        # No need to apply it again

        # Developer debug info
        self.logger.debug(
            f"Components after filtering: {list(filtered_elements['components'].keys()) if 'components' in filtered_elements else []}"
        )

        # Process dependencies and required components
        self.logger.debug(
            f"Before _process_dependencies_and_required - contexts keys: {list(filtered_elements.get('contexts', {}).keys())}"
        )
        if filtered_elements.get("contexts"):
            first_ctx_name = (
                list(filtered_elements["contexts"].keys())[0]
                if filtered_elements["contexts"]
                else None
            )
            if first_ctx_name:
                self.logger.debug(
                    f"First context '{first_ctx_name}' in filtered_elements"
                )
        processed_elements = self._process_dependencies_and_required(filtered_elements)

        component_count = (
            len(processed_elements["components"])
            if "components" in processed_elements
            else 0
        )
        context_count = (
            len(processed_elements["contexts"])
            if "contexts" in processed_elements
            else 0
        )
        self.console.debug(
            f"After filtering: {context_count} contexts and {component_count} components selected for generation"
        )

        # Replace filtered elements with processed elements that include dependencies
        filtered_elements = processed_elements

        # Generate files for each element
        results: dict[str, Any] = {
            "generated_files": [],
            "skipped_files": [],
            "errors": [],
            "component_details": [],  # Added for table output
        }

        self.logger.debug(f"filtered_elements keys: {list(filtered_elements.keys())}")
        self.logger.debug(
            f"Number of contexts: {len(filtered_elements.get('contexts', {}))}"
        )

        # Track contexts and components for summary
        contexts_processed = set()
        total_components = 0

        # Process each context and its components
        for context_name, context in filtered_elements["contexts"].items():
            self.logger.debug(f"Generating files for context: {context_name}")

            if context is None:
                self.logger.error(f"Context {context_name} is None!")
                results["errors"].append(f"Context {context_name} is None")
                continue

            # Get components for this context - MAINTAINING SORT ORDER
            # Since processed_elements["components"] is now sorted, we preserve that order
            context_components = {}
            for component_key, component in processed_elements["components"].items():
                if component_key.startswith(f"{context_name}/"):
                    component_name = component_key.split("/", 1)[1]
                    self.logger.debug(
                        f"Found component: {component_name} for context: {context_name}"
                    )
                    # Dict maintains insertion order in Python 3.7+
                    context_components[component_name] = component

            # Generate files for this context and its components
            context_results = self._generate_for_context(
                context, context_components, skip_commit_dir, output_dir
            )

            # Track what we processed
            if context_components:
                contexts_processed.add(context_name)
                total_components += len(context_components)

            # Merge results
            results["generated_files"].extend(context_results["generated_files"])
            results["skipped_files"].extend(context_results["skipped_files"])
            results["errors"].extend(context_results["errors"])
            if "component_details" in context_results:
                results["component_details"].extend(
                    context_results["component_details"]
                )

        # Add summary info to results for CLI to display
        results["contexts_count"] = len(contexts_processed)
        results["components_count"] = total_components

        return results

    def _clean_directory_for_delete_action(
        self, directory: Path, description: str = "directory"
    ) -> bool:
        """Clean directory if DELETE action is specified.

        Args:
            directory: The directory to potentially clean
            description: Human-readable description for logging

        Returns:
            True if directory was cleaned or would be cleaned (dry run), False otherwise
        """
        if self.file_action != FileAction.DELETE or not directory.exists():
            return False

        if self.dry_run:
            if not self.quiet:
                # No Rich markup in service strings: presentation belongs to the
                # CLI layer, and markup corrupts non-text output channels
                self.console.info(f"Would delete {description}: {directory}")
            self.logger.debug(f"Dry-run: Would delete {description} {directory}")
        else:
            try:
                if not self.quiet:
                    self.console.info(f"Deleting existing {description}: {directory}")
                shutil.rmtree(directory)
                self.logger.debug(
                    f"Deleted {description} for clean generation: {directory}"
                )
                return True
            except (PermissionError, OSError) as e:
                self.logger.error(f"Failed to delete {directory}: {e}")
                return False
        return True  # In dry-run, we assume it would be cleaned

    def _generate_for_context(
        self,
        context: Context,
        components: dict[str, Component],
        skip_commit_dir: bool,
        output_dir_override: Path | None,
    ) -> dict[str, Any]:
        """Generate files for a context and its components.

        Args:
            context: Context to generate files for
            components: Dictionary of components to generate
            skip_commit_dir: If True, skip generating to context's commit_dir
            output_dir_override: Optional override for output directory

        Returns:
            Dictionary with results of generation
        """
        self.logger.debug(
            f"Generating for context {context.name} with {len(components)} components: {list(components.keys())}"
        )

        # Initialize results
        results: dict[str, list[Any]] = {
            "generated_files": [],
            "skipped_files": [],
            "errors": [],
            "component_details": [],  # Added for table output
        }

        # Get workspace for this context
        workspace = self.config_access.find_workspace_for_context(context)
        if workspace is None:
            error_msg = f"Could not find workspace for context: {context.name}"
            self.console.error(error_msg)
            results["errors"].append(error_msg)
            return results
        workspace_name = workspace.name

        # Determine primary output directory
        primary_output_dir: Path
        if output_dir_override:
            primary_output_dir = output_dir_override
        else:
            # Use workspace output_dir - resolve it relative to config root
            workspace_paths = self.path_service.resolve_workspace_paths(workspace)
            resolved_output_path = workspace_paths.get("output_path")
            if resolved_output_path:
                primary_output_dir = resolved_output_path
            else:
                # Fallback to default if output_path not resolved
                primary_output_dir = (
                    self.path_service.resolver.root_path / workspace.output_dir
                )

        # Create context-specific output directory
        context_output_dir = primary_output_dir / context.name

        # Process each component
        for component_name, component in components.items():
            self.logger.debug(f"Generating files for component: {component_name}")

            # Track files and errors for this component across all locations
            component_file_count = 0
            component_errors = []

            # Create component output directory in primary location
            component_output_dir = context_output_dir / component_name

            # Clean the component directory if DELETE action is specified
            self._clean_directory_for_delete_action(
                component_output_dir, f"component directory: {component_name}"
            )

            # Generate to primary location
            component_results = self._generate_for_component(
                context, component, component_output_dir
            )

            component_file_count += len(component_results["generated_files"])
            component_errors.extend(component_results["errors"])

            # Merge results
            results["generated_files"].extend(component_results["generated_files"])
            results["skipped_files"].extend(component_results["skipped_files"])
            results["errors"].extend(component_results["errors"])

            # Check if we should also generate to context's commit_dir
            if not skip_commit_dir and getattr(component.config, "for_commit", False):
                # Get context path and commit_dir
                context_path = getattr(context, "path", None)
                commit_dir = getattr(context, "commit_dir", "for-commit")

                if context_path:
                    # Create base commit_dir path
                    commit_base_dir = Path(context_path) / commit_dir

                    # Create component output directory in commit_dir
                    commit_output_dir = commit_base_dir / component_name

                    # Clean the component's commit directory if DELETE action is specified
                    self._clean_directory_for_delete_action(
                        commit_output_dir,
                        f"component commit directory: {component_name}",
                    )

                    # Generate to commit_dir
                    commit_results = self._generate_for_component(
                        context, component, commit_output_dir
                    )

                    component_file_count += len(commit_results["generated_files"])
                    component_errors.extend(commit_results["errors"])

                    # Merge results
                    results["generated_files"].extend(commit_results["generated_files"])
                    results["skipped_files"].extend(commit_results["skipped_files"])
                    results["errors"].extend(commit_results["errors"])

            # Collect component details for table output
            component_detail = {
                "context": context.name,
                "workspace": workspace_name,
                "component": component_name,
                "priority": getattr(component.config, "priority", None),
                "status": len(component_errors) == 0,
                "for_commit": getattr(component.config, "for_commit", False),
                "files": component_file_count,
                "output_location": str(component_output_dir),
                "errors": component_errors,
            }
            results["component_details"].append(component_detail)

        return results

    def _process_dependencies_and_required(
        self, elements: dict[str, Any]
    ) -> dict[str, Any]:
        """Process component dependencies and include required components.

        This method:
        1. Finds all components marked as 'required' and includes them
        2. Recursively includes all dependencies of selected components
        3. MAINTAINS SORT ORDER from Context model (critical for deployment)

        Args:
            elements: Dictionary of matched elements after filtering

        Returns:
            Updated elements dictionary with dependencies and required components
        """
        self.logger.debug("Processing dependencies and required components")

        # Make a copy to avoid modifying the original during iteration
        # IMPORTANT: We maintain sort order by collecting components in a list first
        result = {
            "workspaces": elements.get("workspaces", {}),
            "contexts": elements.get("contexts", {}),
            "components": {},  # Will be rebuilt in sorted order
        }

        # First, find all components marked as 'required'
        required_added = 0

        # Copy existing components from elements, maintaining their order
        existing_components = elements.get("components", {})

        # Track all components we need to include (preserving order)
        all_components_ordered = []  # List of (context_name, comp_name, component)
        components_to_include = set()  # Set of comp_keys for quick lookup
        component_by_key: dict[str, Component] = {}  # "ctx/name" -> component

        # Add existing components first (they're already filtered)
        for comp_key, comp in existing_components.items():
            components_to_include.add(comp_key)

        # Look through all contexts to find required components
        for context_name in result["contexts"]:
            context = result["contexts"][context_name]
            self.logger.debug(f"Processing context {context_name}")

            # Get all components for this context (already sorted)
            try:
                if hasattr(context, "get_all_components"):
                    components = (
                        context.get_all_components()
                    )  # This returns sorted dict
                else:
                    self.logger.error(
                        f"Context {context_name} has no get_all_components method!"
                    )
                    continue
            except Exception as e:
                self.logger.error(
                    f"Error calling get_all_components on context {context_name}: {e}"
                )
                raise

            # Process components in their sorted order
            for comp_name, comp in components.items():
                comp_key = f"{context_name}/{comp_name}"

                # Add to ordered list for final assembly
                all_components_ordered.append((context_name, comp_name, comp))
                component_by_key[comp_key] = comp

                # Check if this component is marked as required
                if hasattr(comp.config, "required") and comp.config.required:
                    if comp_key not in components_to_include:
                        self.logger.debug(f"Adding required component: {comp_key}")
                        components_to_include.add(comp_key)
                        required_added += 1

        if required_added > 0:
            self.console.debug(f"Added {required_added} required components")

        # Now process dependencies recursively
        # Keep track of components we've already processed
        processed = set()
        to_process = list(components_to_include)
        dependency_added = 0

        while to_process:
            comp_key = to_process.pop(0)
            if comp_key in processed:
                continue
            processed.add(comp_key)

            context_name = comp_key.split("/")[0]

            component = component_by_key.get(comp_key)
            if not component:
                continue

            # Check for dependencies
            if hasattr(component, "config") and hasattr(
                component.config, "dependencies"
            ):
                for dep in component.get_dependencies():
                    dep_name = dep.get("name")
                    if not dep_name:
                        continue

                    # First try to find the dependency in the same context
                    dep_key = f"{context_name}/{dep_name}"

                    # Skip if we've already included this dependency
                    if dep_key in components_to_include:
                        continue

                    # Add dependency to be included
                    components_to_include.add(dep_key)
                    to_process.append(dep_key)
                    dependency_added += 1
                    self.logger.debug(
                        f"Added dependency {dep_key} for component {comp_key}"
                    )

        if dependency_added > 0:
            self.logger.debug(f"Added {dependency_added} components from dependencies")

        # Now rebuild components dict in sorted order
        # This preserves the sort order from Context.get_all_components()
        for context_name, comp_name, component in all_components_ordered:
            comp_key = f"{context_name}/{comp_name}"
            if comp_key in components_to_include:
                result["components"][comp_key] = component

        return result

    def _generate_for_component(
        self, context: Context, component: Component, output_dir: Path
    ) -> dict[str, Any]:
        """Generate files for a component.

        Args:
            context: Context containing the component
            component: Component to generate files for
            output_dir: Output directory for generated files

        Returns:
            Dictionary with results of generation
        """
        self.logger.debug(
            f"Generating files for component: {component.name} to {output_dir}"
        )

        # Initialize results
        results: dict[str, list[Any]] = {
            "generated_files": [],
            "skipped_files": [],
            "errors": [],
            "warnings": [],  # For template issues
        }

        # Guard: the context must belong to a known workspace
        if self.config_access.find_workspace_for_context(context) is None:
            error_msg = f"Could not find workspace for context: {context.name}"
            self.console.error(error_msg)
            results["errors"].append(error_msg)
            return results

        # Get the component path from the resolved paths - this MUST exist from config processing
        if not hasattr(component, "resolved_paths") or not component.resolved_paths.get(
            "component_path"
        ):
            # Missing resolved_paths is a critical error in our pipeline
            error_msg = f"Component '{component.name}' is missing resolved_paths. Configuration processing is incomplete."
            self.console.error(error_msg)
            results["errors"].append(error_msg)
            return results

        try:
            # Use the component's path directly as the template source directory
            # Templates are identified by their .j2 extension, not by being in a special directory
            template_dir = str(component.resolved_paths["component_path"])
            self.logger.debug(
                f"Using component path for template discovery: {template_dir}"
            )

            # Check if template directory exists
            if not os.path.exists(template_dir):
                error_msg = f"Template directory does not exist: {template_dir}"
                self.console.error(error_msg)
                results["errors"].append(error_msg)
                return results

        except Exception as e:
            error_msg = f"Error resolving path for component {component.name}: {str(e)}"
            self.console.error(error_msg)
            results["errors"].append(error_msg)
            return results

        # Create template context
        template_context = self._create_template_context(context, component)

        # Process templates
        try:
            # Process all files in template directory
            for root, dirs, files in os.walk(template_dir):
                self.logger.debug(f"Found {len(files)} files in {root}")
                for file in files:
                    # Get source path - ensure it's a Path object
                    source_path = Path(os.path.join(root, file))
                    # Process file paths
                    rel_path = os.path.relpath(source_path, template_dir)
                    processed_rel_path = self._process_template_path(
                        rel_path, template_context
                    )
                    dest_path = output_dir / processed_rel_path

                    # Output containment: substituted values (context/component
                    # names) could carry "../" or absolute segments and write
                    # outside the output tree.
                    resolved_dest = dest_path.resolve()
                    resolved_out = output_dir.resolve()
                    if (
                        resolved_dest != resolved_out
                        and resolved_out not in resolved_dest.parents
                    ):
                        error_msg = (
                            f"Generated path escapes output directory: "
                            f"{processed_rel_path}"
                        )
                        self.console.error(error_msg)
                        results["errors"].append(error_msg)
                        continue

                    # Create parent directories
                    self.file_manager.create_directory(dest_path.parent)

                    # Check if file is a template
                    if file.endswith(".j2"):
                        # Remove .j2 extension
                        dest_path = Path(str(dest_path)[:-3])

                        # Process template
                        try:
                            # Check if the template file exists and is readable
                            if not os.path.exists(source_path):
                                self.console.error(
                                    f"Template file does not exist: {source_path}"
                                )
                                results["errors"].append(
                                    f"Template file does not exist: {source_path}"
                                )
                                continue

                            if not os.access(source_path, os.R_OK):
                                self.console.error(
                                    f"Template file is not readable: {source_path}"
                                )
                                results["errors"].append(
                                    f"Template file is not readable: {source_path}"
                                )
                                continue

                            # Generate the template
                            errors = Generator.generate(
                                template_path=source_path,
                                output_path=dest_path,
                                template_values=template_context,
                                dry_run=self.dry_run,
                                file_action=self.file_action,
                                quiet=self.quiet,
                                verbose=self.verbose,
                                no_color=self.no_color,
                                context_name=context.name,  # Pass context name
                            )

                            # Add detailed debug logging
                            self.logger.debug(
                                f"Returned from Generator.generate for {source_path}: errors = {errors}"
                            )
                            self.logger.debug(
                                f"Checking 'if errors:' condition for {source_path}: {bool(errors)}"
                            )

                            # Add any errors or warnings from template generation
                            if errors:
                                # Add debug logging inside the block
                                self.logger.debug(
                                    f"Entered 'if errors:' block for {source_path}. Appending {len(errors)} errors."
                                )
                                for error in errors:
                                    results["errors"].append(error)
                            else:
                                # Log if no errors were found
                                self.logger.debug(
                                    f"Skipped 'if errors:' block for {source_path} (no errors reported by Generator). Adding to generated_files."
                                )
                                results["generated_files"].append(str(dest_path))

                        except Exception as e:
                            error_msg = (
                                f"Error processing template {source_path}: {str(e)}"
                            )
                            self.console.error(error_msg)
                            results["errors"].append(error_msg)
                    else:
                        # Copy file
                        try:
                            # Use file_manager to copy non-template files
                            self.file_manager.copy_file(source_path, dest_path)
                            results["generated_files"].append(str(dest_path))
                        except Exception as e:
                            error_msg = f"Error copying file {source_path}: {str(e)}"
                            self.console.error(error_msg)
                            results["errors"].append(error_msg)

        except Exception as e:
            error_msg = (
                f"Error processing templates for component {component.name}: {str(e)}"
            )
            self.console.error(error_msg)
            results["errors"].append(error_msg)

        return results

    def _create_template_context(
        self, context: Context, component: Component
    ) -> dict[str, Any]:
        """Create template context for rendering templates."""
        # Get workspace for this context
        workspace = self.config_access.find_workspace_for_context(context)
        if workspace is None:
            self.console.error(f"Could not find workspace for context: {context.name}")
            return {}

        # Use TemplateContextAdapter to create the complete template context
        adapter = TemplateContextAdapter(
            context, context_type=workspace.context_type, current_component=component
        )
        template_context = adapter.to_dict()

        # Add backward compatibility fields
        template_context["component_config"] = component.config

        # Add non-hyphenated versions for Jinja2 compatibility
        for key in list(template_context.keys()):
            if "-" in key:
                non_hyphenated_key = key.replace("-", "_")
                if non_hyphenated_key not in template_context:
                    template_context[non_hyphenated_key] = template_context[key]
                    self.logger.debug(
                        f"Added non-hyphenated namespace {non_hyphenated_key}"
                    )

        # Add workspace data
        template_context["workspace"] = (
            workspace.model_dump(exclude_defaults=False)
            if hasattr(workspace, "model_dump")
            else workspace.dict(exclude_defaults=False)
        )

        # Add 'context' alias for backward compatibility with templates that use {{ context.name }}
        if (
            "context" not in template_context
            and workspace.context_type in template_context
        ):
            template_context["context"] = template_context[workspace.context_type]

        # Log the final context structure for debugging
        self.logger.debug(f"Template context keys: {list(template_context.keys())}")
        context_type = workspace.context_type
        if context_type in template_context:
            self.logger.debug(
                f"Context {context_type} keys: {list(template_context[context_type].keys())}"
            )

        return template_context

    def _process_template_path(self, path: str, context: dict[str, Any]) -> str:
        """Process template variables in a path.

        Args:
            path: Path to process
            context: Template context

        Returns:
            Processed path
        """
        # Simple variable replacement
        result = path
        for key, value in context.items():
            if isinstance(value, str):
                placeholder = f"{{{key}}}"
                if placeholder in result:
                    result = result.replace(placeholder, value)

        return result
