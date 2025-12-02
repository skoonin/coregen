"""
Field discovery service for Pydantic model introspection.

This module provides field discovery capabilities for the filtering system,
enabling intelligent filtering on both defined model fields and user-defined
custom fields found in YAML configurations.
"""

from __future__ import annotations

import difflib
from typing import Any

from pydantic import BaseModel

from coregen.common.field_types import FieldInfo, FieldType
from coregen.common.logger import Logger
from coregen.config_model.access import ConfigAccess


class FieldDiscovery:
    """Service for discovering and validating fields in Pydantic models.

    This service uses Pydantic model introspection to discover:
    - Base model fields defined in the Pydantic model
    - Custom user fields added via ConfigDict(extra="allow")
    - Nested fields like config.active, vars.helm_chart_version

    Attributes:
        config_access: Access to configuration elements for field discovery
        logger: Logger instance for this service
    """

    def __init__(self, config_access: ConfigAccess, logger: Logger | None = None):
        """Initialize the field discovery service.

        Args:
            config_access: ConfigAccess instance for configuration lookups
            logger: Optional logger instance, creates new one if not provided
        """
        self.config_access = config_access
        self.logger = logger or Logger(__name__)

    def discover_fields(self, entity_type: str) -> dict[str, FieldInfo]:
        """Discover all fields for a specific entity type.

        Args:
            entity_type: Type of entity ("workspace", "context", or "component")

        Returns:
            Dictionary mapping field names to FieldInfo objects

        Raises:
            ValueError: If entity_type is not supported
        """
        self.logger.info(f"Discovering fields for entity type: {entity_type}")

        if entity_type not in ("workspace", "context", "component"):
            raise ValueError(f"Unsupported entity type: {entity_type}")

        # Get sample entities to analyze
        sample_entities = self._get_sample_entities(entity_type)
        if not sample_entities:
            self.logger.info(
                f"No {entity_type} entities found for field discovery. "
                f"Verify that your configuration files contain {entity_type} definitions."
            )
            return {}

        # Discover fields from samples
        fields = {}

        # Discover from first entity's model definition
        first_entity = sample_entities[0]
        model_fields = self._discover_model_fields(first_entity)
        fields.update(model_fields)

        # Discover custom fields from all entities
        custom_fields = self._discover_custom_fields(sample_entities)
        fields.update(custom_fields)

        # Discover nested fields
        nested_fields = self._discover_nested_fields(sample_entities, entity_type)
        fields.update(nested_fields)

        self.logger.info(f"Discovered {len(fields)} fields for {entity_type}")
        self.logger.debug(f"Field names: {list(fields.keys())}")
        return fields

    def get_field_suggestions(self, partial_name: str, entity_type: str) -> list[str]:
        """Get field name suggestions for partial matches.

        Args:
            partial_name: Partial or misspelled field name
            entity_type: Type of entity to search within

        Returns:
            List of suggested field names, sorted by similarity
        """
        available_fields = self.discover_fields(entity_type)
        field_names = list(available_fields.keys())

        # Use difflib for fuzzy matching
        suggestions = difflib.get_close_matches(
            partial_name,
            field_names,
            n=3,  # Return up to 3 suggestions
            cutoff=0.6,  # Minimum similarity threshold
        )

        return suggestions

    def validate_field_exists(self, field_path: str, entity_type: str) -> bool:
        """Validate that a field path exists for the given entity type.

        Args:
            field_path: Dot-separated field path (e.g., "config.active")
            entity_type: Type of entity to validate against

        Returns:
            True if field exists, False otherwise
        """
        available_fields = self.discover_fields(entity_type)
        return field_path in available_fields

    def _get_sample_entities(self, entity_type: str) -> list[BaseModel]:
        """Get sample entities for field discovery.

        Args:
            entity_type: Type of entity to sample

        Returns:
            List of sample entity instances
        """
        entities: list[BaseModel] = []

        try:
            if entity_type == "workspace":
                # Get a few workspaces for sampling
                workspaces = self.config_access.find_workspaces("*")
                entities.extend(workspaces[:5])  # Sample up to 5 workspaces

            elif entity_type == "context":
                # Get contexts from all workspaces
                workspaces = self.config_access.find_workspaces("*")
                for workspace in workspaces[:3]:  # Sample from first 3 workspaces
                    contexts = self.config_access.get_all_contexts(workspace)
                    for context_name, context in list(contexts.items())[
                        :3
                    ]:  # Sample up to 3 contexts per workspace
                        entities.append(context)
                        if len(entities) >= 10:  # Limit total samples
                            break
                    if len(entities) >= 10:
                        break

            elif entity_type == "component":
                # Get components from contexts
                workspaces = self.config_access.find_workspaces("*")
                for workspace in workspaces[:2]:  # Sample from first 2 workspaces
                    contexts = self.config_access.get_all_contexts(workspace)
                    for context_name, context in list(contexts.items())[
                        :2
                    ]:  # Sample from first 2 contexts
                        components = context.get_all_components()
                        entities.extend(
                            list(components.values())[:5]
                        )  # Sample up to 5 components
                        if len(entities) >= 15:  # Limit total samples
                            break
                    if len(entities) >= 15:
                        break

        except Exception as e:
            self.logger.info(
                f"Failed to sample {entity_type} entities: {e}. "
                f"Check that your configuration files are valid and accessible."
            )

        return entities

    def _discover_model_fields(self, entity: BaseModel) -> dict[str, FieldInfo]:
        """Discover fields defined in the Pydantic model.

        Args:
            entity: Pydantic model instance to analyze

        Returns:
            Dictionary of model fields
        """
        fields = {}

        for field_name, field_info in entity.model_fields.items():
            # Skip internal fields
            if field_name.startswith("_") or field_name in ("contexts", "components"):
                continue

            field_type = self._detect_field_type_from_annotation(field_info.annotation)
            description = (
                field_info.description if hasattr(field_info, "description") else None
            )
            default_value = (
                field_info.default if hasattr(field_info, "default") else None
            )

            fields[field_name] = FieldInfo(
                name=field_name,
                field_type=field_type,
                source="model",
                description=description,
                default_value=default_value,
            )

        return fields

    def _discover_custom_fields(
        self, entities: list[BaseModel]
    ) -> dict[str, FieldInfo]:
        """Discover custom fields from model_extra across entities.

        Args:
            entities: List of entity instances to analyze

        Returns:
            Dictionary of custom fields
        """
        custom_fields = {}

        for entity in entities:
            if not hasattr(entity, "model_extra"):
                continue

            for field_name, field_value in entity.model_extra.items():
                # Skip if already discovered
                if field_name in custom_fields:
                    continue

                field_type = self._detect_field_type_from_value(field_value)

                custom_fields[field_name] = FieldInfo(
                    name=field_name,
                    field_type=field_type,
                    source="custom",
                    description=f"Custom field found in YAML configuration",
                )

        return custom_fields

    def _discover_nested_fields(
        self, entities: list[BaseModel], entity_type: str
    ) -> dict[str, FieldInfo]:
        """Discover nested fields like config.active, vars.helm_chart_version.

        This method discovers 2-level nested fields from Pydantic models:
        - For components: config.* fields from the structured ComponentConfig model
        - For all entities: <any_dict>.* fields from dictionaries in model_extra

        Common patterns discovered:
        - config.active, config.priority (component structured fields)
        - vars.helm_chart_version, versions.helmfile (custom dict fields)
        - metadata.owner, tool_versions.terraform (custom dict fields)

        Note: Only supports 2-level nesting (e.g., versions.helmfile).
        Deeper nesting (e.g., metadata.owner.email) is not discovered.

        Args:
            entities: List of entity instances to analyze
            entity_type: Type of entity being analyzed

        Returns:
            Dictionary of nested fields (field_path -> FieldInfo)
        """
        nested_fields = {}

        for entity in entities:
            # Component-specific: discover config.* fields from structured model
            if entity_type == "component" and hasattr(entity, "config"):
                config = entity.config
                for field_name, field_info in config.model_fields.items():
                    nested_path = f"config.{field_name}"
                    field_type = self._detect_field_type_from_annotation(
                        field_info.annotation
                    )

                    nested_fields[nested_path] = FieldInfo(
                        name=nested_path,
                        field_type=field_type,
                        source="nested",
                        nested_path="config",
                        description=f"Component configuration field",
                    )

            # All entities: discover nested fields from dicts in model_extra
            model_extra = getattr(entity, "model_extra", {})
            for key, value in model_extra.items():
                if isinstance(value, dict):
                    for nested_name, nested_value in value.items():
                        nested_path = f"{key}.{nested_name}"
                        field_type = self._detect_field_type_from_value(nested_value)

                        # Determine appropriate description based on context
                        if entity_type == "component" and key == "vars":
                            description = "Component variable field"
                        else:
                            description = f"{entity_type.capitalize()} custom nested field from '{key}'"

                        nested_fields[nested_path] = FieldInfo(
                            name=nested_path,
                            field_type=field_type,
                            source="nested",
                            nested_path=key,
                            description=description,
                        )

        return nested_fields

    def _detect_field_type_from_annotation(self, annotation: Any) -> FieldType:
        """Detect field type from Pydantic field annotation.

        Args:
            annotation: Pydantic field annotation

        Returns:
            Detected field type
        """
        # Handle string representations
        if isinstance(annotation, str):
            if annotation in ("str", "string"):
                return FieldType.STRING
            elif annotation in ("bool", "boolean"):
                return FieldType.BOOLEAN
            elif annotation in ("int", "integer"):
                return FieldType.INTEGER
            elif annotation in ("float"):
                return FieldType.FLOAT

        # Handle direct type comparisons
        if annotation == str:
            return FieldType.STRING
        elif annotation == bool:
            return FieldType.BOOLEAN
        elif annotation == int:
            return FieldType.INTEGER
        elif annotation == float:
            return FieldType.FLOAT
        elif annotation == dict:
            return FieldType.DICT
        elif annotation == list:
            return FieldType.LIST

        # Handle Union types like int | None (Python 3.10+ syntax and typing.Union)
        if hasattr(annotation, "__origin__"):
            origin = annotation.__origin__
            if origin == list:
                return FieldType.LIST
            elif origin == dict:
                return FieldType.DICT
            elif hasattr(annotation, "__args__"):
                # For Union types like int | None, check the first non-None type
                args = annotation.__args__
                for arg in args:
                    if arg is not type(None):
                        return self._detect_field_type_from_annotation(arg)

        # Handle Python 3.10+ union syntax (types.UnionType)
        if (
            hasattr(annotation, "__class__")
            and annotation.__class__.__name__ == "UnionType"
        ):
            # For int | None style unions, get the non-None type
            if hasattr(annotation, "__args__"):
                args = annotation.__args__
                for arg in args:
                    if arg is not type(None):
                        return self._detect_field_type_from_annotation(arg)

        # Handle typing constructs
        if hasattr(annotation, "__name__"):
            name = annotation.__name__
            if name == "str":
                return FieldType.STRING
            elif name == "bool":
                return FieldType.BOOLEAN
            elif name == "int":
                return FieldType.INTEGER
            elif name == "float":
                return FieldType.FLOAT

        # Default to string for complex or unknown types
        return FieldType.STRING

    def _detect_field_type_from_value(self, value: Any) -> FieldType:
        """Detect field type from actual value.

        Args:
            value: Actual value to analyze

        Returns:
            Detected field type
        """
        # Handle None values explicitly
        if value is None:
            self.logger.debug("Field value is None, returning UNKNOWN")
            return FieldType.UNKNOWN

        # Check bool before int since bool is a subclass of int
        if isinstance(value, bool):
            return FieldType.BOOLEAN
        elif isinstance(value, int):
            return FieldType.INTEGER
        elif isinstance(value, float):
            return FieldType.FLOAT
        elif isinstance(value, dict):
            return FieldType.DICT
        elif isinstance(value, list):
            return FieldType.LIST
        elif isinstance(value, str):
            return FieldType.STRING
        else:
            self.logger.debug(
                f"Unknown field type detected: {type(value).__name__} for value: {value!r}"
            )
            return FieldType.UNKNOWN
