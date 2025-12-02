"""Formatters for generate command output."""

from typing import Any

from rich.box import HEAVY_HEAD
from rich.panel import Panel
from rich.table import Table

from coregen.cli.enums.enum_output_format import GenerateOutputFormat
from coregen.common.console import Console


class GenerateTableFormatter:
    """Formatter for table output of generate command."""

    def __init__(self, console: Console | None = None):
        """Initialize the formatter."""
        self.console = console or Console()

    def format(
        self,
        results: dict[str, Any],
        num_generated: int,
        num_components: int,
        num_errors: int,
        num_warnings: int,
        unique_errors: list[str],
        dry_run: bool = False,
    ) -> None:
        """Format and display results in table format."""
        # Create table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=HEAVY_HEAD,
            border_style="blue",
        )

        # Add columns
        table.add_column("Context", style="cyan", no_wrap=True)
        table.add_column("Component", style="white")
        table.add_column("Priority", justify="center", style="yellow")
        table.add_column("Status", justify="center")
        table.add_column("For Commit", justify="center")
        table.add_column("Files", justify="center", style="yellow")

        # Add rows from component details
        component_details = results.get("component_details", [])
        for detail in component_details:
            status = "[green]✓[/]" if detail["status"] else "[red]✗[/]"
            for_commit = "[green]True[/]" if detail["for_commit"] else "[dim]False[/]"
            priority = (
                str(detail.get("priority", ""))
                if detail.get("priority") is not None
                else ""
            )

            table.add_row(
                detail["context"],
                detail["component"],
                priority,
                status,
                for_commit,
                str(detail["files"]),
            )

        # Add totals row
        table.add_section()
        table.add_row(
            "[bold]TOTAL[/]",
            f"[bold]{num_components}[/]",
            "",
            "",
            "",
            f"[bold]{num_generated}[/]",
            style="bold on dark_blue",
        )

        # Display the table
        if dry_run:
            self.console.print(
                Panel(
                    table,
                    title="[bold red]DRY RUN MODE[/]",
                    title_align="center",
                    border_style="red",
                    expand=False,
                )
            )
        else:
            self.console.print(table)

        # Show errors below the table
        if num_errors > 0:
            self.console.print("\n[red]Errors:[/]")
            for error_msg in unique_errors:
                self.console.print(f"  • {error_msg}")

        # Show warnings if any
        if num_warnings > 0:
            self.console.print("\n[yellow]Warnings:[/]")
            for warning in results.get("warnings", []):
                self.console.print(f"  • {warning}")


class GenerateTextFormatter:
    """Formatter for text output of generate command."""

    def __init__(self, console: Console | None = None):
        """Initialize the formatter."""
        self.console = console or Console()

    def format(
        self,
        results: dict[str, Any],
        options: dict[str, Any],
        num_contexts: int,
        num_components: int,
        num_generated: int,
        num_skipped: int,
        num_errors: int,
        num_warnings: int,
        unique_errors: list[str],
    ) -> None:
        """Format and display results in text format."""
        self.console.info("\n")
        self.console.info("Generation Summary:")
        self.console.info(f"  Contexts processed: {num_contexts}")
        self.console.info(f"  Components generated: {num_components}")
        self.console.info(f"  Files generated: {num_generated}")
        self.console.info(f"  Files skipped: {num_skipped}")
        self.console.info(f"  Errors: [red]{num_errors}[/]")
        self.console.info(f"  Warnings: {num_warnings}")

        if num_warnings > 0:
            self.console.info("\n")
            self.console.info("Warnings:")
            for warning in results.get("warnings", []):
                self.console.info(f"  - {warning}")

        if num_errors > 0:
            self.console.info("\n")
            self.console.info("Encountered Errors:")
            for error_msg in unique_errors:
                self.console.info(f"  - [red]ERROR:[/] {error_msg}")

        # In verbose mode, show skipped files if any
        if options.get("verbose") and num_skipped > 0:
            self.console.info("\nSkipped Files:")
            for file in results.get("skipped_files", []):
                self.console.info(f"  - {file}")


class GenerateFormatter:
    """Main formatter that delegates to specific formatters."""

    def __init__(self, console: Console | None = None):
        """Initialize the formatter."""
        self.console = console or Console()
        self.table_formatter = GenerateTableFormatter(console)
        self.text_formatter = GenerateTextFormatter(console)

    def format_results(
        self,
        results: dict[str, Any],
        options: dict[str, Any],
        output_format: GenerateOutputFormat,
    ) -> int:
        """Format and display results based on output format.

        Returns:
            Number of errors that occurred
        """
        # Count results
        num_generated = len(results.get("generated_files", []))
        num_skipped = len(results.get("skipped_files", []))
        original_errors = results.get("errors", [])
        unique_errors = list(dict.fromkeys(original_errors))
        num_errors = len(unique_errors)
        num_warnings = len(results.get("warnings", []))
        num_contexts = results.get("contexts_count", 0)
        num_components = results.get("components_count", 0)

        # Delegate to appropriate formatter
        if output_format == GenerateOutputFormat.TABLE:
            self.table_formatter.format(
                results,
                num_generated,
                num_components,
                num_errors,
                num_warnings,
                unique_errors,
                dry_run=options.get("dry_run", False),
            )
        else:
            self.text_formatter.format(
                results,
                options,
                num_contexts,
                num_components,
                num_generated,
                num_skipped,
                num_errors,
                num_warnings,
                unique_errors,
            )

        return num_errors
