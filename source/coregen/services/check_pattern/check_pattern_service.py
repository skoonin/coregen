"""
Test pattern service implementation.

This module provides functionality to test pattern matching against configuration elements
and visualize matching results.
"""

from typing import Any, TypedDict

from coregen.common.inactive_filter_service import InactiveFilterService
from coregen.common.pattern import PatternSelector
from coregen.common.pattern.pattern_spec import LogicalPatternSpec  # noqa: F401
from coregen.services.services_base import ServicesBase


class PatternExamples(TypedDict):
    """Matched and rejected example elements for a pattern analysis."""

    matched: list[dict[str, str]]
    rejected: list[dict[str, str]]


class PatternAnalysis(TypedDict):
    """Structured result of analyzing why a pattern matches or rejects elements."""

    pattern: str
    pattern_type: str
    pattern_parts: list[dict[str, Any]]
    examples: PatternExamples
    match_attempts: list[str]
    phase1_results: dict[str, Any]
    phase2_results: dict[str, Any]


class CheckPatternService(ServicesBase):
    """Service for testing pattern matching against configuration.

    This service helps users understand how patterns match against their configuration
    by providing detailed information about what elements match and why.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the test pattern service."""
        # Handle config_file explicitly if it's passed
        config_file = kwargs.pop("config_file", None)

        super().__init__(**kwargs)

        # Save config_file as an instance attribute if provided
        if config_file:
            self.config_file = config_file

        self.provider = self.config_provider
        self.inactive_filter_service = InactiveFilterService()
        self.logger.debug("Initialized CheckPatternService")

    def check_pattern(
        self,
        patterns: list[str],
        filters: list[str] | None = None,
        show_rejected: bool = False,
        analyze: bool = False,
        include_inactive: bool = False,
        type: str | None = None,
    ) -> dict[str, Any]:
        """Test pattern matching against configuration.

        Args:
            patterns: List of patterns to test
            filters: Optional list of filter expressions
            show_rejected: If True, include elements that don't match
            analyze: If True, analyze why patterns match or don't match
            include_inactive: If True, include inactive components and contexts
            type: Optional entity type filter ('all', 'workspace', 'context', 'component')

        Returns:
            Dictionary with pattern match results
        """
        self.logger.debug(
            f"Testing patterns: {patterns}, filters: {filters}, "
            f"show_rejected: {show_rejected}, analyze: {analyze}"
        )

        results: dict[str, Any] = {
            "patterns": patterns,
            "filters": filters or [],
            "matched": {},
            "rejected": {} if show_rejected else None,
            "stats": {},
            "analysis": {} if analyze else None,
        }

        for pattern in patterns:
            self.logger.debug(f"Testing pattern: {pattern}")
            pattern_results = self._test_single_pattern(
                pattern, filters, show_rejected, include_inactive
            )

            # Merge results
            if "workspaces" in pattern_results["matched"]:
                if "workspaces" not in results["matched"]:
                    results["matched"]["workspaces"] = {}
                results["matched"]["workspaces"].update(
                    pattern_results["matched"]["workspaces"]
                )

            if "contexts" in pattern_results["matched"]:
                if "contexts" not in results["matched"]:
                    results["matched"]["contexts"] = {}
                results["matched"]["contexts"].update(
                    pattern_results["matched"]["contexts"]
                )

            if "components" in pattern_results["matched"]:
                if "components" not in results["matched"]:
                    results["matched"]["components"] = {}
                results["matched"]["components"].update(
                    pattern_results["matched"]["components"]
                )

            if "files" in pattern_results["matched"]:
                if "files" not in results["matched"]:
                    results["matched"]["files"] = []
                # Use extend for lists, update for dicts
                results["matched"]["files"].extend(pattern_results["matched"]["files"])

            # Include rejected items if requested
            if show_rejected and pattern_results.get("rejected"):
                if results["rejected"] is None:
                    results["rejected"] = {}

                if "contexts" in pattern_results["rejected"]:
                    if "contexts" not in results["rejected"]:
                        results["rejected"]["contexts"] = {}
                    results["rejected"]["contexts"].update(
                        pattern_results["rejected"]["contexts"]
                    )

                if "components" in pattern_results["rejected"]:
                    if (
                        results["rejected"] is not None
                        and "components" not in results["rejected"]
                    ):
                        results["rejected"]["components"] = {}
                    results["rejected"]["components"].update(
                        pattern_results["rejected"]["components"]
                    )

            # Add analysis if requested
            if analyze:
                results["analysis"][pattern] = self._analyze_pattern_matching(pattern)

        # Calculate stats using the internal lookup tables from ConfigAccess
        total_contexts_count = sum(
            len(contexts) for contexts in self.config_access._context_lookup.values()
        )
        total_components_count = sum(
            len(context_components)
            for ws_components in self.config_access._component_lookup.values()
            for context_components in ws_components.values()
        )

        results["stats"] = {
            "total_contexts": total_contexts_count,
            "total_components": total_components_count,
            "matched_contexts": len(results["matched"].get("contexts", {})),
            "matched_components": len(results["matched"].get("components", {})),
            "rejected_contexts": (
                len(results["rejected"].get("contexts", {}))
                if results["rejected"]
                else 0
            ),
            "rejected_components": (
                len(results["rejected"].get("components", {}))
                if results["rejected"]
                else 0
            ),
        }

        # Apply type filtering if specified
        type_value = getattr(type, "value", type)
        if type_value:
            matched_results: dict[str, Any] = results["matched"]
            results["matched"] = self._filter_results_by_type(
                matched_results, type_value
            )
            if results["rejected"] and isinstance(results["rejected"], dict):
                results["rejected"] = self._filter_results_by_type(
                    results["rejected"], type_value
                )

        # Return results for CLI formatting - don't directly output to console
        return results

    def _filter_results_by_type(
        self, results: dict[str, Any], entity_type: str
    ) -> dict[str, Any]:
        """Filter results to include only the specified entity type.

        Args:
            results: Results dictionary to filter
            entity_type: Entity type to keep ('workspace', 'context', 'component')

        Returns:
            Filtered results dictionary
        """
        filtered_results = {}

        if entity_type == "workspace" and "workspaces" in results:
            filtered_results["workspaces"] = results["workspaces"]
        elif entity_type == "context" and "contexts" in results:
            filtered_results["contexts"] = results["contexts"]
        elif entity_type == "component" and "components" in results:
            filtered_results["components"] = results["components"]

        # Always preserve files section if it exists
        if "files" in results:
            filtered_results["files"] = results["files"]

        return filtered_results

    def _test_single_pattern(
        self,
        pattern: str,
        filters: list[str] | None,
        show_rejected: bool,
        include_inactive: bool,
    ) -> dict[str, Any]:
        """Test a single pattern against the configuration.

        Args:
            pattern: Pattern to test
            filters: Optional list of filter expressions
            show_rejected: If True, include elements that don't match

        Returns:
            Dictionary with pattern match results
        """
        pattern_results: dict[str, Any] = {
            "pattern": pattern,
            "matched": {},
            "rejected": {} if show_rejected else None,
        }

        # Load complete model first (filter-first architecture)
        complete_model = self.config_access.get_complete_model()

        # Apply filters if specified
        if filters:
            parsed_filters = []
            for filter_expr in filters:
                parsed_filters.append(self.parse_filter_expression(filter_expr))
            complete_model = self.filter_service.apply_filters_complete(
                complete_model, parsed_filters
            )

        # Apply inactive filtering
        complete_model = self.inactive_filter_service.filter_complete_model(
            complete_model, include_inactive
        )

        # Now apply pattern selection on the filtered model
        pattern_selector = PatternSelector(logger=self.logger)
        matched_elements = pattern_selector.select_by_pattern(complete_model, pattern)

        # Store matched elements
        pattern_results["matched"] = matched_elements

        # If showing rejected, find all elements that didn't match
        if show_rejected:
            pattern_results["rejected"] = self._find_rejected_elements(matched_elements)

        return pattern_results

    def _find_rejected_elements(
        self, matched_elements: dict[str, Any]
    ) -> dict[str, Any]:
        """Find contexts and components that were not matched by the pattern."""
        rejected: dict[str, dict[str, Any]] = {"contexts": {}, "components": {}}

        # Find rejected contexts
        all_contexts = {}
        all_workspaces = self.config_access.find_workspaces("*")
        for workspace in all_workspaces:
            workspace_contexts = self.config_access.get_all_contexts(
                workspace=workspace
            )
            all_contexts.update(workspace_contexts)

        matched_contexts = matched_elements.get("contexts", {})
        for context_name, context in all_contexts.items():
            if context_name not in matched_contexts:
                rejected["contexts"][context_name] = {
                    "name": context.name,
                    "environment": context.environment,
                    "workspace": self.filter_service.get_workspace_for_context(context),
                }

            all_components_in_context = context.get_all_components()
            matched_components_in_context = {
                comp_key.split("/")[1]: comp_data
                for comp_key, comp_data in matched_elements.get(
                    "components", {}
                ).items()
                if comp_key.startswith(f"{context_name}/")
            }

            for component_name, component in all_components_in_context.items():
                if component_name not in matched_components_in_context:
                    component_key = f"{context_name}/{component_name}"
                    rejected["components"][component_key] = {
                        "name": component.name,
                        "context": context_name,
                        "workspace": self.filter_service.get_workspace_for_context(
                            context
                        ),
                    }

        return rejected

    def _analyze_pattern_matching(self, pattern: str) -> PatternAnalysis:
        """Analyze why elements match or don't match a pattern, using the two-phase matching approach.

        Args:
            pattern: Pattern to analyze

        Returns:
            Dictionary with pattern analysis
        """
        analysis: PatternAnalysis = {
            "pattern": pattern,
            "pattern_type": "Unknown",
            "pattern_parts": self._break_down_pattern(pattern),
            "examples": {"matched": [], "rejected": []},
            "match_attempts": [],
            "phase1_results": {},  # Store Phase 1 (compilation) results
            "phase2_results": {},  # Store Phase 2 (execution) results
        }

        # Use our new two-phase pattern matching system for better analysis
        try:
            # Import our pattern matching components
            from coregen.common.pattern.pattern_parser import PatternParser
            from coregen.common.pattern.pattern_spec import (
                LogicalPrefixType,
                PatternType,
            )

            # Phase 1: Pattern Compilation
            analysis["match_attempts"].append(
                "Phase 1: Pattern Compilation - Converting raw pattern to structured specification"
            )

            parser = PatternParser()
            try:
                pattern_spec = parser.parse(pattern)

                # Store the structured specification information
                if pattern_spec.pattern_type == PatternType.LOGICAL:
                    analysis["pattern_type"] = "Logical"
                    logical_spec = pattern_spec  # type: LogicalPatternSpec

                    # Add detailed logical pattern information
                    analysis["phase1_results"] = {
                        "prefix_type": str(logical_spec.prefix_type),
                        "segments": logical_spec.segments,
                        "tokens": [
                            {
                                "value": t.value,
                                "is_wildcard": t.is_wildcard,
                                "is_recursive": t.is_recursive,
                            }
                            for t in logical_spec.tokens
                        ],
                    }

                    # Explain what this logical pattern will match
                    if logical_spec.prefix_type == LogicalPrefixType.WORKSPACE:
                        analysis["match_attempts"].append(
                            f"Logical workspace pattern detected: {pattern}"
                        )
                        if len(logical_spec.segments) == 1:
                            analysis["match_attempts"].append(
                                f"Will match workspace names like: '{logical_spec.segments[0]}'"
                            )
                        elif len(logical_spec.segments) == 2:
                            analysis["match_attempts"].append(
                                f"Will match contexts in workspace '{logical_spec.segments[0]}' with names like: '{logical_spec.segments[1]}'"
                            )
                        elif len(logical_spec.segments) == 3:
                            analysis["match_attempts"].append(
                                f"Will match components named '{logical_spec.segments[2]}' "
                                f"in context '{logical_spec.segments[1]}' of workspace '{logical_spec.segments[0]}'"
                            )

                    elif logical_spec.prefix_type == LogicalPrefixType.CONTEXT:
                        analysis["match_attempts"].append(
                            f"Logical context pattern detected: {pattern}"
                        )
                        if len(logical_spec.segments) == 1:
                            analysis["match_attempts"].append(
                                f"Will match context names like: '{logical_spec.segments[0]}'"
                            )
                        elif len(logical_spec.segments) >= 2:
                            analysis["match_attempts"].append(
                                f"Will match components named '{logical_spec.segments[1]}' in context '{logical_spec.segments[0]}'"
                            )

                    elif logical_spec.prefix_type == LogicalPrefixType.COMPONENT:
                        analysis["match_attempts"].append(
                            f"Logical component pattern detected: {pattern}"
                        )
                        analysis["match_attempts"].append(
                            f"Will match component names like: '{logical_spec.segments[0]}'"
                        )

            except Exception as e:
                analysis["match_attempts"].append(f"Error parsing pattern: {str(e)}")
                analysis["phase1_results"] = {"error": str(e)}

            # Phase 2: Pattern Execution
            analysis["match_attempts"].append(
                "Phase 2: Pattern Execution - Applying pattern specification to configuration"
            )

            # Get the matching results
            actual_results = self._test_single_pattern(
                pattern, None, True, True
            )  # Include rejected items, include inactive for analysis

            # Count of matched and rejected items
            matched_ctx_count = len(actual_results["matched"].get("contexts", {}))
            matched_comp_count = len(actual_results["matched"].get("components", {}))
            rejected_ctx_count = 0
            rejected_comp_count = 0

            if actual_results.get("rejected"):
                rejected_ctx_count = len(actual_results["rejected"].get("contexts", {}))
                rejected_comp_count = len(
                    actual_results["rejected"].get("components", {})
                )

            analysis["phase2_results"] = {
                "matched_contexts": matched_ctx_count,
                "matched_components": matched_comp_count,
                "rejected_contexts": rejected_ctx_count,
                "rejected_components": rejected_comp_count,
            }

            # Add examples of matched elements
            matched_items = []
            for ctx_name, ctx in actual_results["matched"].get("contexts", {}).items():
                ws = self.config_access._get_workspace_from_context(ctx)
                matched_items.append(
                    {
                        "path": f"{ws.name if ws else '?'}/{ctx_name}",
                        "type": "Context",
                        "reason": "Matched pattern specification",
                    }
                )

            for comp_key, comp in (
                actual_results["matched"].get("components", {}).items()
            ):
                ctx_name = comp_key.split("/")[0]
                comp_name = comp_key.split("/")[1]
                ctx = actual_results["matched"].get("contexts", {}).get(ctx_name)
                comp_ws = (
                    self.config_access._get_workspace_from_context(ctx) if ctx else None
                )

                matched_items.append(
                    {
                        "path": f"{comp_ws.name if comp_ws else '?'}/{ctx_name}/{comp_name}",
                        "type": "Component",
                        "reason": "Matched pattern specification",
                    }
                )

            # Add examples of rejected elements
            rejected_items = []
            if actual_results.get("rejected"):
                for ctx_name, ctx_info in (
                    actual_results["rejected"].get("contexts", {}).items()
                ):
                    ws_name = ctx_info.get("workspace", "?")
                    rejected_items.append(
                        {
                            "path": f"{ws_name}/{ctx_name}",
                            "type": "Context",
                            "reason": "Did not match pattern specification",
                        }
                    )

                for comp_key, comp_info in (
                    actual_results["rejected"].get("components", {}).items()
                ):
                    ctx_name = comp_info.get("context", "?")
                    ws_name = comp_info.get("workspace", "?")
                    rejected_items.append(
                        {
                            "path": f"{ws_name}/{comp_key}",
                            "type": "Component",
                            "reason": "Did not match pattern specification",
                        }
                    )

            # If we have a lot of matches/rejections, suggest more specific patterns
            if matched_ctx_count > 10 or matched_comp_count > 20:
                analysis["match_attempts"].append(
                    f"Pattern matched many elements ({matched_ctx_count} contexts, {matched_comp_count} components)"
                )
                analysis["match_attempts"].append(
                    "Consider using a more specific pattern to narrow down results"
                )

                if pattern.endswith("*"):
                    analysis["match_attempts"].append(
                        f"Try adding more characters before the wildcard, e.g., '{pattern.replace('*', 'abc*')}'"
                    )
                elif "*" not in pattern and "?" not in pattern:
                    analysis["match_attempts"].append(
                        f"Try adding a suffix to be more specific, e.g., '{pattern}-suffix'"
                    )

            # If we have no matches but many rejections, suggest broader patterns
            if (
                matched_ctx_count == 0
                and matched_comp_count == 0
                and (rejected_ctx_count > 0 or rejected_comp_count > 0)
            ):
                analysis["match_attempts"].append(
                    f"Pattern didn't match any elements (rejected {rejected_ctx_count} contexts, {rejected_comp_count} components)"
                )
                analysis["match_attempts"].append(
                    "Consider using a more general pattern or wildcards"
                )

                if "*" not in pattern:
                    analysis["match_attempts"].append(
                        f"Try adding wildcards, e.g., '{pattern}*' or '*{pattern}*'"
                    )

            # Add matched and rejected examples
            analysis["examples"]["matched"] = matched_items[:5]
            analysis["examples"]["rejected"] = rejected_items[:5]

        except Exception as e:
            analysis["match_attempts"].append(
                f"Error during pattern analysis: {str(e)}"
            )

        return analysis

    def _break_down_pattern(self, pattern: str) -> list[dict[str, Any]]:
        """Break down a pattern into its components for analysis.

        Args:
            pattern: Pattern to analyze

        Returns:
            List of pattern components and their meaning
        """
        parts = []
        segments = pattern.split("/")

        for segment in segments:
            segment_info: dict[str, Any] = {"segment": segment, "wildcards": []}

            # Check for wildcards
            if "*" in segment:
                segment_info["wildcards"].append(
                    {
                        "type": "asterisk",
                        "description": "Matches any sequence of characters (including none)",
                    }
                )
            if "?" in segment:
                segment_info["wildcards"].append(
                    {
                        "type": "question_mark",
                        "description": "Matches any single character",
                    }
                )
            if "[" in segment and "]" in segment:
                segment_info["wildcards"].append(
                    {
                        "type": "character_class",
                        "description": "Matches any character within the brackets",
                    }
                )

            parts.append(segment_info)

        return parts
