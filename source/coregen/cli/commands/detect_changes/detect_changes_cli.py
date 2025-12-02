"""Detect Changes command implementation V2 - Generation-based approach."""

import sys
from pathlib import Path
from typing import Annotated, Any

import typer

from coregen.cli.enums.enum_output_format import DetectChangesOutputFormat
from coregen.cli.format_validation_mixin import FormatValidationMixin
from coregen.cli.global_options import GlobalOptions
from coregen.common.console import Console
from coregen.common.logger import Logger
from coregen.config_model.models.settings import get_settings
from coregen.services.detect_changes.detect_changes_service import DetectChangesService
from coregen.services.detect_changes.formatters import DetectChangesFormatter
from coregen.services.detect_changes.models import DetectChangesResult

# Get settings instance
settings = get_settings()
console = Console

option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Global Options",
}


class DetectChanges(FormatValidationMixin):
    """Command class for detecting changes using generation-based comparison."""

    # Define supported formats for the detect-changes command
    SUPPORTED_FORMATS = [
        DetectChangesOutputFormat.TEXT,
        DetectChangesOutputFormat.JSON,
        DetectChangesOutputFormat.YAML,
        DetectChangesOutputFormat.MATRIX,
        DetectChangesOutputFormat.TABLE,
    ]
    DEFAULT_FORMAT = settings.options.detect_changes.output_format

    def __init__(self) -> None:
        """Initialize the command."""
        self.logger = Logger(__name__)
        self.ctx: typer.Context | None = None
        self.options: dict[str, Any] | None = None
        self.service: Any | None = None
        self.global_options: GlobalOptions | None = None

    @staticmethod
    def callback(
        ctx: typer.Context,
        base_branch: Annotated[
            str,
            typer.Option(
                "--base-branch",
                "-b",
                help="Base branch to compare against (default: main)",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = settings.options.detect_changes.base_branch,
        output: Annotated[
            DetectChangesOutputFormat,
            typer.Option(
                "--output",
                "-o",
                help="Output format: text (default), yaml, json, matrix, table",
                **option_params,
            ),
        ] = settings.options.detect_changes.output_format,
        filters: Annotated[
            list[str] | None,
            typer.Option(
                "--filter",
                "-f",
                help="Filter expressions to narrow results. Examples: 'component.config.priority=none', 'context.environment=production'. See docs/reference/filter-operators.md",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = None,
        include_inactive: Annotated[
            bool,
            typer.Option(
                "--include-inactive",
                "-ii",
                help="Include inactive components in results",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = settings.options.global_defaults.include_inactive,
        changed_only: Annotated[
            bool,
            typer.Option(
                "--changed-only",
                help="Show only changed components (exclude unchanged/deleted)",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = settings.options.detect_changes.changed_only,
        deleted_only: Annotated[
            bool,
            typer.Option(
                "--deleted-only",
                help="Show only deleted components",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = settings.options.detect_changes.deleted_only,
        name_only: Annotated[
            bool,
            typer.Option(
                "--name-only",
                help="Output only names, not full details",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = settings.options.detect_changes.name_only,
        include_required_changes: Annotated[
            bool,
            typer.Option(
                "--include-required-changes",
                "-ir",
                help="Include required_changes array in JSON/YAML output (default: false)",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = settings.options.detect_changes.include_required_changes,
        output_dir: Annotated[
            Path | None,
            typer.Option(
                "--output-dir",
                help="Custom temp directory for generated files (default: .cgtmp)",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = None,
        keep_generated: Annotated[
            bool,
            typer.Option(
                "--keep-generated",
                "-k",
                help="Don't delete generated files after comparison (for debugging)",
                **{**option_params, "rich_help_panel": "Options"},
            ),
        ] = settings.options.detect_changes.keep_generated,
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
                help="Show detailed progress during generation and comparison",
                **option_params,
            ),
        ] = settings.options.global_options.verbose,
    ) -> None:
        """Detect components changed between branches by comparing generated output.

        Generates components from both branches, compares output, applies required cascade logic.
        Status: changed | deleted. Reason: direct | deleted | required_cascade.
        """
        # Help handling
        parent_help = False
        if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
            parent_help = ctx.parent.obj.get("help", False)
        if help or parent_help:
            console.info(ctx.get_help())
            raise typer.Exit()

        # Ensure ctx.obj exists and inherit from parent
        if ctx.obj is None:
            ctx.obj = {}
            # If parent has ctx.obj, inherit it
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
                ctx.obj.update(ctx.parent.obj)

        # Store command-specific options in context
        ctx.obj["base_branch"] = base_branch
        ctx.obj["output"] = output
        ctx.obj["filters"] = filters
        ctx.obj["include_inactive"] = include_inactive
        ctx.obj["changed_only"] = changed_only
        ctx.obj["deleted_only"] = deleted_only
        ctx.obj["name_only"] = name_only
        ctx.obj["include_required_changes"] = include_required_changes
        ctx.obj["output_dir"] = output_dir
        ctx.obj["keep_generated"] = keep_generated

        # Store global options
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

        # For config_file, only override if explicitly provided
        if (
            config_file != settings.options.global_options.config_file
            or "config_file" not in parent_obj
        ):
            ctx.obj["config_file"] = config_file

        # Create and run command instance
        cmd = DetectChanges()
        cmd.ctx = ctx
        cmd.run()

    def _get_options(self) -> dict[str, Any]:
        """Get command options from context.

        Returns:
            Dictionary of options to use for command execution
        """
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options using the standardized pattern
        global_options = GlobalOptions.from_context(self.ctx)
        options = global_options.to_dict()

        # Add command-specific options
        command_options = {
            "base_branch": self.ctx.obj.get("base_branch"),
            "output": self.ctx.obj.get("output"),
            "filters": self.ctx.obj.get("filters"),
            "include_inactive": self.ctx.obj.get("include_inactive"),
            "changed_only": self.ctx.obj.get("changed_only"),
            "deleted_only": self.ctx.obj.get("deleted_only"),
            "name_only": self.ctx.obj.get("name_only"),
            "include_required_changes": self.ctx.obj.get("include_required_changes"),
            "output_dir": self.ctx.obj.get("output_dir"),
            "keep_generated": self.ctx.obj.get("keep_generated"),
        }

        # Merge global and command-specific options
        options.update(command_options)

        # Store global_options for service initialization
        self.global_options = global_options

        return options

    def _prepare_output_data(self, result: DetectChangesResult) -> Any:
        """Prepare detect-changes result data for console output pipeline.

        Transforms DetectChangesResult into a format compatible with common formatters.
        Handles filtering based on command options.

        Args:
            result: DetectChangesResult from the service

        Returns:
            Data formatted for console output (dict or list depending on options)
        """
        # Handle name-only output
        if self.options and self.options.get("name_only", False):
            if self.options and self.options.get("changed_only", False):
                return result.to_name_only_format(changed_only=True)
            elif self.options and self.options.get("deleted_only", False):
                # Return only deleted component names
                return sorted({c.component_name for c in result.deleted})
            else:
                return result.to_name_only_format(changed_only=False)

        # For structured output, use the dict representation
        include_required = bool(
            self.options and self.options.get("include_required_changes", False)
        )
        data = result.to_dict(include_required_changes=include_required)

        # Apply filtering
        if self.options and self.options.get("changed_only", False):
            data["changes"] = [c for c in data["changes"] if c["status"] == "changed"]
            data.pop("deleted", None)
        elif self.options and self.options.get("deleted_only", False):
            data = {"deleted": data.get("deleted", [])}

        # Handle empty results
        if not data.get("changes") and not data.get("deleted"):
            return {"message": "No changes detected"}

        return data

    def _prepare_table_data(
        self, result: DetectChangesResult
    ) -> list[dict[str, Any]] | list[list[str]]:
        """Prepare detect-changes result data for table output.

        Flattens the DetectChangesResult into a list of dictionaries suitable
        for tabular display.

        Args:
            result: DetectChangesResult from the service

        Returns:
            List of dicts with flattened component data for table display
        """
        # If name-only, return compact 2D table: headers and rows
        if self.options and self.options.get("name_only", False):
            headers = ["Name", "Status"]
            name_rows: list[list[str]] = [headers]
            for change in result.changes:
                # Apply filters
                if (
                    self.options
                    and self.options.get("changed_only", False)
                    and change.status.value != "changed"
                ):
                    continue
                if (
                    self.options
                    and self.options.get("deleted_only", False)
                    and change.status.value != "deleted"
                ):
                    continue
                name_rows.append([change.component_name, change.status.value])

            if len(name_rows) == 1:
                return [["Message"], ["No changes detected"]]
            return name_rows

        # Full table with explicit column order
        headers = [
            "Name",
            "Context",
            "Workspace",
            "Environment",
            "Status",
            "Reason",
            "Priority",
            "Dependencies",
        ]
        rows: list[list[str]] = [headers]

        # Process all changes (includes deleted)
        for change in result.changes:
            # Apply filters
            if (
                self.options
                and self.options.get("changed_only", False)
                and change.status.value != "changed"
            ):
                continue
            if (
                self.options
                and self.options.get("deleted_only", False)
                and change.status.value != "deleted"
            ):
                continue

            # Priority
            pri = (
                str(change.component_priority)
                if change.component_priority is not None
                else "-"
            )

            # Make Context cell clickable to the context config file if available
            context_cell = change.context_name
            try:
                cfg_file_path = getattr(change, "context_config_file_path", None)
                if cfg_file_path:
                    from pathlib import Path as _P

                    cfg_path = _P(cfg_file_path)
                    if not cfg_path.is_absolute():
                        cfg_path = (_P.cwd() / cfg_path).resolve()
                    cfg_uri = cfg_path.as_uri()
                    # Display the context name as the clickable text
                    context_cell = f"[link={cfg_uri}]{change.context_name}[/link]"
            except Exception:
                # Fallback to plain context name on any error
                context_cell = change.context_name

            # Get environment value - try different possible attribute names
            env = "-"
            if hasattr(change, "environment"):
                env = change.environment if change.environment else "-"
            elif hasattr(change, "context_environment"):
                env = change.context_environment if change.context_environment else "-"

            # Get dependencies - try different possible attribute names
            deps = "-"
            if (
                hasattr(change, "component_dependencies")
                and change.component_dependencies
            ):
                # Extract names from dependency objects
                dep_names = []
                for dep in change.component_dependencies:
                    if hasattr(dep, "name"):
                        dep_names.append(dep.name)
                    elif isinstance(dep, dict) and "name" in dep:
                        dep_names.append(dep["name"])
                    elif isinstance(dep, str):
                        dep_names.append(dep)
                if dep_names:
                    deps = ", ".join(dep_names)

            rows.append(
                [
                    change.component_name,
                    context_cell,
                    change.workspace_name,
                    env,
                    change.status.value,
                    change.reason.value,
                    pri,
                    deps,
                ]
            )

        if len(rows) == 1:
            return [["Message"], ["No changes detected"]]
        return rows

    def run(self) -> None:
        """Execute the detect-changes command.

        This method:
        1. Gets the options from context
        2. Validates output format
        3. Instantiates the DetectChangesServiceV2
        4. Calls the detect_changes method
        5. Formats and displays the results
        """
        # Get options
        self.options = self._get_options()
        self.logger.debug(f"Running detect-changes with options: {self.options}")

        # Validate output format is supported for this command
        output_format = self.options["output"]
        self.validate_output_format(output_format)

        try:
            # Set output format for proper stderr/stdout routing
            console.set_output_format(output_format)

            # Create service instance with global options
            self.service = DetectChangesService(global_options=self.global_options)

            # Show verbose progress if enabled
            if self.options and self.options.get("verbose", False):
                self.logger.debug(
                    f"Starting detect-changes analysis (base: {self.options['base_branch']})"
                )

            result = self.service.detect_changes(
                base_branch=self.options["base_branch"],
                output_dir=self.options.get("output_dir") if self.options else None,
                filters=self.options.get("filters") if self.options else None,
                include_inactive=(
                    bool(self.options.get("include_inactive", False))
                    if self.options
                    else False
                ),
                keep_generated=(
                    bool(self.options.get("keep_generated", False))
                    if self.options
                    else False
                ),
                verbose=(
                    bool(self.options.get("verbose", False)) if self.options else False
                ),
            )

            # Handle text output with custom formatter (domain-specific)
            if output_format == DetectChangesOutputFormat.TEXT:
                if isinstance(result, DetectChangesResult):
                    formatter = DetectChangesFormatter()
                    output = formatter.format_text(
                        result,
                        name_only=(
                            bool(self.options.get("name_only", False))
                            if self.options
                            else False
                        ),
                        changed_only=(
                            bool(self.options.get("changed_only", False))
                            if self.options
                            else False
                        ),
                        deleted_only=(
                            bool(self.options.get("deleted_only", False))
                            if self.options
                            else False
                        ),
                    )
                    console.print(output)
                else:
                    # Legacy/compat: if service returned plain data, print it directly
                    # Convert lists to newline-joined text for readability
                    if isinstance(result, list):
                        console.print("\n".join(str(i) for i in result))
                    else:
                        console.print(str(result))
            else:
                # For structured formats (JSON, YAML, MATRIX, TABLE), use Console pipeline
                from coregen.cli.enums.enum_output_format import OutputFormat

                if output_format == DetectChangesOutputFormat.JSON:
                    if isinstance(result, DetectChangesResult):
                        data = self._prepare_output_data(result)
                    else:
                        # Pass through legacy list/dict results directly  # type: ignore[unreachable]
                        data = result  # type: ignore[unreachable]
                    console.print(data, output_format=OutputFormat.JSON)
                elif output_format == DetectChangesOutputFormat.YAML:
                    if isinstance(result, DetectChangesResult):
                        data = self._prepare_output_data(result)
                    else:
                        data = result  # type: ignore[unreachable]
                    console.print(data, output_format=OutputFormat.YAML)
                elif output_format == DetectChangesOutputFormat.MATRIX:
                    if isinstance(result, DetectChangesResult):
                        matrix_data = result.to_matrix_format()
                        # Apply filtering for matrix output
                        if self.options and self.options.get("changed_only", False):
                            matrix_data["include"] = [
                                c
                                for c in matrix_data["include"]
                                if c["status"] == "changed"
                            ]
                        elif self.options and self.options.get("deleted_only", False):
                            matrix_data["include"] = [
                                c
                                for c in matrix_data["include"]
                                if c["status"] == "deleted"
                            ]
                    else:
                        # Allow list/dict to flow into matrix formatter  # type: ignore[unreachable]
                        matrix_data = result  # type: ignore[unreachable]
                    console.print(matrix_data, output_format=OutputFormat.MATRIX)
                elif output_format == DetectChangesOutputFormat.TABLE:
                    if isinstance(result, DetectChangesResult):
                        table_data = self._prepare_table_data(result)
                    else:
                        # Simple fallback: list -> single-column Name table; dict -> key/value rows  # type: ignore[unreachable]
                        if isinstance(result, list):  # type: ignore[unreachable]
                            table_data = [["Name"], *[[str(x)] for x in result]]
                        elif isinstance(result, dict):
                            table_data = [
                                ["Key", "Value"],
                                *[[str(k), str(v)] for k, v in result.items()],
                            ]
                        else:
                            table_data = [["Value"], [str(result)]]
                    console.print(table_data, output_format=OutputFormat.TABLE)

            self.logger.debug("Detect-changes command completed successfully")

        except Exception as e:
            console.error(f"Failed to detect changes: {str(e)}")
            self.logger.exception("Error during detect-changes command execution:")
            sys.exit(2)
        finally:
            # Always reset output format
            console.set_output_format(None)
