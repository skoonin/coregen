# Coregen End-to-End (E2E) Tests

This directory contains end-to-end tests for the Coregen CLI application. These tests validate complete workflows from a user's perspective, ensuring all components work together correctly.

## Test Structure

The E2E tests are organized as follows:

- `conftest.py` - Fixtures for setting up test environments
- `test_environment.py` - Tests for validating test environment setup
- `test_fixture_setup.py` - Tests for setting up test fixtures
- `test_installation.py` - Tests for installation processes
- `test_config_workflow.py` - Tests for configuration workflows
- `test_resource_discovery.py` - Tests for resource discovery workflows
- `test_generation.py` - Tests for code generation workflows
- `test_pattern_matching.py` - Tests for pattern matching functionality
- `test_change_detection.py` - Tests for change detection workflows
- `test_error_handling.py` - Tests for error handling scenarios
- `test_cross_platform.py` - Tests for cross-platform compatibility
- `test_full_workflows.py` - Tests for complete multi-step workflows
- `test_performance.py` - Tests for performance benchmarks

## Running E2E Tests

To run all E2E tests:

```bash
python -m pytest tests/test_e2e -v -m e2e
```

To run a specific test file:

```bash
python -m pytest tests/test_e2e/test_environment.py -v
```

To run a specific test function:

```bash
python -m pytest tests/test_e2e/test_environment.py::test_temp_dir_creation -v
```

## Test Environment

E2E tests create a temporary testing environment with:

1. Isolated test directories
2. Copies of test data
3. Temporary git repositories
4. Test configuration files
5. Test templates and contexts

The environment is cleaned up automatically after tests complete.

## Test Fixtures

The following fixtures are available for E2E tests:

- `temp_test_dir` - Temporary test directory
- `test_data_dir` - Copy of test_data directory
- `test_git_repo` - Git repository for change detection tests
- `env_setup` - Full environment setup with all components
- `run_cli_command` - Function to run CLI commands
- `e2e_test_setup` - Session-scoped fixture with test contexts and templates

## Test Coverage

The E2E tests aim to validate:

1. Installation and setup processes
2. Configuration workflows
3. Resource discovery and filtering
4. Template-based code generation
5. Pattern matching functionality
6. Change detection with git integration
7. Error handling and recovery
8. Cross-platform behavior
9. Complete end-to-end workflows
10. Performance and scalability

## Contributing New Tests

When adding new E2E tests:

1. Use the `@pytest.mark.e2e` marker
2. Follow the existing test structure
3. Use appropriate fixtures from `conftest.py`
4. Clean up any resources created during tests
5. Follow the E2E testing guidelines documented in this README
