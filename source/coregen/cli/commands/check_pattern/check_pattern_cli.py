"""Test pattern command implementation."""

from pathlib import Path
from typing import Annotated, Any

import typer

from coregen.cli.enums.enum_entity_type import EntityType
from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import CheckPatternOutputFormat
from coregen.cli.format_validation_mixin import FormatValidationMixin
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings
from coregen.services.check_pattern.check_pattern_service import CheckPatternService

# Get settings instance
settings = get_settings()
console = Console

option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}


class CheckPattern(FormatValidationMixin):
    """Command class for testing pattern matching against configuration."""

    # Define supported formats for the check-pattern command (TABLE only)
    SUPPORTED_FORMATS = [CheckPatternOutputFormat.TABLE]
    DEFAULT_FORMAT = CheckPatternOutputFormat.TABLE

    def __init__(self) -> None:
        """Initialize the command."""
        self.logger = Logger(__name__)  # Initialize logger here
        self.ctx: typer.Context | None = None
        self.options: dict[str, Any] | None = None
        self.service: Any | None = None
        self.global_options: GlobalOptions | None = None

    @staticmethod
    def callback(
        ctx: typer.Context,
        patterns: Annotated[
            list[str] | None,
            typer.Argument(
                help="Patterns to test and analyze using prefixes: w/workspace c/context cm/component",
            ),
        ] = None,
        filters: Annotated[
            list[str] | None,
            typer.Option(
                "--filter",
                "-f",
                help="Filter expressions (e.g. 'component.active=true', 'context.name~=aws' uses regex). A pattern can be filtered by its own or an ancestor entity's fields (cm/* with component.*/context.*/workspace.*); filtering by a more specific entity is rejected.",
                **option_params,
            ),
        ] = None,
        show_rejected: Annotated[
            bool,
            typer.Option(
                "--show-rejected",
                "-r",
                help="Show elements that don't match the pattern",
                **option_params,
            ),
        ] = False,
        analyze: Annotated[
            bool,
            typer.Option(
                "--analyze",
                "-a",
                help="Analyze why patterns match or don't match elements",
                **option_params,
            ),
        ] = False,
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
                help="Filter output to specific entity types (all, workspace, context, component)",
                **option_params,
            ),
        ] = settings.options.global_defaults.type,
        # Global options
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
        no_color: Annotated[
            bool,
            typer.Option(
                "--no-color",
                "-nc",
                help="Disable colored output",
                **option_params,
            ),
        ] = settings.options.global_options.no_color,
        file_action: Annotated[
            FileAction,
            typer.Option(
                "--file-action",
                "-fa",
                help="Action to take when file exists",
                **option_params,
                hidden=True,
            ),
        ] = settings.options.global_options.file_action,
        config_file: Annotated[
            Path | None,
            typer.Option(
                "--config-file",
                "-c",
                help="Path to config file (.cgconfig.yaml)",
                **option_params,
            ),
        ] = settings.options.global_options.config_file,
        quiet: Annotated[
            bool,
            typer.Option(
                "--quiet",
                "-q",
                help="Suppress output",
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
    ) -> None:
        """Test and analyze pattern matching against configuration elements.

        Pattern prefixes: w/ (workspace), c/ (context), cm/ (component)
        Use --analyze to see why patterns match/don't match.
        All patterns MUST have prefixes.
        """
        # Check for help flag explicitly
        parent_help = False
        if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
            parent_help = ctx.parent.obj.get("help", False)
        if help or parent_help:
            console.info(ctx.get_help())
            raise typer.Exit(0)

        # Check if patterns are provided
        if not patterns:
            console.info(ctx.get_help())
            console.error("Missing argument 'PATTERNS...'.")
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
        ctx.obj["show_rejected"] = show_rejected
        ctx.obj["analyze"] = analyze  # Store the new analyze option
        ctx.obj["include_inactive"] = include_inactive
        ctx.obj["type"] = type

        # For global options, inherit from parent and only override if explicitly provided
        parent_obj = (
            ctx.parent.obj
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj
            else {}
        )

        # For boolean flags, use OR logic with parent
        ctx.obj["no_color"] = no_color or parent_obj.get("no_color", False)
        ctx.obj["quiet"] = quiet or parent_obj.get("quiet", False)
        ctx.obj["verbose"] = verbose or parent_obj.get("verbose", False)

        # For non-boolean options, check if they differ from defaults
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

        # Debug logging for config file
        # _logger = Logger(__name__)
        # _logger.debug(f"Config file passed to callback: {config_file}")
        # _logger.debug(f"Config file type: {type(config_file).__name__}")

        # Create and run command instance
        cmd = CheckPattern()
        cmd.ctx = ctx
        cmd.run()  # Call run instead of execute

    def _get_options(self) -> dict[str, Any]:
        """Get command options from context with defaults from settings.

        Returns:
            Dictionary of options to use for command execution
        """
        # Print the context dict for debugging
        self.logger.debug(f"Context obj contents: {self.ctx.obj if self.ctx else None}")

        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options using the standardized pattern
        global_options = GlobalOptions.from_context(self.ctx)
        options = global_options.to_dict()

        # Add command-specific options
        type_value = self.ctx.obj.get("type", None)
        # Convert EntityType enum to string for service
        if type_value and hasattr(type_value, "value"):
            type_value = type_value.value

        command_options = {
            "patterns": self.ctx.obj.get("patterns", []),
            "filters": self.ctx.obj.get("filters", None),
            "show_rejected": self.ctx.obj.get("show_rejected", False),
            "analyze": self.ctx.obj.get("analyze", False),
            "include_inactive": self.ctx.obj.get("include_inactive", False),
            "type": type_value,
        }

        # Merge global and command-specific options
        options.update(command_options)

        # Store global_options for service initialization
        self.global_options = global_options

        return options

    def _display_check_pattern_results(
        self, results: dict[str, Any], output_format: Any
    ) -> None:
        """Display check-pattern results with multiple specialized tables.

        This method processes raw check-pattern data and makes multiple
        console calls to display section headers and tables separately.
        """
        # 1. Pattern Matching Summary table
        total_contexts = results["stats"]["total_contexts"] or 1
        total_components = results["stats"]["total_components"] or 1
        overall_percentage = (
            (
                (
                    results["stats"]["matched_contexts"]
                    + results["stats"]["matched_components"]
                )
                / (total_contexts + total_components)
            )
            * 100
            if (total_contexts + total_components) > 0
            else 0
        )

        summary_data = []
        for pattern in results["patterns"]:
            summary_data.append(
                {
                    "Pattern": pattern,
                    "Contexts": f"{results['stats']['matched_contexts']} / {total_contexts}",
                    "Components": f"{results['stats']['matched_components']} / {total_components}",
                    "Match %": f"{overall_percentage:.1f}%",
                }
            )

        console.header("Pattern Matching Summary:")
        console.print(summary_data, output_format=output_format)

        # 2. Applied Filters table (if any)
        if results["filters"]:
            filter_data = []
            for filter_expr in results["filters"]:
                filter_data.append({"Filter Expression": filter_expr})

            console.header("Applied Filters:")
            console.print(filter_data, output_format=output_format)

        # 3. Matched Contexts table
        if "contexts" in results["matched"] and results["matched"]["contexts"]:
            context_data = []
            for context_name, context in results["matched"]["contexts"].items():
                workspace_name = getattr(context, "workspace", "unknown")
                environment = getattr(context, "environment", "unknown")
                context_data.append(
                    {
                        "Workspace": workspace_name,
                        "Environment": environment,
                        "Context": context_name,
                    }
                )

            console.header("Matched Contexts:")
            console.print(context_data, output_format=output_format)

        # 4. Matched Components table
        if "components" in results["matched"] and results["matched"]["components"]:
            component_data = []
            for component_key, component in results["matched"]["components"].items():
                # Split the component key into context and component names
                if "/" in component_key:
                    context_name, component_name = component_key.split("/", 1)
                else:
                    context_name = "unknown"
                    component_name = component_key

                # Get workspace from context if available
                workspace_name = "unknown"
                if (
                    "contexts" in results["matched"]
                    and context_name in results["matched"]["contexts"]
                ):
                    context = results["matched"]["contexts"][context_name]
                    workspace_name = getattr(context, "workspace", "unknown")

                # Get component active status
                component_active = "unknown"
                if hasattr(component, "config") and hasattr(component.config, "active"):
                    component_active = str(component.config.active)

                # Get component priority if available
                component_priority = "None"
                if hasattr(component, "config") and hasattr(
                    component.config, "priority"
                ):
                    component_priority = (
                        str(component.config.priority)
                        if component.config.priority is not None
                        else "None"
                    )

                component_data.append(
                    {
                        "Workspace": workspace_name,
                        "Context": context_name,
                        "Component": component_name,
                        "Active": component_active,
                        "Priority": component_priority,
                    }
                )

            # Components are already sorted by Context model, no need to re-sort
            sorted_rows = component_data

            console.header("Matched Components:")
            console.print(sorted_rows, output_format=output_format)

        # 5. Non-Matching Elements table (if rejected results and show_rejected)
        if results.get("rejected") and "contexts" in results["rejected"]:
            rejected_data = []

            for context_name, context_data in results["rejected"]["contexts"].items():
                workspace_name = context_data.get("workspace", "unknown")
                environment = context_data.get("environment", "unknown")
                path = f"{workspace_name}/{environment}/{context_name}"
                rejected_data.append({"Path": path, "Type": "Context"})

            if "components" in results["rejected"]:
                for comp_key, comp_data in results["rejected"]["components"].items():
                    context_name = comp_data.get("context", "unknown")
                    component_name = comp_data.get("name", "unknown")
                    workspace_name = comp_data.get("workspace", "unknown")

                    environment = "unknown"
                    if context_name in results["rejected"]["contexts"]:
                        environment = results["rejected"]["contexts"][context_name].get(
                            "environment", "unknown"
                        )

                    path = f"{workspace_name}/{environment}/{context_name}/{component_name}"
                    rejected_data.append({"Path": path, "Type": "Component"})

            if rejected_data:  # Only show if there's data
                console.header("Non-Matching Elements:")
                console.print(rejected_data, output_format=output_format)

        # 6. Pattern Analysis (if available)
        if results.get("analysis"):
            console.header("Pattern Analysis:")
            for pattern, analysis in results["analysis"].items():
                console.info(
                    f"Analysis for pattern: {pattern} ({analysis.get('pattern_type', 'Unknown')} Pattern)"
                )

                if analysis.get("match_attempts"):
                    console.info("Match Attempts:")
                    for attempt in analysis["match_attempts"]:
                        console.info(f"  - {attempt}")

                if analysis["examples"]["matched"]:
                    console.info("Example Matches:")
                    for ex in analysis["examples"]["matched"]:
                        console.info(f"  {ex['path']} ({ex.get('type', '?')})")
                        if "reason" in ex:
                            console.info(f"    Why: {ex['reason']}")

                if analysis["examples"]["rejected"]:
                    console.info("Example Non-matches:")
                    for ex in analysis["examples"]["rejected"]:
                        console.info(f"  {ex['path']} ({ex.get('type', '?')})")
                        if "reason" in ex:
                            console.info(f"    Why: {ex['reason']}")

    def run(self) -> None:
        """Execute the test pattern command."""
        # Get options
        self.options = self._get_options()
        self.logger.debug(
            f"Running check-pattern command with patterns: {self.options['patterns']}"
        )

        try:
            # Force output_format to TABLE for check-pattern (diagnostic analysis only)
            # Validate that TABLE format is supported and set it as the format
            self.validate_output_format(CheckPatternOutputFormat.TABLE)
            if self.global_options is None:
                raise RuntimeError("Global options not initialized")
            setattr(
                self.global_options, "output_format", CheckPatternOutputFormat.TABLE
            )

            # Create service instance with global options
            self.service = CheckPatternService(global_options=self.global_options)

            # Call the service method with pattern-specific parameters
            results = self.service.check_pattern(
                patterns=self.options["patterns"],
                filters=self.options["filters"],
                show_rejected=self.options["show_rejected"],
                analyze=self.options["analyze"],
                include_inactive=self.options.get("include_inactive", False),
                type=self.options["type"],
            )

            # Display results using multiple console calls
            output_format = (
                getattr(
                    self.global_options, "output_format", CheckPatternOutputFormat.TABLE
                )
                if self.global_options
                else CheckPatternOutputFormat.TABLE
            )
            self._display_check_pattern_results(results, output_format)

            self.logger.debug(f"Test pattern results: {results['stats']}")

        except Exception as e:
            console.error(f"Failed to test patterns: {str(e)}")
            # Optionally re-raise or log traceback for debugging
            self.logger.exception("Error during check-pattern execution:")
            raise typer.Exit(2)
