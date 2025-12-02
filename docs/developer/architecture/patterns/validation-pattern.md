# Validation Pattern

## Pattern Name and Purpose

**Validation Pattern** - Standardizes how input validation, configuration validation, and data validation are performed throughout the application using Pydantic models and custom validators.

## When to Use

- **ALWAYS** when accepting user input
- **ALWAYS** when loading configuration files
- **ALWAYS** use Pydantic for structured data validation
- **ALWAYS** validate early in the processing pipeline
- **NEVER** trust external input without validation

## Implementation Checklist

- [ ] Use Pydantic models for structured data
- [ ] Add Field validators for complex rules
- [ ] Provide clear validation error messages
- [ ] Validate at service boundaries
- [ ] Use FormatValidationMixin for output formats
- [ ] Create custom validators for domain logic
- [ ] Test validation with invalid inputs

## Code Examples

### ✓CORRECT Pydantic Model Validation

```python
# Location: source/coregen/config_model/models/your_model.py

from typing import Annotated
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator

class ComponentConfig(BaseModel):
    """Component configuration with validation."""

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            pattern=r"^[a-z][a-z0-9-]*$",
            description="Component name (lowercase, alphanumeric, hyphens)"
        )
    ]

    type: Annotated[
        str,
        Field(
            description="Component type",
            examples=["service", "database", "cache"]
        )
    ]

    priority: Annotated[
        int,
        Field(
            ge=1,
            le=100,
            default=50,
            description="Processing priority (1-100)"
        )
    ] = 50

    path: Annotated[
        Path | None,
        Field(
            default=None,
            description="Optional override path"
        )
    ] = None

    dependencies: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="List of component dependencies"
        )
    ] = []

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate component name format."""
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Name cannot start or end with hyphen")
        if "--" in v:
            raise ValueError("Name cannot contain consecutive hyphens")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Path | None) -> Path | None:
        """Validate path if provided."""
        if v is None:
            return v

        # Convert to Path if string
        if isinstance(v, str):
            v = Path(v)

        # Check if absolute paths are allowed
        if v.is_absolute():
            raise ValueError("Absolute paths not allowed")

        return v

    @model_validator(mode="after")
    def validate_dependencies(self) -> "ComponentConfig":
        """Validate dependencies don't include self."""
        if self.name in self.dependencies:
            raise ValueError(f"Component cannot depend on itself: {self.name}")
        return self
```

### ✓CORRECT Custom Validator Class

```python
# Location: source/coregen/config_model/dictionary_validator.py

from typing import Any
from common.logger import Logger

class ConfigDictValidator:
    """Validates configuration dictionaries."""

    def __init__(self):
        self.logger = Logger(self.__class__.__name__)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self, config_dict: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate configuration dictionary.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        self.errors = []
        self.warnings = []

        # Check required fields
        if not self._validate_required_fields(config_dict):
            return False, self.errors

        # Validate structure
        if not self._validate_structure(config_dict):
            return False, self.errors

        # Validate values
        if not self._validate_values(config_dict):
            return False, self.errors

        # Check for warnings (non-fatal)
        self._check_deprecations(config_dict)

        if self.warnings:
            for warning in self.warnings:
                self.logger.warning(warning)

        return len(self.errors) == 0, self.errors

    def _validate_required_fields(self, config: dict[str, Any]) -> bool:
        """Validate required fields are present."""
        required = ["version", "workspaces"]

        for field in required:
            if field not in config:
                self.errors.append(f"Missing required field: {field}")

        return len(self.errors) == 0

    def _validate_structure(self, config: dict[str, Any]) -> bool:
        """Validate configuration structure."""
        # Check workspaces is a list
        if "workspaces" in config and not isinstance(config["workspaces"], list):
            self.errors.append("'workspaces' must be a list")
            return False

        # Validate each workspace
        for i, workspace in enumerate(config.get("workspaces", [])):
            if not isinstance(workspace, dict):
                self.errors.append(f"Workspace {i} must be a dictionary")
                continue

            if "name" not in workspace:
                self.errors.append(f"Workspace {i} missing required field: name")

        return len(self.errors) == 0
```

### ✓CORRECT Format Validation Mixin

```python
# Location: source/coregen/cli/format_validation_mixin.py

from cli.enums.enum_output_format import OutputFormat

class FormatValidationMixin:
    """Mixin for validating output formats in commands."""

    # Define in subclass
    SUPPORTED_FORMATS: list[OutputFormat] = []
    DEFAULT_FORMAT: OutputFormat = OutputFormat.TEXT

    def validate_output_format(self, format: OutputFormat | str) -> None:
        """Validate output format is supported by this command.

        Args:
            format: The output format to validate

        Raises:
            ValueError: If format is not supported
        """
        # Convert string to enum if needed
        if isinstance(format, str):
            try:
                format = OutputFormat(format.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid output format: {format}. "
                    f"Valid formats: {', '.join(f.value for f in OutputFormat)}"
                )

        # Check if supported
        if format not in self.SUPPORTED_FORMATS:
            supported = ", ".join(f.value for f in self.SUPPORTED_FORMATS)
            raise ValueError(
                f"Output format '{format.value}' not supported by this command. "
                f"Supported formats: {supported}"
            )
```

### ✓CORRECT Input Validation in Service

```python
# Location: source/coregen/services/your_service.py

class YourService(ServiceBase):
    """Service with input validation."""

    def process(self, pattern: str, filters: list[str] | None = None) -> dict:
        """Process with validation."""
        # Validate pattern
        if not pattern:
            raise ValidationError("Pattern cannot be empty")

        if not self._is_valid_pattern(pattern):
            raise ValidationError(
                f"Invalid pattern: {pattern}. "
                f"Must start with prefix (w/, c/, cm/)"
            )

        # Validate filters
        if filters:
            for filter_expr in filters:
                if not self._validate_filter(filter_expr):
                    raise ValidationError(
                        f"Invalid filter expression: {filter_expr}. "
                        f"Expected format: field.path=value"
                    )

        # Process after validation
        return self._do_processing(pattern, filters or [])

    def _is_valid_pattern(self, pattern: str) -> bool:
        """Check if pattern has valid format."""
        valid_prefixes = ["w/", "c/", "cm/", "d/", "p/"]
        return any(pattern.startswith(prefix) for prefix in valid_prefixes)

    def _validate_filter(self, filter_expr: str) -> bool:
        """Validate filter expression format."""
        # Must have = or operators
        operators = ["=", "!=", ">", "<", ">=", "<=", "~="]
        return any(op in filter_expr for op in operators)
```

### ✗ INCORRECT Validation (Anti-patterns)

```python
# DON'T DO THIS - No validation
def process(self, data: dict) -> dict:
    # WRONG: No validation
    name = data["name"]  # KeyError possible
    value = int(data["value"])  # ValueError possible

# DON'T DO THIS - Poor error messages
if not pattern:
    raise ValueError("Invalid")  # WRONG: Not helpful

# DON'T DO THIS - Validation too late
def process(self, config_path: str):
    # WRONG: Process before validating
    content = read_file(config_path)
    data = parse_yaml(content)

    # Validation should be first!
    if not config_path:
        raise ValueError("Path required")

# DON'T DO THIS - Inconsistent validation
class BadModel(BaseModel):
    name: str  # WRONG: No constraints
    age: int   # WRONG: No range validation
```

## Common Mistakes

1. **Late validation** - Validate after processing starts
2. **Poor error messages** - Not explaining what's wrong
3. **Missing edge cases** - Empty strings, None values
4. **No type validation** - Assuming correct types
5. **Inconsistent validation** - Different rules in different places

## Validation Layers

### 1. CLI Layer

- Validate command arguments
- Check output format support
- Verify file paths exist

### 2. Service Layer

- Validate business logic constraints
- Check data consistency
- Verify permissions

### 3. Model Layer

- Validate data structure
- Check field constraints
- Ensure relationships

## For AI Workers

### Before Adding Validation

1. Understand the data constraints
2. Check existing validators
3. Plan error messages
4. Consider edge cases

### When Implementing

1. Validate early in the flow
2. Use Pydantic for structured data
3. Provide helpful error messages
4. Test with invalid inputs
5. Document validation rules

### After Implementation

1. Test all validation paths
2. Verify error messages are clear
3. Check performance impact
4. Document in docstrings

## Common Validation Patterns

### Path Validation

```python
@field_validator("path")
@classmethod
def validate_path(cls, v: Path | str) -> Path:
    """Validate and normalize path."""
    path = Path(v) if isinstance(v, str) else v

    # Check dangerous paths
    if ".." in path.parts:
        raise ValueError("Path cannot contain '..'")

    # Normalize
    return path.resolve()
```

### List Validation

```python
@field_validator("items")
@classmethod
def validate_items(cls, v: list[str]) -> list[str]:
    """Validate list items."""
    if not v:
        raise ValueError("List cannot be empty")

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for item in v:
        if item not in seen:
            seen.add(item)
            unique.append(item)

    return unique
```

### Cross-field Validation

```python
@model_validator(mode="after")
def validate_dates(self) -> "Model":
    """Validate start/end date relationship."""
    if self.start_date and self.end_date:
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")
    return self
```

## Related Patterns

- [Error Handling Pattern](./error-handling-pattern.md) - Handling validation errors
- [Service Layer Pattern](./service-layer-pattern.md) - Service validation
- [Configuration Pattern](./configuration-pattern.md) - Config validation

## References

- Pydantic documentation: https://docs.pydantic.dev/
- `source/coregen/config_model/dictionary_validator.py` - Custom validator
- `source/coregen/cli/format_validation_mixin.py` - Format validation
