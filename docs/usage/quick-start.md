# Quick Start Guide

Get started with Coregen in under 10 minutes. This guide will take you from installation to generating your first configuration files.

## What is Coregen?

Coregen is a configuration management and code generation tool designed for multi-environment deployments. It solves a common problem in infrastructure management: maintaining consistent configurations across multiple environments while allowing for environment-specific values.

Instead of manually maintaining separate configuration files for dev, staging, and production environments, Coregen uses templates and structured YAML configurations to generate environment-specific files automatically. This approach reduces errors, ensures consistency, and makes it easy to identify which components are affected by code changes.

**You should use Coregen if you:**

- Manage infrastructure across multiple environments (dev, staging, prod)
- Generate configuration files from templates with environment-specific values
- Need to identify exactly which components are affected by code changes
- Want to implement selective deployments based on what actually changed

## Installation

### Install from Git

```bash
# Install the latest version
pip install git+https://github.com/skoonin/coregen.git

# Verify installation
coregen version
```

### Install for Development

```bash
# Clone and install in editable mode
git clone https://github.com/skoonin/coregen.git
cd coregen
pip install -e .

# Verify installation
coregen version
```

## Core Concepts

Before diving in, understand these three concepts that model your infrastructure:

| Concept | Description | Example |
|---------|-------------|---------|
| **Workspaces** | Top-level organizational units | AWS, GCP, or project divisions |
| **Contexts** | Specific deployment targets with an environment property | Clusters, regions, or deployment zones |
| **Components** | Individual deployable units | Services, applications, or microservices |

**Important**: Environment is a property of contexts, not a rigid directory level. You organize files however you want.

## Your First Configuration (5 minutes)

### Step 1: Initialize Configuration

Create your main configuration file and workspace directories:

```bash
coregen config generate
```

This creates `.cgconfig.yaml` with a basic structure and initializes the workspace directories:

```yaml
workspaces:
  - name: "my-workspace"
    context_type: "cluster"
    context_config_files:
      - "${workspace_name}/**/*-cgvalues.yaml"
```

### Step 2: Create a Context

Create your first context configuration file at `my-workspace/dev-cluster-cgvalues.yaml`:

```yaml
# Top-level key matches the workspace's context_type ("cluster")
cluster:
  name: "dev-cluster"
  environment: "dev"
  active: true
  # Components live under the component_type key (default "component")
  component:
    - name: "web-service"
      config:
        active: true
        for_commit: true
        replicas: 2
        domain: "dev.example.com"
```

### Step 3: Create a Template

Create a template directory and file:

```bash
mkdir -p my-workspace/dev-cluster/web-service/templates
```

Create `my-workspace/dev-cluster/web-service/templates/config.yaml.j2`:

```yaml
# Generated configuration for {{ component.name }}
apiVersion: v1
kind: Service
metadata:
  name: {{ component.name }}
  environment: {{ context.environment }}
spec:
  replicas: {{ component.config.replicas }}
  domain: {{ component.config.domain }}
```

### Step 4: Verify Your Setup

```bash
# View your configuration
coregen config view

# List all components
coregen get "w/*" --output table
```

You should see your workspace, context, and web-service component listed.

## Generate Your First Files (2 minutes)

### Basic Generation

Generate configuration files from your templates:

```bash
# Generate all components
coregen generate "w/*"

# Generate with dry-run to see what would happen
coregen generate "w/*" --dry-run

# Generate with verbose output
coregen generate "w/*" --verbose
```

Generated files will be placed in the `output` directory by default.

### Using Pattern Matching

Target specific components using patterns:

```bash
# Generate specific component
coregen generate "component/web-service"

# Generate all components in a workspace
coregen generate "workspace/my-workspace"

# Use short prefixes
coregen generate "w/my-workspace"
coregen generate "cm/web-service"
```

**Pattern Prefixes:**

| Type | Short | Long | Example |
|------|-------|------|---------|
| Workspace | `w/` | `workspace/` | `w/aws`, `w/*` |
| Context | `c/` | `context/` | `c/dev-cluster` |
| Component | `cm/` | `component/` | `cm/web-service` |

### Environment-Specific Generation

Use filters to target specific environments:

```bash
# Generate only dev environment
coregen generate "w/*" --filter "context.environment=dev"

# Generate only prod environment
coregen generate "w/*" --filter "context.environment=prod"

# Generate components with specific priority
coregen generate "w/*" --filter "component.config.priority>=5"
```

## Common Workflows

### Finding Components

List and query your configuration:

```bash
# List all components
coregen get "component/*" --output table

# Find components in production
coregen get "cm/*" --filter "context.environment=prod"

# Find components with custom properties
coregen get "cm/*" --filter "component.config.replicas>=3"
```

### Testing Patterns

Not sure if your pattern will match correctly?

```bash
# Analyze pattern matching
coregen check-pattern "workspace/my-*" --analyze

# Test with dry-run
coregen generate "cm/web*" --dry-run
```

### Detecting Changes

Identify which components are affected by code changes:

```bash
# Find affected components
coregen detect-changes --base-branch main

# Output for CI/CD pipelines
coregen detect-changes --base-branch main --output matrix
```

## Real-World Example: Multi-Environment Setup

Let's expand your setup to handle multiple environments:

### Configuration Structure

```yaml
# .cgconfig.yaml
workspaces:
  - name: "k8s"
    context_type: "cluster"
    context_config_files:
      - "${workspace_name}/**/*-cgvalues.yaml"
```

### Development Environment

Create `k8s/dev-cluster-cgvalues.yaml`:

```yaml
cluster:
  name: "dev-cluster"
  environment: "dev"
  active: true
  region: "us-east-1"
  component:
    - name: "web-service"
      config:
        active: true
        for_commit: true
        replicas: 2
        domain: "dev.example.com"
    - name: "api-service"
      config:
        active: true
        for_commit: true
        replicas: 1
        domain: "api-dev.example.com"
```

### Production Environment

Create `k8s/prod-cluster-cgvalues.yaml`:

```yaml
cluster:
  name: "prod-cluster"
  environment: "prod"
  active: true
  region: "us-west-2"
  component:
    - name: "web-service"
      config:
        active: true
        for_commit: true
        replicas: 5
        domain: "www.example.com"
    - name: "api-service"
      config:
        active: true
        for_commit: true
        replicas: 3
        domain: "api.example.com"
```

### Generate Environment-Specific Configurations

```bash
# Generate only dev configurations
coregen generate "w/*" --filter "context.environment=dev"

# Generate only prod configurations
coregen generate "w/*" --filter "context.environment=prod"

# Generate specific service across all environments
coregen generate "cm/web-service"
```

## Working with Templates

Templates use Jinja2 syntax and have access to three main variable namespaces:

- `context`: Context-level properties (name, environment, region)
- `component`: Current component being processed
- `app`: All components accessible by name

Example template with conditionals:

```yaml
# config.yaml.j2
apiVersion: v1
kind: Deployment
metadata:
  name: {{ component.name }}
  environment: {{ context.environment }}
spec:
  replicas: {{ component.config.replicas }}
  {% if context.environment == "prod" %}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  {% endif %}
  domain: {{ component.config.domain }}
  region: {{ context.region }}
```

## File Management

Control what happens when files already exist:

```bash
# Overwrite existing files (default)
coregen generate "w/*"

# Skip existing files
coregen generate "w/*" --file-action skip

# Prompt before overwriting
coregen generate "w/*" --file-action ask

# Archive old files before generating
coregen generate "w/*" --file-action archive
```

## Troubleshooting

### Pattern Not Matching

```bash
# Check pattern syntax
coregen check-pattern "your-pattern" --analyze

# Verify configuration loaded correctly
coregen config view

# Try a broader pattern first
coregen get "w/*" --output table
```

### Template Errors

```bash
# Use verbose mode to see detailed errors
coregen generate "w/*" --verbose

# Set debug logging
CG_LOG_LEVEL=debug coregen generate "w/*"
```

### Cannot Find Configuration

```bash
# Default is .cgconfig.yaml in current directory
# Specify a different file:
coregen --config-file=/path/to/config.yaml config view
```

## Next Steps

Now that you have the basics, explore these resources for deeper knowledge:

### Documentation
- [CLI Reference](cli-reference.md) - Complete command and option reference
- [Pattern Matching Guide](pattern-matching.md) - Advanced pattern techniques and filtering
- [Template Reference](templates.md) - Complete template variable documentation
- [Context Values Files Reference](../developer/reference/context-values-files.md) - Context configuration reference
- [Component Dependencies](../developer/reference/component-dependencies.md) - Understanding component dependencies

### Advanced Topics
- [Architecture Overview](../developer/architecture/overview.md) - System design and concepts
- [Configuration Model](../developer/architecture/configuration-model.md) - Detailed configuration structure
- [Detect Changes Reference](../developer/reference/detect-changes-reference.md) - CI/CD change detection

### Getting Help

- Use `--help` with any command: `coregen generate --help`
- Enable verbose output: `coregen generate "w/*" --verbose`
- Check the [troubleshooting guide](troubleshooting.md) for common issues

## Quick Reference

### Common Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `config generate` | Initialize configuration and workspace | `coregen config generate` |
| `config view` | View current configuration | `coregen config view` |
| `generate` | Generate files from templates | `coregen generate "w/*"` |
| `get` | Query configuration data | `coregen get "cm/*" --output table` |
| `check-pattern` | Test pattern matching | `coregen check-pattern "w/aws*"` |
| `detect-changes` | Find changed components | `coregen detect-changes --base-branch main` |

### Environment Variables

All Coregen environment variables use the `CG_` prefix:

- `CG_VERBOSE=true` - Enable verbose output
- `CG_LOG_LEVEL=debug` - Set logging level
- `CG_CONFIG_FILE=/path/to/config.yaml` - Specify config file location

### Default Paths

| Path | Default | Override |
|------|---------|----------|
| Workspace directory | `contexts` | In `.cgconfig.yaml`: `workspace_dir` |
| Output directory | `output` | In `.cgconfig.yaml`: `output_dir` |
| Archive directory | `archive` | In `.cgconfig.yaml`: `archive_dir` |
| Commit directory | `generated` | In context config: `commit_dir` |
