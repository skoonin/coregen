"""CLI command for displaying model schemas."""

from pathlib import Path
from typing import Annotated, Any

import typer

from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import OutputFormat
from coregen.cli.format_validation_mixin import FormatValidationMixin
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings
from coregen.services.config.cfg_schema_service import ConfigSchemaService

# Get settings instance at module level for default values
settings = get_settings()

# Option parameters for consistent formatting
option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}


class SchemaCommand(FormatValidationMixin):
    """Command for displaying model schemas."""

    # Define supported formats for the config schema command
    SUPPORTED_FORMATS = [
        OutputFormat.JSON,
        OutputFormat.YAML,
    ]
    DEFAULT_FORMAT = settings.options.config.schema_output_format

    def __init__(self) -> None:
        """Initialize schema command."""
        self.logger = Logger(__name__)
        self.console = Console
        self.ctx: typer.Context | None = None
        self.options: dict[str, Any] | None = None
        self.schema_service: ConfigSchemaService | None = None
        self.global_options: GlobalOptions | None = None

    @staticmethod
    def callback(
        ctx: typer.Context,
        config_file: Annotated[
            Path | None,
            typer.Option(
                "--config-file",
                "-c",
                help="Path to config file (.cgconfig.yaml)",
                **option_params,
            ),
        ] = settings.options.global_options.config_file,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "-d",
                help="Show what would be done without making changes",
                hidden=True,
                **option_params,
            ),
        ] = settings.options.global_options.dry_run,
        file_action: Annotated[
            FileAction,
            typer.Option(
                "--file-action",
                "-fa",
                help="Action to take when file exists",
                hidden=True,
                **option_params,
            ),
        ] = settings.options.global_options.file_action,
        help: Annotated[
            bool,
            typer.Option(
                "--help",
                "-h",
                help="Show this message and exit.",
                **{**option_params, "is_eager": True},
            ),
        ] = False,
        no_color: Annotated[
            bool,
            typer.Option(
                "--no-color",
                "-nc",
                help="Disable colored output",
                **option_params,
            ),
        ] = settings.options.global_options.no_color,
        output_format: Annotated[
            OutputFormat,
            typer.Option(
                "--output",
                "-o",
                help="Output format (JSON, YAML)",
                **option_params,
            ),
        ] = settings.options.config.schema_output_format,
        quiet: Annotated[
            bool,
            typer.Option(
                "--quiet",
                "-q",
                help="Suppress output",
                hidden=True,
                **option_params,
            ),
        ] = settings.options.global_options.quiet,
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose",
                "-v",
                help="Enable verbose output",
                **option_params,
            ),
        ] = settings.options.global_options.verbose,
        # This is an ARGUMENT instead of an OPTION to allow for multiple schema types
        schema_types: Annotated[
            list[str] | None,
            typer.Argument(
                help="Schema type (settings, workspace, context, component, all)",
            ),
        ] = None,
    ) -> None:
        """Display JSON schema for configuration models.

        Specify schema types: settings | workspace | context | component | all
        """
        Logger(__name__)

        # Check for help flag explicitly in parent context first
        parent_help = False
        if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
            parent_help = ctx.parent.obj.get("help", False)

        if help or parent_help:
            typer.echo(ctx.get_help())
            raise typer.Exit()

        # Ensure ctx.obj exists and inherit from parent
        if ctx.obj is None:
            ctx.obj = {}
            # If parent has ctx.obj, inherit it
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
                ctx.obj.update(ctx.parent.obj)

        # Store command-specific options in context
        ctx.obj["schema_types"] = schema_types

        # For global options in subcommands, we need to handle inheritance properly
        # Only override parent values if the local value was explicitly provided
        # For boolean flags, use OR logic with parent
        parent_obj = (
            ctx.parent.obj
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj
            else {}
        )

        ctx.obj["dry_run"] = dry_run or parent_obj.get("dry_run", False)
        ctx.obj["no_color"] = no_color or parent_obj.get("no_color", False)
        ctx.obj["quiet"] = quiet or parent_obj.get("quiet", False)
        ctx.obj["verbose"] = verbose or parent_obj.get("verbose", False)

        # For non-boolean options, check if they differ from defaults
        if (
            output_format != settings.options.config.schema_output_format
            or "output_format" not in parent_obj
        ):
            ctx.obj["output_format"] = output_format

        if (
            file_action != settings.options.global_options.file_action
            or "file_action" not in parent_obj
        ):
            ctx.obj["file_action"] = file_action

        # For config_file, only override if explicitly provided (different from default)
        if (
            config_file != settings.options.global_options.config_file
            or "config_file" not in parent_obj
        ):
            ctx.obj["config_file"] = config_file

        # Create and run command
        cmd = SchemaCommand()
        cmd.ctx = ctx
        cmd.run()

    def _get_options(self) -> dict[str, Any]:
        """Get command options from context with defaults from settings."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Reuse global options fetched in run(); fetch on demand otherwise  # type: ignore[unreachable]
        if self.global_options is None:
            self.global_options = GlobalOptions.from_context(self.ctx)
        options = self.global_options.to_dict()

        # Add command-specific options
        options.update(
            {
                "schema_types": self.ctx.obj.get("schema_types", []),
                "output_format": self.ctx.obj.get("output_format"),
            }
        )

        return options

    def run(self) -> None:
        """Run the schema command."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options first  # type: ignore[unreachable]
        self.global_options = GlobalOptions.from_context(self.ctx)

        # Get options from context
        self.options = self._get_options()
        self.logger.debug(f"Running schema command with options: {self.options}")

        schema_types = self.options.get("schema_types", [])
        output_format = self.options.get("output_format", OutputFormat.JSON)

        # Validate output format is supported for this command
        self.validate_output_format(output_format)

        try:
            # Set output format for proper stderr/stdout routing
            self.console.set_output_format(output_format)

            # Debug log the schema types being processed
            if schema_types:
                self.logger.debug(f"Processing schema types: {', '.join(schema_types)}")
            else:
                self.logger.debug("No schema types specified")

            # Initialize the schema service with global options
            self.schema_service = ConfigSchemaService(
                global_options=self.global_options
            )

            # Use the schema service to process the request
            result = self.schema_service.process_schema_request(
                schema_types, output_format
            )

            # Debug log the processing results
            self.logger.debug(
                f"Valid schema types found: {', '.join(result['valid_types'])}"
            )
            if result["unknown_types"]:
                self.logger.debug(
                    f"Unknown schema types: {', '.join(result['unknown_types'])}"
                )

            # Handle unknown types
            for unknown in result["unknown_types"]:
                self.logger.error(f"Unknown schema type: {unknown}")

            # If no valid schema types, exit with error
            if not result["valid_types"]:
                if result["unknown_types"]:
                    raise ValueError(
                        f"Unknown schema type(s): {', '.join(result['unknown_types'])}"
                    )
                else:
                    raise ValueError("No schema type specified")

            # Single schema output
            if not result["has_multiple"]:
                schema_type = result["valid_types"][0]
                schema_data = result["schema_data"].get(schema_type)
                if schema_data:
                    self.logger.debug(
                        f"Successfully generated schema for '{schema_type}'"
                    )
                    # For single schema, output through console
                    self.console.print(schema_data, output_format=output_format)
                else:
                    error_msg = result.get("errors", {}).get(
                        schema_type, "Unknown error"
                    )
                    self.logger.error(
                        f"Error generating schema for {schema_type}: {error_msg}"
                    )
                    raise typer.Exit(1)
            else:
                # Multiple schemas requested
                self.logger.debug(
                    f"Successfully generated {len(result['valid_types'])} schemas"
                )
                # Output the combined schema data through console
                self.console.print(result["schema_data"], output_format=output_format)

        except FileNotFoundError as e:
            self.logger.error(f"Config file not found: {str(e)}")
            self.console.error(f"{str(e)}")
            raise typer.Exit(1)
        except Exception as e:
            self.logger.error(f"Error generating schema: {e}")
            self.console.error(f"Failed to generate schema. {str(e)}")
            raise typer.Exit(1)
        finally:
            # Always reset output format
            self.console.set_output_format(None)


def register(app: typer.Typer) -> None:
    """
    Register the schema command with the provided app.

    Args:
        app: The typer app to register with
    """
    app.command(
        name="schema",
        help="Display JSON schema for configuration models",
        no_args_is_help=True,
    )(SchemaCommand.callback)
