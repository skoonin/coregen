# Testing Guide

Comprehensive guide to testing in the Coregen project, covering test organization, execution, coverage tracking, and platform-specific considerations.

## Table of Contents

- [Overview](#overview)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
  - [Basic Commands](#basic-commands)
  - [Unit Tests](#unit-tests)
  - [Integration Tests](#integration-tests)
  - [End-to-End Tests](#end-to-end-tests)
  - [Platform-Specific Tests](#platform-specific-tests)
  - [Docker Testing](#docker-testing)
- [Code Coverage](#code-coverage)
  - [Measuring Coverage](#measuring-coverage)
  - [Coverage Requirements](#coverage-requirements)
  - [Coverage Reports](#coverage-reports)
- [Writing Tests](#writing-tests)
  - [Test Patterns](#test-patterns)
  - [Fixtures](#fixtures)
  - [Mocking](#mocking)
  - [Platform Markers](#platform-markers)
- [CI/CD Integration](#cicd-integration)
  - [Test Matrix Strategy](#test-matrix-strategy)
  - [Coverage Aggregation](#coverage-aggregation)
- [Troubleshooting](#troubleshooting)

## Overview

Coregen uses pytest for all testing with a comprehensive approach covering multiple test types:

| Test Type | Focus | Speed | Coverage |
|-----------|-------|-------|----------|
| Unit | Individual functions/classes | Fast | High |
| Integration | Component interactions | Medium | Medium |
| E2E | Complete workflows | Slower | Comprehensive |
| Platform | OS-specific behaviors | Varies | Targeted |

**Current Test Status** (as of June 2025):
- **Total Tests**: 947 passing (100% pass rate)
- **Overall Coverage**: 78%
- **Test Run Time**: ~22 seconds

**Tools Used**:
- **pytest**: Test framework
- **pytest-cov**: Coverage measurement
- **coverage.py**: Coverage reporting
- **tox**: Test environment management
- **Docker**: Cross-platform testing

## Test Organization

Tests mirror the codebase structure:

```
tests/
├── test_cli/           # CLI layer (180 tests)
├── test_common/        # Common utilities (200 tests)
├── test_config_model/  # Configuration model (100 tests)
├── test_e2e/           # End-to-end workflows (99 tests)
└── test_services/      # Service layer (130 tests)
```

**Test Markers** (defined in `pytest.ini`):
- `unit`: Unit tests
- `integration`: Integration tests
- `e2e`: End-to-end tests
- `platform_macos`: macOS-only tests
- `platform_linux`: Linux-only tests
- `performance`: Performance benchmarks

## Running Tests

### Basic Commands

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run E2E tests only
make test-e2e

# Run platform-specific tests
make test-platform
```

### Unit Tests

Test individual functions, methods, or classes in isolation.

**Characteristics**:
- Fast execution (< 1ms per test)
- No external dependencies
- Heavy use of mocks
- Focus on single functionality

**Example**:
```bash
# Run all unit tests
tox -e py311 -- -m unit

# Run specific module
tox -e py311 -- tests/test_common/test_path_resolver.py

# Run specific test
tox -e py311 -- tests/test_common/test_path_resolver.py::test_resolve_template_basic
```

### Integration Tests

Verify interactions between multiple components.

**Characteristics**:
- Test component collaboration
- Minimal mocking (external systems only)
- Verify data flow between layers

**Current Focus**:
- Service + Config Model integration
- CLI + Service integration
- File Manager + Template Generator

**Example**:
```bash
# Run integration tests
tox -e py311 -- -m integration

# Run service integration tests
tox -e py311 -- tests/test_services/test_shell_expansion_integration.py
```

### End-to-End Tests

Validate complete user workflows from start to finish.

**Coverage Areas**:
- Configuration workflows
- Pattern matching and shell expansion detection (73 tests)
- Resource discovery
- Generation workflows
- Change detection
- Error handling scenarios

**Example**:
```bash
# Run all E2E tests
make test-e2e

# Run specific E2E category
tox -e py311 -- tests/test_e2e/test_config_workflows.py
```

### Platform-Specific Tests

Tests for OS-dependent functionality (~30 tests).

**When to Mark as Platform-Specific**:
- File path handling differences
- Environment variable behavior
- OS-specific APIs
- Permission handling

**Markers**:
```python
@pytest.mark.platform_macos
def test_macos_specific_behavior():
    """Test that verifies macOS-specific behavior."""
    # Test code

@pytest.mark.platform_linux
def test_linux_specific_behavior():
    """Test that verifies Linux-specific behavior."""
    # Test code
```

**Running Platform Tests**:
```bash
# Run macOS tests (on macOS)
tox -e py311 -- -m platform_macos

# Run Linux tests (on Linux)
tox -e py311 -- -m platform_linux

# Run platform-agnostic tests only
tox -e py311 -- -m "not platform_macos and not platform_linux"
```

**Guidelines**:
1. Minimize platform-specific tests - make platform-agnostic where possible
2. Use conditional skips for granular control:
   ```python
   @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
   def test_macos_feature():
       # Test code
   ```
3. Mock platform-specific behavior when feasible
4. Document why test is platform-specific
5. Group related platform tests together

### Docker Testing

Run tests in a Linux environment on any platform.

**Use Cases**:
- Verify Linux compatibility from macOS
- Debug platform-specific issues
- CI pipeline preparation
- Cross-platform validation

**Commands**:
```bash
# Run all tests with verbose output
make test-docker

# Run with minimal output
make test-docker-quick
```

**How It Works**:
1. Uses Ubuntu 22.04 base image
2. Installs Python 3.11 and dependencies
3. Mounts project directory at `/app`
4. Runs pytest with standard configuration
5. Container removed automatically after run

**Expected Results**:
- All tests pass except platform-specific macOS tests (auto-skipped)
- Typical: 817 passed, 1 skipped

**Performance Note**: Docker tests are slower due to container overhead. Use for final verification, not active development.

## Code Coverage

### Measuring Coverage

Coverage tracks which lines are executed during tests to identify untested code.

**Quick Commands**:
```bash
# Run tests with coverage
make test-coverage

# View HTML report
open coverage-html/index.html

# Console report with missing lines
coverage report -m

# Check specific file
coverage report -m source/coregen/common/path_resolver.py
```

**How Coverage Works**:
1. **Collection**: Coverage tool instruments code and tracks execution
2. **Processing**: Data combined from multiple runs, percentages calculated
3. **Reporting**: Generated in console, HTML, XML, and badge formats

### Coverage Requirements

**Current Status** (May 2025):
- **Overall**: 78% (target: 85%)
- **Lines Covered**: 4,509 / 5,781
- **Uncovered Lines**: 1,272

**Coverage by Component**:

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| Common Module | 85% | 90% | Medium |
| Config Model | 90% | 95% | Low |
| CLI | 88% | 90% | Low |
| Services | 70% | 80% | High |

**High Coverage Modules** (>90%):
- path_service.py: 100%
- pattern_parser.py: 98%
- pattern_facade.py: 95%
- pattern_matcher.py: 93%
- cfg_view_enhanced_service.py: 93%

**Low Coverage Modules** (<70%):
- console.py: 60% (target: 80%)
- logger.py: 55% (target: 75%)
- generator.py: 45% (target: 70%)
- workspace_initializer.py: 40% (target: 70%)

**Coverage Philosophy**:
- Focus on critical code paths
- Don't aim for 100% everywhere (diminishing returns)
- Prioritize complex logic over simple getters/setters
- Look for patterns of uncovered code

### Coverage Reports

**Local Reports**:
```bash
# Generate all report types
make test-coverage

# HTML report (interactive, browsable)
coverage html
open coverage-html/index.html

# XML report (for tools)
coverage xml

# Console report with missing lines
coverage report -m
```

**Report Formats**:
- **Console**: Summary statistics, missing line numbers
- **HTML**: Interactive browsable reports with syntax highlighting
- **XML**: Machine-readable format (Cobertura standard)
- **Badge**: SVG image for README/docs

**CI Reports**:
CI automatically:
1. Collects coverage from parallel test runs
2. Combines data with `coverage combine`
3. Generates comprehensive reports
4. Creates coverage badge
5. Posts results to PR comments

## Writing Tests

### Test Patterns

Follow the **Arrange-Act-Assert** pattern:

```python
def test_functionality():
    # Arrange - set up test conditions
    test_data = {"key": "value"}
    service = ServiceUnderTest(config=test_data)

    # Act - perform the action
    result = service.do_something()

    # Assert - verify results
    assert result == expected_value
    assert service.state == expected_state
```

**Error Testing**:
```python
def test_error_handling():
    with pytest.raises(ValueError, match="Expected error message"):
        function_that_raises_error()
```

**Parametrized Tests**:
```python
@pytest.mark.parametrize("input,expected", [
    ("case1", "result1"),
    ("case2", "result2"),
    ("case3", "result3"),
])
def test_multiple_cases(input, expected):
    assert process(input) == expected
```

### Fixtures

Use fixtures for common setup and teardown:

```python
@pytest.fixture
def test_config():
    """Provide a test configuration."""
    return {
        "workspaces": [
            {
                "name": "test-workspace",
                "contexts": {"context1": {"name": "test-context"}}
            }
        ]
    }

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    (workspace_dir / "config.yaml").write_text("# test config")
    yield workspace_dir
    # Cleanup happens automatically with tmp_path

def test_using_fixtures(test_config, temp_workspace):
    service = ServiceUnderTest(config=test_config, path=temp_workspace)
    # Test code
```

**Common Fixture Patterns**:
- Use `tmp_path` for temporary file operations
- Create reusable fixtures in `conftest.py`
- Use fixture scope (`function`, `module`, `session`) appropriately
- Yield for setup/teardown operations

### Mocking

Use `unittest.mock` or `pytest-mock` for mocking dependencies:

```python
def test_with_mocking(mocker):
    # Mock external dependencies
    mock_config_provider = mocker.Mock()
    mock_config_provider.get_config.return_value = {"test": "value"}

    # Mock specific methods
    mocker.patch('coregen.services.some_service.external_call',
                 return_value="mocked result")

    # Test code with mocks
    service = ServiceUnderTest(config_provider=mock_config_provider)
    result = service.do_something()

    # Verify mock interactions
    assert result == expected_result
    mock_config_provider.get_config.assert_called_once()
```

**Mocking Best Practices**:
- Mock at the interface boundary (not internal implementation)
- Use `mocker.patch` for module-level functions
- Use `mocker.Mock()` for object dependencies
- Verify mock calls when behavior depends on them
- Don't over-mock - integration tests should use real components

### Platform Markers

Mark tests for specific platforms when necessary:

```python
import sys
import pytest

@pytest.mark.platform_macos
def test_macos_only():
    """Test macOS-specific functionality."""
    # Test code

@pytest.mark.platform_linux
def test_linux_only():
    """Test Linux-specific functionality."""
    # Test code

@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_with_conditional_skip():
    """Alternative approach using skipif."""
    # Test code
```

**When to Use Platform Markers**:
- Testing platform-specific path handling
- OS-specific API calls
- Different behavior on different platforms
- File permission handling differences

## CI/CD Integration

### Test Matrix Strategy

CI runs tests in parallel using a matrix strategy:

```yaml
strategy:
  matrix:
    test-category:
      - common
      - config-model
      - cli
      - services
      - e2e
      - platform-specific
```

**Benefits**:
- Faster overall execution (parallel runs)
- Isolated coverage per category
- Easy identification of failures
- Platform-specific handling

**CI Jobs**:
1. **Lint**: Code style checks
2. **Test Matrix**: Parallel test execution
3. **Coverage Combine**: Aggregate all coverage data
4. **Report**: Generate final reports and badges

### Coverage Aggregation

CI combines coverage from multiple runs:

1. **Data Collection**:
   - Each test job saves `.coverage-*` files
   - XML reports saved as artifacts
   - Binary coverage data preserved

2. **Combining**:
   ```bash
   coverage combine .coverage-*
   ```

3. **Reporting**:
   ```bash
   coverage report
   coverage xml
   coverage html
   ```

4. **Badge Generation**:
   - SVG badge created from coverage percentage
   - Committed to repository
   - Displayed in README

**Artifacts Available**:
- `.coverage-*`: Binary coverage data per job
- `coverage-*.xml`: XML reports per job
- `coverage-html/`: Combined HTML report
- `coverage-badge.svg`: Coverage badge

## Troubleshooting

### Common Test Issues

**Expected Test Errors**: These appear during normal test runs and are NOT failures:
- `No such command 'invalid-command'` - CLI error handling test
- `Permission denied` - File permission error test
- `Invalid git reference: 'HEAD~1'` - Git error handling test
- `mapping values are not allowed here` - YAML parsing error test

**Platform-Specific Failures**:
1. Verify running on correct platform
2. Check if test should be marked platform-specific
3. Use `-v` flag for verbose output:
   ```bash
   tox -e py311 -- -m platform_macos -v
   ```
4. Consider mocking platform-specific behavior

**Coverage Issues**:
1. **Missing branch coverage**: Add tests for error paths and edge cases
2. **Difficult-to-test code**: Consider refactoring or targeted mocking
3. **Incomplete reports**: Ensure all test categories ran in CI

**Docker Test Failures**:
If tests pass locally but fail in Docker:
1. Check for hardcoded macOS paths
2. Verify all dependencies in requirements files
3. Look for platform-specific code without guards
4. Check file permission handling

### Test Performance

**Optimization Strategies**:
- Use fixtures with appropriate scope (module/session for expensive setup)
- Mock expensive operations (network, disk I/O)
- Use parametrized tests instead of multiple similar tests
- Run specific test categories during development

**Current Performance**:
- Full test suite: ~22 seconds
- Unit tests only: ~8 seconds
- Integration tests: ~6 seconds
- E2E tests: ~8 seconds

### Getting Help

**Resources**:
- [pytest Documentation](https://docs.pytest.org/)
- [coverage.py Documentation](https://coverage.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)

**Internal References**:
- Test examples in `tests/` directory
- Fixtures in `tests/conftest.py`
- CI configuration in `.github/workflows/`

---

**Note**: This guide consolidates information from previous testing documents. For historical reference, see `/docs/testing/` directory (archived).
