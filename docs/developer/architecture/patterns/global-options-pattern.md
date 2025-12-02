# Global Options Pattern

## Pattern Name and Purpose

**Global Options Pattern** - Standardizes how global CLI options (verbose, quiet, dry-run, etc.) are accessed and propagated throughout the application.

## When to Use

- **ALWAYS** when implementing a new CLI command
- **ALWAYS** when accessing global options in any command
- **ALWAYS** when passing options to service classes
- **ALWAYS** define ALL global options in command callbacks (required by Typer for help output)
  - This is required, even though Typer makes it look like you don't need it!

## Global Options vs Command-Specific Options

**Global Options** are available across all (or most) commands but may have different default values per command.

### Key Concept: Global Availability ≠ Same Default

An option can be globally available while having command-specific defaults. This is different from command-specific options which are only available on certain commands.

**Example: `--output` option**
- **Availability**: Global (available on most commands)
- **Defaults**: Command-specific
  - `get`: YAML (default)
  - `detect-changes`: TABLE (default)
  - `generate`: TEXT only (no other formats supported)

### When Implementing Global Options

1. **Define the option in the global callback or parent command** - Makes it available to all subcommands
2. **Allow each command to specify its own default** - Use command-specific default values in settings
3. **Document both the global availability and per-command defaults** - Clear documentation prevents confusion

**Example Implementation:**

```python
# In get command
@staticmethod
def callback(
    ctx: typer.Context,
    pattern: str,
    output_format: Annotated[OutputFormat, typer.Option(...)] = OutputFormat.YAML,  # Get default
    # ... other options
) -> None:
    # Implementation...

# In detect-changes command
@staticmethod
def callback(
    ctx: typer.Context,
    output_format: Annotated[OutputFormat, typer.Option(...)] = OutputFormat.TABLE,  # Detect-changes default
    # ... other options
) -> None:
    # Implementation...
```

Both commands have access to `--output`, but each has its own appropriate default.

### Documentation Guidelines

When documenting global options with command-specific defaults:
- Mark as **global** in option tables
- Clearly state that defaults vary by command
- List the default for each command that uses it
- Explain why different defaults make sense for different contexts

## Implementation Checklist

- [ ] Import GlobalOptions from `source/coregen/cli/global_options.py`
- [ ] Define ALL global options in command callback signatures (Typer requirement)
- [ ] Store ALL global options in `ctx.obj` in callback method
- [ ] Handle parent context inheritance for nested commands
- [ ] Apply boolean OR logic for flags (e.g., `dry_run or parent_obj.get("dry_run", False)`)
- [ ] Apply conditional storage for non-boolean options
- [ ] Access options via `GlobalOptions.from_context(ctx)` in command's `run()` method
- [ ] Pass `global_options` parameter to service constructors

## Code Examples

### ✓CORRECT Implementation

```python
# Location: source/coregen/cli/commands/YOUR_COMMAND/your_cli.py

from typing import Annotated, Any
from pathlib import Path
import typer
from cli.enums.enum_file_action import FileAction
from cli.global_options import GlobalOptions
from config_model.models.settings import get_settings
from services.your_service import YourService
from common.console import Console

settings = get_settings()

console = Console

class YourCommand:
    """Command implementation following global options pattern."""

    def __init__(self) -> None:
        """Initialize command."""
        self.ctx = None
        self.global_options = None
        self.service = None

    @staticmethod
    def callback(
        ctx: typer.Context,
        # Command-specific parameters first
        pattern: Annotated[
            str,
            typer.Argument(help="Pattern to process")
        ],
        special_option: Annotated[
            bool,
            typer.Option("--special", help="Command-specific option")
        ] = False,
        # ALL global options MUST be defined here
        dry_run: Annotated[bool, typer.Option(...)] = settings.options.global_options.dry_run,
        no_color: Annotated[bool, typer.Option(...)] = settings.options.global_options.no_color,
        quiet: Annotated[bool, typer.Option(...)] = settings.options.global_options.quiet,
        verbose: Annotated[bool, typer.Option(...)] = settings.options.global_options.verbose,
        config_file: Annotated[Path | None, typer.Option(...)] = settings.options.global_options.config_file,
        file_action: Annotated[FileAction, typer.Option(...)] = settings.options.global_options.file_action,
    ) -> None:
        """Command callback - handles CLI interaction."""
        if not ctx.obj:
            ctx.obj = {}

        # Handle parent context inheritance
        parent_obj = (
            ctx.parent.obj
            if ctx.parent and hasattr(ctx.parent, "obj") and ctx.parent.obj
            else {}
        )

        # Store global options with parent inheritance
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

        # Store command-specific options
        ctx.obj["pattern"] = pattern
        ctx.obj["special_option"] = special_option

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

        # Initialize service with global options
        self.service = YourService(global_options=self.global_options)

        # Get command-specific options
        pattern = self.ctx.obj.get("pattern")
        special_option = self.ctx.obj.get("special_option", False)

        # Execute service logic
        result = self.service.process(pattern, special_option)
        console.print(result)
```

### ✗ INCORRECT Implementation (Anti-patterns)

```python
# DON'T DO THIS - Not handling parent context
@staticmethod
def callback(
    ctx: typer.Context,
    pattern: str,
    dry_run: bool = settings.options.global_options.dry_run,
    verbose: bool = settings.options.global_options.verbose,
) -> None:
    # WRONG: Not checking for parent context
    ctx.obj["dry_run"] = dry_run  # Missing OR logic
    ctx.obj["verbose"] = verbose  # Missing OR logic

# DON'T DO THIS - Direct ctx.obj access in run()
def run(self) -> None:
    # WRONG: Accessing global options directly instead of using GlobalOptions
    verbose = self.ctx.obj.get("verbose", False)
    dry_run = self.ctx.obj.get("dry_run", False)

    # WRONG: Not using GlobalOptions class
    self.service = YourService(verbose=verbose, dry_run=dry_run)

# DON'T DO THIS - Missing global options in callback
@staticmethod
def callback(
    ctx: typer.Context,
    pattern: str,
    # WRONG: Missing global options - they won't appear in help
) -> None:
    cmd = YourCommand()
    cmd.ctx = ctx
    cmd.run()
```

## Common Mistakes

1. **NOT defining global options in command callbacks** - Typer requires ALL options in callback for help
2. **NOT handling parent context inheritance** - Missing parent context check and OR logic
3. **Forgetting boolean OR logic** - Use `value or parent_obj.get("key", False)` for flags
4. **Not checking defaults for non-boolean options** - Only store if different from default
5. **Accessing ctx.obj["verbose"] directly in run()** - Use GlobalOptions.from_context()
6. **Passing individual options to services** - Pass entire global_options object

## Testing the Pattern

### Unit Test Example

```python
# Location: /workspace/tests/cli/commands/test_your_command.py

import pytest
from typer.testing import CliRunner
from cli.global_options import GlobalOptions
from cli.commands.your_command.your_cli import YourCommand

def test_command_uses_global_options(mock_settings):
    """Test that command properly uses GlobalOptions pattern."""
    runner = CliRunner()

    # Test with global options
    result = runner.invoke(
        app,
        ["your-command", "pattern", "--verbose", "--dry-run"]
    )

    # Verify command executed successfully
    assert result.exit_code == 0

    # For deeper testing, mock the service and verify global_options passed
    with patch("services.your_service.YourService") as mock_service:
        runner.invoke(app, ["your-command", "pattern", "--verbose"])

        # Verify service was initialized with GlobalOptions instance
        mock_service.assert_called_once()
        args, kwargs = mock_service.call_args
        assert "global_options" in kwargs
        assert isinstance(kwargs["global_options"], GlobalOptions)
```

### Verification Steps

1. Run the command with various global options:

   ```bash
   coregen your-command "pattern" --verbose --dry-run
   CG_VERBOSE=true coregen your-command "pattern"
   ```

2. Verify options are properly propagated to services
3. Check that no duplicate option storage occurs in ctx.obj

## For AI Workers

### Before Making Changes

1. Read this entire document
2. Check if the command already has global options defined (it shouldn't)
3. Look for GlobalOptions usage in similar commands
4. Verify you're not introducing anti-patterns

### When Implementing

1. Copy the CORRECT implementation example above
2. Replace `YourCommand` with actual command name
3. Add only command-specific parameters to callback
4. Always use `GlobalOptions.from_context(ctx)`
5. Pass `global_options` to all services

### After Implementation

1. Verify all checklist items are complete
2. Test with global options from CLI and environment
3. Ensure no regression in existing functionality
4. Check that service receives GlobalOptions instance

## Related Patterns

- [Service Layer Pattern](./service-layer-pattern.md) - How services accept global options
- [Output Pipeline Pattern](./output-pipeline-pattern.md) - How output format affects global options
- [Configuration Pattern](./configuration-pattern.md) - Default values for global options

## Migration Guide

If you find code violating this pattern:

1. **Add ALL global option parameters** to command callback with proper defaults from settings
2. **Add parent context inheritance logic** at the start of callback
3. **Implement boolean OR logic** for all boolean flags (dry_run, verbose, quiet, no_color)
4. **Add conditional storage** for non-boolean options (file_action, config_file)
5. **Store ALL options in ctx.obj** following the inheritance pattern
6. **Add GlobalOptions import** and usage in run() method
7. **Update service initialization** to accept global_options
8. **Test thoroughly** with nested commands and various option combinations

## References

- `source/coregen/cli/global_options.py` - GlobalOptions class implementation
- `source/coregen/cli/cli.py` - Main CLI with global option definitions
