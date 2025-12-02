# Test Fixtures Reference

This document provides a comprehensive guide to all test fixtures available in the CoreGen test suite. Fixtures are organized by scope and purpose to help you quickly find the right tools for your tests.

## Table of Contents

- [Fixture Scopes](#fixture-scopes)
- [Root Fixtures (Available Everywhere)](#root-fixtures-available-everywhere)
- [Directory-Specific Fixtures](#directory-specific-fixtures)
- [Common Usage Patterns](#common-usage-patterns)
- [Guidelines for Adding New Fixtures](#guidelines-for-adding-new-fixtures)

---

## Fixture Scopes

Understanding fixture scopes is crucial for writing efficient tests:

- **session**: Created once per test run, shared across all tests. Use for expensive setup or read-only data.
- **module**: Created once per test module/file. Use for module-level setup.
- **function**: Created fresh for each test function (default). Use when tests need isolation.

---

## Root Fixtures (Available Everywhere)

These fixtures are defined in `/tests/conftest.py` and are automatically available to all tests.

### Console State Management

#### `reset_console_state` (autouse, function)

Automatically resets Console static state before each test to ensure isolation.

```python
# No need to explicitly use this fixture - it runs automatically
def test_something():
    # Console state is already reset
    pass
```

### CLI Test Fixtures

#### `cli_runner` (session)

Returns a Typer CliRunner for testing CLI commands.

```python
def test_help_command(cli_runner, cli_app):
    result = cli_runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
```

#### `cli_app_mocked` (session)

CLI app with Console and Logger mocked. Use for most CLI unit tests.

```python
def test_command(cli_runner, cli_app_mocked):
    result = cli_runner.invoke(cli_app_mocked, ["config", "view"])
    assert result.exit_code == 0
```

#### `cli_app` (session)

Alias for `cli_app_mocked` for backward compatibility.

```python
# Same as cli_app_mocked
def test_command(cli_runner, cli_app):
    result = cli_runner.invoke(cli_app, ["config", "view"])
```

#### `cli_app_raw` (function)

CLI app without any mocking. Use for integration/e2e tests where you need to verify actual console output.

```python
def test_actual_output(cli_runner, cli_app_raw):
    result = cli_runner.invoke(cli_app_raw, ["--help"])
    assert "Usage:" in result.stdout
```

### Global Options Fixtures

#### `global_options` (function)

Returns a GlobalOptions instance with default values.

```python
def test_with_options(global_options):
    global_options.dry_run = True
    service = MyService(global_options=global_options)
    assert service.dry_run is True
```

#### `service_defaults` (function)

Dictionary with common default values for service initialization.

```python
def test_service_init(service_defaults):
    service = MyService(**service_defaults)
    assert service.dry_run is False
```

### Configuration Model Mock Fixtures

#### `mock_workspace` (function)

Mock WorkspaceConfig with sensible defaults.

```python
def test_workspace(mock_workspace):
    mock_workspace.name = "production"
    assert mock_workspace.name == "production"
```

#### `mock_context` (function)

Mock Context with sensible defaults.

```python
def test_context(mock_context):
    mock_context.environment = "production"
    assert mock_context.active is True
```

#### `mock_component` (function)

Mock Component with sensible defaults.

```python
def test_component(mock_component):
    assert mock_component.name == "test-component"
    assert mock_component.config.active is True
```

#### `mock_config_hierarchy` (function)

Complete mock configuration hierarchy with workspace, context, and component properly interconnected.

```python
def test_hierarchy(mock_config_hierarchy):
    workspace = mock_config_hierarchy["workspace"]
    context = mock_config_hierarchy["context"]
    component = mock_config_hierarchy["component"]

    # Relationships are pre-configured
    assert workspace.find_context.return_value == context
```

#### `sample_config_dict` (session)

Comprehensive sample configuration dictionary with multiple workspaces, contexts, and components.

```python
def test_config_loading(sample_config_dict):
    assert len(sample_config_dict["workspaces"]) == 2
    assert "settings" in sample_config_dict
```

### Service Infrastructure Mock Fixtures

#### `mock_console` (function)

Mock Console for verifying console output calls.

```python
def test_console_output(mock_console):
    service = MyService(console=mock_console)
    service.do_something()
    mock_console.info.assert_called_once()
```

#### `mock_logger` (function)

Context manager that mocks the Logger class.

```python
def test_logging(mock_logger):
    # Logger is already mocked
    my_function_that_logs()
```

#### `mock_config_access` (function)

Mock ConfigAccess with pre-populated lookup tables and mock methods.

```python
def test_config_access(mock_config_access):
    workspaces = mock_config_access.find_workspaces(["test-*"])
    assert len(workspaces) > 0
```

---

## Directory-Specific Fixtures

### CLI Tests (`/tests/test_cli/conftest.py`)

Currently contains no additional fixtures - all common CLI fixtures have been moved to the root conftest.

### Service Tests (`/tests/test_services/conftest.py`)

#### `mock_paths_for_services` (autouse, function)

Mocks file system paths to prevent actual file operations during tests. Skipped for tests marked with `@pytest.mark.integration`.

```python
# Automatically applied to all service tests
def test_service():
    # Paths are already mocked
    pass

# Skip for integration tests
@pytest.mark.integration
def test_with_real_fs():
    # Real file system access
    pass
```

#### `mock_path_service` (function)

Mock PathService with configured resolver and path methods.

```python
def test_path_resolution(mock_path_service):
    path = mock_path_service.get_component_path()
    assert path == Path("/path/to/context/test-component")
```

#### `mock_config_provider` (function)

Mock configuration provider with path_service and config_access.

```python
def test_provider(mock_config_provider, mock_path_service):
    assert mock_config_provider.has_config() is True
```

#### `mock_file_manager` (function)

Mock FileManager for testing file operations.

```python
def test_file_ops(mock_file_manager):
    mock_file_manager.write_file("test.txt", "content")
    mock_file_manager.write_file.assert_called_once()
```

#### `mock_workspace_initializer` (function)

Mock WorkspaceInitializer.

```python
def test_initialization(mock_workspace_initializer):
    mock_workspace_initializer.initialize_workspace()
```

#### `git_mock` (function)

Factory fixture for creating git subprocess mocks.

```python
def test_git_operations(git_mock):
    mock_run = git_mock(changed_files=["/path/to/file.txt"])
    result = mock_run(["git", "diff", "--name-only"])
    assert result.returncode == 0
```

### Config Model Tests (`/tests/test_config_model/conftest.py`)

#### `default_settings` (function)

Returns default CoregenSettings.

```python
def test_settings(default_settings):
    assert default_settings.system is not None
```

#### `sample_component_dict` (function)

Sample component dictionary for testing.

```python
def test_component_parsing(sample_component_dict):
    assert sample_component_dict["name"] == "test-component"
```

#### `sample_context_dict` (function)

Sample context dictionary for testing.

```python
def test_context_parsing(sample_context_dict):
    assert sample_context_dict["environment"] == "dev"
```

#### `sample_workspace_dict` (function)

Sample workspace dictionary for testing.

```python
def test_workspace_parsing(sample_workspace_dict):
    assert sample_workspace_dict["name"] == "test-workspace"
```

### E2E Tests (`/tests/test_e2e/conftest.py`)

#### `isolate_working_directory` (autouse, function)

Ensures tests restore original working directory after execution.

```python
# Automatically applied - no explicit use needed
def test_with_directory_change():
    os.chdir("/some/path")
    # Original directory automatically restored after test
```

#### `e2e_test_root` (session)

Returns the root directory for E2E tests.

```python
def test_with_test_root(e2e_test_root):
    test_file = e2e_test_root / "test_data" / "sample.yaml"
```

#### `temp_test_dir` (function)

Creates a temporary directory for test execution, automatically deleted after test.

```python
def test_with_temp_dir(temp_test_dir):
    test_file = temp_test_dir / "test.txt"
    test_file.write_text("content")
    # Directory automatically cleaned up
```

#### `test_data_dir` (function)

Creates a copy of test_data directory in temporary location.

```python
def test_with_test_data(test_data_dir):
    config = test_data_dir / ".cgconfig.yaml"
    assert config.exists()
```

#### `test_git_repo` (function)

Creates a test Git repository in temporary directory.

```python
def test_git_functionality(test_git_repo):
    # Git repo is initialized and ready
    subprocess.run(["git", "status"], cwd=test_git_repo)
```

#### `env_setup` (function)

Sets up complete test environment with all necessary components.

```python
def test_full_environment(env_setup):
    config_path = env_setup["config_path"]
    root_dir = env_setup["root_dir"]
```

#### `run_cli_command` (function)

Factory fixture for running CLI commands in tests.

```python
def test_cli_execution(run_cli_command):
    result = run_cli_command("config view", expected_code=0)
    assert result["success"]
    assert "workspaces" in result["stdout"]
```

---

## Common Usage Patterns

### Testing a CLI Command

```python
def test_cli_command(cli_runner, cli_app, mock_console):
    result = cli_runner.invoke(cli_app, ["get", "w/*"])
    assert result.exit_code == 0
```

### Testing a Service

```python
def test_service(mock_workspace, mock_context, mock_console):
    service = MyService(
        workspace=mock_workspace,
        context=mock_context,
        console=mock_console
    )
    result = service.execute()
    assert result is not None
```

### Testing with Complete Hierarchy

```python
def test_with_hierarchy(mock_config_hierarchy, service_defaults):
    workspace = mock_config_hierarchy["workspace"]
    service = MyService(workspace=workspace, **service_defaults)
    assert service.workspace.name == "test-workspace"
```

### E2E Testing

```python
@pytest.mark.e2e
def test_end_to_end(run_cli_command, env_setup):
    result = run_cli_command(
        "generate w/test-workspace",
        cwd=env_setup["root_dir"],
        expected_code=0
    )
    assert result["success"]
```

---

## Guidelines for Adding New Fixtures

### Where to Add Fixtures

1. **Root conftest** (`/tests/conftest.py`): Common fixtures used across multiple test directories
2. **Directory-specific conftest**: Fixtures only needed by tests in that specific directory

### Fixture Design Principles

1. **Single Responsibility**: Each fixture should do one thing well
2. **Minimal Scope**: Use the narrowest scope possible (function > module > session)
3. **Clear Naming**: Use descriptive names that indicate what the fixture provides
4. **Comprehensive Docstrings**: Include scope, purpose, and usage examples
5. **Sensible Defaults**: Provide reasonable default values that work for most tests

### Example Template

```python
@pytest.fixture(scope="function")  # Use appropriate scope
def my_fixture(dependency1, dependency2):
    """Brief description of what this fixture provides.

    Longer description if needed, explaining when to use this fixture
    and any important considerations.

    Scope: function (created fresh for each test)

    Example:
        def test_something(my_fixture):
            result = my_fixture.do_something()
            assert result is not None
    """
    # Setup code
    fixture_object = create_object()

    yield fixture_object

    # Teardown code (if needed)
    cleanup()
```

### Testing New Fixtures

Always verify new fixtures work correctly:

```python
def test_my_new_fixture(my_new_fixture):
    """Verify the new fixture provides expected functionality."""
    assert my_new_fixture is not None
    assert hasattr(my_new_fixture, "expected_attribute")
```

---

## Troubleshooting

### Fixture Not Found

If pytest reports a fixture is not found:

1. Check the fixture is defined in the correct conftest.py
2. Verify the conftest.py file exists in the test directory hierarchy
3. Ensure you're not trying to use a session-scoped fixture from a module-scoped fixture

### Fixture Scope Issues

If you see state leaking between tests:

1. Check if the fixture scope is too broad (session/module instead of function)
2. Verify autouse fixtures like `reset_console_state` are working
3. Consider if you need to add cleanup code in the fixture

### Mocking Issues

If mocks aren't working as expected:

1. Verify you're patching the right import path
2. Check the patch is active when the code under test runs
3. Ensure you're using the mocked version, not the real one

---

## Related Documentation

- [pytest fixtures documentation](https://docs.pytest.org/en/stable/fixture.html)
- [Test Suite Refactoring Plan](../.claude/plans/test-suite-refactoring-plan.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
