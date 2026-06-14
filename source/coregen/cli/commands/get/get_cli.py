"""Get command implementation."""

from pathlib import Path
from typing import Annotated, Any

import typer

from coregen.cli.enums.enum_entity_type import EntityType
from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_format import Format
from coregen.cli.enums.enum_output_format import GetOutputFormat
from coregen.cli.format_validation_mixin import FormatValidationMixin
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings
from coregen.services.get.get_service import GetService

# Get settings instance
settings = get_settings()
console = Console

option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Options",
}


class Get(FormatValidationMixin):
    """Command class for getting configuration elements."""

    # Define supported formats for the get command
    SUPPORTED_FORMATS = [
        GetOutputFormat.YAML,
        GetOutputFormat.JSON,
        GetOutputFormat.TABLE,
        GetOutputFormat.MATRIX,
    ]
    DEFAULT_FORMAT = settings.options.get.output_format

    ctx: typer.Context | None
    options: dict[str, Any] | None
    service: GetService | None
    global_options: GlobalOptions | None

    def __init__(self) -> None:
        """Initialize the command."""
        self.logger = Logger(__name__)
        self.ctx = None
        self.options = None
        self.service = None
        self.global_options = None

    @staticmethod
    def callback(
        ctx: typer.Context,
        patterns: Annotated[
            list[str] | None,
            typer.Argument(
                help="Patterns to match configuration elements using prefixes: w/workspace c/context cm/component",
            ),
        ] = None,
        filters: Annotated[
            list[str] | None,
            typer.Option(
                "--filter",
                "-f",
                help="Filter expressions. A pattern can be filtered by its own or a parent entity's fields (e.g. cm/* with component.*, context.*, or workspace.*). Examples: 'component.config.priority=none', 'context.name~=aws' (regex). See docs/reference/filter-operators.md",
                **option_params,
            ),
        ] = None,
        from_json: Annotated[
            str | None,
            typer.Option(
                "--from-json",
                "-j",
                help="JSON string with component specifications",
                **option_params,
            ),
        ] = None,
        json_file: Annotated[
            Path | None,
            typer.Option(
                "--json-file",
                "-jf",
                help="Path to JSON file with component specifications",
                **option_params,
            ),
        ] = None,
        name_only: Annotated[
            bool,
            typer.Option(
                "--name-only",
                help="Return only names as simple arrays (de-duplicates component names)",
                **option_params,
            ),
        ] = settings.options.global_defaults.name_only,
        include_inactive: Annotated[
            bool,
            typer.Option(
                "--include-inactive",
                "-ii",
                help="Include inactive components and contexts in results",
                **option_params,
            ),
        ] = settings.options.global_defaults.include_inactive,
        type: Annotated[
            EntityType | None,
            typer.Option(
                "--type",
                "-t",
                help="Filter output to specific entity types (workspace, context, component)",
                **option_params,
            ),
        ] = settings.options.global_defaults.type,
        format_type: Annotated[
            Format,
            typer.Option(
                "--format-type",
                "-ft",
                help="Output structure type (flat/nested)",
                **option_params,
            ),
        ] = settings.options.get.format,
        help: Annotated[
            bool,
            typer.Option(
                "--help",
                "-h",
                help="Show this message and exit.",
                show_envvar=False,
                **{**option_params, "is_eager": True},
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "-d",
                help="Show what would be done without making changes",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.dry_run,
        no_color: Annotated[
            bool,
            typer.Option(
                "--no-color",
                "-nc",
                help="Disable colored output",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.no_color,
        output_format: Annotated[
            GetOutputFormat,
            typer.Option(
                "--output",
                "-o",
                help="Output format (YAML, JSON, TABLE, MATRIX)",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.get.output_format,
        file_action: Annotated[
            FileAction,
            typer.Option(
                "--file-action",
                "-fa",
                help="Action to take when file exists",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.file_action,
        config_file: Annotated[
            Path | None,
            typer.Option(
                "--config-file",
                "-c",
                help="Path to config file (.cgconfig.yaml)",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.config_file,
        quiet: Annotated[
            bool,
            typer.Option(
                "--quiet",
                "-q",
                help="Suppress output",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.quiet,
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose",
                "-v",
                help="Enable verbose output",
                rich_help_panel="Global Options",
            ),
        ] = settings.options.global_options.verbose,
    ) -> None:
        """Get configuration elements by pattern or JSON input.

        Pattern prefixes: w/ (workspace), c/ (context), cm/ (component)
        A pattern can be filtered by its own or a parent entity's fields
        (e.g. cm/* with component.*, context.*, or workspace.*); filtering by a
        more specific entity than the pattern is rejected.
        All patterns MUST have prefixes. Use 'check-pattern' to test.
        """
        # Check for help flag explicitly
        parent_help = False
        if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
            parent_help = ctx.parent.obj.get("help", False)
        if help or parent_help:
            console.info(ctx.get_help())
            raise typer.Exit()

        # Check that either patterns or JSON input is provided (but not both)
        if patterns and len(patterns) > 0 and (from_json or json_file):
            console.error("Cannot use both patterns and JSON input.")
            console.info(ctx.get_help())
            raise typer.Exit(1)

        if (not patterns or len(patterns) == 0) and not from_json and not json_file:
            console.info(ctx.get_help())
            console.error("Either patterns or JSON input must be provided.")
            raise typer.Exit()  # Clean exit without error code

        # Ensure ctx.obj exists and inherit from parent
        if ctx.obj is None:
            ctx.obj = {}
            # If parent has ctx.obj, inherit it
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
                ctx.obj.update(ctx.parent.obj)

        # Store command-specific options in context
        ctx.obj["patterns"] = patterns
        ctx.obj["filters"] = filters
        ctx.obj["from_json"] = from_json
        ctx.obj["json_file"] = json_file
        ctx.obj["name_only"] = name_only
        ctx.obj["include_inactive"] = include_inactive
        ctx.obj["type"] = type
        ctx.obj["format_type"] = format_type

        # For global options, inherit from parent and only override if explicitly provided
        parent_obj = (
            ctx.parent.obj
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj
            else {}
        )

        # For boolean flags, use OR logic with parent
        ctx.obj["dry_run"] = dry_run or parent_obj.get("dry_run", False)
        ctx.obj["no_color"] = no_color or parent_obj.get("no_color", False)
        ctx.obj["quiet"] = quiet or parent_obj.get("quiet", False)
        ctx.obj["verbose"] = verbose or parent_obj.get("verbose", False)

        # For non-boolean options, check if they differ from defaults
        if (
            output_format != settings.options.get.output_format
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

        # Create and run command instance
        cmd = Get()
        cmd.ctx = ctx
        cmd.run()

    def _get_options(self) -> dict[str, Any]:
        """Get command options from context with defaults from settings.

        Returns:
            Dictionary of options to use for command execution
        """
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options using the standardized pattern
        global_options = GlobalOptions.from_context(self.ctx)
        options = global_options.to_dict()

        # Add command-specific options
        options.update(
            {
                "patterns": self.ctx.obj.get("patterns"),
                "filters": self.ctx.obj.get("filters"),
                "from_json": self.ctx.obj.get("from_json"),
                "json_file": self.ctx.obj.get("json_file"),
                "name_only": self.ctx.obj.get("name_only"),
                "include_inactive": self.ctx.obj.get("include_inactive"),
                "type": self.ctx.obj.get("type"),
                "output_format": self.ctx.obj.get("output_format"),
                "format_type": self.ctx.obj.get("format_type"),
            }
        )

        # Store global_options for service initialization
        self.global_options = global_options

        return options

    def run(self) -> None:
        """Execute the get command.

        This method:
        1. Gets the options from context
        2. Validates output format
        3. Instantiates the GetService
        4. Calls the get_elements method
        5. Formats and displays the results
        """
        # Get options
        self.options = self._get_options()
        self.logger.debug(f"Running get command with options: {self.options}")

        try:
            # Validate output format is supported for this command
            output_format = self.options["output_format"]
            self.validate_output_format(output_format)

            # Set the output format in Console for proper routing of info/debug messages
            console.set_output_format(output_format)

            # Validate pattern prefixes if patterns are provided
            if self.options["patterns"]:
                valid_prefixes = [
                    "w/",
                    "c/",
                    "cm/",
                    "workspace/",
                    "context/",
                    "component/",
                ]
                for pattern in self.options["patterns"]:
                    if not any(pattern.startswith(prefix) for prefix in valid_prefixes):
                        console.error(f"Invalid pattern: '{pattern}'")
                        console.error(
                            f"All patterns must start with a valid prefix: {', '.join(valid_prefixes)}"
                        )
                        console.info("\nExamples of valid patterns:")
                        console.info("  w/aws           - Get AWS workspace")
                        console.info("  c/dev           - Get dev context")
                        console.info("  cm/nginx        - Get nginx component")
                        console.info(
                            "  workspace/prod  - Get prod workspace (long form)"
                        )
                        console.info(
                            "  context/*-dev   - Get all contexts ending with '-dev'"
                        )
                        console.info(
                            "  component/prom* - Get components starting with 'prom'"
                        )
                        console.info(
                            "\nUse 'coregen check-pattern' to test your patterns before running."
                        )
                        # Exit 2 = input/validation error per the documented
                        # exit-code contract (docs/developer/architecture/overview.md)
                        raise typer.Exit(2)

            # Create service instance with global options
            self.service = GetService(global_options=self.global_options)

            # Determine format_type - default to flat for table output
            format_type = self.options.get("format_type")
            # If format_type is the default (nested) and output is table, use flat instead
            if format_type == Format.NESTED and output_format == GetOutputFormat.TABLE:
                # Default to flat format for table output for better display
                format_type = Format.FLAT
                self.logger.debug("Using flat format for table output (better display)")

            # Call the service method with the appropriate parameters
            results: list[str] | dict[str, Any] = self.service.get_elements(
                patterns=self.options["patterns"],
                filters=self.options["filters"],
                from_json=self.options["from_json"],
                json_file=self.options["json_file"],
                name_only=self.options["name_only"],
                include_inactive=self.options.get("include_inactive", False),
                type=self.options["type"],
                format_type=format_type,
            )

            # Transform results for name-only output if needed
            if self.options.get("name_only") and isinstance(results, dict):
                # Use centralized transformation logic from NameFilterService
                from coregen.common.name_filter_service import NameFilterService

                name_filter_service = NameFilterService()

                type_value = self.options.get("type")
                type_str = getattr(type_value, "value", type_value)

                results = name_filter_service.transform_for_output(
                    results,
                    entity_type=type_str,
                    patterns=self.options.get("patterns", []),
                )

            # Format and display results based on output format
            console.print(results, output_format=output_format)

            self.logger.debug("Get command completed successfully")

        except typer.Exit:
            # Deliberate exits carry their own code and already printed their
            # message; re-wrapping them produced a spurious trailer line
            raise
        except FileNotFoundError as e:
            # Config/file errors are general errors (exit 1) per the documented
            # contract; exit 2 is reserved for input/validation errors
            console.error(f"Failed to get elements: {str(e)}")
            self.logger.exception("Error during get command execution:")
            raise typer.Exit(1)
        except Exception as e:
            error_msg = str(e)
            # Check if this is our validation error that's already been displayed
            if "Configuration invalid" not in error_msg:
                console.error(f"Failed to get elements: {error_msg}")
            # Log traceback for debugging
            self.logger.exception("Error during get command execution:")
            raise typer.Exit(2)
        finally:
            # Clear the output format when done
            console.set_output_format(None)
