# Coregen

Coregen is a configuration management and code generation tool designed for managing multi-environment deployments at scale. Configure once in YAML, deploy everywhere.

[![CI: Code Quality & Tests](https://github.com/skoonin/coregen/actions/workflows/ci-code.yaml/badge.svg)](https://github.com/skoonin/coregen/actions/workflows/ci-code.yaml)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## About

Coregen solves common DevOps challenges through:

1. **Simple Configuration**

   - Single YAML files to configure complete deployments
   - Intuitive hierarchy (workspace → context → component)
   - Ability to utilize template code in any component file
   - Flexible to work with any dir structure
   - Easy querying of all workspaces, contexts, and components
   - Deep filtering capabilities allowing any field in your repo.

2. **CI/CD Ready**
   - Can detect changes between branches for changes and deletions
   - JSON/YAML/MATRIX output for easy automation
   - Detection of changes for targeted deployments
   - Prioritized component outputs
   - Dependency aware

## Quick Start

See our complete [quick-start guide](docs/usage/quick-start.md).

### Install with Pip

```bash
# Install the latest version directly from git
pip install git+https://github.com/skoonin/coregen.git

# Or install a specific version
pip install git+https://github.com/skoonin/coregen.git@v1.0.0

# Development installation from cloned repo
git clone https://github.com/skoonin/coregen.git
cd coregen
pip install -e .
```

### Development Environment Setup

```bash
make setup  # Creates virtual environment and installs dev dependencies
```

## Basic Usage

```bash
# Generate config file and initialize workspace structure
coregen config generate

# Or generate config file only (skip workspace initialization)
coregen config generate --config-file-only

```

## Key Concepts

- **Workspace**: Top-level organizational unit (e.g., AWS, GCP)
- **Context**: Specific instance within a workspace (e.g., Kubernetes cluster)
- **Component**: Deployable unit within a context (e.g., an application service)
- **Template**: Jinja2 template for generating configuration files (any file with a .j2 extension)
- **Environment**: Set in the context level configuration file, use filters to utilize it.

## Code Quality

Pre-commit hooks provide automated code fixing and quality checks including:

- **Auto-fixers**: black, isort, autoflake, pyupgrade, whitespace/formatting fixes
- **Validators**: flake8, mypy, bandit security scanning, YAML/JSON syntax

## Documentation

See the `docs/` directory for more detailed documentation.
