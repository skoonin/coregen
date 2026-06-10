# Output Pipeline Pattern

## Pattern Name and Purpose

**Output Pipeline Pattern** - Ensures proper routing of output to stdout/stderr based on output format, preventing corruption of structured output (JSON/YAML/MATRIX) by verbose/debug messages.

## When to Use

- **ALWAYS** for all commands - even TEXT-only commands should follow the pattern for consistency
- **ALWAYS** when command supports structured output formats (JSON, YAML, MATRIX)
- **ALWAYS** when using FormatValidationMixin
- **NEVER** manipulate quiet_mode directly

### TEXT-Only Commands

The output pipeline pattern is used for ALL commands, including TEXT-only ones:

- Ensures consistent stderr/stdout routing across all commands
- Simplifies the mental model - one pattern for all commands
- Future-proofs commands if they add format support later
- No performance overhead for TEXT format

## Implementation Checklist

- [ ] Import FormatValidationMixin if supporting multiple formats
- [ ] Call `self.validate_output_format(output_format)` before processing
- [ ] Call `console.set_output_format(output_format)` after validation
- [ ] Use try/finally to ensure `console.set_output_format(None)` cleanup
- [ ] Use `console.print()` with output_format parameter for final output
- [ ] Never use print() or sys.stdout.write() directly

## Code Examples

### ✓CORRECT Implementation

```python
# Location: source/coregen/cli/commands/YOUR_COMMAND/your_cli.py

from cli.format_validation_mixin import FormatValidationMixin
from cli.enums.enum_output_format import OutputFormat
from common.console import Console

console = Console

class YourCommand(FormatValidationMixin):
    """Command with structured output support."""

    # Define supported formats
    SUPPORTED_FORMATS = [
        OutputFormat.JSON,
        OutputFormat.YAML,
        OutputFormat.TEXT,
        OutputFormat.TABLE,
    ]
    DEFAULT_FORMAT = OutputFormat.TEXT

    def run(self) -> None:
        """Execute command with proper output pipeline."""
        if not self.ctx:
            raise RuntimeError("Context not initialized")

        # Get output format from options
        output_format = self.options.get("output_format", self.DEFAULT_FORMAT)

        try:
            # Validate format is supported
            self.validate_output_format(output_format)

            # Set output format for proper stderr/stdout routing
            # This ensures verbose/debug go to stderr for structured formats
            console.set_output_format(output_format)

            # Your command logic here
            console.debug("Processing started...")  # Goes to stderr
            result = self.service.process()
            console.info("Processing complete")     # Goes to stderr

            # Output final result to stdout
            console.print(result, output_format=output_format)

        finally:
            # CRITICAL: Always reset output format
            console.set_output_format(None)
```

### ✓CORRECT Implementation (with spinner)

```python
def run(self) -> None:
    """Execute with spinner for long operations."""
    output_format = self.options.get("output_format", self.DEFAULT_FORMAT)

    try:
        self.validate_output_format(output_format)
        console.set_output_format(output_format)

        # Use spinner only for TEXT format
        if output_format == OutputFormat.TEXT:
            with console.progress_spinner("Processing...") as spinner:
                result = self.service.process()
                spinner.update("Complete!")
        else:
            # No spinner for structured formats
            result = self.service.process()

        console.print(result, output_format=output_format)

    finally:
        console.set_output_format(None)
```

### ✓CORRECT Implementation (TEXT-Only Command)

```python
# TEXT-only commands follow the pattern for consistency
class GenerateCommand:
    """Command that only supports TEXT output."""

    def run(self) -> None:
        """Execute command with proper output pipeline."""
        # Get options
        self.options = self._get_options()

        try:
            # Set output format even for TEXT-only
            output_format = self.global_options.output_format
            console.set_output_format(output_format)

            # Execute command logic
            self.service = GenerateService(global_options=self.global_options)
            results = self.service.generate_files(...)

            # Display results using console methods
            console.info("Generation Summary:")
            console.info(f"  Files generated: {num_generated}")

        finally:
            # Always clean up
            console.set_output_format(None)
```

### ✗ INCORRECT Implementation (Anti-patterns)

```python
# DON'T DO THIS - Missing output format setup
def run(self) -> None:
    # WRONG: Not setting output format
    result = self.service.process()
    console.print(result, output_format=output_format)

# DON'T DO THIS - Manipulating quiet mode
def run(self) -> None:
    # WRONG: Don't use - bypasses output pipeline
    old_quiet = console.quiet_mode
    if output_format in [OutputFormat.JSON, OutputFormat.YAML]:
        console.quiet_mode = True

    # WRONG: No cleanup in finally
    result = self.service.process()
    console.quiet_mode = old_quiet

# DON'T DO THIS - Direct stdout usage
def run(self) -> None:
    result = self.service.process()
    # WRONG: Bypasses output pipeline
    print(json.dumps(result))
```

## Common Mistakes

1. **Forgetting to set output format** - Verbose messages corrupt JSON/YAML
2. **Not cleaning up in finally** - Affects subsequent commands
3. **Using quiet_mode manipulation** - Use set_output_format instead
4. **Direct print/stdout usage** - Bypasses routing logic
5. **Using spinners with structured output** - Corrupts the output

## Testing the Pattern

### Unit Test Example

```python
# Location: /workspace/tests/cli/commands/test_your_command.py

def test_structured_output_routing(capsys, mock_service):
    """Test that verbose messages go to stderr with structured output."""
    runner = CliRunner(mix_stderr=False)  # Keep streams separate

    # Test JSON output with verbose
    result = runner.invoke(
        app,
        ["your-command", "--output", "json", "--verbose"],
        catch_exceptions=False
    )

    # Should succeed
    assert result.exit_code == 0

    # Stdout should contain only valid JSON
    stdout = result.stdout
    parsed = json.loads(stdout)  # Should not raise
    assert "result" in parsed

    # Stderr should contain verbose messages
    assert "Processing started" in result.stderr

def test_output_format_cleanup():
    """Test that output format is properly cleaned up."""
    runner = CliRunner()

    # Run command with JSON output
    result = runner.invoke(app, ["your-command", "-o", "json"])
    assert result.exit_code == 0

    # Verify console state is reset
    assert console._output_format is None
```

### Manual Testing

```bash
# Test that JSON output is clean (should parse without errors)
coregen your-command -o json --verbose | jq .

# Test that verbose messages go to stderr
coregen your-command -o json --verbose 2>stderr.log | jq .
cat stderr.log  # Should contain verbose messages

# Test YAML output
coregen your-command -o yaml --verbose | yq .
```

## For AI Workers

### Before Making Changes

1. Check if command has structured output support
2. Look for FormatValidationMixin usage
3. Verify SUPPORTED_FORMATS list
4. Check for existing output format handling

### When Implementing

1. Add FormatValidationMixin if needed
2. Define SUPPORTED_FORMATS for your command
3. Always use try/finally pattern
4. Call set_output_format() before any console output
5. Reset in finally block

### After Implementation

1. Test all supported output formats
2. Verify verbose/debug messages don't corrupt output
3. Test with piping to jq/yq
4. Ensure cleanup happens even on errors

## Output Format Behaviors

| Format | Verbose/Debug/Info | Final Output | Spinner |
| ------ | ------------------ | ------------ | ------- |
| TEXT   | stdout             | stdout       | Yes     |
| JSON   | stderr             | stdout       | No      |
| YAML   | stderr             | stdout       | No      |
| MATRIX | stderr             | stdout       | No      |
| TABLE  | stderr             | stdout       | No      |

## GenerateCommand

The `generate` command supports TEXT and TABLE output and follows the pattern:

**Current Implementation:**

- Supports TEXT and TABLE output formats
- Uses try/finally pattern with `console.set_output_format()`
- `GenerateService` returns structured results (generated/skipped files, errors,
  and per-component details); the command's formatter renders them
- Writes template outputs directly to the filesystem as a side effect

**Output Model:**

The generate command has a different output model compared to query commands like
`get` or `detect-changes`. Rather than returning a single structured document, it:

1. Writes template outputs directly to the filesystem
2. Returns per-component details that the formatter renders as TEXT status lines
   or a TABLE summary
3. Shows a final generation report

Because the service returns data instead of printing user-facing status, there is
no longer any quiet-mode manipulation: the previous TABLE-mode workaround that
fabricated a `GlobalOptions(quiet=True, ...)` object to suppress service output
has been removed. The same service instance is used for both formats.

**Reference Implementation:**
For proper output pipeline pattern usage, see `GetCommand` (`source/coregen/cli/commands/get/get_cli.py`) which demonstrates the correct implementation.

## Related Patterns

- [Global Options Pattern](./global-options-pattern.md) - How verbose/quiet affect output
- [Service Layer Pattern](./service-layer-pattern.md) - Services should not handle output format
- [Error Handling Pattern](./error-handling-pattern.md) - Error output routing

## Migration Guide

If you find code violating this pattern:

1. **Remove quiet_mode manipulation** - Replace with set_output_format()
2. **Add FormatValidationMixin** - If supporting multiple formats
3. **Wrap in try/finally** - Ensure cleanup
4. **Update tests** - Verify output routing
5. **Remove direct print()** - Use console.print()

## Command Examples

### Commands Properly Implementing Pattern

- `source/coregen/cli/commands/get/get_cli.py` - Reference implementation

### Commands Needing Updates (Issue #217)

- Detect Changes - Uses manual quiet_mode manipulation
- Config View - Missing set_output_format()
- Config Schema - Missing set_output_format()
- Check Pattern - TABLE-only but missing set_output_format()

## References

- Issue #217: Output pipeline inconsistency
- PR #210: Original stderr routing implementation
- `source/coregen/common/console.py` - Console class with set_output_format()
- `source/coregen/cli/format_validation_mixin.py` - Format validation mixin
