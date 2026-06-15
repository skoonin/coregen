# Coding Conventions

This document outlines the coding standards and conventions for the Coregen project. These conventions ensure code consistency, maintainability, and readability across the entire codebase.

**IMPORTANT**: This document covers general coding style. For architectural patterns and implementation guidelines, see [Architecture Patterns](../architecture/patterns/README.md). Always check the patterns documentation before implementing features or fixing bugs, especially:

- [Global Options Pattern](../architecture/patterns/global-options-pattern.md) - Critical for CLI commands
- [Output Pipeline Pattern](../architecture/patterns/output-pipeline-pattern.md) - Critical for structured output
- [Service Layer Pattern](../architecture/patterns/service-layer-pattern.md) - Critical for business logic

## Table of Contents

- [General Principles](#general-principles)
- [Python Style Guide](#python-style-guide)
- [Code Organization](#code-organization)
- [Documentation](#documentation)
- [Testing](#testing)
- [Type Hints](#type-hints)
- [Error Handling](#error-handling)
- [Imports](#imports)
- [Naming Conventions](#naming-conventions)
- [Tools and Automation](#tools-and-automation)
- [Enumerations](#enumerations)
- [Data Classes](#data-classes)
- [Global Variables and Constants](#global-variables-and-constants)
- [Class Design Patterns](#class-design-patterns)
- [Testing Conventions](#testing-conventions)
- [CLI Development Patterns](#cli-development-patterns)
- [Rich Console Integration](#rich-console-integration)
- [Field Discovery and Validation](#field-discovery-and-validation)
- [File Management Patterns](#file-management-patterns)
- [Documentation Standards](#documentation-standards)

## General Principles

### Code Quality Standards

- **Readability First**: Code should be self-documenting and easy to understand
- **Consistency**: Follow established patterns throughout the codebase
- **Maintainability**: Write code that is easy to modify and extend
- **Testing**: All functionality must be thoroughly tested
- **Type Safety**: Use type hints extensively for better code clarity and IDE support

### Development Philosophy

- **Fail Fast**: Catch errors early with proper validation
- **Single Responsibility**: Each function/class should have one clear purpose
- **DRY Principle**: Don't repeat yourself - extract common functionality
- **SOLID Principles**: Follow object-oriented design principles

## Python Style Guide

### Line Length and Formatting

- **Maximum line length**:
  - **Black**: 88 characters (default)
  - **Flake8**: 160 characters (allows for longer comments and complex expressions)
- **Use Black formatter** for automatic code formatting
- **Trailing commas**: Include trailing commas in multi-line structures

```python
# Good
option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Options",
}

# Bad
option_params = {"case_sensitive": False, "show_default": True, "show_choices": True, "rich_help_panel": "Options"}
```

### Indentation and Spacing

- **4 spaces** for indentation (no tabs)
- **2 blank lines** between top-level classes and functions
- **1 blank line** between class methods
- **No trailing whitespace**

## Code Organization

### Project Structure

```text
source/coregen/
├── cli/                    # Command-line interface components
│   ├── commands/          # CLI command implementations
│   ├── enums/            # CLI-specific enumerations
│   └── global_options.py # Global CLI options
├── common/               # Shared utilities and services
├── config_model/         # Configuration data models
├── services/            # Business logic and service layer
└── __main__.py          # Application entry point
```

### Module Organization

Each module should follow this structure:

```python
"""Module docstring describing the module's purpose."""

# Standard library imports
import os
from pathlib import Path
from typing import Annotated, Any

# Third-party imports
import typer
from pydantic import BaseModel

# First-party imports
from cli.enums.enum_entity_type import EntityType
from common.logger import Logger
from config_model.models.settings import get_settings

# Module-level constants
CONSTANT_VALUE = "value"

# Module-level variables
settings = get_settings()
logger = Logger(__name__)


class ExampleClass:
    """Class implementation."""
    pass


def example_function() -> None:
    """Function implementation."""
    pass
```

## Documentation

### Docstring Standards

Use **Google-style docstrings** for all public functions, classes, and modules:

```python
def process_configuration(
    config_path: Path,
    output_format: str = "yaml",
    validate: bool = True,
) -> dict[str, Any]:
    """Process configuration file and return structured data.

    Args:
        config_path: Path to the configuration file
        output_format: Desired output format (yaml, json, etc.)
        validate: Whether to validate the configuration

    Returns:
        Dictionary containing processed configuration data

    Raises:
        ConfigurationError: If configuration is invalid
        FileNotFoundError: If config file doesn't exist

    Example:
        >>> config = process_configuration(Path("config.yaml"))
        >>> print(config["workspace"]["name"])
        "my-workspace"
    """
```

### Module Docstrings

Every module should have a descriptive docstring:

```python
"""
Workspace models for Coregen.

Defines the models for workspaces and their configurations, including:
- WorkspaceConfig: Main workspace configuration
- Context: Individual deployment contexts
"""
```

### Comments

- Use comments sparingly for complex logic
- Prefer descriptive variable names over comments
- Use TODO comments with tickets/issues when appropriate

```python
# TODO: Implement caching for configuration validation (#123)
# FIXME: Handle edge case with empty workspace names (#456)
```

## Testing

### Test Organization

- **Test files**: Mirror the source structure in `tests/`
- **Test naming**: `test_<module_name>.py`
- **Test methods**: `test_<functionality>`

```python
"""Unit tests for logging functionality."""

import pytest
from unittest.mock import MagicMock, patch

from common.logger import Logger


class TestLogger:
    """Test cases for Logger class."""

    def test_logger_initialization(self):
        """Test logger creates with correct name."""
        logger = Logger("test_module")
        assert logger.name == "test_module"

    def test_logger_level_setting(self):
        """Test logger level can be set correctly."""
        logger = Logger("test")
        logger.set_level("debug")
        assert logger.level == Logger.DEBUG
```

### Test Standards

- **100% test coverage** for business logic
- **Use fixtures** for common test setup
- **Mock external dependencies** appropriately
- **Descriptive test names** that explain what is being tested

```python
@pytest.fixture
def sample_workspace_config():
    """Provide a sample workspace configuration for testing."""
    return {
        "name": "test-workspace",
        "contexts": [
            {"name": "dev", "environment": "development"}
        ]
    }

def test_workspace_validation_with_valid_config(sample_workspace_config):
    """Test that valid workspace configuration passes validation."""
    # Test implementation
```

## Type Hints

### Type Annotation Standards

- **All public functions** must have type hints
- **Use modern type syntax** (Python 3.11+)
- **Import types from typing** when needed

```python
from typing import Annotated, Any
from pathlib import Path

def process_files(
    file_paths: list[Path],
    options: dict[str, Any] | None = None,
) -> list[str]:
    """Process multiple files and return results."""
    return []

# Use Annotated for complex types
UserId = Annotated[int, "Unique user identifier"]

def get_user(user_id: UserId) -> dict[str, Any]:
    """Retrieve user by ID."""
    return {}
```

### Pydantic Models

Use Pydantic for data validation and configuration:

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated

class WorkspaceConfig(BaseModel):
    """Workspace configuration model."""

    model_config = ConfigDict(extra="allow")

    name: Annotated[
        str,
        Field(description="Workspace name")
    ]
    active: bool = True
    contexts: list[str] = Field(default_factory=list)
```

## Error Handling

### Exception Handling

- **Use specific exceptions** instead of generic Exception
- **Create custom exceptions** for domain-specific errors
- **Include context** in error messages

```python
import yaml
from pathlib import Path

class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, config_path: Path | None = None):
        self.config_path = config_path
        super().__init__(message)

def validate_config(config_path: Path) -> None:
    """Validate configuration file."""
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigurationError(
            f"Configuration file not found: {config_path}",
            config_path=config_path
        )
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML in configuration: {e}",
            config_path=config_path
        )
```

### Logging

Use structured logging throughout the application:

```python
from common.logger import Logger

logger = Logger(__name__)

def process_workspace(workspace_name: str) -> None:
    """Process workspace configuration."""
    logger.debug(f"Processing workspace: {workspace_name}")

    try:
        # Processing logic
        logger.info(f"Successfully processed workspace: {workspace_name}")
    except Exception as e:
        logger.error(f"Failed to process workspace {workspace_name}: {e}")
        raise
```

## Imports

### Import Organization

Use **isort** for automatic import sorting. Imports should be organized as:

1. **Standard library imports**
2. **Third-party imports**
3. **First-party imports**

```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Any

# Third-party
import typer
import yaml
from pydantic import BaseModel
from rich.console import Console

# First-party
from cli.global_options import GlobalOptions
from common.logger import Logger
from services.config_service import ConfigService
```

### Import Guidelines

- **Avoid wildcard imports** (`from module import *`)
- **Use relative imports** within packages
- **Import only what you need**
- **Group related imports** together

```python
# Good
from pathlib import Path
from typing import Any

# Bad
from pathlib import *
import typing
```

## Naming Conventions

### Variable and Function Names

- **snake_case** for variables, functions, and modules
- **UPPER_CASE** for constants
- **PascalCase** for classes
- **Descriptive names** that explain purpose

```python
# Variables and functions
user_config = load_config()
workspace_name = "production"
MAX_RETRY_ATTEMPTS = 3

def validate_workspace_configuration(config: dict) -> bool:
    """Validate workspace configuration."""
    return True

# Classes
class WorkspaceManager:
    """Manages workspace operations."""
    pass

# Constants
DEFAULT_TIMEOUT = 30
CONFIG_FILE_EXTENSION = ".yaml"
```

### File and Directory Names

- **snake_case** for Python files
- **kebab-case** for configuration files
- **Descriptive names** that indicate purpose

```text
# Python files
workspace_manager.py
config_validator.py
user_service.py

# Configuration files
workspace-config.yaml
dev-cluster-cgvalues.yaml
production-settings.yml
```

### CLI Commands and Options

- **kebab-case** for CLI commands and options
- **Short forms** for frequently used options

```python
@typer.option("--config-file", "-c", help="Configuration file path")
@typer.option("--output-format", "-f", help="Output format")
def generate_config(
    config_file: Path,
    output_format: str = "yaml"
) -> None:
    """Generate configuration files."""
    pass
```

## Tools and Automation

### Code Quality Standards

We maintain high code quality through a combination of automated formatting tools, linters, and type checking. These tools run during development (via pre-commit hooks), during continuous integration, and can be run manually via Make commands.

### Standardized Tooling

| Tool | Purpose | Configuration | Auto-fixes | Command |
|------|---------|---------------|------------|---------|
| **Black** | Code formatting | Line length 88 (default) | Yes | `make format` |
| **isort** | Import sorting | Black profile in pyproject.toml | Yes | `make format` |
| **flake8** | PEP 8 style checking | Max line length 160 in pyproject.toml | No | `make lint` |
| **pylint** | Static code analysis | Line length 160 in pyproject.toml | No | `make lint` |
| **mypy** | Type checking | Configured in pyproject.toml | No | `make lint` |

### Tool Selection Rationale

1. **Black** is our primary code formatter because:
   - It's opinionated with minimal configuration
   - It produces consistent formatting across the codebase
   - It integrates well with modern IDEs and CI pipelines

2. **isort** handles import sorting because:
   - It automatically groups imports (standard lib, third-party, local)
   - It works well with Black (using Black profile for compatibility)
   - It improves code readability and organization

3. **flake8** checks PEP 8 compliance because:
   - It ensures adherence to Python style guidelines
   - It catches common programming errors
   - It has good IDE integration

4. **pylint** provides deep static analysis because:
   - It catches more complex code issues
   - It identifies potential bugs, anti-patterns, and maintainability issues
   - It enforces good practices beyond PEP 8

5. **mypy** enforces type checking because:
   - It catches type-related errors early
   - It improves code self-documentation
   - It enhances IDE auto-completion and navigation

### Tool Integration

These tools are integrated at multiple levels:

1. **Pre-commit Hooks**: Automatically run on staged files before commit
2. **Makefile Commands**: `make format` and `make lint` for manual checking
3. **CI Pipeline**: Enforces all checks on pull requests
4. **IDE Integration**: Recommended for real-time feedback

### Development Workflow

1. **Writing Code**:
   - Use an IDE with integrated linting (VSCode, PyCharm)
   - Follow type annotation practices
   - Adhere to project code style

2. **Before Committing**:
   - Run `make format` to automatically format code
   - Run `make lint` to check for issues
   - Fix any reported problems

3. **During Review**:
   - Check CI build for linting errors
   - Review code for adherence to project standards
   - Ensure all tools pass before merging

### Configuration Files

All tool configurations are centralized in `pyproject.toml`:
- Black configuration under `[tool.black]`
- isort configuration under `[tool.isort]`
- flake8 configuration under `[tool.flake8]`
- pylint configuration under `[tool.pylint]`
- mypy configuration under `[tool.mypy]`

### IDE Setup Recommendations

#### VSCode
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm
- Enable Black as external tool
- Enable isort as external tool
- Enable pylint, flake8, and mypy inspections

### Makefile Commands

- `make format`: Run Black and isort to format code
- `make lint`: Run flake8, pylint, and mypy
- `make check-format`: Check formatting without making changes

### Notes on Autopep8

We explicitly do not use autopep8 since Black is our primary formatter. Using both would lead to conflicts and inconsistent formatting.

## Enumerations

### Enum Standards

- **Inherit from `str, enum.Enum`** for string-based enums used in CLI/JSON
- **Use descriptive docstrings** explaining the purpose and values
- **Include helper methods** for common operations

```python
import enum

class OutputFormat(str, enum.Enum):
    """Enumeration of all supported output formats.

    Some formats (like matrix and table) only work when explicitly allowed
    in the message's allowed_outputs parameter.

    Attributes:
        TEXT: Plain text output (default)
        JSON: JSON format output
        YAML: YAML format output
    """

    TEXT = "text"  # Default format
    JSON = "json"
    YAML = "yaml"

    @classmethod
    def from_string(cls, value: str) -> "OutputFormat | None":
        """Convert string to enum value."""
        try:
            return cls(value.lower())
        except ValueError:
            return None
```

### Pattern for Enum Subsets

Create limited enums for specific use cases:

```python
class LimitedOutputFormat(str, enum.Enum):
    """A subset of OutputFormat with only commonly used formats."""

    JSON = OutputFormat.JSON.value
    YAML = OutputFormat.YAML.value
    TEXT = OutputFormat.TEXT.value
```

## Data Classes

### When to Use Dataclasses vs Pydantic

- **Use dataclasses** for simple data containers without validation
- **Use Pydantic models** for configuration and data validation
- **Use TypeVar** for generic class methods

```python
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T", bound="ProcessingOptions")

@dataclass
class ProcessingOptions:
    """Options for configuration processing."""

    validate: bool = True
    output_format: str = "yaml"
    include_metadata: bool = False

    @classmethod
    def from_dict(cls: type[T], data: dict) -> T:
        """Create instance from dictionary."""
        return cls(**data)
```

## Global Variables and Constants

### Global Variables Usage

- **Minimize global variables** - use dependency injection instead
- **Document global variables** clearly with purpose and usage
- **Use UPPER_CASE** for true constants
- **Group related globals** in dedicated modules

```python
# __init__.py - Only for truly global program constants
PROGRAM_NAME = "coregen"
__version__ = "0.2.0-beta"

# For module-level singletons, use factory functions instead
def get_settings() -> Settings:
    """Get global settings instance."""
    return Settings()
```

### Version Management

- **Single source of truth** for version in `__init__.py`
- **Use semantic versioning** (MAJOR.MINOR.PATCH)
- **Include pre-release identifiers** when appropriate

```python
# In __init__.py
__version__ = "0.2.0-beta"

# In pyproject.toml - version is managed there
# The version in __init__.py should match pyproject.toml
```

## Class Design Patterns

### Properties and Class Methods

- **Use `@property`** for computed attributes
- **Use `@classmethod`** for alternative constructors
- **Use `@staticmethod`** for utility functions that belong conceptually to the class

```python
class ConfigurationService:
    """Service for configuration management."""

    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._settings = None

    @property
    def is_configured(self) -> bool:
        """Check if service is properly configured."""
        return self._config_path.exists()

    @classmethod
    def from_default_path(cls) -> "ConfigurationService":
        """Create service with default configuration path."""
        return cls(Path.cwd() / ".cgconfig.yaml")

    @staticmethod
    def validate_config_structure(data: dict) -> bool:
        """Validate configuration structure."""
        return "workspaces" in data
```

### Service Base Classes

- **Inherit from base service classes** for common functionality
- **Use dependency injection** for service dependencies
- **Provide default implementations** where appropriate

```python
class GenerateService(ServicesBase):
    """Service for generating configuration files."""

    def __init__(
        self,
        console: Console | None = None,
        file_manager: FileManager | None = None,
        # ... other dependencies
    ):
        super().__init__(
            console=console,
            file_manager=file_manager,
            # Pass dependencies to base class
        )
```

## Testing Conventions

### Fixture Organization

- **Global fixtures** in root `conftest.py`
- **Module-specific fixtures** in module `conftest.py`
- **Use descriptive fixture names** that explain their purpose

```python
# conftest.py
@pytest.fixture
def mock_path_resolver() -> Generator[MagicMock, None, None]:
    """Mock PathResolver to prevent file system operations during tests.

    Only use this fixture when explicitly needed in a test.
    """
    with patch("common.path_resolver.PathResolver") as mock_resolver:
        mock_instance = MagicMock()
        mock_instance._root_path = Path("/mock/root/path")
        mock_resolver.return_value = mock_instance
        yield mock_resolver
```

### Test Class Organization

- **Group related tests** in test classes
- **Use descriptive test method names** that explain the scenario
- **Include setup and teardown** in fixtures rather than methods

```python
class TestLogger:
    """Test cases for Logger class."""

    def test_logger_initialization_with_explicit_name(self):
        """Test logger creates with explicitly provided name."""
        logger = Logger("test_logger")
        assert logger._logger.name == "test_logger"

    def test_logger_initialization_with_automatic_detection(self):
        """Test logger automatically detects name from calling context."""
        class TestClass:
            def __init__(self):
                self.logger = Logger()

        test_instance = TestClass()
        assert test_instance.logger._logger.name == "TestClass"
```

### Test State Management

- **Reset global state** between tests using fixtures
- **Mock external dependencies** to ensure test isolation
- **Use parameterized tests** for multiple input scenarios

```python
@pytest.fixture
def reset_logger():
    """Reset logger state between tests."""
    Logger._global_level = Logger.NORMAL
    Logger._global_verbosity = "normal"
    Logger.global_level_set = False
    yield
    # Clean up after tests
    logging.getLogger().setLevel(logging.WARNING)
```

## CLI Development Patterns

### Command Organization

- **One command per file** in `cli/commands/`
- **Use command classes** for complex commands
- **Group related options** in parameter dictionaries

```python
# cli/commands/get/get_cli.py
option_params = {
    "case_sensitive": False,
    "show_default": True,
    "show_choices": True,
    "rich_help_panel": "Options",
}

class Get:
    """Command class for getting configuration elements."""

    @staticmethod
    def callback(
        ctx: typer.Context,
        patterns: Annotated[
            list[str] | None,
            typer.Argument(
                help="Patterns to match configuration elements",
                autocompletion=complete_patterns,
            ),
        ] = None,
        # ... other parameters
    ):
        """Implementation of get command."""
        pass
```

### Error Handling in CLI

- **Use `typer.Exit()`** for graceful command exits within CLI commands
- **Use `sys.exit()`** only in the main entry point for system-level errors
- **Catch and log exceptions** before exiting
- **Provide helpful error messages** to users

```python
import sys
import typer
from common.logger import Logger

# In CLI command functions - use typer.Exit()
def some_command():
    """Example CLI command."""
    try:
        # Command logic here
        pass
    except SomeError as e:
        logger.error(f"Command failed: {e}")
        raise typer.Exit(1)

# In main entry point - use sys.exit()
def main() -> None:
    """Main entry point for the application."""
    try:
        app()
    except KeyboardInterrupt:
        logger = Logger("main")
        logger.warning("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger = Logger("main")
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception(e)
        sys.exit(1)
```

## Rich Console Integration

### Console Usage Patterns

- **Use Console singleton** for consistent output
- **Define color themes** for different message types
- **Support no-color mode** for accessibility

### Logger Integration

- **Integrate Rich with Python logging** for consistent output
- **Support multiple verbosity levels** (quiet, normal, verbose)
- **Use structured logging** with context information

## Field Discovery and Validation

### Custom Field Types

- **Define field types** for domain-specific validation
- **Use dataclasses** for field metadata
- **Support nested field discovery**

### Validation Patterns

- **Separate validation logic** from models to avoid circular imports
- **Use class methods** for validators
- **Provide clear error messages** with context

## Path Handling and Completion

### Path Resolution Patterns

- **Use `pathlib.Path`** for all path operations
- **Resolve paths early** in the application flow
- **Support relative and absolute paths**

### Custom Completion Systems

- **Implement context-aware completion** for CLI arguments
- **Use caching** for expensive completion operations
- **Handle completion errors gracefully**

## File Management Patterns

- **Abstract file operations** through a file manager service
- **Support dry-run mode** for all file operations
- **Log all file operations** for debugging

## Documentation Standards

- **Use Google-style docstrings** for all public functions, classes, and modules
- **Document public APIs** with comprehensive docstrings
- **Include usage examples** for complex functions
- **Document exceptions** that may be raised
- **Use type hints** as part of the documentation

---
