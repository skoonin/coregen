"""
Entity resolution service for determining what entities to include.

This module provides centralized logic for resolving which entities should be
included in output based on patterns, type filters, and format types.
"""

from dataclasses import dataclass

from coregen.common.logger import Logger


@dataclass
class EntityResolution:
    """Resolution result for entity filtering."""

    primary_entity: str | None  # 'workspaces', 'contexts', 'components'
    included_entities: set[str]  # Which entities to include
    filter_parents: bool  # Whether to filter out parent entities


class EntityResolutionService:
    """Centralizes entity resolution logic based on patterns and type filters.

    This service determines:
    - What entities to include based on pattern prefixes
    - How pattern prefixes interact with --type filters
    - Whether to filter out parent entities
    - Validation of invalid pattern/type combinations
    """

    def __init__(self, logger: Logger | None = None):
        """Initialize the entity resolution service.

        Args:
            logger: Optional logger instance, creates new one if not provided
        """
        self.logger = logger or Logger(__name__)

    def resolve(
        self, patterns: list[str], type_filter: str | None, format_type: str
    ) -> EntityResolution:
        """Determine what entities to include based on patterns and type filter.

        Args:
            patterns: List of patterns (e.g., ["w/*", "c/prod-*"])
            type_filter: Optional entity type filter ('workspace', 'context', 'component')
            format_type: Output format type ('flat' or 'nested')

        Returns:
            EntityResolution with details about what to include

        Raises:
            ValueError: If pattern/type combination is invalid

        Examples:
            - patterns=["w/*"], type_filter="component" → only components
            - patterns=["cm/*"], type_filter=None → only components (filter parents)
            - patterns=["c/*"], type_filter=None → contexts and components
            - patterns=["c/*"], type_filter="workspace" → ERROR (invalid)
        """
        # Determine primary entity type from pattern
        primary_entity = self._get_primary_entity_type(patterns)

        # Start with all entities
        included_entities = {"workspaces", "contexts", "components"}
        filter_parents = False

        # Apply pattern-based filtering
        if primary_entity:
            if primary_entity == "components":
                # cm/* patterns - only components
                included_entities = {"components"}
                filter_parents = True
            elif primary_entity == "contexts":
                # c/* patterns - contexts and their components
                included_entities = {"contexts", "components"}
                filter_parents = True
            elif primary_entity == "workspaces":
                if format_type == "flat":
                    # w/* patterns in flat format - for table display, only show workspaces
                    # This provides a better default behavior for table output
                    included_entities = {"workspaces"}
                    filter_parents = False
                else:
                    # w/* patterns in nested format - only show workspaces at top level
                    # Contexts and components will be nested inside workspaces
                    included_entities = {"workspaces"}
                    filter_parents = False
            # Other patterns include everything by default

        # Apply type filter if specified
        if type_filter:
            # Normalize type filter
            type_map = {
                "workspace": "workspaces",
                "context": "contexts",
                "component": "components",
            }
            requested_type = type_map.get(type_filter, type_filter)

            # Validate the combination
            self._validate_combination(primary_entity, requested_type, patterns)

            # For type filtering, we only return the requested type
            included_entities = {requested_type}

        self.logger.debug(
            f"Entity resolution - primary: {primary_entity}, "
            f"included: {included_entities}, filter_parents: {filter_parents}"
        )

        return EntityResolution(
            primary_entity=primary_entity,
            included_entities=included_entities,
            filter_parents=filter_parents,
        )

    def _get_primary_entity_type(self, patterns: list[str]) -> str | None:
        """Determine the primary entity type from pattern prefix.

        Args:
            patterns: List of patterns used in the query

        Returns:
            Primary entity type ('workspaces', 'contexts', 'components') or None
        """
        if not patterns:
            return None

        # Check the first pattern to determine primary type
        pattern = patterns[0]

        if pattern.startswith(("w/", "workspace/")):
            return "workspaces"
        elif pattern.startswith(("c/", "context/")):
            return "contexts"
        elif pattern.startswith(("cm/", "component/")):
            return "components"

        return None  # filesystem or other patterns

    def _validate_combination(
        self, primary_entity: str | None, requested_type: str, patterns: list[str]
    ) -> None:
        """Validate that the pattern/type combination is valid.

        Args:
            primary_entity: Entity type determined from pattern
            requested_type: Entity type requested via --type filter
            patterns: Original patterns for error message

        Raises:
            ValueError: If the combination is invalid
        """
        self.logger.debug(
            f"Validating combination: primary_entity={primary_entity}, "
            f"requested_type={requested_type}, patterns={patterns}"
        )

        # Define invalid combinations
        invalid_combinations = [
            # Can't get workspaces from context patterns
            primary_entity == "contexts" and requested_type == "workspaces",
            # Can't get workspaces or contexts from component patterns
            primary_entity == "components"
            and requested_type in ["workspaces", "contexts"],
        ]

        for condition in invalid_combinations:
            if condition:
                pattern_str = patterns[0] if patterns else "unknown"
                # Create a more specific error message based on the condition
                if primary_entity == "contexts" and requested_type == "workspaces":
                    error_msg = (
                        f"Invalid combination: pattern '{pattern_str}' cannot return workspaces. "
                        f"Context patterns (c/*) can only return contexts and components."
                    )
                elif primary_entity == "components" and requested_type in [
                    "workspaces",
                    "contexts",
                ]:
                    error_msg = (
                        f"Invalid combination: pattern '{pattern_str}' cannot return {requested_type}. "
                        f"Component patterns (cm/*) can only return components."
                    )
                else:
                    error_msg = f"Invalid combination: pattern '{pattern_str}' cannot return {requested_type}."

                raise ValueError(error_msg)
