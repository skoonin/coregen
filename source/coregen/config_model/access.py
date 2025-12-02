"""
Configuration access module.

This module provides the ConfigAccess class, which enables path-based access to
configuration elements with pattern matching capabilities.
"""

import fnmatch
from typing import Any

from coregen.common.path_service import PathService
from coregen.config_model.models.components import Component
from coregen.config_model.models.config import CoregenConfig
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig


class ConfigAccess:
    """
    Provides path-based access to configuration elements.

    This class is responsible for:
    - Providing intuitive path-based access to configuration elements
    - Supporting pattern matching with glob syntax
    - Handling property-based filtering
    - Enabling cross-workspace queries

    Available methods:

    - find_components: Find components matching a pattern and filters
    - find_contexts: Find contexts matching a pattern and filters
    - find_workspaces: Find workspaces matching a pattern and filters
    - get_all_contexts: Retrieve all contexts in a workspace
    - get_component: Retrieve a component by workspace, context, and component name
    - get_context: Retrieve a context by workspace and context name
    - get_workspace: Retrieve a workspace by name
    - get: Retrieve configuration elements by path

    """

    def __init__(
        self,
        config_or_workspaces: CoregenConfig | list[WorkspaceConfig],
        path_service: PathService | None = None,
    ):
        """
        Initialize with a CoregenConfig or a list of processed workspaces.

        Args:
            config_or_workspaces: CoregenConfig instance or List of WorkspaceConfig instances
            path_service: Optional PathService instance for path resolution
        """
        # Extract workspaces from CoregenConfig if provided
        if isinstance(config_or_workspaces, CoregenConfig):
            self.workspaces = config_or_workspaces.workspaces
        else:
            self.workspaces = config_or_workspaces

        self.path_service = path_service

        # Build lookup tables for faster access
        self._workspace_lookup: dict[str, WorkspaceConfig] = {}
        self._context_lookup: dict[str, dict[str, Context]] = {}
        self._component_lookup: dict[str, dict[str, dict[str, Component]]] = {}

        # Additional lookup for environments to contexts
        self._environment_lookup: dict[str, list[Context]] = {}

        self._build_lookup_tables()

    def _build_lookup_tables(self) -> None:
        """Build internal lookup tables for efficient access."""
        for workspace in self.workspaces:
            # Add workspace to lookup
            self._workspace_lookup[workspace.name] = workspace

            # Initialize context lookup for this workspace
            self._context_lookup[workspace.name] = {}
            self._component_lookup[workspace.name] = {}

            # Add each context to lookup
            contexts = self.get_all_contexts(workspace)
            for context_name, context in contexts.items():
                # Add context to lookup
                self._context_lookup[workspace.name][context_name] = context

                # Add to environment lookup
                env = context.environment
                if env not in self._environment_lookup:
                    self._environment_lookup[env] = []
                self._environment_lookup[env].append(context)

                # Initialize component lookup for this context
                self._component_lookup[workspace.name][context_name] = {}

                # Add each component to lookup
                for component_name, component in context.get_all_components().items():
                    # Set context fields on component
                    component.environment = context.environment
                    component.workspace = workspace.name
                    component.context = context.name
                    self._component_lookup[workspace.name][context_name][
                        component_name
                    ] = component

    def get_all_contexts(self, workspace: WorkspaceConfig) -> dict[str, Context]:
        """
        Get all contexts from all context types in a workspace as a flattened dictionary.

        Args:
            workspace: The workspace to get all contexts from

        Returns:
            Dict[str, Context]: Dictionary of context names to context objects
        """
        result = {}
        for contexts in workspace.contexts.values():
            result.update(contexts)
        return result

    def get(self, path: str) -> Any:
        """
        Get a configuration element by path.

        The path format is "workspace_name/context_name/component_name".
        Each part is optional, and the appropriate type is returned based on
        how many path parts are provided.

        Args:
            path: Path to the configuration element

        Returns:
            The configuration element at the specified path
            (WorkspaceConfig, Context, or Component)

        Raises:
            ValueError: If the path is invalid or not found
        """
        parts = path.split("/")
        num_parts = len(parts)

        if num_parts == 1:
            # Return workspace
            return self.get_workspace(parts[0])
        elif num_parts == 2:
            # Return context
            return self.get_context(parts[0], parts[1])
        elif num_parts == 3:
            # Return component
            return self.get_component(parts[0], parts[1], parts[2])
        else:
            raise ValueError(f"Invalid path: {path}")

    def get_workspace(self, workspace_name: str) -> WorkspaceConfig:
        """
        Get a workspace by name.

        Args:
            workspace_name: Name of the workspace

        Returns:
            WorkspaceConfig instance

        Raises:
            ValueError: If the workspace is not found
        """
        if workspace_name not in self._workspace_lookup:
            raise ValueError(f"Workspace not found: {workspace_name}")
        return self._workspace_lookup[workspace_name]

    def get_context(self, workspace_name: str, context_name: str) -> Context:
        """
        Get a context by workspace and context name.

        Args:
            workspace_name: Name of the workspace
            context_name: Name of the context

        Returns:
            Context instance

        Raises:
            ValueError: If the workspace or context is not found
        """
        if workspace_name not in self._context_lookup:
            raise ValueError(f"Workspace not found: {workspace_name}")
        if context_name not in self._context_lookup[workspace_name]:
            raise ValueError(
                f"Context not found: {context_name} in workspace {workspace_name}"
            )
        return self._context_lookup[workspace_name][context_name]

    def get_component(
        self, workspace_name: str, context_name: str, component_name: str
    ) -> Component:
        """
        Get a component by workspace, context, and component name.

        Args:
            workspace_name: Name of the workspace
            context_name: Name of the context
            component_name: Name of the component

        Returns:
            Component instance

        Raises:
            ValueError: If the workspace, context, or component is not found
        """
        if workspace_name not in self._component_lookup:
            raise ValueError(f"Workspace not found: {workspace_name}")
        if context_name not in self._component_lookup[workspace_name]:
            raise ValueError(
                f"Context not found: {context_name} in workspace {workspace_name}"
            )
        if component_name not in self._component_lookup[workspace_name][context_name]:
            raise ValueError(
                f"Component not found: {component_name} in context {context_name} in workspace {workspace_name}"
            )
        return self._component_lookup[workspace_name][context_name][component_name]

    def find_workspaces(
        self, pattern: str = "*", **filters: Any
    ) -> list[WorkspaceConfig]:
        """
        Find workspaces matching a pattern and filters.

        Args:
            pattern: Glob pattern to match workspace names
            **filters: Property filters to apply

        Returns:
            List of matching WorkspaceConfig instances
        """
        # First filter by pattern
        matches = []
        for workspace_name, workspace in self._workspace_lookup.items():
            if fnmatch.fnmatch(workspace_name, pattern):
                matches.append(workspace)

        # Then apply property filters
        return self._apply_filters(matches, filters)

    def find_contexts(self, pattern: str = "*/*", **filters: Any) -> list[Context]:
        """
        Find contexts matching a pattern and filters.

        The pattern format is "workspace_name/context_name" or just "context_name".

        Example patterns:
        - "aws/*" -> all contexts in aws workspace
        - "frontend" -> all contexts named frontend across all workspaces
        - "my-ws/frontend" -> the frontend context in my-ws workspace

        Special property filters:
        - environment="dev" -> all contexts in dev environment (filtered after pattern matching)

        Args:
            pattern: Glob pattern to match context paths
            **filters: Property filters to apply (including environment)

        Returns:
            List of matching Context instances
        """
        # Add debug logging for the pattern and filters
        if hasattr(self, "logger"):
            self.logger.debug(
                f"Finding contexts with pattern: {pattern}, filters: {filters}"
            )

        # Parse the pattern
        parts = pattern.split("/")

        # Handle different pattern formats
        if len(parts) == 2:
            # Format: workspace/context
            workspace_pattern = parts[0]
            context_pattern = parts[1]
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"Two-part pattern: workspace='{workspace_pattern}', context='{context_pattern}'"
                )
        elif len(parts) == 1:
            # Format: context (match any workspace)
            workspace_pattern = "*"
            context_pattern = parts[0]
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"One-part pattern: context='{context_pattern}', matching all workspaces"
                )
        else:
            if hasattr(self, "logger"):
                self.logger.error(
                    f"Invalid context pattern: {pattern}. Format is 'workspace/context' or 'context'"
                )
            raise ValueError(
                f"Invalid context pattern: {pattern}. Format is 'workspace/context' or 'context'"
            )

        # Expand patterns without glob chars to substring match, but handle patterns
        # from ContextMatcher ("aws" should match "aws-*" not "*aws*")
        def _expand(pat: str) -> str:
            # If pattern doesn't have glob chars
            if not any(c in pat for c in "*?[]"):
                # If pattern is from the pattern matcher subsystem
                if caller_is_pattern_matcher():
                    # Ensure pattern matches from start (e.g., "aws" matches "aws-*" not "*aws*")
                    return f"{pat}*"
                else:
                    # Default behavior: substring match
                    return f"*{pat}*"
            return pat

        def caller_is_pattern_matcher() -> bool:
            """Check if the caller is from the pattern matcher subsystem.

            This allows us to handle patterns differently when they come from
            the matchers vs. direct API calls.
            """
            import inspect

            frames = inspect.stack()
            for frame in frames[1:]:  # Skip current frame
                filename = frame.filename
                if (
                    "matchers.py" in filename
                    or "pattern_matcher.py" in filename
                    or "pattern/facade.py" in filename
                ):
                    return True
            return False

        workspace_pattern = _expand(workspace_pattern)
        context_pattern = _expand(context_pattern)

        # First get all possible matching contexts
        matches = []

        # Check all workspaces and contexts
        for workspace_name, contexts in self._context_lookup.items():
            workspace_match = fnmatch.fnmatch(workspace_name, workspace_pattern)

            if workspace_match:
                if hasattr(self, "logger"):
                    self.logger.debug(
                        f"  - Workspace '{workspace_name}' matches pattern '{workspace_pattern}'"
                    )

                for context_name, context in contexts.items():
                    # Match context name only
                    context_match = fnmatch.fnmatch(context_name, context_pattern)
                    if context_match:
                        if hasattr(self, "logger"):
                            self.logger.debug(
                                f"  - Context '{context_name}' matches pattern '{context_pattern}'"
                            )
                        matches.append(context)
                    elif hasattr(self, "logger"):
                        self.logger.debug(
                            f"  - Context '{context_name}' does not match pattern '{context_pattern}'"
                        )

        # Handle environment filter separately
        remaining_filters = dict(filters)

        if hasattr(self, "logger"):
            self.logger.debug(
                f"Found {len(matches)} contexts before applying remaining filters: {remaining_filters}"
            )
            if matches:
                self.logger.debug(f"  - Matched contexts: {[c.name for c in matches]}")

        filtered_matches = self._apply_filters(matches, remaining_filters)

        if hasattr(self, "logger"):
            self.logger.debug(
                f"Returning {len(filtered_matches)} contexts after all filters"
            )

        return filtered_matches

    def _get_workspace_from_context(self, context: Context) -> WorkspaceConfig:
        """Get the workspace that contains a given context."""
        for workspace in self.workspaces:
            for contexts in workspace.contexts.values():
                if context.name in contexts and contexts[context.name] == context:
                    return workspace
        # This should not happen if the context is part of the configuration
        raise ValueError(f"Context {context.name} not found in any workspace")

    def find_components(self, pattern: str = "*/*", **filters: Any) -> list[Component]:
        """
        Find components matching a pattern and filters.

        The pattern format can be:
        - "workspace_name/context_name/component_name" (3 segments)
        - "context_name/component_name" (2 segments)
        - "component_name" (1 segment)

        Wildcards can be used in any part.

        Example patterns:
        - "aws/frontend/api" -> the api component in frontend context in aws workspace
        - "frontend/api" -> all api components in frontend contexts across any workspace
        - "api" -> all api components in any context/workspace

        Args:
            pattern: Glob pattern to match component paths
            **filters: Property filters to apply

        Returns:
            List of matching Component instances
        """
        if hasattr(self, "logger"):
            self.logger.debug(
                f"Finding components with pattern: {pattern}, filters: {filters}"
            )

        # Parse pattern
        parts = pattern.split("/")

        # Handle various pattern formats
        if len(parts) == 3:
            # Format: workspace/context/component
            workspace_pattern = parts[0]
            context_pattern = parts[1]
            component_pattern = parts[2]
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"3-part pattern detected: workspace='{workspace_pattern}', context='{context_pattern}', component='{component_pattern}'"
                )
        elif len(parts) == 2:
            # Format: context/component (match any workspace)
            workspace_pattern = "*"
            context_pattern = parts[0]
            component_pattern = parts[1]
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"2-part pattern detected: context='{context_pattern}', component='{component_pattern}', workspace='*' (any)"
                )
        elif len(parts) == 1:
            # Format: component (match any workspace and context)
            workspace_pattern = "*"
            context_pattern = "*"
            component_pattern = parts[0]
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"1-part pattern detected: component='{component_pattern}', workspace='*' (any), context='*' (any)"
                )
        else:
            if hasattr(self, "logger"):
                self.logger.error(f"Invalid component pattern: {pattern}")
            raise ValueError(
                f"Invalid component pattern: {pattern}. Format is 'workspace/context/component', 'context/component', or 'component'"
            )  # Find matching components - with enhanced debugging
        matches = []

        # Debug helper for verbose logging
        def log_debug(message: str) -> None:
            if hasattr(self, "logger"):
                self.logger.debug(message)

        log_debug(
            f"PATTERN DEBUG: Processing pattern '{pattern}' => workspace='{workspace_pattern}', context='{context_pattern}', component='{component_pattern}'"
        )

        # Check each workspace against workspace pattern
        for workspace_name, contexts in self._component_lookup.items():
            ws_match = fnmatch.fnmatch(workspace_name, workspace_pattern)

            if ws_match:
                log_debug(
                    f"  - Workspace '{workspace_name}' matches pattern '{workspace_pattern}'"
                )

                # For each matching workspace, check contexts against context pattern
                for context_name, components in contexts.items():
                    # DETAILED MATCHING DEBUG - show exactly how the pattern matching is applied
                    match_result = fnmatch.fnmatch(context_name, context_pattern)
                    log_debug(
                        f"    - Context match check: '{context_name}' against pattern '{context_pattern}' => {match_result}"
                    )

                    ctx_match = match_result

                    if ctx_match:
                        log_debug(
                            f"    - Context '{context_name}' matches pattern '{context_pattern}'"
                        )

                        # For each matching context, check components against component pattern
                        for component_name, component in components.items():
                            # DETAILED MATCHING DEBUG
                            comp_match_result = fnmatch.fnmatch(
                                component_name, component_pattern
                            )
                            log_debug(
                                f"      - Component match check: '{component_name}' against pattern '{component_pattern}' => {comp_match_result}"
                            )

                            comp_match = comp_match_result

                            if comp_match:
                                log_debug(
                                    f"      - Component '{component_name}' matches pattern '{component_pattern}'"
                                )
                                # All three segments match - add to results
                                matches.append(component)
                            elif component_pattern != "*":
                                log_debug(
                                    f"      - Component '{component_name}' doesn't match pattern '{component_pattern}'"
                                )
                    elif context_pattern != "*":
                        log_debug(
                            f"    - Context '{context_name}' doesn't match pattern '{context_pattern}'"
                        )
            elif workspace_pattern != "*":
                log_debug(
                    f"  - Workspace '{workspace_name}' doesn't match pattern '{workspace_pattern}'"
                )

        # Compatibility option: for exact patterns without wildcards, fall back to exact full path matching
        if "*" not in pattern and "?" not in pattern and "[" not in pattern:
            for workspace_name, contexts in self._component_lookup.items():
                for context_name, components in contexts.items():
                    for component_name, component in components.items():
                        full_path = f"{workspace_name}/{context_name}/{component_name}"
                        if full_path == pattern and component not in matches:
                            log_debug(
                                f"    - Exact path match: '{full_path}' equals pattern '{pattern}'"
                            )
                            matches.append(component)

        # Handle environment in filters
        environment = filters.get("environment")
        remaining_filters = dict(filters)

        if environment is not None:
            if hasattr(self, "logger"):
                self.logger.debug(f"Applying environment filter: '{environment}'")

            # We need to apply environment filter separately since it's a property of context, not component
            filtered_by_env = []
            for component in matches:
                context_with_component = self._find_context_with_component(component)
                if (
                    context_with_component
                    and context_with_component.environment == environment
                ):
                    filtered_by_env.append(component)
                    if hasattr(self, "logger"):
                        self.logger.debug(
                            f"  - Component '{component.name}' in context '{context_with_component.name}' matches environment '{environment}'"
                        )
                elif hasattr(self, "logger") and context_with_component:
                    self.logger.debug(
                        f"  - Component '{component.name}' in context '{context_with_component.name}' with environment '{context_with_component.environment}' does not match filter '{environment}'"
                    )

            if hasattr(self, "logger"):
                self.logger.debug(
                    f"Environment filter reduced matches from {len(matches)} to {len(filtered_by_env)} components"
                )

            matches = filtered_by_env
            # Remove environment from remaining filters
            remaining_filters.pop("environment", None)
            remaining_filters.pop("env", None)

        # Then apply remaining property filters
        if hasattr(self, "logger"):
            self.logger.debug(
                f"Found {len(matches)} components before applying remaining filters: {remaining_filters}"
            )
            if matches:
                self.logger.debug(
                    f"  - Matched components: {[c.name for c in matches]}"
                )

        filtered_matches = self._apply_filters(matches, remaining_filters)

        if hasattr(self, "logger"):
            self.logger.debug(
                f"Returning {len(filtered_matches)} components after all filters"
            )

        return filtered_matches

    def _find_context_with_component(self, component: Component) -> Context | None:
        """Find the context that contains a specific component."""
        for workspace_name, contexts in self._context_lookup.items():
            for context_name, context in contexts.items():
                all_components = context.get_all_components()
                if (
                    component.name in all_components
                    and all_components[component.name] is component
                ):
                    return context
        return None

    def find_contexts_in_workspace(
        self, workspace: WorkspaceConfig, pattern: str = "*"
    ) -> list[Context]:
        """Find contexts within a specific workspace matching a pattern.

        Args:
            workspace: The workspace to search in
            pattern: Glob pattern to match context names

        Returns:
            List of matching Context instances within the workspace
        """
        matches = []

        # Get all contexts in this workspace
        all_contexts = self.get_all_contexts(workspace)

        # Match context names against the pattern
        for context_name, context in all_contexts.items():
            if fnmatch.fnmatch(context_name, pattern):
                matches.append(context)

        return matches

    def find_components_in_context(
        self, context: Context, pattern: str = "*"
    ) -> list[Component]:
        """Find components within a specific context matching a pattern.

        Args:
            context: The context to search in
            pattern: Glob pattern to match component names

        Returns:
            List of matching Component instances within the context
        """
        matches = []

        # Get all components in this context
        all_components = context.get_all_components()

        # Match component names against the pattern
        for component_name, component in all_components.items():
            if fnmatch.fnmatch(component_name, pattern):
                matches.append(component)

        return matches

    # find_contexts_by_environment is removed as we now use filters instead of embedding environment in path patterns

    def _apply_filters(self, items: list[Any], filters: dict[str, Any]) -> list[Any]:
        """
        Apply property filters to a list of items.

        Args:
            items: List of items to filter
            filters: Dictionary of property filters

        Returns:
            List of items matching all filters
        """
        if not filters:
            return items

        filtered_items = []

        for item in items:
            # Check each filter against item properties
            match = True
            for prop, value in filters.items():
                if not self._check_filter(item, prop, value):
                    match = False
                    break

            if match:
                filtered_items.append(item)

        return filtered_items

    def _check_filter(self, item: Any, prop: str, value: Any) -> bool:
        """
        Check if an item matches a property filter.

        Args:
            item: The item to check
            prop: The property name to check
            value: The value to compare against

        Returns:
            True if the item matches the filter, False otherwise
        """
        # Handle nested properties (e.g. "config.active")
        if "." in prop:
            parts = prop.split(".")
            current = item

            # Navigate to nested property
            for part in parts:
                if not hasattr(current, part):
                    return False
                current = getattr(current, part)

            return bool(current == value)

        # Handle direct properties
        if not hasattr(item, prop):
            return False

        return bool(getattr(item, prop) == value)

    def get_complete_model(self) -> dict[str, dict[str, Any]]:
        """
        Returns complete configuration model with all relationships.

        This method provides the full configuration hierarchy including:
        - All workspaces with their complete configuration
        - All contexts with their parent workspace reference
        - All components with their parent context reference

        The returned structure maintains all relationships, allowing filters
        to access parent properties (e.g., context.environment when filtering components).

        Returns:
            Dictionary with three keys:
            - "workspaces": {name: WorkspaceConfig, ...}
            - "contexts": {name: Context, ...}
            - "components": {key: Component, ...}

            Component keys are in the format "context_name/component_name"
            to maintain uniqueness across contexts.
        """
        complete_model: dict[str, dict[str, Any]] = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        # Add all workspaces and their nested contexts/components
        for workspace in self.workspaces:
            # Add workspace
            complete_model["workspaces"][workspace.name] = workspace

            # Get all contexts in this workspace
            all_contexts = self.get_all_contexts(workspace)

            # Add contexts
            for context_name, context in all_contexts.items():
                # Ensure context has workspace field set
                if not context.workspace:
                    context.workspace = workspace.name
                complete_model["contexts"][context_name] = context

                # Add components from this context
                all_components = context.get_all_components()
                for component_name, component in all_components.items():
                    # Use context/component as key to ensure uniqueness
                    component_key = f"{context_name}/{component_name}"
                    # Set context fields on component
                    component.workspace = workspace.name
                    component.environment = context.environment
                    component.context = context_name
                    complete_model["components"][component_key] = component

        return complete_model
