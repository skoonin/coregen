"""Pattern matchers.

This module provides matcher classes that apply pattern specifications against configuration
elements to find matching workspaces, contexts, and components.
"""

from abc import ABC, abstractmethod
from typing import Any

from coregen.config_model.access import ConfigAccess
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.workspace import WorkspaceConfig

from .pattern_spec import LogicalPatternSpec, LogicalPrefixType, PatternSpec


class Matcher(ABC):
    """Base class for all pattern matchers."""

    def __init__(self, spec: PatternSpec, config_access: ConfigAccess):
        """Initialize the matcher.

        Args:
            spec: The pattern specification to match against
            config_access: Access to configuration elements
        """
        self.spec = spec
        self.config_access = config_access

    @abstractmethod
    def match(self, result: dict[str, dict[str, Any]]) -> bool:
        """Execute the pattern matching, populating the result dict.

        Args:
            result: Dictionary to be populated with matched elements

        Returns:
            True if any element was matched, False otherwise
        """

    def _add_matched_workspace(
        self,
        workspace: WorkspaceConfig,
        result: dict[str, dict[str, Any]],
        add_children: bool = False,
    ) -> None:
        """Add a matched workspace to the result.

        Args:
            workspace: The workspace to add
            result: The result dictionary to populate
            add_children: Whether to also add the workspace's contexts and components
        """
        if workspace.name not in result["workspaces"]:
            result["workspaces"][workspace.name] = workspace

            if add_children:
                contexts = self.config_access.get_all_contexts(workspace)
                for ctx_name, ctx in contexts.items():
                    self._add_matched_context(
                        ctx, result, add_children=True, add_parent=False
                    )

    def _add_matched_context(
        self,
        context: Context,
        result: dict[str, dict[str, Any]],
        add_children: bool = False,
        add_parent: bool = True,
    ) -> None:
        """Add a matched context to the result.

        Args:
            context: The context to add
            result: The result dictionary to populate
            add_children: Whether to also add the context's components
            add_parent: Whether to also add the context's parent workspace
        """
        if context.name not in result["contexts"]:
            result["contexts"][context.name] = context

            if add_parent:
                ws = self.config_access._get_workspace_from_context(context)
                if ws:
                    self._add_matched_workspace(ws, result, add_children=False)

            if add_children:
                components = context.get_all_components()
                for comp_name, comp in components.items():
                    self._add_matched_component(comp, context, result, add_parent=False)

    def _add_matched_component(
        self,
        component: Component,
        context: Context,
        result: dict[str, dict[str, Any]],
        add_parent: bool = True,
    ) -> None:
        """Add a matched component to the result.

        Args:
            component: The component to add
            context: The component's parent context
            result: The result dictionary to populate
            add_parent: Whether to also add the component's parent context and workspace
        """
        key = f"{context.name}/{component.name}"
        if key not in result["components"]:
            result["components"][key] = component

            if add_parent:
                self._add_matched_context(
                    context, result, add_children=False, add_parent=True
                )


class WorkspaceMatcher(Matcher):
    """Matcher for workspace logical patterns."""

    def __init__(self, spec: LogicalPatternSpec, config_access: ConfigAccess):
        """Initialize the matcher.

        Args:
            spec: The logical pattern specification
            config_access: Access to configuration elements
        """
        super().__init__(spec, config_access)
        assert spec.prefix_type == LogicalPrefixType.WORKSPACE

    def match(self, result: dict[str, dict[str, Any]]) -> bool:
        """Match workspace pattern against configuration.

        Args:
            result: Dictionary to be populated with matched elements

        Returns:
            True if any element was matched, False otherwise
        """
        matched_something = False
        segments = self.spec.segments

        # Handle the first segment (workspace name)
        if not segments:
            return matched_something

        ws_name_pattern = segments[0]
        matched_workspaces = self.config_access.find_workspaces(ws_name_pattern)

        if not matched_workspaces:
            return matched_something

        # Handle different pattern formats based on segments
        if len(segments) == 1:  # workspace/ws_pattern
            for ws in matched_workspaces:
                self._add_matched_workspace(ws, result, add_children=True)
                matched_something = True

        elif (
            len(segments) >= 2
        ):  # workspace/ws_pattern/ctx_pattern or workspace/ws_pattern/ctx_pattern/comp_pattern
            ctx_pattern = segments[1]

            # Special handling for wildcard patterns (e.g., workspace/aws/* or workspace/aws/**)
            # For workspace patterns, * and ** are equivalent since contexts are only one level deep
            if ctx_pattern == "**" or ctx_pattern == "*":
                for ws in matched_workspaces:
                    self._add_matched_workspace(ws, result, add_children=True)
                    matched_something = True
                return matched_something

            # Regular context pattern matching
            for ws in matched_workspaces:
                matched_contexts = self.config_access.find_contexts_in_workspace(
                    ws, ctx_pattern
                )

                for ctx in matched_contexts:
                    # If we have a component pattern (3+ segments)
                    if len(segments) >= 3:
                        comp_pattern = segments[2]

                        # Recursive pattern for components
                        if comp_pattern == "**":
                            self._add_matched_context(
                                ctx, result, add_children=True, add_parent=True
                            )
                            matched_something = True
                        else:
                            # Match specific components
                            matched_components = (
                                self.config_access.find_components_in_context(
                                    ctx, comp_pattern
                                )
                            )
                            for comp in matched_components:
                                self._add_matched_component(
                                    comp, ctx, result, add_parent=True
                                )
                                matched_something = True
                    else:
                        # Just match contexts
                        self._add_matched_context(
                            ctx, result, add_children=True, add_parent=True
                        )
                        matched_something = True

        return matched_something


class ContextMatcher(Matcher):
    """Matcher for context logical patterns."""

    def __init__(self, spec: LogicalPatternSpec, config_access: ConfigAccess):
        """Initialize the matcher.

        Args:
            spec: The logical pattern specification
            config_access: Access to configuration elements
        """
        super().__init__(spec, config_access)
        assert spec.prefix_type == LogicalPrefixType.CONTEXT

    def match(self, result: dict[str, dict[str, Any]]) -> bool:
        """Match context pattern against configuration.

        Args:
            result: Dictionary to be populated with matched elements

        Returns:
            True if any element was matched, False otherwise
        """
        matched_something = False
        segments = self.spec.segments

        # Handle the first segment (context name)
        if not segments:
            return matched_something

        ctx_name_pattern = segments[0]

        # Special handling for recursive patterns
        if len(segments) >= 2 and segments[1] == "**":
            matched_contexts = self.config_access.find_contexts(
                ctx_name_pattern, from_matcher=True
            )
            for ctx in matched_contexts:
                self._add_matched_context(
                    ctx, result, add_children=True, add_parent=True
                )
                matched_something = True
            return matched_something

        # Regular pattern handling
        matched_contexts = self.config_access.find_contexts(
            ctx_name_pattern, from_matcher=True
        )

        if len(segments) == 1:  # context/ctx_pattern
            for ctx in matched_contexts:
                self._add_matched_context(
                    ctx, result, add_children=True, add_parent=True
                )
                matched_something = True
        elif len(segments) >= 2:  # context/ctx_pattern/comp_pattern
            comp_pattern = segments[1]
            for ctx in matched_contexts:
                matched_components = self.config_access.find_components_in_context(
                    ctx, comp_pattern
                )
                for comp in matched_components:
                    self._add_matched_component(comp, ctx, result, add_parent=True)
                    matched_something = True

        return matched_something


class ComponentMatcher(Matcher):
    """Matcher for component logical patterns."""

    def __init__(self, spec: LogicalPatternSpec, config_access: ConfigAccess):
        """Initialize the matcher.

        Args:
            spec: The logical pattern specification
            config_access: Access to configuration elements
        """
        super().__init__(spec, config_access)
        assert spec.prefix_type == LogicalPrefixType.COMPONENT

    def match(self, result: dict[str, dict[str, Any]]) -> bool:
        """Match component pattern against configuration.

        Args:
            result: Dictionary to be populated with matched elements

        Returns:
            True if any element was matched, False otherwise
        """
        matched_something = False
        segments = self.spec.segments

        # Handle the first segment (component name)
        if not segments:
            return matched_something

        # Component patterns shouldn't have multiple segments
        if len(segments) > 1:
            return matched_something

        comp_name_pattern = segments[0]
        matched_components = self.config_access.find_components(comp_name_pattern)

        for comp in matched_components:
            ctx = self.config_access._find_context_with_component(comp)
            if ctx:
                self._add_matched_component(comp, ctx, result, add_parent=True)
                matched_something = True

        return matched_something
