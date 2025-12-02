# Error Handling Pattern

## Pattern Name and Purpose

**Error Handling Pattern** - Standardizes how errors are defined, raised, caught, and presented to users throughout the application, ensuring consistent and helpful error messages.

## When to Use

- **ALWAYS** when defining new error conditions
- **ALWAYS** use custom exceptions for domain-specific errors
- **ALWAYS** provide context in error messages
- **NEVER** catch generic Exception without re-raising
- **NEVER** silently swallow errors

## Implementation Checklist

- [ ] Create custom exception classes for specific error types
- [ ] Include relevant context in exception messages
- [ ] Log errors before re-raising or handling
- [ ] Use appropriate exit codes in CLI
- [ ] Provide user-friendly error messages
- [ ] Clean up resources in finally blocks
- [ ] Test error scenarios

## Code Examples

### ✓CORRECT Custom Exceptions

```python
# Location: Domain-specific modules (e.g., source/coregen/common/pattern/pattern_parser.py)

from pathlib import Path
from typing import Any

# Example: PatternParseError in pattern_parser.py
class PatternParseError(ValueError):
    """Raised when pattern parsing fails with helpful context."""

    def __init__(
        self,
        message: str,
        pattern: str,
        suggestions: list[str] | None = None
    ):
        super().__init__(message)
        self.pattern = pattern
        self.suggestions = suggestions or []

# Note: Coregen uses scattered exception classes in domain-specific modules
# rather than a centralized exception hierarchy. This is a valid approach that
# keeps exceptions close to their usage.

# Example of other domain-specific exceptions you might create:
class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_path: Path | None = None):
        super().__init__(message)
        self.config_path = config_path

class GenerationError(Exception):
    """Raised when code generation fails."""

    def __init__(self, component: str, reason: str):
        message = f"Failed to generate {component}: {reason}"
        super().__init__(message)
        self.component = component
```

### ✓CORRECT Service Error Handling

```python
# Location: source/coregen/services/your_service.py

from common.logger import Logger
# Import domain-specific exceptions as needed

class YourService(ServiceBase):
    """Service with proper error handling."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = Logger(self.__class__.__name__)

    def process(self, config_path: Path) -> dict[str, Any]:
        """Process configuration with comprehensive error handling."""
        try:
            # Validate input
            if not config_path:
                raise ValueError("Configuration path cannot be empty")

            # Check file exists
            if not self._file_manager.file_exists(config_path):
                raise ConfigurationError(
                    f"Configuration file not found: {config_path}",
                    config_path=config_path
                )

            # Read and parse configuration
            try:
                content = self._file_manager.read_file(config_path)
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                self.logger.error(f"YAML parsing error: {e}")
                raise ConfigurationError(
                    f"Invalid YAML in configuration file",
                    config_path=config_path,
                    details={"parse_error": str(e)}
                )
            except Exception as e:
                self.logger.error(f"Unexpected error reading config: {e}")
                raise ConfigurationError(
                    f"Failed to read configuration: {str(e)}",
                    config_path=config_path
                )

            # Process data
            return self._process_data(data)

        except CoregenError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Log unexpected errors before re-raising
            self.logger.exception("Unexpected error in process method")
            raise GenerationError(
                component="configuration",
                reason=f"Unexpected error: {str(e)}"
            )
```

### ✓CORRECT CLI Error Handling

```python
# Location: source/coregen/cli/commands/your_command/your_cli.py

import typer
# Import domain-specific exceptions as needed

class YourCommand:
    """Command with proper error handling."""

    def run(self) -> None:
        """Execute command with error handling."""
        try:
            # Validate output format
            output_format = self.options.get("output_format")
            self.validate_output_format(output_format)

            # Set output format
            console.set_output_format(output_format)

            # Process
            result = self.service.process(self.options["pattern"])
            console.print(result, output_format=output_format)

        except ValueError as e:
            # User input errors - exit code 2
            self.logger.error(f"Validation error: {e}")
            console.error(f"Invalid input: {str(e)}")
            raise typer.Exit(2)

        except FileNotFoundError as e:
            # File not found errors - exit code 1
            self.logger.error(f"File not found: {e}")
            console.error(f"File not found: {str(e)}")
            raise typer.Exit(1)

        except TypeError as e:
            # Type errors - exit code 1
            self.logger.error(f"Type error: {e}")
            console.error(f"Failed to generate files (TypeError): {str(e)}")
            raise typer.Exit(1)

        except Exception as e:
            # Unexpected errors - log full traceback
            self.logger.exception("Unexpected error")
            console.error(f"Unexpected error: {str(e)}")
            console.error("Please check the logs for more details.")
            raise typer.Exit(1)

        finally:
            # Always clean up
            console.set_output_format(None)
```

### ✗ INCORRECT Error Handling (Anti-patterns)

```python
# DON'T DO THIS - Catching and ignoring
try:
    process_data()
except Exception:
    pass  # WRONG: Silent failure

# DON'T DO THIS - Generic exceptions
raise Exception("Something went wrong")  # WRONG: No context

# DON'T DO THIS - Print and continue
try:
    result = service.process()
except Exception as e:
    print(f"Error: {e}")  # WRONG: Use console.error
    result = {}  # WRONG: Masking the error

# DON'T DO THIS - No cleanup
console.set_output_format(format)
result = process()  # WRONG: No finally block
console.print(result)

# DON'T DO THIS - Poor error messages
raise ValueError("Invalid")  # WRONG: What's invalid?
```

## Exit Code Standards

| Code | Meaning       | Usage                        |
| ---- | ------------- | ---------------------------- |
| 0    | Success       | Normal completion            |
| 1    | General error | Catch-all for errors         |
| 2    | Invalid input | Validation/generation errors |

Note: Coregen uses exit codes 0, 1, and 2. Exit code 3 is not used.

## Common Mistakes

1. **Silent failures** - Catching without handling
2. **Generic messages** - "Error occurred" without context
3. **No logging** - Errors not recorded for debugging
4. **Missing cleanup** - Resources not released
5. **Wrong exit codes** - Not following standards

## Error Message Guidelines

### User-Facing Messages

```python
# Good - Clear and actionable
console.error(f"Configuration file not found: {path}")
console.error("Create one with: coregen config init")

# Bad - Technical jargon
console.error(f"IOError: [Errno 2] No such file or directory: '{path}'")
```

### Log Messages

```python
# Good - Detailed context
self.logger.error(
    f"Failed to parse pattern '{pattern}' at position {pos}: "
    f"unexpected character '{char}'"
)

# Bad - No context
self.logger.error("Parse error")
```

## For AI Workers

### Before Implementing

1. Check for existing exception classes
2. Understand the error scenarios
3. Plan appropriate exit codes
4. Consider user experience

### When Implementing

1. Create specific exception classes
2. Include all relevant context
3. Log before presenting to user
4. Use console.error for output
5. Clean up in finally blocks

### After Implementation

1. Test all error scenarios
2. Verify exit codes are correct
3. Check error messages are helpful
4. Ensure logging is adequate

## Exception Strategy

Coregen uses a **scattered exception approach** where custom exceptions are defined in their domain-specific modules rather than a centralized hierarchy. This keeps exceptions close to their usage:

- `PatternParseError` in `source/coregen/common/pattern/pattern_parser.py`
- Template errors handled via Jinja2's built-in exceptions
- File errors use Python's built-in exceptions (FileNotFoundError, PermissionError, etc.)
- Validation errors typically use ValueError or custom domain exceptions

This approach is simpler and avoids over-engineering when you don't need a complex exception hierarchy.

## Testing Error Handling

```python
def test_error_with_context(service):
    """Test that errors include proper context."""
    with pytest.raises(ConfigurationError) as exc_info:
        service.process(Path("/invalid/path"))

    error = exc_info.value
    assert "not found" in str(error)
    assert error.config_path == Path("/invalid/path")

def test_cli_error_exit_code(runner, cli_app):
    """Test CLI exits with correct code."""
    result = runner.invoke(cli_app, ["command", "--invalid"])
    assert result.exit_code == 2  # Validation error
```

## Related Patterns

- [Service Layer Pattern](./service-layer-pattern.md) - Error handling in services
- [CLI Command Pattern](./cli-command-pattern.md) - CLI error presentation
- [Testing Pattern](./testing-pattern.md) - Testing error scenarios

## References

- Python exception hierarchy: https://docs.python.org/3/library/exceptions.html
- Exit code standards: https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html
