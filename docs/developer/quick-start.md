# Developer Quick Start

Get set up and productive with Coregen development in under 10 minutes.

## Prerequisites

- Python 3.11 or higher
- Git
- Make
- Basic understanding of Python type hints and Pydantic

## Development Setup

```bash
# Clone the repository
git clone https://github.com/skoonin/coregen.git
cd coregen

# Run automated setup (creates venv, installs dependencies, sets up pre-commit)
make setup

# Verify installation
make test
make lint
```

The `make setup` command handles:

- Virtual environment creation
- Development dependencies installation
- Pre-commit hooks configuration
- Tool configuration (Black, isort, flake8, mypy)

## Project Structure

| Component         | Purpose                              | Location                              |
| ----------------- | ------------------------------------ | ------------------------------------- |
| **CLI Commands**  | User interface, argument parsing     | `/source/coregen/cli/commands/`       |
| **Services**      | Business logic, no output formatting | `/source/coregen/services/`           |
| **Config Models** | Pydantic models for configuration    | `/source/coregen/config_model/`       |
| **Patterns**      | Pattern matching system              | `/source/coregen/common/pattern/`     |
| **Generator**     | Template processing                  | `/source/coregen/common/generator.py` |
| **Tests**         | Test suites                          | `/tests/`                             |

See [Architecture Overview](architecture/overview.md) for detailed structure.

## Key Concepts

### 1. Global Options Pattern

**Critical for CLI commands.** All commands must properly handle global options inheritance. Define ALL options in callback, use OR logic for boolean flags, and inherit from parent context.

See: [Global Options Pattern](architecture/patterns/global-options-pattern.md)

### 2. Service Layer Pattern

**Critical separation of concerns.** Services return data, CLI commands handle output. Services NEVER print directly.

See: [Service Layer Pattern](architecture/patterns/service-layer-pattern.md)

### 3. Output Pipeline Pattern

**Critical for JSON/YAML output.** Always use try/finally to reset output format. Missing cleanup causes corrupted JSON output.

See: [Output Pipeline Pattern](architecture/patterns/output-pipeline-pattern.md)

### 4. Pattern System

**Mandatory prefixes for pattern matching.**

| Type          | Short | Long         | Example                     | Description      |
| ------------- | ----- | ------------ | --------------------------- | ---------------- |
| **Workspace** | `w/`  | `workspace/` | `w/aws`, `w/*`              | Match workspaces |
| **Context**   | `c/`  | `context/`   | `c/cluster-dev`, `c/*-prod` | Match contexts   |
| **Component** | `cm/` | `component/` | `cm/nginx`, `cm/app-*`      | Match components |

## Development Workflow

### Branching Strategy

- **`main`** - Production-ready code; all feature PRs target this branch
- **Workflow**: Feature branches → PR to `main`

### Development Process

1. **Create feature branch** from `main`:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Before coding**: Read relevant patterns in `/docs/architecture/patterns/`

3. **Write code** following [patterns](architecture/patterns/) and [coding conventions](contributing/coding-standards.md)

4. **Test and validate**:

   ```bash
   make test coverage lint format
   ```

5. **Commit** (pre-commit hooks run automatically)

6. **Create PR to `main`** from your feature branch, with tests passing and coverage maintained

7. **Release**: Maintainers tag a release from `main`

## Essential Commands

### Make Commands

| Command           | Purpose                          |
| ----------------- | -------------------------------- |
| `make setup`      | Initial development setup        |
| `make test`       | Run all tests                    |
| `make coverage`   | Generate coverage report         |
| `make lint`       | Run all linters                  |
| `make format`     | Auto-format code (Black, isort)  |
| `make clean`      | Remove build artifacts           |
| `make help`       | Show all available commands      |

### Testing Commands

```bash
pytest                                                  # Run all tests
pytest tests/test_services/test_generate.py             # Specific file
pytest --cov=coregen --cov-report=html                  # With coverage
pytest -v                                               # Verbose output
pytest tests/test_services/test_generate.py::test_name  # Specific test
```

## Common Tasks

| Task                | Solution                                                                                               |
| ------------------- | ------------------------------------------------------------------------------------------------------ |
| **Add new command** | 1. Read [CLI Command Pattern](architecture/patterns/cli-command-pattern.md)<br>2. Use GlobalOptions pattern<br>3. Create service class<br>4. Delegate to service |
| **Add JSON output** | 1. Add FormatValidationMixin<br>2. Use Output Pipeline pattern<br>3. Test: `cmd -o json \| jq .`       |
| **Access settings** | `settings = get_settings()`<br>`value = settings.options.cmd.option`                                   |
| **Handle files**    | Use FileManager from ServiceBase:<br>`self._file_manager.read_file(path)`                              |
| **Match patterns**  | Use PatternMatcher with prefixes:<br>`matcher.match("w/aws/*")`                                        |

## Common Mistakes

| Mistake                            | Fix                                                         |
| ---------------------------------- | ----------------------------------------------------------- |
| Missing global options in callback | Add ALL options (Typer needs them for help)                 |
| `ctx.obj["verbose"] = verbose`     | Use OR logic: `verbose or parent_obj.get("verbose", False)` |
| `console = Console()`              | Use `console = Console` (class reference)                   |
| `print("output")`                  | Use `console.print()`                                       |
| Business logic in CLI              | Move to service layer                                       |
| Service doing output               | Return data, let CLI format                                 |
| `open(file)` directly              | Use `FileManager` methods                                   |
| Pattern without prefix             | Add prefix: `aws` → `w/aws`                                 |

## Testing Requirements

All services require 100% coverage. Use pytest fixtures, mock external dependencies, test success and error paths. See [Testing Pattern](architecture/patterns/testing-pattern.md).

## Quick Tips

- **Environment variables**: All use `CG_` prefix (e.g., `CG_VERBOSE=true`)
- **Exit codes**: 0=success, 1=general error, 2=invalid input/validation
- **Path handling**: Always use `pathlib.Path`, never string manipulation
- **Type hints**: Required on all public functions
- **Line length**: 160 chars (flake8), 88 chars (Black default)
- **Console output**: Use `console.print()`, never `print()`

## Next Steps

### Essential Reading

| Topic                     | Location                                            | Purpose                      |
| ------------------------- | --------------------------------------------------- | ---------------------------- |
| **Architecture Overview** | [Coregen Architecture](architecture/overview.md) | Understand system design     |
| **Architecture Patterns** | [Patterns](architecture/patterns/)               | Learn required patterns      |
| **Coding Conventions**    | [Coding Conventions](contributing/coding-standards.md) | Follow code standards        |
| **Testing Guide**         | [Testing Pattern](architecture/patterns/testing-pattern.md) | Write effective tests        |

### Key Patterns to Study

1. [CLI Command Pattern](architecture/patterns/cli-command-pattern.md) - Before adding commands
2. [Service Layer Pattern](architecture/patterns/service-layer-pattern.md) - Before implementing business logic
3. [Global Options Pattern](architecture/patterns/global-options-pattern.md) - Before working with CLI
4. [Output Pipeline Pattern](architecture/patterns/output-pipeline-pattern.md) - Before adding output formats
5. [Error Handling Pattern](architecture/patterns/error-handling-pattern.md) - Before handling errors

### Additional Resources

- [Pre-commit Guide](contributing/pre-commit.md) - Understanding pre-commit hooks
- [Release Guide](contributing/release-process.md) - Release process (maintainers)
- [Configuration Pattern](architecture/patterns/configuration-pattern.md) - Working with config
- [Validation Pattern](architecture/patterns/validation-pattern.md) - Input validation
