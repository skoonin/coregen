# Global Options Implementation Guide

This document provides a guide for implementing the new GlobalOptions pattern across commands and services in Coregen.

## Overview

The GlobalOptions pattern provides a standardized way to handle global CLI options across all commands in the application.
By using this pattern consistently, we ensure:

1. Consistent access to global options
2. Proper handling of config_file paths
3. Default values from settings
4. CLI option overrides
5. Clean service initialization

## Critical Requirements

**IMPORTANT**: Commands MUST define all global options in their callback signatures and store them in ctx.obj. This is required for GlobalOptions.from_context() to work properly. The global options cannot be inherited or shared - each command must explicitly define them.

## Implementation Steps for Commands

To update a command to use GlobalOptions:

### 1. Define Global Options in the Callback

Commands MUST define all global options in their callback method and store them in ctx.obj for GlobalOptions.from_context() to work properly:

```python
@staticmethod
def callback(
    ctx: typer.Context,
    # Command-specific options first
    pattern: str,
    special_option: bool = False,
    # Global options MUST be defined here
    help: Annotated[bool, typer.Option(...)] = False,
    dry_run: Annotated[bool, typer.Option(...)] = settings.options.global_options.dry_run,
    no_color: Annotated[bool, typer.Option(...)] = settings.options.global_options.no_color,
    quiet: Annotated[bool, typer.Option(...)] = settings.options.global_options.quiet,
    verbose: Annotated[bool, typer.Option(...)] = settings.options.global_options.verbose,
    config_file: Annotated[Path | None, typer.Option(...)] = settings.options.global_options.config_file,
    file_action: Annotated[FileAction, typer.Option(...)] = settings.options.global_options.file_action,
) -> None:
    """Command help text."""
    # Ensure ctx.obj exists
    if ctx.obj is None:
        ctx.obj = {}

    # Store ALL global options in ctx.obj - this is REQUIRED
    ctx.obj["dry_run"] = dry_run
    ctx.obj["no_color"] = no_color
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose
    ctx.obj["config_file"] = config_file
    ctx.obj["file_action"] = file_action

    # Store command-specific options
    ctx.obj["pattern"] = pattern
    ctx.obj["special_option"] = special_option

    # Create and run command
    cmd = YourCommand()
    cmd.ctx = ctx
    cmd.run()
```

### 2. Update the Command's _get_options Method

```python
def _get_options(self) -> Dict[str, Any]:
    """Get command options from context with defaults from settings."""
    # Use GlobalOptions.from_context() which reads from ctx.obj
    global_options = GlobalOptions.from_context(self.ctx)

    # Create the options dictionary
    options = global_options.to_dict()

    # Add command-specific options
    command_options = {
        "pattern": self.ctx.obj.get("pattern"),
        "special_option": self.ctx.obj.get("special_option"),
    }

    # Merge global and command-specific options
    options.update(command_options)

    return options
```

### 3. Update Service Initialization in the run() Method

```python
def run(self) -> None:
    """Run the command."""
    # Get global options using the standardized method
    self.global_options = GlobalOptions.from_context(self.ctx)

    # Get all options including command-specific ones
    self.options = self._get_options()
    self.logger.debug(f"Running command with options: {self.options}")

    # Create service instance with GlobalOptions
    self.service = MyService(global_options=self.global_options)

    # Call service methods with command-specific parameters
    results = self.service.process(
        pattern=self.options["pattern"],
        special_option=self.options["special_option"],
    )
```

## Implementation Steps for Services

To update a service to use GlobalOptions:

### 1. Update Service's __init__ Method

```python
def __init__(self, **kwargs):
    """Initialize the service."""
    # Initialize logger first
    self.logger = Logger(__name__)

    # Check if global_options is provided
    from cli.global_options import GlobalOptions
    global_options = kwargs.get("global_options")

    # If global_options isn't provided but we have kwargs that match GlobalOptions attributes,
    # create a GlobalOptions instance
    if global_options is None and any(k in GlobalOptions.__init__.__code__.co_varnames for k in kwargs):
        self.logger.debug("Creating GlobalOptions from kwargs")
        global_options = GlobalOptions.from_dict(kwargs)
        # Add global_options to kwargs for ServicesBase
        kwargs["global_options"] = global_options

    # ServicesBase handles global_options and config_file
    super().__init__(**kwargs)

    # Store kwargs as options for backward compatibility
    self.options = kwargs.copy()

    self.logger.debug(f"Initialized {self.__class__.__name__}")
```

### 2. Use config_access for Configuration

Instead of manually loading configuration, use the `config_access` property from `ServicesBase`:

```python
# Access config_access to trigger loading of configuration
config = self.config_access.config
self.logger.debug("Successfully loaded configuration through config_access")
```

## Benefits

1. **Consistency**: All commands handle global options the same way
2. **Maintainability**: Centralized option handling in one place
3. **Less Duplication**: No need to manually parse options in each command
4. **Better Error Handling**: Consistent handling of config file paths and errors
5. **Future-Proofing**: Adding new global options only requires updating the GlobalOptions class

## Example Commands

The following commands correctly implement the GlobalOptions pattern:

- `detect_changes_cli.py` - Complete implementation with all patterns
- `cfg_schema.py` - Correctly uses GlobalOptions.from_context()
- `get_cli.py` - Reference implementation

See these files for complete examples of the pattern.

## Migration Notes

When migrating existing commands/services:

1. Add GlobalOptions but maintain backward compatibility
2. Use the config_access property instead of direct configuration loading
3. Run tests to ensure the command still works as expected
4. Update one command/service at a time to minimize risk
