# Service Layer Pattern

## Pattern Name and Purpose

**Service Layer Pattern** - Standardizes how business logic is encapsulated in service classes, ensuring proper separation of concerns between CLI and business logic.

## When to Use

- **ALWAYS** when implementing business logic for a command
- **ALWAYS** when operations involve file I/O, API calls, or complex processing
- **ALWAYS** inherit from ServiceBase for common functionality
- **NEVER** put business logic directly in CLI command classes

## Implementation Checklist

- [ ] Inherit from `ServiceBase` class
- [ ] Accept `global_options: GlobalOptions` in constructor
- [ ] Use dependency injection for all dependencies
- [ ] Provide default instances for optional dependencies
- [ ] No direct console output (return data instead)
- [ ] No direct file operations (use FileManager)
- [ ] Proper error handling with custom exceptions

## Code Examples

### ✓CORRECT Implementation

```python
# Location: source/coregen/services/your_service/your_service.py

from typing import Any
from pathlib import Path

from cli.global_options import GlobalOptions
from common.console import Console
from common.file_manager import FileManager
from common.logger import Logger
from services.service_base import ServiceBase
from config_model.models.settings import get_settings

settings = get_settings()

class YourService(ServiceBase):
    """Service for handling your business logic.

    This service processes data and returns results without
    handling output formatting or direct user interaction.
    """

    def __init__(
        self,
        global_options: GlobalOptions | None = None,
        console: Console | None = None,
        file_manager: FileManager | None = None,
        workspace_initializer: Any | None = None,
    ) -> None:
        """Initialize service with dependencies.

        Args:
            global_options: Global CLI options (verbose, dry-run, etc.)
            console: Console instance for output (optional)
            file_manager: File manager for file operations (optional)
            workspace_initializer: Workspace initializer (optional)
        """
        # Call parent constructor - handles all dependency setup
        super().__init__(
            global_options=global_options,
            console=console,
            file_manager=file_manager,
            workspace_initializer=workspace_initializer,
        )

        # Initialize service-specific attributes
        self.logger = Logger(self.__class__.__name__)
        self._cache = {}

    def process(self, input_data: str, special_option: bool = False) -> dict[str, Any]:
        """Process input data and return results.

        Args:
            input_data: Data to process
            special_option: Special processing flag

        Returns:
            Dictionary containing processed results

        Raises:
            ProcessingError: If processing fails
            ValidationError: If input is invalid
        """
        self.logger.debug(f"Processing input: {input_data}")

        # Validate input
        if not input_data:
            raise ValidationError("Input data cannot be empty")

        # Use file manager for any file operations
        if self._file_manager.file_exists(Path(input_data)):
            content = self._file_manager.read_file(Path(input_data))
        else:
            content = input_data

        # Process data (business logic here)
        result = self._perform_processing(content, special_option)

        # Return data - let CLI handle formatting
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "options": {"special": special_option}
            }
        }

    def _perform_processing(self, content: str, special: bool) -> Any:
        """Internal processing logic.

        Private methods contain the actual business logic.
        """
        # Implementation here
        pass
```

### ✓CORRECT Service with Workspace

```python
class WorkspaceService(ServiceBase):
    """Service that requires workspace context."""

    def process_workspace(self, pattern: str) -> dict[str, Any]:
        """Process workspace-related operations."""
        # Initialize workspace if needed
        if not self._workspace_initializer.is_initialized():
            self._workspace_initializer.initialize()

        # Get workspace configuration
        config = self._workspace_initializer.get_config()

        # Process using workspace context
        results = []
        for workspace in config.workspaces:
            if self._matches_pattern(workspace.name, pattern):
                results.append(self._process_single_workspace(workspace))

        return {"workspaces": results}
```

### ✗ INCORRECT Implementation (Anti-patterns)

```python
# DON'T DO THIS - Direct console output in service
class BadService:
    def process(self, data: str) -> None:
        # WRONG: Service shouldn't handle output
        console.print(f"Processing {data}")
        result = self._do_work(data)
        print(json.dumps(result))  # WRONG: Direct output

# DON'T DO THIS - Not using ServiceBase
class BadService:
    def __init__(self, verbose: bool = False):
        # WRONG: Individual options instead of GlobalOptions
        self.verbose = verbose
        # WRONG: Creating own dependencies
        self.file_manager = FileManager()

# DON'T DO THIS - Business logic in CLI
class BadCommand:
    def run(self) -> None:
        # WRONG: Business logic should be in service
        with open(self.file_path) as f:
            data = yaml.safe_load(f)

        processed = {}
        for key, value in data.items():
            processed[key] = value.upper()

        console.print(processed)
```

## Common Mistakes

1. **Direct console output** - Services return data, CLI handles output
2. **Not inheriting from ServiceBase** - Miss common functionality
3. **Creating own dependencies** - Use dependency injection
4. **Not accepting GlobalOptions** - Can't respect dry-run, verbose, etc.
5. **Business logic in CLI** - Violates separation of concerns
6. **Calling Console.setup()** - Services should NEVER configure Console; it's configured by CLI

## Testing the Pattern

### Unit Test Example

```python
# Location: /workspace/tests/services/test_your_service.py

import pytest
from unittest.mock import MagicMock, patch

from cli.global_options import GlobalOptions
from services.your_service import YourService

class TestYourService:
    """Test cases for YourService."""

    @pytest.fixture
    def mock_global_options(self):
        """Create mock global options."""
        return GlobalOptions(
            dry_run=False,
            verbose=True,
            quiet=False,
            no_color=False,
            file_action="skip"
        )

    @pytest.fixture
    def service(self, mock_global_options):
        """Create service instance with mocked dependencies."""
        return YourService(
            global_options=mock_global_options,
            console=MagicMock(),
            file_manager=MagicMock(),
        )

    def test_service_respects_dry_run(self, mock_global_options):
        """Test service respects dry-run mode."""
        mock_global_options.dry_run = True
        service = YourService(global_options=mock_global_options)

        # Verify file operations are skipped in dry-run
        result = service.process("test")
        assert service._file_manager.dry_run is True

    def test_service_returns_data_not_output(self, service):
        """Test service returns data structure, not formatted output."""
        result = service.process("test input")

        # Should return dict/list/data, not formatted string
        assert isinstance(result, dict)
        assert "status" in result
        assert "data" in result

        # Should not have called console.print
        service._console.print.assert_not_called()
```

## For AI Workers

### Before Making Changes

1. Check if ServiceBase is already imported
2. Look for existing service patterns in codebase
3. Verify separation of CLI and business logic
4. Check if GlobalOptions is properly used

### When Implementing

1. Always inherit from ServiceBase
2. Accept global_options as first parameter
3. Use super().**init**() to initialize base
4. Return data structures, not formatted output
5. Use FileManager for all file operations

### After Implementation

1. Verify service can be tested independently
2. Check that no console output occurs in service
3. Ensure all file operations use FileManager
4. Test with various global options (dry-run, verbose)

## Service Method Patterns

### Query Methods

```python
def get_items(self, pattern: str) -> list[dict[str, Any]]:
    """Query methods return data structures."""
    return [{"name": "item1"}, {"name": "item2"}]
```

### Action Methods

```python
def create_item(self, name: str, config: dict) -> dict[str, Any]:
    """Action methods return result status and data."""
    # Perform action
    created = self._do_creation(name, config)

    return {
        "status": "created",
        "item": created,
        "location": str(created.path)
    }
```

### Validation Methods

```python
def validate_config(self, config: dict) -> tuple[bool, list[str]]:
    """Validation methods return success and errors."""
    errors = []

    if "required_field" not in config:
        errors.append("Missing required_field")

    return len(errors) == 0, errors
```

## Related Patterns

- [Global Options Pattern](./global-options-pattern.md) - How services receive options
- [Error Handling Pattern](./error-handling-pattern.md) - Service exceptions
- [Configuration Pattern](./configuration-pattern.md) - Using settings

## ServiceBase Features

The ServiceBase class provides:

1. **Dependency Injection** - Console, FileManager, WorkspaceInitializer
2. **Global Options Handling** - Accepts both GlobalOptions object or individual options
3. **Logging Setup** - Consistent logger initialization
4. **Property Access** - `_console`, `_file_manager`, `_workspace_initializer`
5. **Default Instances** - Creates dependencies if not provided
6. **Console Handling** - Supports both Console class reference and instance

Note: Console is typically used as a class reference (`console = Console`) since it uses class methods.

## Service Inheritance Hierarchy: ServiceBase vs ServicesBase

Coregen provides two base classes for services, each serving different needs:

### ServiceBase (Single Service)

**Use for:** Commands that operate on a single entity type or perform standalone operations.

**Provides:**
- Core dependency injection (file manager, console, workspace initializer)
- Global options handling (dry-run, verbose, quiet)
- Logging setup
- Property access (`_console`, `_file_manager`, `_workspace_initializer`)

**Example:**

```python
from services.service_base import ServiceBase

class ConfigViewService(ServiceBase):
    """Service for viewing configuration - operates independently."""

    def process(self, config_path: str) -> dict:
        # Operates on config files without needing other services
        config = self._file_manager.read_config(config_path)
        return {"config": config}
```

**Use when:**
- Command works with one type of entity
- Service doesn't coordinate multiple services
- Simple data transformation or query operations

### ServicesBase (Multiple Services)

**Use for:** Commands that coordinate multiple services or need configuration access and pattern matching.

**Extends ServiceBase with:**
- Configuration provider functionality (`_config_provider`)
- Pattern matching capabilities
- Service coordination helpers
- Configuration access methods

**Example:**

```python
from services.services_base import ServicesBase

class DetectChangesService(ServicesBase):
    """Coordinates multiple services for change detection."""

    def __init__(self, global_options: GlobalOptions):
        super().__init__(global_options)
        # Initialize dependent services
        self.generate_service = GenerateService(global_options)
        self.git_service = GitService(global_options)

    def process(self) -> dict:
        # Coordinates multiple services
        changes = self.git_service.get_changes()
        affected = self.generate_service.analyze(changes)
        return self._combine_results(changes, affected)
```

**Use when:**
- Command coordinates multiple services
- Need access to configuration provider
- Require pattern matching across configuration elements
- Complex workflow orchestration

### Choosing Between Them

| Scenario | Use |
|----------|-----|
| Single entity type operation | ServiceBase |
| Multiple service coordination | ServicesBase |
| Simple data transformation | ServiceBase |
| Complex workflow orchestration | ServicesBase |
| Need configuration provider | ServicesBase |
| Need pattern matching | ServicesBase |
| Standalone operation | ServiceBase |
| Service composition | ServicesBase |

### Implementation Examples

**ServiceBase Implementation:**

```python
class SchemaService(ServiceBase):
    """Simple service for schema operations."""

    def get_schema(self, model_name: str) -> dict:
        # Single, focused operation
        return self._generate_schema(model_name)
```

**ServicesBase Implementation:**

```python
class GetService(ServicesBase):
    """Service requiring configuration and pattern matching."""

    def get_elements(self, pattern: str) -> list:
        # Uses configuration provider
        config = self._config_provider.get_config()

        # Uses pattern matching
        matches = self._match_pattern(pattern, config)

        return matches
```

Most services should inherit from ServiceBase. Only services that need configuration access and pattern matching (like `GenerateService` and `GetService`) should inherit from ServicesBase.

## Directory Structure

```
source/coregen/services/
├── service_base.py          # Base class for all services
├── services_base.py         # Extended base for config/pattern services
├── your_service/
│   ├── __init__.py
│   └── your_service.py      # Service implementation
├── generate/
│   └── gen_generate_service.py  # Inherits from ServicesBase
├── get/
│   └── get_service.py           # Inherits from ServicesBase
└── config/
    ├── cfg_view_base_service.py  # Specialized base for config view services
    └── cfg_view_service.py       # Example service implementation
```

## References

- `source/coregen/services/service_base.py` - ServiceBase implementation
- `source/coregen/services/` - Example service implementations
