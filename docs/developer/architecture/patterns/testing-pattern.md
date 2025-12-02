# Testing Pattern

## Pattern Name and Purpose

**Testing Pattern** - Standardizes how tests are organized, written, and structured across the Coregen codebase to ensure comprehensive coverage and maintainability.

## When to Use

- **ALWAYS** when writing tests for new features
- **ALWAYS** follow the existing test organization structure
- **ALWAYS** use appropriate fixtures from conftest.py
- **NEVER** perform actual file I/O or network calls in unit tests

## Implementation Checklist

- [ ] Place tests in appropriate directory (test_cli/, test_services/, etc.)
- [ ] Use descriptive test class and method names
- [ ] Import and use fixtures from conftest.py
- [ ] Mock external dependencies appropriately
- [ ] Test both success and error scenarios
- [ ] Use parametrized tests for multiple input cases
- [ ] Follow AAA pattern (Arrange, Act, Assert)

## Code Examples

### ✓CORRECT Test Structure

```python
# Location: /workspace/tests/test_services/test_your_service.py

import pytest
from unittest.mock import MagicMock, patch
from cli.global_options import GlobalOptions
from services.your_service import YourService

class TestYourService:
    """Test cases for YourService.

    Groups related tests together for better organization.
    """

    @pytest.fixture
    def service(self, mock_console, mock_file_manager):
        """Create service instance with mocked dependencies."""
        global_options = GlobalOptions(
            dry_run=False,
            verbose=True,
            quiet=False,
        )
        return YourService(
            global_options=global_options,
            console=mock_console,
            file_manager=mock_file_manager,
        )

    def test_process_success(self, service):
        """Test successful processing scenario."""
        # Arrange
        input_data = "test data"
        expected_result = {"status": "success", "data": "processed"}

        # Act
        result = service.process(input_data)

        # Assert
        assert result == expected_result
        assert service._console.debug.called

    def test_process_with_error(self, service):
        """Test error handling in process method."""
        # Arrange
        service._perform_processing = MagicMock(
            side_effect=ValueError("Processing failed")
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Processing failed"):
            service.process("bad data")

    @pytest.mark.parametrize("input_data,expected", [
        ("test1", {"result": "test1_processed"}),
        ("test2", {"result": "test2_processed"}),
        ("", {"result": "empty_processed"}),
    ])
    def test_process_various_inputs(self, service, input_data, expected):
        """Test processing with various inputs."""
        # Mock the internal processing
        service._perform_processing = MagicMock(return_value=expected)

        result = service.process(input_data)
        assert result == expected
```

### ✓CORRECT CLI Test

```python
# Location: /workspace/tests/test_cli/commands/test_your_command.py

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

class TestYourCommand:
    """Test cases for your-command CLI."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner(mix_stderr=False)  # Keep streams separate

    @pytest.fixture
    def mock_service(self):
        """Mock the service to isolate CLI testing."""
        with patch("cli.commands.your_command.your_cli.YourService") as mock:
            instance = MagicMock()
            mock.return_value = instance
            instance.process.return_value = {"result": "test"}
            yield instance

    def test_command_basic(self, runner, mock_service, cli_app):
        """Test basic command execution."""
        result = runner.invoke(cli_app, ["your-command", "pattern"])

        assert result.exit_code == 0
        mock_service.process.assert_called_once_with("pattern")

    def test_command_with_json_output(self, runner, mock_service, cli_app):
        """Test command with JSON output format."""
        result = runner.invoke(
            cli_app,
            ["your-command", "pattern", "--output", "json"],
            catch_exceptions=False
        )

        assert result.exit_code == 0
        # Verify JSON output
        import json
        output_data = json.loads(result.stdout)
        assert output_data == {"result": "test"}

    def test_command_error_handling(self, runner, mock_service, cli_app):
        """Test command handles service errors gracefully."""
        mock_service.process.side_effect = ValueError("Service error")

        result = runner.invoke(cli_app, ["your-command", "pattern"])

        assert result.exit_code == 1
        assert "Error: Service error" in result.stdout
```

### ✓CORRECT Fixture Usage

```python
# Location: /workspace/tests/test_services/conftest.py

@pytest.fixture
def mock_workspace():
    """Create a mock WorkspaceConfig for testing."""
    workspace = MagicMock(spec=WorkspaceConfig)
    workspace.name = "test-workspace"
    workspace.output_dir = "/mock/output"
    workspace.contexts = {}
    workspace.type = "kubernetes"
    return workspace

@pytest.fixture
def mock_config_hierarchy(mock_workspace, mock_context, mock_component):
    """Create a complete mock configuration hierarchy.

    Composes smaller fixtures into a complete structure.
    """
    # Set up relationships
    mock_workspace.contexts = {"cluster": [mock_context]}
    mock_context.components = {"app": {"test-component": mock_component}}

    return {
        "workspace": mock_workspace,
        "context": mock_context,
        "component": mock_component,
    }
```

### ✗ INCORRECT Testing (Anti-patterns)

```python
# DON'T DO THIS - Direct file I/O in tests
def test_bad_file_operation():
    # WRONG: Real file operations
    with open("/tmp/test.txt", "w") as f:
        f.write("test")

    service = YourService()
    service.process("/tmp/test.txt")

# DON'T DO THIS - No error scenarios
class BadTests:
    def test_only_happy_path(self):
        # WRONG: Only testing success
        result = service.process("data")
        assert result["status"] == "success"
        # Missing: error cases, edge cases

# DON'T DO THIS - Poor test names
def test_1():  # WRONG: Non-descriptive
    pass

def test_service():  # WRONG: Too generic
    pass

# DON'T DO THIS - No mocking
def test_without_mocks():
    # WRONG: Will hit real filesystem/network
    service = YourService()
    service.process("file.txt")
```

## Common Mistakes

1. **Not using fixtures** - Duplicate setup code
2. **Poor test isolation** - Tests affect each other
3. **No error testing** - Only happy path covered
4. **Bad test names** - Can't understand purpose
5. **Real I/O operations** - Slow and fragile tests

## Testing Patterns by Type

### Unit Tests

- Test single units in isolation
- Mock all dependencies
- Fast execution
- Located in test_services/, test_common/

### Integration Tests

- Test component interactions
- May use real implementations
- Located in test_cli/

### E2E Tests

- Test complete workflows
- May create temporary files
- Located in test_e2e/

## For AI Workers

### Before Writing Tests

1. Check existing test patterns in the same directory
2. Look for relevant fixtures in conftest.py
3. Understand what needs mocking
4. Plan test scenarios (success, errors, edge cases)

### When Writing Tests

1. Use descriptive test names that explain the scenario
2. Follow AAA pattern (Arrange, Act, Assert)
3. One assertion focus per test
4. Use fixtures to reduce duplication
5. Mock external dependencies

### After Writing Tests

1. Run tests in isolation
2. Verify coverage of the code under test
3. Ensure tests fail when code is broken
4. Check that mocks are properly configured

## Fixture Patterns

### Global Fixtures (root conftest.py)

```python
@pytest.fixture(autouse=True)
def mock_paths_for_services():
    """Auto-applied to prevent file operations."""
    with patch("pathlib.Path.exists", return_value=True):
        yield
```

### Service Fixtures

```python
@pytest.fixture
def mock_console():
    """Reusable console mock."""
    console = MagicMock(spec=Console)
    console.print = MagicMock()
    return console
```

### CLI Fixtures

```python
@pytest.fixture
def cli_runner():
    """CLI test runner with proper configuration."""
    return CliRunner(mix_stderr=False)
```

## Parametrized Testing

```python
@pytest.mark.parametrize("pattern,expected_count", [
    ("w/*", 2),
    ("c/*", 4),
    ("cm/*", 8),
])
def test_pattern_matching(service, pattern, expected_count):
    """Test various pattern scenarios."""
    results = service.match_pattern(pattern)
    assert len(results) == expected_count
```

## Test Organization

```
tests/
├── conftest.py              # Root fixtures
├── test_cli/
│   ├── conftest.py         # CLI-specific fixtures
│   └── test_*.py           # CLI tests
├── test_services/
│   ├── conftest.py         # Service fixtures
│   └── test_*.py           # Service tests
├── test_common/
│   └── test_*.py           # Utility tests
└── test_e2e/
    └── test_*.py           # End-to-end tests
```

## Related Patterns

- [Service Layer Pattern](./service-layer-pattern.md) - Testing services
- [CLI Command Pattern](./cli-command-pattern.md) - Testing CLI
- [Error Handling Pattern](./error-handling-pattern.md) - Testing errors

## References

- `/workspace/tests/` - Test implementations
- Pytest documentation: https://docs.pytest.org/
- `/workspace/tests/test_helpers.py` - Test utilities
