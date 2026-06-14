"""
Get service implementation.

This module provides functionality to retrieve configuration elements based on patterns or JSON input.
It leverages the existing configuration access mechanisms and returns raw data for the CLI to format.
"""

import json
from pathlib import Path
from typing import Any

from coregen.common.entity_resolution_service import EntityResolutionService
from coregen.common.format_type_service import FormatTypeService
from coregen.common.inactive_filter_service import InactiveFilterService
from coregen.common.logger import Logger
from coregen.common.name_filter_service import NameFilterService
from coregen.common.pattern import PatternSelector
from coregen.common.type_filter_service import TypeFilterService
from coregen.services.services_base import ServicesBase

# NEW ARCHITECTURE: Complete model loading with filter-first approach


class GetService(ServicesBase):
    """Service for retrieving configuration elements.

    This service handles:
    - Processing path patterns to identify contexts and components
    - Processing JSON input to identify specific components
    - Filtering elements based on properties
    - Returning raw configuration data (formatting is handled by CLI/Formatter)

    Attributes:
        logger: Logger instance for this service
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the get service.

        Args:
            **kwargs: Keyword arguments passed to ServicesBase
        """
        super().__init__(**kwargs)
        self.logger = Logger(__name__)
        self.entity_resolution_service = EntityResolutionService(logger=self.logger)
        self.format_type_service = FormatTypeService()
        self.name_filter_service = NameFilterService()
        self.inactive_filter_service = InactiveFilterService()
        self.type_filter_service = TypeFilterService(logger=self.logger)
        self.logger.debug("Initialized GetService")

    def _process_json_input(
        self,
        json_string: str | None = None,
        json_file_path: Path | None = None,
        filters: list[str] | None = None,
        include_inactive: bool = False,
        type: str | None = None,
    ) -> dict[str, Any]:
        """Process JSON input to get components.

        Args:
            json_string: JSON string with component specifications
            json_file_path: Path to a JSON file with component specifications
            filters: Optional filter expressions to apply
            include_inactive: If True, include inactive components and contexts
            type: Optional entity type filter

        Returns:
            Dictionary with matched elements

        Raises:
            ValueError: If both json_string and json_file_path are None
            ValueError: If JSON cannot be parsed
            ValueError: If JSON format is invalid
        """
        if not json_string and not json_file_path:
            raise ValueError("Either json_string or json_file_path must be provided")

        # Parse JSON input
        try:
            if json_string:
                components_spec = json.loads(json_string)
            else:
                if json_file_path is None:
                    raise ValueError("json_file_path cannot be None at this point")
                with open(json_file_path) as f:
                    components_spec = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error reading JSON file: {str(e)}")

        # Validate JSON format
        if not isinstance(components_spec, list):
            raise ValueError("JSON input must be a list of component specifications")

        # Get the components based on the specifications
        matched_elements: dict[str, dict[str, Any]] = {
            "workspaces": {},
            "contexts": {},
            "components": {},
        }

        # Process each component specification
        for comp_spec in components_spec:
            if not isinstance(comp_spec, dict):
                self.logger.warning(
                    f"Skipping invalid component specification: {comp_spec}"
                )
                continue

            # Extract workspace, context, and component names
            workspace_name = comp_spec.get("workspace")
            context_name = comp_spec.get("context")
            component_name = comp_spec.get("component")

            if not workspace_name or not context_name or not component_name:
                self.logger.warning(f"Skipping incomplete component spec: {comp_spec}")
                continue

            # Find the workspace
            workspaces = self.config_access.find_workspaces(workspace_name)
            if not workspaces:
                self.logger.warning(f"Workspace not found: {workspace_name}")
                continue
            workspace = workspaces[0]

            # Get the context
            contexts = self.config_access.get_all_contexts(workspace)
            if context_name not in contexts:
                self.logger.warning(f"Context not found: {context_name}")
                continue
            context = contexts[context_name]

            # Get the component
            components = context.get_all_components()
            if component_name not in components:
                self.logger.warning(f"Component not found: {component_name}")
                continue
            component = components[component_name]

            # Add to matched elements
            matched_elements["workspaces"][workspace.name] = workspace
            matched_elements["contexts"][context.name] = context
            matched_elements["components"][
                f"{context.name}/{component_name}"
            ] = component

        # Apply filters if provided
        parsed_filters = []
        if filters:
            self.logger.debug(f"Applying filters: {filters}")
            for filter_expr in filters:
                parsed_filters.append(self.parse_filter_expression(filter_expr))

        # Apply regular filters
        if parsed_filters:
            matched_elements = self.apply_filters(matched_elements, parsed_filters)

        # Apply inactive filtering
        matched_elements = self.inactive_filter_service.filter_inactive(
            matched_elements, include_inactive
        )

        # Apply entity type filtering if specified
        type_value = getattr(type, "value", type)
        if type_value:
            matched_elements = self.type_filter_service.filter_exclusive(
                matched_elements, type_value
            )

        # Return raw matched elements without formatting
        # The CLI layer will handle formatting based on output format
        return matched_elements

    def get_elements(
        self,
        patterns: list[str] | None = None,
        filters: list[str] | None = None,
        from_json: str | None = None,
        json_file: Path | None = None,
        name_only: bool = False,
        include_inactive: bool = False,
        type: str | None = None,
        format_type: str | None = None,
    ) -> dict[str, Any]:
        """Get configuration elements using filter-first architecture.

        This method implements:
        1. Complete model is loaded first
        2. Filters are applied on the complete model
        3. Pattern selection happens after filtering
        4. Formatting is applied last

        Args:
            patterns: Optional glob patterns to match against configuration
            filters: Optional filter expressions to refine results
            from_json: Optional JSON string containing component specifications
            json_file: Optional path to a JSON file containing component specifications
            name_only: If True, return only simple arrays of names
            include_inactive: If True, include inactive components and contexts
            type: Optional entity type filter ('all', 'workspace', 'context', 'component')
            format_type: Optional output structure type ('flat', 'nested')

        Returns:
            Dictionary with matched elements
        """
        self.logger.debug(
            f"Getting elements with patterns={patterns}, filters={filters}, "
            f"from_json={from_json is not None}, json_file={json_file}"
        )

        # Input validation - need either patterns or JSON input
        if not patterns and not from_json and not json_file:
            raise ValueError(
                "Either patterns or JSON input (string or file) must be provided"
            )

        # Determine the source of results
        result: dict[str, dict[str, Any]]
        if from_json or json_file:
            # Process JSON input
            result = self._process_json_input(
                from_json, json_file, filters, include_inactive, type
            )
            # Load complete model for format_type processing
            complete_model = self.config_access.get_complete_model()
        else:
            # Load complete model first
            self.logger.debug("Loading complete model")
            complete_model = self.config_access.get_complete_model()

            # Apply filters on complete model if provided
            if filters:
                self.logger.debug(f"Applying filters on complete model: {filters}")
                parsed_filters = []
                for filter_expr in filters:
                    parsed_filters.append(self.parse_filter_expression(filter_expr))

                # Validate pattern/filter compatibility
                if patterns:
                    self.validate_pattern_filter_compatibility(patterns, filters)

                # Apply filters using complete model method
                complete_model = self.filter_service.apply_filters_complete(
                    complete_model, parsed_filters
                )

            # Apply inactive filtering on complete model
            complete_model = self.inactive_filter_service.filter_complete_model(
                complete_model, include_inactive
            )

            # Now apply pattern selection on the filtered model
            if patterns is None:
                raise ValueError("Patterns cannot be None at this point")

            self.logger.debug(f"Applying pattern selection: {patterns}")

            # For multiple patterns, merge results
            result = {
                "workspaces": {},
                "contexts": {},
                "components": {},
            }

            for pattern in patterns:
                # Use pattern selector for all patterns now (including filesystem)
                self.logger.debug(f"Using PatternSelector for pattern: {pattern}")
                pattern_selector = PatternSelector(logger=self.logger)
                selected = pattern_selector.select_by_pattern(complete_model, pattern)
                # Merge selected entities into result
                for entity_type in ["workspaces", "contexts", "components"]:
                    result[entity_type].update(selected.get(entity_type, {}))

        # Apply format_type if specified
        if format_type:
            self.logger.debug(f"Applying format_type: {format_type}")
            # Resolve entity types for format application
            format_str = (
                format_type.value
                if hasattr(format_type, "value")
                else str(format_type).lower() if format_type else "nested"
            )
            type_value = getattr(type, "value", type)

            entity_resolution = self.entity_resolution_service.resolve(
                patterns if patterns is not None else [], type_value, format_str
            )

            result = self.format_type_service.apply_format(
                result, format_type, type_value, entity_resolution
            )

        # Note: Type filtering is now handled within apply_format for flat format
        # to ensure proper exclusive filtering when --type is specified

        # Apply name-only filtering LAST
        if name_only:
            self.logger.debug("Applying name-only filtering")
            result = self.name_filter_service.filter_names_only(result)

        return result
