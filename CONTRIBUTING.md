# Contributing to Coregen

Thank you for your interest in contributing to Coregen! This guide will help you get started.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/skoonin/coregen.git
cd coregen

# Set up development environment
make setup-dev

# Run tests
make test
```

## Development Workflow

1. **Fork and clone** the repository
2. **Create a branch** for your changes: `git checkout -b feature/your-feature-name`
3. **Make your changes** and ensure tests pass
4. **Submit a pull request** to the `main` branch

## Code Quality

All contributions must pass our automated quality checks:

- **Formatting**: black, isort
- **Linting**: flake8, pylint
- **Type checking**: mypy
- **Security**: bandit
- **Tests**: pytest with >79% coverage

### Pre-commit Hooks

We use pre-commit hooks to automatically enforce code quality. It is installed during the setup process.

```bash
# Install hooks (done automatically by 'make setup-dev')
pre-commit install

# Run manually
pre-commit run --all-files
```

See [Pre-commit Guide](docs/developer/contributing/pre-commit.md) for details.

## Testing

```bash
# Run all tests
make test

# Run tests in parallel (faster but no e2e tests)
make test-parallel

# Run specific test file
pytest tests/test_cli/test_generate_cli.py -v

# Run with coverage
pytest --cov=source --cov-report=html
```

See [Testing Guide](docs/developer/contributing/testing-guide.md) for comprehensive testing documentation.

## Coding Standards

- Follow existing code patterns and architecture
- Write tests for new functionality
- Update documentation for user-facing changes
- Keep functions focused and under 300 lines
- Use type hints for all function parameters and returns

See [Coding Standards](docs/developer/contributing/coding-standards.md) for detailed guidelines.

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass locally
- [ ] Pre-commit hooks pass
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated with your changes
- [ ] No merge conflicts with main branch

### PR Process

1. **Title format**: `type: brief description` (e.g., `feat: add matrix output format`)
   - Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
2. **Description**: Explain what and why, not just how
3. **Link issues**: Reference any related issues (`Fixes #123`)
4. **Wait for CI**: All status checks must pass
5. **Review**: Address feedback and discussion

### Branch Protection

Once the repository is public, the `main` branch will be protected:

- All changes must go through pull requests
- CI checks must pass before merging
- Direct pushes are disabled

## Architecture and Patterns

Coregen follows specific architectural patterns:

- **Service Layer**: All business logic in services (not CLI)
- **Configuration Model**: Pydantic models with validation
- **Path Resolution**: Always use PathService
- **Testing**: Comprehensive fixtures and unit tests

See [Architecture Documentation](docs/developer/architecture/overview.md) for details.

## Detailed Documentation

### For Contributors

- [Quick Start Guide](docs/developer/quick-start.md) - Getting started with development
- [Testing Guide](docs/developer/contributing/testing-guide.md) - Comprehensive testing practices
- [Coding Standards](docs/developer/contributing/coding-standards.md) - Code style and patterns
- [Pre-commit Setup](docs/developer/contributing/pre-commit.md) - Automated quality checks
- [Release Process](docs/developer/contributing/release-process.md) - How releases are created

### For Architecture

- [Architecture Overview](docs/developer/architecture/overview.md) - System design
- [Configuration Model](docs/developer/architecture/configuration-model.md) - Data structures
- [Pattern System](docs/developer/architecture/pattern-system.md) - Design patterns

### For Users

- [User Documentation](docs/usage/README.md) - How to use Coregen
- [CLI Reference](docs/usage/cli-reference.md) - Command documentation

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/skoonin/coregen/discussions)
- **Bugs**: Open an [Issue](https://github.com/skoonin/coregen/issues)
- **Security**: See [SECURITY.md](SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.
