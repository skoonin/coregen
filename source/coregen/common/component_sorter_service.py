"""
ComponentSorterService: Simplified sorting for all entity types.

This service provides consistent ordering across all output formats.
Priority ordering: 0 (highest) → 1 → 2 → ... → None (lowest)

Dependencies do NOT affect sort order. The validation rules (especially Rule 3:
dependencies must have equal/better priority) ensure that sorting by priority
alone produces correct dependency ordering.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Literal


# Custom exception classes for component validation errors
class ComponentValidationError(Exception):
    """Exception raised when component validation fails."""


class ComponentSorterService:
    """Simplified sorting service for all entity types.

    Priority ordering: 0 (highest) → 1 → 2 → ... → None (lowest).
    Components are sorted by priority and name only - dependencies do NOT affect sort order.
    """

    def __init__(self, config: Any = None, **kwargs: Any) -> None:
        """Initialize service. Legacy kwargs are accepted for compatibility."""
        # Accept legacy parameters for backward compatibility
        if config:
            # Extract values from config object if provided
            self.none_priority_value = getattr(config, "none_priority_value", 999)
            self.cycle_break_strategy = getattr(
                config, "cycle_break_strategy", "stable"
            )
            # strict_validation is deprecated - all rules now run always
            _ = getattr(config, "strict_validation", False)  # Accept but ignore
        else:
            self.none_priority_value = kwargs.get("none_priority_value", 999)
            self.cycle_break_strategy = kwargs.get("cycle_break_strategy", "stable")
            # strict_validation is deprecated - all rules now run always
            _ = kwargs.get("strict_validation", False)  # Accept but ignore

    def sort_entities(
        self,
        entities: Sequence[dict[str, Any]] | Sequence[Any],
        entity_type: Literal["workspace", "context", "component"],
        skip_validation: bool = False,
    ) -> list[dict[str, Any]] | list[Any]:
        """Sort entities with consistent ordering rules.

        Args:
            entities: List of entities to sort (dicts or objects)
            entity_type: Type of entity being sorted
            skip_validation: If True, skip validation checks (useful for base branch comparison)

        Returns:
            Sorted list of entities

        Sorting rules by entity type:
        - workspace: alphabetical by name
        - context: alphabetical by workspace then name
        - component: workspace → context → priority → name

        Note: Components are sorted by priority and name only. Dependencies do NOT
        affect sort order. The validation rules (especially Rule 3: dependencies must
        have equal/better priority) ensure that sorting by priority alone produces
        correct dependency ordering.
        """
        if not entities:
            return []

        items = list(entities)

        # Simple alphabetical sorting for workspaces
        if entity_type == "workspace":
            return sorted(items, key=lambda x: self._get_field(x, "name"))

        # Contexts: sort by workspace then name
        if entity_type == "context":
            return sorted(
                items,
                key=lambda x: (
                    self._get_field(x, "workspace"),
                    self._get_field(x, "name"),
                ),
            )

        # Components: sort by priority and name
        # Run validations first (unless skip_validation is True)
        if entity_type == "component":
            if not skip_validation:
                self._validate_components_grouped(items)
            # Simple sort by context, workspace, priority, name
            return sorted(items, key=self._component_sort_key)

        return items

    def _validate_components_grouped(self, components: list[Any]) -> None:
        """Validate components grouped by context.

        Groups components by workspace and context, then validates each group
        independently. This ensures all validation rules are enforced.

        Args:
            components: List of components to validate
        """
        if not components:
            return

        # Group components by workspace and context
        context_groups: dict[tuple[str, str], list[Any]] = defaultdict(list)
        for comp in components:
            workspace = self._get_field(comp, "workspace")
            context = self._get_field(comp, "context")
            context_groups[(workspace, context)].append(comp)

        # Validate each context group independently
        for (workspace, context), context_components in context_groups.items():
            # Create local name index for this context
            local_comp_map = {self._get_field(c, "name"): c for c in context_components}

            # Run all validations
            self._validate_components_always(
                context_components, local_comp_map, workspace, context
            )

    def _validate_components_always(
        self,
        components: list[Any],
        local_comp_map: dict[str, Any],
        workspace: str = "",
        context: str = "",
    ) -> None:
        """Validate critical component rules that always run.

        These validations include:
        - No duplicate priorities within a context
        - Priority components cannot depend on null priority components
        - Dependencies must have equal or better priority (lower number)
        - Null priority components cannot depend on other null components
        - No circular dependencies

        This method collects ALL validation errors before raising, providing a complete
        picture of configuration issues.

        Args:
            components: List of components to validate
            local_comp_map: Mapping of component names to components in this context
            workspace: Workspace name for error messages
            context: Context name for error messages

        Raises:
            ComponentValidationError: Combined error message containing all validation issues found.
                Includes context/workspace information and details for all violations.
        """
        errors: list[str] = []
        context_label = (
            f"workspace '{workspace}', context '{context}'"
            if workspace and context
            else "context group"
        )
        # Check for duplicate priorities
        priority_to_components: dict[int, list[str]] = defaultdict(list)
        for comp in components:
            priority = self._get_priority(comp)
            if priority is not None:
                priority_to_components[priority].append(self._get_field(comp, "name"))

        # Collect duplicate priority errors
        duplicates = {
            pri: comps
            for pri, comps in priority_to_components.items()
            if len(comps) > 1
        }
        if duplicates:
            error_msg = f"Duplicate priority values in {context_label}:"
            for pri, comps in sorted(duplicates.items()):
                error_msg += f"\n  Priority {pri}: {', '.join(sorted(comps))}"
            error_msg += "\nFix: Assign unique priority values to each component."
            errors.append(error_msg)

        # Check dependency priority relationships
        for comp in components:
            comp_name = self._get_field(comp, "name")
            comp_priority = self._get_priority(comp)
            deps = self._get_dependencies(comp)

            for dep_name in deps:
                # Only check dependencies within this context
                if dep_name not in local_comp_map:
                    continue

                dep_comp = local_comp_map[dep_name]
                dep_priority = self._get_priority(dep_comp)

                # Priority component cannot depend on null priority
                if comp_priority is not None and dep_priority is None:
                    error_msg = (
                        f"Invalid priority configuration in {context_label}:\n"
                        f"  Component '{comp_name}' (priority={comp_priority}) cannot depend on "
                        f"'{dep_name}' (priority=null).\n"
                        f"  Fix: Assign priority to '{dep_name}' that is <= {comp_priority}."
                    )
                    errors.append(error_msg)

                # Null priority cannot depend on other null priority
                if comp_priority is None and dep_priority is None:
                    error_msg = (
                        f"Invalid priority configuration in {context_label}:\n"
                        f"  Component '{comp_name}' (priority=null) cannot depend on '{dep_name}' (priority=null).\n"
                        f"  Fix: Assign explicit priority to at least one component."
                    )
                    errors.append(error_msg)

                # Check priority consistency - if A depends on B, then B.priority <= A.priority
                # This is CRITICAL for priority-based sorting to work correctly
                if comp_priority is not None and dep_priority is not None:
                    if dep_priority > comp_priority:
                        error_msg = (
                            f"Priority conflict in {context_label}:\n"
                            f"  Component '{comp_name}' (priority={comp_priority}) depends on\n"
                            f"  Component '{dep_name}' (priority={dep_priority})\n"
                            f"  Fix: '{dep_name}' should have priority <= {comp_priority} (lower numbers deploy earlier)."
                        )
                        errors.append(error_msg)

        # Check for circular dependencies using DFS
        # Collect all unique cycles found
        cycles_found: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def detect_cycle(comp_name: str) -> bool:
            """Detect cycles using DFS. Returns True if cycle found."""
            visited.add(comp_name)
            rec_stack.add(comp_name)
            path.append(comp_name)

            comp = local_comp_map.get(comp_name)
            if comp:
                for dep_name in self._get_dependencies(comp):
                    # Only check dependencies within this context
                    if dep_name not in local_comp_map:
                        continue

                    if dep_name not in visited:
                        if detect_cycle(dep_name):
                            return True
                    elif dep_name in rec_stack:
                        # Found cycle - build cycle path and collect it
                        cycle_start = path.index(dep_name)
                        cycle = path[cycle_start:] + [dep_name]
                        cycles_found.append(cycle)
                        return True

            path.pop()
            rec_stack.remove(comp_name)
            return False

        # Check all components for cycles
        for comp in components:
            comp_name = self._get_field(comp, "name")
            if comp_name not in visited:
                detect_cycle(comp_name)

        # Collect circular dependency errors
        if cycles_found:
            error_msg = f"Circular dependencies detected in {context_label}:"
            for cycle in cycles_found:
                error_msg += f"\n  {' -> '.join(cycle)}"
            error_msg += "\nFix: Remove one of the dependencies to break the cycle(s)."
            errors.append(error_msg)

        # If any errors were collected, raise a combined error
        if errors:
            combined_error = (
                f"\nValidation errors found in {context_label}:\n\n"
                + "\n\n".join(errors)
            )
            raise ComponentValidationError(combined_error)

    def _component_sort_key(self, comp: Any) -> tuple:
        """Generate sort key for a component."""
        return (
            self._get_field(comp, "workspace"),
            self._get_field(comp, "context"),
            self._get_priority(comp) if self._get_priority(comp) is not None else 999,
            self._get_field(comp, "name"),
        )

    def _get_field(self, obj: Any, field: str) -> str:
        """Get field value from dict or object."""
        if isinstance(obj, dict):
            # Handle table format field names
            if field == "name" and "Component" in obj:
                return str(obj["Component"])
            elif field == "workspace" and "Workspace" in obj:
                return str(obj["Workspace"])
            elif field == "context" and "Context" in obj:
                return str(obj["Context"])
            return str(obj.get(field, ""))

        # For objects, try different attribute patterns
        if field == "name":
            return str(getattr(obj, "component_name", getattr(obj, "name", "")))
        elif field == "context":
            return str(getattr(obj, "context_name", getattr(obj, "context", "")))
        elif field == "workspace":
            return str(getattr(obj, "workspace_name", getattr(obj, "workspace", "")))

        return str(getattr(obj, field, ""))

    def _get_priority(self, obj: Any) -> int | None:
        """Get priority value from dict or object."""
        if isinstance(obj, dict):
            # Check table format
            if "Priority" in obj:
                priority_str = obj.get("Priority", "")
                if priority_str and str(priority_str).isdigit():
                    return int(priority_str)
                return None

            # Check direct priority field first (for test compatibility)
            if "priority" in obj and obj["priority"] is not None:
                try:
                    return int(obj["priority"])
                except (ValueError, TypeError):
                    return None

            # Then check config.priority
            config = obj.get("config", {}) or {}
            if isinstance(config, dict):
                priority = config.get("priority")
                if priority is not None:
                    try:
                        return int(priority)
                    except (ValueError, TypeError):
                        return None

            return None

        # For objects - check config.priority first for Component objects
        if hasattr(obj, "config") and hasattr(obj.config, "priority"):
            priority = obj.config.priority
            if priority is None:
                return None
            try:
                return int(priority)
            except (ValueError, TypeError):
                return None

        return getattr(obj, "component_priority", None)

    def _get_dependencies(self, obj: Any) -> list[str]:
        """Get dependencies from dict or object."""
        # Check for legacy accessor function
        if hasattr(self, "_legacy_get_dependencies") and self._legacy_get_dependencies:
            deps = self._legacy_get_dependencies(obj)
            return deps if deps else []

        if isinstance(obj, dict):
            config = obj.get("config", {}) or {}
            deps = config.get("dependencies", []) or []
            # Handle both dict and string dependency formats
            result = []
            for dep in deps:
                if isinstance(dep, dict) and "name" in dep:
                    result.append(dep["name"])
                elif isinstance(dep, str):
                    result.append(dep)
            return result

        # For objects - check config.dependencies first for Component objects
        if hasattr(obj, "config") and hasattr(obj.config, "dependencies"):
            deps = obj.config.dependencies
        else:
            # Check for component_dependencies (used by ComponentChange objects in detect-changes)
            # or regular dependencies attribute
            deps = getattr(
                obj, "component_dependencies", getattr(obj, "dependencies", [])
            )

        if not deps:
            return []

        # Handle both dict and string dependency formats
        result = []
        for dep in deps:
            if isinstance(dep, dict) and "name" in dep:
                result.append(dep["name"])
            elif isinstance(dep, str):
                result.append(dep)
            elif hasattr(dep, "name"):
                result.append(str(getattr(dep, "name")))  # Use getattr for type safety
        return result

    # ========== Legacy Compatibility Methods ==========
    # These methods are maintained for backward compatibility

    def sort_component_dicts(
        self,
        components: Sequence[dict[str, Any]],
        **_kwargs: Any,  # Accepted for backward compatibility
    ) -> list[dict[str, Any]]:
        """Legacy method for sorting component dictionaries.

        This method is maintained for backward compatibility.
        New code should use sort_entities() instead.
        """
        return self.sort_entities(components, "component")

    def sort_changes(
        self,
        changes: Sequence[Any],
        **_kwargs: Any,  # Accepted for backward compatibility
    ) -> list[Any]:
        """Legacy method for sorting change objects.

        This method is maintained for backward compatibility.
        New code should use sort_entities() instead.
        """
        return self.sort_entities(changes, "component")

    def sort_table_rows(
        self,
        rows: Sequence[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Legacy method for sorting table rows.

        This method is maintained for backward compatibility.
        New code should use sort_entities() instead.
        """
        # Store legacy accessor if provided
        self._legacy_get_dependencies = kwargs.get("deps_accessor")

        # Use the new unified method
        result = self.sort_entities(rows, "component")

        # Clear legacy accessor
        self._legacy_get_dependencies = None

        return result
