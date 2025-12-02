# Developer Documentation

This section contains technical documentation for contributors to the Coregen project.

## Getting Started

Start here if you're contributing to Coregen:

1. **[Developer Quick Start](./quick-start.md)** - Get your dev environment set up
   - Development setup
   - Project structure
   - Key concepts
   - Development workflow

## Architecture

### Core Architecture
- **[Architecture Overview](./architecture/overview.md)** - High-level system design
  - Core components
  - Data flow
  - Key concepts

- **[Configuration Model](./architecture/configuration-model.md)** - Configuration system internals
  - Pydantic models
  - Validation
  - Configuration loading

- **[Pattern System](./architecture/pattern-system.md)** - Pattern matching internals
  - Pattern compilation
  - Pattern execution
  - Matcher hierarchy

### Implementation Patterns

The **[Architecture Patterns](./architecture/patterns/)** directory contains critical patterns for implementing features correctly:

**Critical Patterns:**
- [Global Options Pattern](./architecture/patterns/global-options-pattern.md) - CLI option handling
- [Output Pipeline Pattern](./architecture/patterns/output-pipeline-pattern.md) - Stdout/stderr routing
- [Service Layer Pattern](./architecture/patterns/service-layer-pattern.md) - Business logic separation

**Development Patterns:**
- [CLI Command Pattern](./architecture/patterns/cli-command-pattern.md) - Command structure
- [Testing Pattern](./architecture/patterns/testing-pattern.md) - Test organization
- [Error Handling Pattern](./architecture/patterns/error-handling-pattern.md) - Exception handling
- [Validation Pattern](./architecture/patterns/validation-pattern.md) - Input validation

[→ Browse all patterns](./architecture/patterns/)

## Contributing

### Development Workflow
- **[Coding Standards](./contributing/coding-standards.md)** - Style guide and conventions
  - Code style
  - Type hints
  - Docstrings
  - Best practices

- **[Testing Guide](./contributing/testing-guide.md)** - Testing strategies
  - Test organization
  - Running tests
  - Coverage requirements
  - Writing tests

- **[Pre-commit Guide](./contributing/pre-commit.md)** - Pre-commit hooks
  - Setup
  - Hook configuration
  - Troubleshooting

- **[Release Process](./contributing/release-process.md)** - Creating releases
  - Versioning
  - Branching strategy
  - Release workflow
  - Changelog management

## Technical Reference

Detailed technical references:

- **[Component Dependencies](./reference/component-dependencies.md)** - Dependency system
- **[Context Values Files](./reference/context-values-files.md)** - Context config reference
- **[Detect Changes Reference](./reference/detect-changes-reference.md)** - Change detection algorithm
- **[Output Formats](./reference/output-formats/)** - Output format specifications
- **[Global Options Implementation](./reference/global-options-implementation-guide.md)** - Global options guide

## Quick Links

### Before You Code
- [Read the coding standards](./contributing/coding-standards.md)
- [Check the architecture patterns](./architecture/patterns/)
- [Understand the configuration model](./architecture/configuration-model.md)

### Development Tools
- `make setup` - Set up development environment
- `make test` - Run all tests
- `make coverage` - Generate coverage report
- `make lint` - Run linters
- `make format` - Format code

### Getting Help
- [Architecture patterns](./architecture/patterns/) - Check patterns first
- [GitHub Issues](https://github.com/skoonin/coregen/issues) - Report bugs or ask questions
- [Contributing guide](./contributing/coding-standards.md) - Contribution guidelines

---

**Need usage documentation?** See [Usage Documentation](../usage/)
