# Coregen Architecture Patterns

This directory contains architectural patterns for the Coregen codebase. These patterns ensure consistency, maintainability, and proper implementation across all features.

## For AI Workers

**IMPORTANT**: When implementing any feature or fixing bugs, always check these patterns first. They contain critical implementation guidelines and known anti-patterns to avoid.

## Pattern Categories

### Critical Patterns

These patterns fix known inconsistencies and must be followed:

1. **[Global Options Pattern](./global-options-pattern.md)**

   - How to properly access and propagate CLI global options
   - Prevents redundant option storage and inconsistent access

2. **[Output Pipeline Pattern](./output-pipeline-pattern.md)**
   - Ensures proper stdout/stderr routing for structured output
   - Prevents corruption of JSON/YAML output by debug messages

### Core Architecture Patterns

These patterns form the foundation of the application:

3. **[Service Layer Pattern](./service-layer-pattern.md)**

   - Separation of business logic from CLI
   - Proper dependency injection and testing

4. **[CLI Command Pattern](./cli-command-pattern.md)**

   - Standard structure for CLI commands
   - Command registration and help text
   - Callback pattern

5. **[Configuration Pattern](./configuration-pattern.md)**
   - Settings management and defaults
   - Environment variable handling
   - Precedence rules

### Development Patterns

6. **[Testing Pattern](./testing-pattern.md)**

   - Test organization and fixtures
   - Mocking strategies
   - Unit vs integration testing

7. **[Error Handling Pattern](./error-handling-pattern.md)**

   - Exception hierarchy
   - User-friendly error messages
   - Exit code standards

8. **[Validation Pattern](./validation-pattern.md)**

   - Pydantic model validation
   - Input validation strategies
   - Custom validators

## Pattern Template

Each pattern document follows this structure:

1. **Pattern Name and Purpose** - Clear identification
2. **When to Use** - Explicit conditions
3. **Implementation Checklist** - Step-by-step guide
4. **Code Examples** - Copy-paste ready
5. **Common Mistakes** - Anti-patterns to avoid
6. **Testing the Pattern** - Verification steps
7. **For AI Workers** - Specific AI guidance

## Anti-Pattern Quick Reference

### Never Do These

```python
# Global Options Anti-patterns
ctx.obj["verbose"] = verbose  # Don't store global options
def cmd(verbose: bool):       # Don't redefine global options

# Output Pipeline Anti-patterns
console.quiet_mode = True     # Don't manipulate quiet mode
print(json.dumps(result))     # Don't bypass console

# Service Layer Anti-patterns
console.print(result)         # Don't output from services
file = open(path)            # Don't bypass FileManager
```

### Always Do These

```python
# Global Options
global_options = GlobalOptions.from_context(ctx)
service = YourService(global_options=global_options)

# Output Pipeline
console.set_output_format(output_format)
try:
    # ... work ...
finally:
    console.set_output_format(None)

# Service Layer
class YourService(ServiceBase):
    def process(self) -> dict:
        return {"result": "data"}  # Return data, not output
```

## Contributing New Patterns

When documenting a new pattern:

1. Use the pattern template structure
2. Include real code examples from the codebase
3. Document both correct and incorrect implementations
4. Add to this README with appropriate categorization
5. Update the quick decision guide if needed

## References

- [Coding Conventions](../../contributing/coding-standards.md) - General coding standards
