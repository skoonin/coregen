"""
Filter service for applying filters to configuration elements.

This module provides a centralized filtering system that can be used across
all services that need to filter workspaces, contexts, and components.
"""

import re
from typing import Any

from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess


class FilterValidationError(ValueError):
    """Raised when a filter expression or pattern/filter combination is invalid.

    Subclasses ``ValueError`` so existing handlers keep catching it, while
    letting the CLI distinguish user-input filter errors (exit 2) from runtime
    errors (exit 1).
    """


class FilterService:
    """Service for parsing and applying filter expressions to configuration elements.

    This service handles:
    - Parsing filter expressions into structured specifications
    - Applying filters to collections of configuration elements
    - Type conversion and value comparison
    - Future: Field inheritance and hierarchical filtering

    Attributes:
        config_access: Access to configuration elements for lookups
        logger: Logger instance for this service
    """

    # Bare component config field names mapped to their config.<field> path, so
    # "component.required" resolves the same as "component.config.required".
    _COMPONENT_FIELD_ALIASES = {
        "active": "config.active",
        "for_commit": "config.for_commit",
        "required": "config.required",
        "priority": "config.priority",
    }

    def __init__(self, config_access: ConfigAccess, logger: Logger | None = None):
        """Initialize the filter service.

        Args:
            config_access: ConfigAccess instance for configuration lookups
            logger: Optional logger instance, creates new one if not provided
        """
        self.config_access = config_access
        self.logger = logger or Logger(__name__)

    def parse_filter_expression(self, filter_string: str) -> dict[str, Any]:
        """Parse a filter expression into a structured filter specification.

        Args:
            filter_string: Filter expression string

        Returns:
            Filter specification dictionary
        """
        self.logger.debug(f"Parsing filter expression: {filter_string}")

        # Initialize filter specification
        filter_spec: dict[str, Any] = {
            "entity_type": None,
            "property": None,
            "operator": "=",
            "value": None,
        }

        # Check for entity type qualification
        if filter_string.startswith(("workspace.", "context.", "component.")):
            # Split into entity type and property
            entity_type, rest = filter_string.split(".", 1)
            filter_spec["entity_type"] = entity_type
            filter_string = rest

        # Detect the operator, longest first so e.g. ">=" wins over ">" and
        # "!=" over "=".
        for operator in ("!=", "~=", "=~", ">=", "<=", ">", "<", "="):
            if operator in filter_string:
                property_name, value = filter_string.split(operator, 1)
                filter_spec["property"] = property_name.strip()
                filter_spec["operator"] = operator
                filter_spec["value"] = value.strip()
                break
        else:
            # No operator: treat as an existence check (property=true).
            filter_spec["property"] = filter_string.strip()
            filter_spec["operator"] = "="
            filter_spec["value"] = True

        # Reject structurally malformed expressions at the boundary.
        if not filter_spec["property"]:
            raise FilterValidationError(
                f"Invalid filter expression: missing property name before "
                f"'{filter_spec['operator']}'."
            )

        # Surface an invalid regex at parse time instead of deferring the failure
        # to apply time where it is harder to attribute.
        if filter_spec["operator"] in ("~=", "=~") and isinstance(
            filter_spec["value"], str
        ):
            try:
                re.compile(filter_spec["value"])
            except re.error as e:
                raise FilterValidationError(
                    f"Invalid regex pattern '{filter_spec['value']}': {e}"
                ) from e

        # Convert only none/null to Python None (case-insensitive), for non-regex
        # operators. Int/bool/float coercion is intentionally NOT done here:
        # _compare_values coerces the value against each field's actual type,
        # which also lets custom string fields whose values look numeric or
        # boolean match. Regex operators keep none/null as literal patterns.
        if (
            isinstance(filter_spec["value"], str)
            and filter_spec["operator"] not in ("~=", "=~")
            and filter_spec["value"].lower() in ("none", "null")
        ):
            filter_spec["value"] = None

        return filter_spec

    def apply_filters_complete(
        self,
        complete_model: dict[str, dict[str, Any]],
        filters: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Apply filters to complete model where all relationships are available.

        This works with a complete model where all parent-child relationships
        are intact, allowing filters like "context.environment" to work even when
        selecting components.

        Args:
            complete_model: Complete model with 'workspaces', 'contexts', 'components'
            filters: List of parsed filter specifications

        Returns:
            Filtered complete model maintaining the same structure
        """
        if not filters:
            return complete_model

        self.logger.debug(f"Applying {len(filters)} filters to complete model")

        # Create a copy to avoid modifying the original
        result = {
            "workspaces": complete_model.get("workspaces", {}).copy(),
            "contexts": complete_model.get("contexts", {}).copy(),
            "components": complete_model.get("components", {}).copy(),
        }

        # Apply each filter
        for filter_spec in filters:
            self._apply_filter_complete(result, filter_spec)

        return result

    def _apply_filter_complete(
        self, complete_model: dict[str, dict[str, Any]], filter_spec: dict[str, Any]
    ) -> None:
        """
        Apply a single filter to complete model.

        This method can handle cross-entity filters because all relationships
        are available in the complete model.

        Args:
            complete_model: Complete model to filter
            filter_spec: Filter specification
        """
        self.logger.debug(f"Applying filter to complete model: {filter_spec}")

        # Extract filter components
        entity_type = filter_spec.get("entity_type")
        property_name = filter_spec["property"]
        operator = filter_spec["operator"]
        value = filter_spec["value"]

        # workspace and context are special cases
        # this is to allow filtering components by their parent's properties
        if entity_type in ["workspace", "context"]:
            self._apply_cross_entity_filter_complete(
                complete_model, entity_type, property_name, operator, value
            )
            self.logger.debug(
                f" Applied cross-entity filter: {entity_type}.{property_name} {operator} {value}"
            )
            return

        # Check if this is a cross-entity filter (e.g., filtering components by context.environment)
        if "." in property_name and not entity_type:
            # Parse the property path more robustly
            parent_type, actual_property = self._parse_property_path(property_name)

            if parent_type and parent_type in self._get_valid_entity_types():
                # This is a cross-entity filter
                self._apply_cross_entity_filter_complete(
                    complete_model, parent_type, actual_property, operator, value
                )
                self.logger.debug(
                    f"Applied cross-entity filter: {parent_type}.{actual_property} {operator} {value}"
                )
                return

        # Apply filter based on entity type
        if entity_type == "workspace" or entity_type is None:
            self._filter_workspaces_complete(
                complete_model, property_name, operator, value
            )
        if entity_type == "context" or entity_type is None:
            self._filter_contexts_complete(
                complete_model, property_name, operator, value
            )
        if entity_type == "component" or entity_type is None:
            self._filter_components_complete(
                complete_model, property_name, operator, value
            )

    def _apply_cross_entity_filter_complete(
        self,
        complete_model: dict[str, dict[str, Any]],
        parent_type: str,
        property_name: str,
        operator: str,
        value: Any,
    ) -> None:
        """
        Apply cross-entity filters (e.g., filter components by context.environment).

        Args:
            complete_model: Complete model
            parent_type: Type of parent entity (workspace, context)
            property_name: Property on the parent entity
            operator: Comparison operator
            value: Value to compare
        """
        self.logger.debug(
            f" Applying cross-entity filter: {parent_type}.{property_name} {operator} {value}"
        )

        if parent_type == "context":
            # Filter components based on their context's properties
            filtered_components = {}
            for comp_key, component in complete_model["components"].items():
                # Extract context name from component key
                context_name = comp_key.split("/")[0]

                # Find the context
                if context_name in complete_model["contexts"]:
                    context = complete_model["contexts"][context_name]
                    # Check if context property matches
                    if self._compare_values(
                        self._get_nested_attr(context, property_name), operator, value
                    ):
                        filtered_components[comp_key] = component
                    else:
                        self.logger.debug(
                            f" Filtering out component {comp_key} - "
                            f"context.{property_name} doesn't match"
                        )

            complete_model["components"] = filtered_components

            # Also filter contexts themselves
            filtered_contexts = {
                name: ctx
                for name, ctx in complete_model["contexts"].items()
                if self._compare_values(
                    self._get_nested_attr(ctx, property_name), operator, value
                )
            }
            complete_model["contexts"] = filtered_contexts

        elif parent_type == "workspace":
            # Filter contexts and components based on workspace properties
            filtered_workspaces = {
                name: ws
                for name, ws in complete_model["workspaces"].items()
                if self._compare_values(
                    self._get_nested_attr(ws, property_name), operator, value
                )
            }
            complete_model["workspaces"] = filtered_workspaces

            # Filter contexts belonging to filtered workspaces
            filtered_contexts = {}
            for ctx_name, context in complete_model["contexts"].items():
                if (
                    hasattr(context, "workspace")
                    and context.workspace in filtered_workspaces
                ):
                    filtered_contexts[ctx_name] = context
            complete_model["contexts"] = filtered_contexts

            # Filter components belonging to filtered contexts
            self._prune_components_to_contexts(
                complete_model, set(filtered_contexts.keys())
            )

    def _filter_workspaces_complete(
        self,
        complete_model: dict[str, dict[str, Any]],
        property_name: str,
        operator: str,
        value: Any,
    ) -> None:
        """
        Filter workspaces and cascade to contexts/components in complete model.

        Args:
            complete_model: Complete model
            property_name: Property to filter on
            operator: Comparison operator
            value: Value to compare
        """
        # Filter workspaces
        filtered_workspaces = self._filter_entities_by_property(
            complete_model["workspaces"], property_name, operator, value, "workspace"
        )
        complete_model["workspaces"] = filtered_workspaces

        # Cascade: remove contexts from filtered-out workspaces
        remaining_workspace_names = set(filtered_workspaces.keys())

        filtered_contexts = {}
        for ctx_name, context in complete_model["contexts"].items():
            if (
                hasattr(context, "workspace")
                and context.workspace in remaining_workspace_names
            ):
                filtered_contexts[ctx_name] = context
            else:
                self.logger.debug(
                    f" Removing context {ctx_name} - workspace filtered out"
                )
        complete_model["contexts"] = filtered_contexts

        # Cascade: remove components from filtered-out contexts
        self._prune_components_to_contexts(
            complete_model, set(filtered_contexts.keys())
        )

    def _filter_contexts_complete(
        self,
        complete_model: dict[str, dict[str, Any]],
        property_name: str,
        operator: str,
        value: Any,
    ) -> None:
        """
        Filter contexts and cascade to components in complete model.

        Args:
            complete_model: Complete model
            property_name: Property to filter on
            operator: Comparison operator
            value: Value to compare
        """
        # Filter contexts
        filtered_contexts = self._filter_entities_by_property(
            complete_model["contexts"], property_name, operator, value, "context"
        )
        complete_model["contexts"] = filtered_contexts

        # Cascade: remove components from filtered-out contexts
        self._prune_components_to_contexts(
            complete_model, set(filtered_contexts.keys())
        )

    def _prune_components_to_contexts(
        self, complete_model: dict[str, dict[str, Any]], context_names: set[str]
    ) -> None:
        """Drop components whose owning context is no longer in the model."""
        complete_model["components"] = {
            comp_key: component
            for comp_key, component in complete_model["components"].items()
            if comp_key.split("/")[0] in context_names
        }

    def _filter_components_complete(
        self,
        complete_model: dict[str, dict[str, Any]],
        property_name: str,
        operator: str,
        value: Any,
    ) -> None:
        """
        Filter components in complete model.

        Args:
            complete_model: Complete model
            property_name: Property to filter on
            operator: Comparison operator
            value: Value to compare
        """
        property_name = self._COMPONENT_FIELD_ALIASES.get(property_name, property_name)

        # Filter components directly
        filtered_components = {}
        for comp_key, component in complete_model["components"].items():
            if self._compare_values(
                self._get_nested_attr(component, property_name), operator, value
            ):
                filtered_components[comp_key] = component
            else:
                self.logger.debug(
                    f" Filtering out component {comp_key} - "
                    f"{property_name} doesn't match"
                )

        complete_model["components"] = filtered_components

    def _filter_entities_by_property(
        self,
        entities: dict[str, Any],
        property_name: str,
        operator: str,
        value: Any,
        entity_type: str,
    ) -> dict[str, Any]:
        """Generic method to filter entities based on property, operator, and value.

        Args:
            entities: Dictionary of entities to filter
            property_name: Name of the property to filter on
            operator: Comparison operator
            value: Value to compare against
            entity_type: Type of entity for logging purposes

        Returns:
            Dictionary of filtered entities
        """
        # Use dictionary comprehension for concise filtering
        filtered_entities = {
            name: entity
            for name, entity in entities.items()
            if self._compare_values(
                self._get_nested_attr(entity, property_name), operator, value
            )
        }

        # Log filtered out entities
        for name in entities:
            if name not in filtered_entities:
                self.logger.debug(f"Filtering out {entity_type}: {name}")

        return filtered_entities

    def _get_nested_attr(self, obj: Any, property_path: str) -> Any:
        """Get a nested property value from a Pydantic model using getattr chains.

        Uses native Pydantic attribute access with support for nested dictionaries
        and the special get_config() method for backward compatibility.

        Args:
            obj: Pydantic model object to get property from
            property_path: Dot-separated path to property (e.g., "config.active")

        Returns:
            Property value or None if not found
        """
        if not property_path:
            return None

        # Split property path into parts
        parts = property_path.split(".")
        current = obj

        try:
            # Navigate through the property path
            for part in parts:
                # Handle dictionary access
                if hasattr(current, "__getitem__") and not isinstance(
                    current, (str, list)
                ):
                    if part in current:
                        current = current[part]
                    else:
                        return None
                # Handle attribute access
                elif hasattr(current, part):
                    current = getattr(current, part)
                # Handle special config attribute for components
                elif part == "config" and hasattr(current, "get_config"):
                    current = current.get_config()
                else:
                    # Property doesn't exist, return None
                    return None

            return current

        except (AttributeError, TypeError, KeyError) as e:
            self.logger.debug(
                f"Failed to get nested attribute '{property_path}' from {type(obj)}: {e}"
            )
            return None

    def get_workspace_for_context(self, context: Any) -> str | None:
        """Get the workspace name for a context.

        Args:
            context: Context to get workspace for

        Returns:
            Workspace name or None if not found
        """
        workspace = self.config_access.find_workspace_for_context(context)
        return workspace.name if workspace is not None else None

    def _compare_values(self, left: Any, operator: str, right: Any) -> bool:
        """Compare two values using the specified operator.

        Args:
            left: Left operand
            operator: Comparison operator
            right: Right operand

        Returns:
            Result of comparison
        """
        # Handle None values
        if left is None:
            # Only equal to None, not equal to everything else
            if operator == "=":
                return right is None
            elif operator == "!=":
                return right is not None
            elif operator in ("~=", "=~"):
                # Regex operators should continue to regex matching logic below
                # where None will be converted to empty string
                pass
            else:
                return False

        if right is None:
            # Handle cases where user searches for None (e.g., priority=none)
            if operator == "=":
                return left is None
            elif operator == "!=":
                return left is not None
            else:
                # Cannot compare non-None values to None with numeric operators
                return False

        # Handle regex operators BEFORE type conversion
        # This preserves the pattern as a string for regex matching
        if operator == "~=" or operator == "=~":
            # Regex pattern matching (bash-style)
            if isinstance(right, str):
                try:
                    # Convert left to string for regex matching
                    left_str = str(left) if left is not None else ""
                    # Use re.search() for substring matching (like bash =~)
                    # Users can use ^ and $ for anchoring if needed
                    return bool(re.search(right, left_str))
                except re.error as e:
                    # Invalid regex pattern - raise clear error for user
                    error_msg = f"Invalid regex pattern '{right}': {e}"
                    self.logger.error(error_msg)
                    raise ValueError(error_msg) from e
            else:
                return False

        # Convert types if needed (only for non-regex operators).
        # bool must be tested before int/float: bool subclasses int, so the
        # numeric branch would coerce via bool("false") == True for boolean
        # fields compared against raw strings.
        if isinstance(left, bool) and isinstance(right, str):
            if right.lower() == "true":
                right = True
            elif right.lower() == "false":
                right = False
        elif isinstance(left, (int, float)) and isinstance(right, str):
            try:
                right = type(left)(right)
            except (ValueError, TypeError) as e:
                # An ordering comparison against a non-numeric value would raise
                # a confusing TypeError (int > str). Surface a clear filter error.
                if operator in (">", "<", ">=", "<="):
                    raise FilterValidationError(
                        f"Cannot compare numeric field with non-numeric "
                        f"value '{right}' using '{operator}'."
                    ) from e
                # For = / != a numeric field never equals a non-numeric string.

        # Perform comparison
        if operator == "=":
            return bool(left == right)
        elif operator == "!=":
            return bool(left != right)
        elif operator == ">":
            return bool(left > right)
        elif operator == "<":
            return bool(left < right)
        elif operator == ">=":
            return bool(left >= right)
        elif operator == "<=":
            return bool(left <= right)

        # Unknown operator
        self.logger.warning(f"Unknown operator: {operator}")
        return False

    def _parse_property_path(self, property_path: str) -> tuple[str | None, str]:
        """
        Parse a property path into entity type and property name.

        Handles complex property paths with validation for supported entity types.
        Examples:
        - "context.environment" -> ("context", "environment")
        - "workspace.config.name" -> ("workspace", "config.name")
        - "invalid.path" -> (None, "invalid.path")

        Args:
            property_path: Dot-separated property path

        Returns:
            Tuple of (entity_type, property_name) where entity_type may be None
        """
        if not property_path or "." not in property_path:
            return None, property_path

        parts = property_path.split(".", 1)
        potential_entity = parts[0]
        remaining_path = parts[1]

        # Validate entity type
        if potential_entity in self._get_valid_entity_types():
            return potential_entity, remaining_path
        else:
            # Not a valid entity type, treat entire path as property
            return None, property_path

    def _get_valid_entity_types(self) -> set[str]:
        """
        Get the set of valid entity types for filtering.

        Returns:
            Set of valid entity type strings
        """
        return {"workspace", "context", "component"}
