"""Generate files command."""

import sys
import traceback
from pathlib import Path
from typing import Annotated, Any

import typer

from coregen.cli.commands.generate.gen_generate_formatter import GenerateFormatter
from coregen.cli.enums.enum_entity_type import EntityType
from coregen.cli.enums.enum_file_action import FileAction
from coregen.cli.enums.enum_output_format import GenerateOutputFormat, OutputFormat
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings
from coregen.services.generate.gen_generate_service import GenerateService

# Get settings instance at module level for default values
settings = get_settings()
console = Console

# Option parameter configurations
option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}

path_params = {
    "exists": False,
    "file_okay": True,
    "dir_okay": True,
    "writable": True,
    "readable": True,
    "resolve_path": True,
    "rich_help_panel": "Generate Options",
}

generate_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Generate Options",
}


class GenerateCommand:
    """Generate files command.

    This command generates files based on configurations in workspaces, contexts, and components.
    It supports filtering by properties and generating to different output locations.
    """

    def __init__(self) -> None:
        """Initialize the command."""
        self.logger = Logger(__name__)
        self.ctx: typer.Context | None = None
        self.global_options: GlobalOptions | None = None
        self.service: Any | None = None
        self.console = Console()
        self.formatter = GenerateFormatter(self.console)
        self.output_format: Any | None = None  # Track output format for cleanup

    @staticmethod
    def callback(
        ctx: typer.Context,
        # Required positional argument - paths to generate
        paths: Annotated[
            list[str] | None,
            typer.Argument(
                help="Patterns to match elements for file generation using prefixes: w/workspace c/context cm/component",
            ),
        ] = None,
        # Command-specific options
        filter: Annotated[
            list[str] | None,
            typer.Option(
                "--filter",
                "-f",
                help="Filter by properties",
                **generate_params,
            ),
        ] = None,
        include_inactive: Annotated[
            bool,
            typer.Option(
                "--include-inactive",
                "-ii",
                help="Include inactive components/contexts in generation",
                **generate_params,
            ),
        ] = settings.options.global_defaults.include_inactive,
        type: Annotated[
            EntityType | None,
            typer.Option(
                "--type",
                "-t",
                help="Filter generation to specific entity types (all, workspace, context, component)",
                **generate_params,
            ),
        ] = settings.options.global_defaults.type,
        skip_commit_dir: Annotated[
            bool,
            typer.Option(
                "--skip-commit-dir",
                "-sc",
                help="Skip generating files to the context's commit_dir",
                **generate_params,
            ),
        ] = False,
        output_dir: Annotated[
            Path | None,
            typer.Option(
                "--output-dir",
                "-od",
                help="Output directory for generated files",
                **path_params,
            ),
        ] = None,
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
        config_file: Annotated[
            Path | None,
            typer.Option(
                "--config-file",
                "-c",
                help="Path to config file (.cgconfig.yaml)",
                exists=False,
                file_okay=True,
                dir_okay=False,
                readable=True,
                resolve_path=False,  # Don't resolve non-existent paths
                **option_params,
            ),
        ] = settings.options.global_options.config_file,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                "-d",
                help="Show what would be done without making changes",
                **option_params,
            ),
        ] = settings.options.global_options.dry_run,
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
            GenerateOutputFormat,
            typer.Option(
                "--output",
                "-o",
                help="Output format (TEXT or TABLE)",
                **option_params,
            ),
        ] = GenerateOutputFormat.TEXT,
        file_action: Annotated[
            FileAction,
            typer.Option(
                "--file-action",
                "-fa",
                help="Action to take when file exists",
                **option_params,
            ),
        ] = settings.options.global_options.file_action,
        quiet: Annotated[
            bool, typer.Option("--quiet", "-q", help="Suppress output", **option_params)
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
        """Generate files from workspace/context/component configurations.

        Pattern prefixes: w/ (workspace), c/ (context), cm/ (component)
        All patterns MUST have prefixes. Use 'check-pattern' to test.
        """
        # Check for help flag
        if help:
            console.info(ctx.get_help())
            raise typer.Exit()

        # Check if paths are provided
        if not paths:
            console.info(ctx.get_help())
            console.error("Missing argument 'PATHS...'.")
            raise typer.Exit()

        # Ensure ctx.obj exists and inherit from parent
        if ctx.obj is None:
            ctx.obj = {}
            # If parent has ctx.obj, inherit it
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
                ctx.obj.update(ctx.parent.obj)

        # Store command-specific options in context
        ctx.obj["paths"] = paths
        ctx.obj["filter"] = filter
        ctx.obj["include_inactive"] = include_inactive
        ctx.obj["type"] = type
        ctx.obj["skip_commit_dir"] = skip_commit_dir
        ctx.obj["output_dir"] = output_dir
        ctx.obj["output_format"] = output_format

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

        # For non-boolean options, store based on where the value came from.
        # Comparing against the settings default cannot distinguish "user passed
        # the flag" from "auto_envvar filled it in"; with interspersed parsing the
        # main callback may own the explicit flag, so an env-sourced subcommand
        # value must not clobber it (CG_FILE_ACTION vs --file-action=skip).
        # Compared by enum name: Typer 0.26+ vendors click, so the ParameterSource
        # class is not importable from a stable public location.
        file_action_source = ctx.get_parameter_source("file_action")
        if (
            file_action_source is not None and file_action_source.name == "COMMANDLINE"
        ) or "file_action" not in parent_obj:
            ctx.obj["file_action"] = file_action

        # For config_file, only override if explicitly provided (different from default)
        if (
            config_file != settings.options.global_options.config_file
            or "config_file" not in parent_obj
        ):
            ctx.obj["config_file"] = config_file

        # Create and run command
        cmd = GenerateCommand()
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

        # Store global_options for service initialization
        self.global_options = global_options

        # Add command-specific options
        type_value = self.ctx.obj.get("type", None)
        # Convert EntityType enum to string for service
        if type_value and hasattr(type_value, "value"):
            type_value = type_value.value

        options.update(
            {
                "paths": self.ctx.obj.get("paths", []),
                "filter": self.ctx.obj.get("filter", None),
                "include_inactive": self.ctx.obj.get("include_inactive", False),
                "type": type_value,
                "skip_commit_dir": self.ctx.obj.get("skip_commit_dir", False),
                "output_dir": self.ctx.obj.get("output_dir", None),
                "output_format": self.ctx.obj.get(
                    "output_format", GenerateOutputFormat.TEXT
                ),
            }
        )

        return options

    def _process_generation(self, options: dict[str, Any]) -> dict[str, Any]:
        """Process the file generation with the service.

        Args:
            options: Command options dictionary

        Returns:
            Results dictionary from the service
        """
        # Check if using table output format
        is_table_output = options.get("output_format") == GenerateOutputFormat.TABLE

        # Generate files
        if (
            not is_table_output
            and self.global_options
            and not self.global_options.quiet
        ):
            console.info("Generating files...")

        results: dict[str, Any] = self.service.generate_files(  # type: ignore[union-attr]
            paths=options["paths"],
            filters=options["filter"],
            include_inactive=options["include_inactive"],
            type=options["type"],
            skip_commit_dir=options["skip_commit_dir"],
            output_dir=options["output_dir"],
        )

        # Log the full results dictionary
        self.logger.debug(f"Final results dictionary received from service: {results}")

        return results

    def _display_results(self, results: dict[str, Any], options: dict[str, Any]) -> int:
        """Display the generation results based on output format.

        Args:
            results: Results dictionary from the service
            options: Command options dictionary

        Returns:
            Number of errors that occurred
        """
        # Delegate to formatter
        output_format = options.get("output_format", GenerateOutputFormat.TEXT)
        return self.formatter.format_results(results, options, output_format)

    def run(self) -> None:
        """Run the generate files command."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get all options (global + command-specific)
        options = self._get_options()

        # Store output format for proper cleanup
        self.output_format = options.get("output_format", GenerateOutputFormat.TEXT)

        self.logger.debug(
            f"Running generate files command with paths: {options['paths']}"
        )

        try:
            # Set output format if needed
            if self.output_format == GenerateOutputFormat.TABLE:
                # For table output, we handle formatting ourselves
                # Create a modified global_options with quiet=True for table output
                if self.global_options is None:
                    raise RuntimeError("Global options not initialized")
                table_global_options = GlobalOptions(
                    dry_run=self.global_options.dry_run,
                    file_action=self.global_options.file_action,
                    quiet=True,  # Suppress service output in table mode
                    verbose=self.global_options.verbose,
                    no_color=self.global_options.no_color,
                    config_file=self.global_options.config_file,
                )
                # Create service instance with modified options
                self.service = GenerateService(global_options=table_global_options)
            else:
                # For text output, ensure console is in correct mode
                self.console.set_output_format(OutputFormat.TEXT)
                # Create service instance with standard global options
                if self.global_options is None:
                    raise RuntimeError("Global options not initialized")
                self.service = GenerateService(global_options=self.global_options)

            # Process generation
            results = self._process_generation(options)

            # Display results (unless quiet)
            num_errors = 0
            if not options["quiet"]:
                num_errors = self._display_results(results, options)

        except TypeError as e:
            # Log detailed error for debugging
            self.logger.error(f"TypeError in generate command: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")

            # Show user-friendly error
            verbose = self.global_options.verbose if self.global_options else False
            if verbose:
                self.console.error(f"Failed to generate files (TypeError): {str(e)}")
                self.console.error("Run with CG_LOG_LEVEL=debug for detailed traceback")
            else:
                self.console.error(f"Failed to generate files: {str(e)}")
            sys.exit(1)
        except FileNotFoundError as e:
            self.logger.error(f"File not found: {str(e)}")
            self.console.error(f"File not found: {str(e)}")
            self.console.error(
                "Please check that all required files and directories exist"
            )
            sys.exit(1)
        except PermissionError as e:
            self.logger.error(f"Permission denied: {str(e)}")
            self.console.error(f"Permission denied: {str(e)}")
            self.console.error("Please check file and directory permissions")
            sys.exit(1)
        except KeyboardInterrupt:
            self.console.warning("\nGeneration cancelled by user")
            sys.exit(130)  # Standard exit code for SIGINT
        except Exception as e:
            self.logger.error(f"Unexpected error in generate command: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")

            # Show appropriate error message
            verbose = self.global_options.verbose if self.global_options else False
            if verbose:
                self.console.error(f"Failed to generate files: {str(e)}")
                self.console.error(f"Error type: {type(e).__name__}")
            else:
                self.console.error(f"Failed to generate files: {str(e)}")
            sys.exit(1)
        finally:
            # Always reset output format
            if self.output_format and self.output_format != GenerateOutputFormat.TEXT:
                self.console.set_output_format(OutputFormat.TEXT)

        # Exit with code 2 if errors occurred during generation
        if num_errors > 0:
            quiet = self.global_options.quiet if self.global_options else False
            if not quiet:
                self.console.info("")
                self.console.error(
                    f"Run FAILED. [yellow1]{num_errors}[/] errors occurred during generation. "
                    "Please check your templates and context files."
                )
            sys.exit(2)
