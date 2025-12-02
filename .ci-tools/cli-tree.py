#!/usr/bin/env python3
"""
Typer Tree Visualizer - Display Typer CLI command structure as a tree.

Analyzes Python files to find and visualize Typer applications.
"""

import argparse
import ast
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import cast

import click
import typer
from rich import print
from rich.console import Console
from rich.tree import Tree

# Ensure we're running from the repo root
if __name__ == "__main__":
    # If running from .ci-tools, change to parent directory
    script_dir = Path(__file__).parent
    if script_dir.name == ".ci-tools":
        os.chdir(script_dir.parent)


def find_imports_in_ast(tree: ast.AST) -> dict[str, dict[str, str | None]]:
    """Extract all imports from AST."""
    imports: dict[str, dict[str, str | None]] = {}

    for node in ast.walk(tree):
        # Handle: from module import something
        if isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    import_name = alias.asname if alias.asname else alias.name
                    imports[import_name] = {
                        "module": node.module,
                        "name": alias.name,
                        "type": "from",
                    }

        # Handle: import module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                import_name = alias.asname if alias.asname else alias.name
                imports[import_name] = {
                    "module": alias.name,
                    "name": None,
                    "type": "import",
                }

    return imports


def find_typer_app_calls(
    tree: ast.AST, imports: dict[str, dict[str, str | None]]
) -> list[str]:
    """Find all potential Typer app calls in the AST."""
    app_calls: list[str] = []

    for node in ast.walk(tree):
        # Look for function calls like app()
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in imports:
                app_calls.append(node.func.id)
            # Also check for attribute access like something.app()
            elif isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id in imports:
                        app_calls.append(f"{node.func.value.id}.{node.func.attr}")

    return app_calls


def extract_typer_app_from_file(
    filepath: str, verbose: bool = False
) -> tuple[typer.Typer, str]:
    """Extract Typer app from a Python file by analyzing imports."""
    filepath = Path(filepath).resolve()

    if verbose:
        print(f"[dim]Analyzing file: {filepath}[/dim]")

    # Read and parse the file
    with open(filepath) as f:
        content = f.read()

    tree = ast.parse(content)

    # Extract all imports
    imports = find_imports_in_ast(tree)

    if verbose:
        print(f"[dim]Found imports: {list(imports.keys())}[/dim]")

    # Find app calls
    app_calls = find_typer_app_calls(tree, imports)

    if verbose and app_calls:
        print(f"[dim]Found app calls: {app_calls}[/dim]")

    # Strategy 1: Look for direct 'app' import or variable
    app_candidates: list[tuple[str, dict[str, str | None]]] = []

    for name, info in imports.items():
        # Direct app import
        if name == "app" or info["name"] == "app":
            app_candidates.append((name, info))
        # CLI module imports
        elif "cli" in info["module"].lower():
            app_candidates.append((name, info))
        # Check if called in the file
        elif name in app_calls:
            app_candidates.append((name, info))

    if not app_candidates:
        # Strategy 2: Look for any import that might be a Typer app
        for name, info in imports.items():
            if name in app_calls:
                app_candidates.append((name, info))

    if not app_candidates:
        raise ValueError(
            f"Could not find Typer app import in {filepath}\n"
            f"Found imports: {', '.join(imports.keys())}\n"
            f"Make sure your file imports a Typer app (e.g., 'from cli import app')"
        )

    # Setup Python path
    parent_dir = filepath.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    # Handle source directory structure
    if filepath.parent.name == "source" and filepath.parent.parent.exists():
        repo_root = filepath.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        # Also add source directory itself to path
        source_dir = filepath.parent
        if str(source_dir) not in sys.path:
            sys.path.insert(0, str(source_dir))

    # Try to import the app
    errors: list[str] = []
    for app_name, info in app_candidates:
        module_path = info["module"]
        if module_path is None:
            continue  # Skip if module path is None
        import_name = info["name"] if info["name"] else app_name

        if verbose:
            print(f"[dim]Trying to import '{import_name}' from '{module_path}'[/dim]")

        # Try different module path variations
        module_paths = [module_path]

        # If in source directory, try with source prefix
        if filepath.parent.name == "source":
            if not module_path.startswith("source.coregen."):
                module_paths.append(f"source.coregen.{module_path}")
            else:
                module_paths.append(module_path[7:])  # Without source prefix

        for path in module_paths:
            try:
                module = importlib.import_module(path)
                app = getattr(module, import_name)

                if isinstance(app, typer.Typer):
                    if verbose:
                        print(
                            f"[green]Success: Found Typer app '{import_name}' in '{path}'[/green]"
                        )
                    return app, import_name
                else:
                    errors.append(f"{import_name} is not a Typer instance")

            except ImportError as e:
                errors.append(f"Could not import {path}: {str(e)}")
            except AttributeError:
                errors.append(f"Module {path} has no attribute '{import_name}'")

    # If we get here, we couldn't import any app
    error_msg = "Failed to load Typer app:\n" + "\n".join(f"  - {e}" for e in errors)
    raise ImportError(error_msg)


def get_param_info(param: click.Parameter, show_help: bool = False) -> str:
    """Extract formatted parameter information."""
    parts: list[str] = []

    # Parameter type
    if hasattr(param.type, "name"):
        type_name = param.type.name.upper()
    else:
        type_name = param.type.__class__.__name__

    # Build parameter signature
    if isinstance(param, click.Argument):
        parts.append(f"[bold cyan]{param.name}[/bold cyan]")
    else:
        # Options with their flags
        opts = "/".join(param.opts)
        parts.append(f"[bold green]{opts}[/bold green]")
        if param.name != param.opts[0].lstrip("-").replace("-", "_"):
            parts.append(f"[dim]({param.name})[/dim]")

    # Type information with separator
    parts.append(f"• [yellow]{type_name}[/yellow]")

    # Required/Optional with separator
    if param.required:
        parts.append("• [red]required[/red]")
    else:
        parts.append("• [dim]optional[/dim]")

    # Default value with separator
    if param.default is not None and not param.required:
        if callable(param.default):
            parts.append("• [blue]default: <function>[/blue]")
        else:
            parts.append(f"• [blue]default: {param.default}[/blue]")

    # Help text
    if show_help and param.help:
        parts.append(f"\n    └─ {param.help}")

    return " ".join(parts)


def add_command_to_tree(
    tree_node: Tree, cmd_name: str, cmd: click.Command, show_help: bool = False
) -> None:
    """Add a command and its parameters to the tree."""
    # Command node with type indicator
    if isinstance(cmd, click.Group):
        cmd_node = tree_node.add(
            f"[bold blue]{cmd_name}[/bold blue] [dim](group)[/dim]"
        )
    else:
        cmd_node = tree_node.add(f"[bold blue]{cmd_name}[/bold blue]")

    # Add help text if available and requested
    if show_help and cmd.help:
        cmd_node.add(f"[dim italic]{cmd.help}[/dim italic]")

    # Separate arguments and options
    arguments: list[click.Argument] = []
    options: list[click.Option] = []

    for param in cmd.params:
        if isinstance(param, click.Argument):
            arguments.append(param)
        else:
            options.append(cast(click.Option, param))

    # Add arguments section
    if arguments:
        args_node = cmd_node.add("[bold]Arguments:[/bold]")
        for arg in arguments:
            args_node.add(get_param_info(arg, show_help))

    # Add options section
    if options:
        # Group options by their rich_help_panel
        option_groups: dict[str, list[click.Option]] = {}
        for opt in options:
            # Get the panel name - TyperOption has rich_help_panel attribute
            panel_name = getattr(opt, "rich_help_panel", "Options")
            if panel_name is None:
                panel_name = "Options"

            if panel_name not in option_groups:
                option_groups[panel_name] = []
            option_groups[panel_name].append(opt)

        # Sort panel names alphabetically
        sorted_panels = sorted(option_groups.keys())

        # Display each group
        for panel_name in sorted_panels:
            panel_node = cmd_node.add(f"[bold]{panel_name}:[/bold]")
            # Sort options within each group alphabetically by their primary flag
            sorted_options = sorted(
                option_groups[panel_name],
                key=lambda opt: (
                    opt.opts[0]
                    if opt.opts and opt.opts[0] is not None
                    else opt.name.cast(str)
                ),
            )
            for opt in sorted_options:
                panel_node.add(get_param_info(opt, show_help))

    # Handle subcommands for groups
    if isinstance(cmd, click.Group):
        if cmd.commands:
            subcmds_node = cmd_node.add("[bold]Subcommands:[/bold]")
            # Sort subcommands alphabetically
            for subcmd_name, subcmd in sorted(cmd.commands.items()):
                add_command_to_tree(subcmds_node, subcmd_name, subcmd, show_help)


def visualize_typer_app(
    app: typer.Typer, title: str | None = None, show_help: bool = False
) -> None:
    """
    Visualize a Typer application structure as a tree.

    Args:
        app: The Typer application instance
        title: Optional custom title for the tree
        show_help: Whether to display help text for commands and options
    """
    console = Console()

    # Get the Click app from Typer
    click_app = typer.main.get_command(app)

    # Create root tree node
    if title:
        tree = Tree(f"[bold]{title}[/bold]")
    else:
        tree = Tree(f"[bold]{click_app.name or 'CLI Application'}[/bold]")

    # Add app-level help if available and requested
    if show_help and click_app.help:
        tree.add(f"[dim italic]{click_app.help}[/dim italic]")

    # Handle based on app type
    if isinstance(click_app, click.Group):
        # Add commands
        if click_app.commands:
            # Sort commands alphabetically
            for cmd_name, cmd in sorted(click_app.commands.items()):
                add_command_to_tree(tree, cmd_name, cmd, show_help)
    else:
        # Single command app - show its parameters directly
        if click_app.params:
            arguments: list[click.Argument] = []
            options: list[click.Option] = []

            for param in click_app.params:
                if isinstance(param, click.Argument):
                    arguments.append(param)
                else:
                    options.append(cast(click.Option, param))

            if arguments:
                args_node = tree.add("[bold]Arguments:[/bold]")
                for arg in arguments:
                    args_node.add(get_param_info(arg, show_help))

            if options:
                # Group options by their rich_help_panel
                option_groups: dict[str, list[click.Option]] = {}
                for opt in options:
                    # Get the panel name - TyperOption has rich_help_panel attribute
                    panel_name = getattr(opt, "rich_help_panel", "Options")
                    if panel_name is None:
                        panel_name = "Options"

                    if panel_name not in option_groups:
                        option_groups[panel_name] = []
                    option_groups[panel_name].append(opt)

                # Sort panel names alphabetically
                sorted_panels = sorted(option_groups.keys())

                # Display each group
                for panel_name in sorted_panels:
                    panel_node = tree.add(f"[bold]{panel_name}:[/bold]")
                    # Sort options within each group alphabetically by their primary flag
                    sorted_options = sorted(
                        option_groups[panel_name],
                        key=lambda opt: (
                            opt.opts[0]
                            if opt.opts and opt.opts[0] is not None
                            else opt.name
                        ),
                    )
                    for opt in sorted_options:
                        panel_node.add(get_param_info(opt, show_help))

    # Print the tree
    console.print(tree)


def create_example_app() -> typer.Typer:
    """Create an example Typer app for demonstration."""
    app = typer.Typer(help="Example CLI application with multiple commands")

    @app.command()
    def hello(
        name: str = typer.Argument(..., help="Name to greet"),
        loud: bool = typer.Option(False, "--loud", "-l", help="Greet loudly"),
        repeat: int = typer.Option(
            1, "--repeat", "-r", help="Number of times to greet"
        ),
    ) -> None:
        """Greet someone with style."""

    @app.command()
    def goodbye(
        name: str = typer.Argument(..., help="Name to say goodbye to"),
        formal: bool = typer.Option(
            False, "--formal", "-f", help="Use formal farewell"
        ),
    ) -> None:
        """Say goodbye to someone."""

    # Create a subcommand group
    user_app = typer.Typer(help="User management commands")
    app.add_typer(user_app, name="user")

    @user_app.command()
    def create(
        username: str = typer.Argument(..., help="Username for the new user"),
        email: str = typer.Option(..., "--email", "-e", help="User's email address"),
        admin: bool = typer.Option(False, "--admin", help="Grant admin privileges"),
    ) -> None:
        """Create a new user."""

    @user_app.command()
    def delete(
        username: str = typer.Argument(..., help="Username to delete"),
        force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    ) -> None:
        """Delete an existing user."""

    return app


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize Typer CLI command structure as a tree",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s source/coregen/main.py      Visualize app from main.py
  %(prog)s app.py --verbose            Show import detection details
  %(prog)s --example                   Show example output

The tool will analyze your Python file to find Typer app imports
and display the complete command structure including all arguments,
options, and subcommands.
        """,
    )

    parser.add_argument(
        "file", nargs="?", help="Path to Python file containing Typer app import"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed import detection information",
    )

    parser.add_argument(
        "-e", "--example", action="store_true", help="Show example app structure"
    )

    parser.add_argument(
        "--show-help",
        action="store_true",
        help="Show help text for commands and options",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    args = parser.parse_args()

    # Handle example mode
    if args.example or not args.file:
        if not args.file and not args.example:
            parser.print_help()
            print()

        print("[yellow]Showing example app structure:[/yellow]\n")
        example_app = create_example_app()
        visualize_typer_app(example_app, "Example CLI", show_help=args.show_help)

        if not args.example:
            print("\n[dim]To visualize your own app, provide a file path:[/dim]")
            print(f"[dim]{parser.prog} path/to/main.py[/dim]")

        sys.exit(0)

    # Process the file
    if not os.path.exists(args.file):
        print(f"[red]Error:[/red] File not found: {args.file}")
        sys.exit(1)

    try:
        app, _ = extract_typer_app_from_file(args.file, verbose=args.verbose)
        visualize_typer_app(app, f"CLI from {args.file}", show_help=args.show_help)
    except (ImportError, ValueError) as e:
        print(f"[red]Error:[/red] {e}")
        if not args.verbose:
            print(
                "\n[yellow]Tip:[/yellow] Use --verbose flag for detailed debugging information"
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
