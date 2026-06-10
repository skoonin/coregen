"""Service for handling config schema operations."""

from typing import Any

from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context
from coregen.config_model.models.settings import CoregenSettings, get_settings
from coregen.config_model.models.workspace import WorkspaceConfig
from coregen.services.services_base import ServicesBase

# Get settings instance at module level for default values
settings = get_settings()

# Constants for schema types
SCHEMA_TYPE_SETTINGS = "settings"
SCHEMA_TYPE_WORKSPACE = "workspace"
SCHEMA_TYPE_CONTEXT = "context"
SCHEMA_TYPE_COMPONENT = "component"
SCHEMA_TYPE_ALL = "all"

SCHEMA_TYPES = [
    SCHEMA_TYPE_SETTINGS,
    SCHEMA_TYPE_WORKSPACE,
    SCHEMA_TYPE_CONTEXT,
    SCHEMA_TYPE_COMPONENT,
]


class ConfigSchemaService(ServicesBase):
    """Service for handling schema operations."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize schema service."""
        super().__init__(*args, **kwargs)
        # Map schema types to their model classes using strings instead of enums
        self._model_map: dict[str, type] = {
            SCHEMA_TYPE_SETTINGS: CoregenSettings,
            SCHEMA_TYPE_WORKSPACE: WorkspaceConfig,
            SCHEMA_TYPE_CONTEXT: Context,
            SCHEMA_TYPE_COMPONENT: Component,
        }
        self.logger.debug(
            f"Initialized ConfigSchemaService with {len(self._model_map)} schema types"
        )
        self.logger.debug(f"Available schema types: {list(self._model_map.keys())}")

    def get_schema_types(self) -> list[str]:
        """
        Get the list of valid schema types.

        Returns:
            List of valid schema types
        """
        return SCHEMA_TYPES

    def get_schema(self, schema_type: str) -> Any:
        """
        Generate schema for a specific model.

        Args:
            schema_type: The type of model to generate schema for

        Returns:
            The schema data (raw, not pre-formatted)
        """
        self.logger.debug(f"get_schema called with schema_type: '{schema_type}'")

        if schema_type not in self._model_map:
            self.logger.debug(f"Schema type '{schema_type}' not found in model map")
            self.logger.debug(f"Available types: {list(self._model_map.keys())}")
            raise ValueError(f"Unknown schema type: {schema_type}")

        model_class = self._model_map[schema_type]
        self.logger.debug(
            f"Mapped schema type '{schema_type}' to model class: {model_class}"
        )

        schema_data = settings.get_model_schema(model_class)
        self.logger.debug(
            f"Schema data type: {type(schema_data)}, size: {len(str(schema_data))} chars"
        )

        return schema_data

    def process_schema_request(
        self, schema_types: list[str], output_format: OutputFormat
    ) -> dict[str, Any]:
        """
        Process a request for schema generation.

        This method handles the logic for generating schemas based on the requested types,
        including handling "all" and multiple schema types.

        Args:
            schema_types: List of schema types to generate
            output_format: The output format to use

        Returns:
            Dictionary with results and metadata for the UI layer to handle
        """
        self.logger.debug(
            f"process_schema_request called with types: {schema_types}, format: {output_format}"
        )

        result = {
            "schema_data": {},
            "valid_types": [],
            "unknown_types": [],
            "has_multiple": False,
            "output_format": output_format,
        }
        self.logger.debug("Initialized result dictionary")

        # Determine if 'all' was requested
        all_requested = any(st.lower() == SCHEMA_TYPE_ALL for st in schema_types)
        self.logger.debug(f"'all' requested: {all_requested}")

        # For 'all', generate all schemas
        if all_requested:
            schemas_to_generate = SCHEMA_TYPES
            self.logger.debug(f"Will generate all {len(SCHEMA_TYPES)} schema types")
        else:
            # Filter to valid schema types only
            self.logger.debug("Filtering requested types to valid types")
            schemas_to_generate = [
                st.lower()
                for st in schema_types
                if st.lower() != SCHEMA_TYPE_ALL and st.lower() in self._model_map
            ]
            self.logger.debug(f"Valid types after filtering: {schemas_to_generate}")

            # Identify unknown schema types
            result["unknown_types"] = [
                st
                for st in schema_types
                if st.lower() != SCHEMA_TYPE_ALL and st.lower() not in self._model_map
            ]

            if result["unknown_types"]:
                self.logger.debug(
                    f"Unknown types identified: {result['unknown_types']}"
                )

        result["valid_types"] = schemas_to_generate
        result["has_multiple"] = len(schemas_to_generate) > 1

        # Generate schemas for each valid type
        self.logger.debug(
            f"Starting schema generation for {len(schemas_to_generate)} types"
        )
        for i, schema_type in enumerate(schemas_to_generate, 1):
            self.logger.debug(
                f"Processing type {i}/{len(schemas_to_generate)}: '{schema_type}'"
            )
            try:
                schema_data = self.get_schema(schema_type)
                result["schema_data"][schema_type] = schema_data
                self.logger.debug(
                    f"Successfully added schema for '{schema_type}' to results"
                )
            except Exception as e:
                self.logger.error(f"Error generating schema for {schema_type}: {e}")
                self.logger.debug(
                    f"Exception type: {type(e).__name__}, details: {str(e)}"
                )
                # Add error to the result instead of raising to allow partial success
                if "errors" not in result:
                    result["errors"] = {}
                result["errors"][schema_type] = str(e)

        # Summary debug message
        schema_data_dict: dict[str, Any] = result["schema_data"]
        errors_dict: dict[str, str] = result.get("errors", {})
        successful_count = len(schema_data_dict)
        error_count = len(errors_dict)
        self.logger.debug(
            f"Schema generation completed - successful: {successful_count}, errors: {error_count}"
        )
        self.logger.debug(f"Final result keys: {list(result.keys())}")

        return result
