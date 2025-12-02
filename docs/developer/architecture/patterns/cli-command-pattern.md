# CLI Command Pattern

## Pattern Name and Purpose

**CLI Command Pattern** - Standardizes the structure and implementation of CLI commands, ensuring consistent user experience and maintainable code.

## When to Use

- **ALWAYS** when creating a new CLI command
- **ALWAYS** when refactoring existing commands
- **NEVER** put business logic in command classes
- **NEVER** mix CLI concerns with service logic

## Implementation Checklist

- [ ] Create command class with `__init__` and `run` methods
- [ ] Create static `callback` method for Typer registration
- [ ] Import and use GlobalOptions (see [Global Options Pattern](./global-options-pattern.md))
- [ ] Delegate business logic to service classes
- [ ] Handle output formatting if supporting multiple formats
- [ ] Group related options in `option_params` dictionary
- [ ] Add proper docstrings and help text
- [ ] Register command in appropriate CLI module

## Code Examples

### ✓CORRECT Implementation

```python
# Location: source/coregen/cli/commands/YOUR_COMMAND/your_cli.py

from pathlib import Path
from typing import Annotated, Any

import typer
from cli.enums.enum_output_format import OutputFormat
from cli.format_validation_mixin import FormatValidationMixin
from cli.global_options import GlobalOptions
from common.completion import complete_patterns
from common.console import Console
from common.logger import Logger
from config_model.models.settings import get_settings
from services.your_service import YourService

# Module setup
settings = get_settings()
console = Console  # Use class reference - Console uses class methods
logger = Logger(__name__)

# Option configuration for consistency
option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Options",
}

class YourCommand(FormatValidationMixin):
    """Command implementation for your functionality.

    This class handles CLI interaction and delegates business
    logic to the service layer.
    """

    # Define supported output formats if applicable
    SUPPORTED_FORMATS = [
        OutputFormat.TEXT,
        OutputFormat.JSON,
        OutputFormat.YAML,
    ]
    DEFAULT_FORMAT = OutputFormat.TEXT

    def __init__(self) -> None:
        """Initialize command instance."""
        self.logger = Logger(self.__class__.__name__)
        self.ctx = None
        self.global_options = None
        self.service = None

    @staticmethod
    def callback(
        ctx: typer.Context,
        # Positional arguments first
        pattern: Annotated[
            str,
            typer.Argument(
                help="Pattern to match items",
                autocompletion=complete_patterns,  # If applicable
            ),
        ],
        # Then command-specific options
        filter: Annotated[
            list[str] | None,
            typer.Option(
                "--filter",
                "-f",
                help="Filter results by criteria",
                **option_params,
            ),
        ] = None,
        output_format: Annotated[
            OutputFormat,
            typer.Option(
                "--output",
                "-o",
                help="Output format",
                **option_params,
            ),
        ] = settings.options.your_command.output_format,
        # IMPORTANT: ALL global options MUST be defined here for Typer help
        # See Global Options Pattern for proper implementation
        help: Annotated[
            bool,
            typer.Option(
                "--help",
                "-h",
                help="Show this message and exit.",
                **option_params,
            ),
        ] = False,
        dry_run: Annotated[bool, typer.Option(...)] = settings.options.global_options.dry_run,
        no_color: Annotated[bool, typer.Option(...)] = settings.options.global_options.no_color,
        quiet: Annotated[bool, typer.Option(...)] = settings.options.global_options.quiet,
        verbose: Annotated[bool, typer.Option(...)] = settings.options.global_options.verbose,
        config_file: Annotated[Path | None, typer.Option(...)] = settings.options.global_options.config_file,
        file_action: Annotated[FileAction, typer.Option(...)] = settings.options.global_options.file_action,
    ) -> None:
        """Process your items matching the given pattern.

        This command does X, Y, and Z. Use it when you need to...

        Examples:
            # Basic usage
            coregen your-command "pattern"

            # With filters
            coregen your-command "pattern" --filter "name=test"

            # With JSON output
            coregen your-command "pattern" --output json
        """
        # Initialize context and handle parent inheritance
        if not ctx.obj:
            ctx.obj = {}
            # Inherit from parent if exists
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj:
                ctx.obj.update(ctx.parent.obj)

        # Store command-specific options
        ctx.obj["pattern"] = pattern
        ctx.obj["filter"] = filter
        ctx.obj["output_format"] = output_format

        # Handle global options with parent inheritance
        parent_obj = (
            ctx.parent.obj
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj
            else {}
        )

        # Boolean flags use OR logic
        ctx.obj["dry_run"] = dry_run or parent_obj.get("dry_run", False)
        ctx.obj["no_color"] = no_color or parent_obj.get("no_color", False)
        ctx.obj["quiet"] = quiet or parent_obj.get("quiet", False)
        ctx.obj["verbose"] = verbose or parent_obj.get("verbose", False)

        # Non-boolean options check if different from default
        if (
            file_action != settings.options.global_options.file_action
            or "file_action" not in parent_obj
        ):
            ctx.obj["file_action"] = file_action

        if (
            config_file != settings.options.global_options.config_file
            or "config_file" not in parent_obj
        ):
            ctx.obj["config_file"] = config_file

        # Create and run command
        cmd = YourCommand()
        cmd.ctx = ctx
        cmd.run()

    def run(self) -> None:
        """Execute the command logic."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get global options using the standard pattern
        self.global_options = GlobalOptions.from_context(self.ctx)

        # Get command options
        pattern = self.ctx.obj.get("pattern")
        filters = self.ctx.obj.get("filter", [])
        output_format = self.ctx.obj.get("output_format", self.DEFAULT_FORMAT)

        try:
            # Validate output format if using FormatValidationMixin
            self.validate_output_format(output_format)

            # Set output format for proper routing
            console.set_output_format(output_format)

            # Initialize service with global options
            self.service = YourService(global_options=self.global_options)

            # Delegate to service for business logic
            self.logger.debug(f"Processing pattern: {pattern}")
            results = self.service.process(
                pattern=pattern,
                filters=filters,
            )

            # Output results in requested format
            console.print(results, output_format=output_format)

        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            console.error(f"Error: {str(e)}")
            raise typer.Exit(1)
        finally:
            # Always clean up
            console.set_output_format(None)
```

### ✓CORRECT Registration

```python
# Location: source/coregen/cli/commands/YOUR_COMMAND/__init__.py

import typer
from .your_cli import YourCommand

# Create command app
app = typer.Typer(
    name="your-command",
    help="Brief description of what this command does",
    rich_markup_mode="rich",
)

# Register the command
app.command()(YourCommand.callback)

# In main CLI app, add:
# app.add_typer(your_command.app, name="your-command")
```

### ✗ INCORRECT Implementation (Anti-patterns)

```python
# DON'T DO THIS - Business logic in command
class BadCommand:
    def run(self):
        # WRONG: Should be in service
        with open(self.file_path) as f:
            data = yaml.safe_load(f)

        # WRONG: Direct data manipulation
        for item in data["items"]:
            item["processed"] = True

        # WRONG: Direct file write
        with open(self.output_path, "w") as f:
            yaml.dump(data, f)

# DON'T DO THIS - No command class
@app.command()
def bad_command(pattern: str, verbose: bool = False):
    # WRONG: Everything in callback
    if verbose:
        print(f"Processing {pattern}")

    # WRONG: No service layer
    results = process_data(pattern)
    print(results)

# DON'T DO THIS - Redefining global options
@staticmethod
def callback(
    pattern: str,
    verbose: bool = False,  # WRONG: Global option
    dry_run: bool = False,  # WRONG: Global option
):
    pass
```

## Common Mistakes

1. **Business logic in command class** - Use services
2. **No command class structure** - Always use class pattern
3. **Redefining global options** - They're inherited
4. **Direct file/network operations** - Use services
5. **Missing error handling** - Always catch and log
6. **No output format cleanup** - Use finally block

## Testing the Pattern

### Unit Test Example

```python
# Location: /workspace/tests/cli/commands/test_your_command.py

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from cli.commands.your_command import app

class TestYourCommand:
    """Test cases for your-command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_service(self):
        """Mock the service to test CLI behavior."""
        with patch("cli.commands.your_command.your_cli.YourService") as mock:
            instance = MagicMock()
            mock.return_value = instance
            instance.process.return_value = {"result": "test"}
            yield instance

    def test_command_basic_usage(self, runner, mock_service):
        """Test basic command execution."""
        result = runner.invoke(app, ["pattern"])

        assert result.exit_code == 0
        mock_service.process.assert_called_once_with(
            pattern="pattern",
            filters=[],
        )

    def test_command_with_options(self, runner, mock_service):
        """Test command with various options."""
        result = runner.invoke(
            app,
            ["pattern", "--filter", "name=test", "--output", "json"]
        )

        assert result.exit_code == 0
        assert mock_service.process.called

        # Verify JSON output
        import json
        output_data = json.loads(result.stdout)
        assert output_data == {"result": "test"}

    def test_command_error_handling(self, runner, mock_service):
        """Test command handles errors gracefully."""
        mock_service.process.side_effect = ValueError("Test error")

        result = runner.invoke(app, ["pattern"])

        assert result.exit_code == 1
        assert "Error: Test error" in result.stdout
```

## For AI Workers

### Before Making Changes

1. Check if command already exists
2. Review similar commands for patterns
3. Identify required service(s)
4. Plan command-specific options

### When Implementing

1. Copy the CORRECT implementation template
2. Never add global options to callback
3. Always use command class structure
4. Delegate all logic to services
5. Handle errors with proper exit codes

### After Implementation

1. Test all option combinations
2. Verify global options work
3. Test error scenarios
4. Update command help text
5. Add to main CLI app

## Command Structure Guidelines

### Help Text

- First line: Brief description (shown in command list)
- Docstring: Detailed explanation with examples
- Option help: Clear, concise descriptions

### Option Organization

1. Positional arguments first
2. Required options next
3. Optional flags last
4. Group related options visually

### Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3+`: Command-specific errors

## Directory Structure

```
source/coregen/cli/commands/
├── your_command/
│   ├── __init__.py       # Command registration
│   └── your_cli.py       # Command implementation
├── config/               # Grouped commands
│   ├── __init__.py       # Group registration
│   ├── cfg_view.py       # Subcommand
│   └── cfg_init.py       # Subcommand
```

## Related Patterns

- [Global Options Pattern](./global-options-pattern.md) - Required reading
- [Output Pipeline Pattern](./output-pipeline-pattern.md) - For structured output
- [Service Layer Pattern](./service-layer-pattern.md) - For business logic
- [Error Handling Pattern](./error-handling-pattern.md) - For exceptions

## References

- `source/coregen/cli/commands/` - Example implementations
- `source/coregen/cli/cli.py` - Main CLI app
- Typer documentation: https://typer.tiangolo.com/
