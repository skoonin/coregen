# Configuration Fields Reference

Quick reference for Coregen configuration files - required fields, defaults, and custom fields.

- [Overview](#overview)
- [Root Configuration (.cgconfig.yaml)](#root-configuration-cgconfigyaml)
- [Context Values Files (\*-cgvalues.yaml)](#context-values-files--cgvaluesyaml)
- [Component Configuration](#component-configuration)
- [Custom Fields](#custom-fields)
- [Default Values Summary](#default-values-summary)
- [Complete Examples](#complete-examples)
- [Must Specify](#must-specify)
- [See Also](#see-also)

## Overview

Coregen uses two types of configuration files:

1. **`.cgconfig.yaml`** - Root configuration defining workspaces
2. **`*-cgvalues.yaml`** - Context values files for individual deployments

## Root Configuration (.cgconfig.yaml)

Defines workspaces and discovery patterns.

### Workspace Fields

| Field | Type | Required | Default | Description |
|-------|------|:--------:|---------|-------------|
| `name` | string | ✓ | - | Unique workspace identifier |
| `context_type` | string | | `"context"` | Top-level key name in context files |
| `context_config_files` | list[string] | | `["**/*-cgvalues.yaml"]` | Glob patterns for discovering context files |
| `workspace_dir` | string | | `"contexts"` | Workspace directory (relative to repo root) |
| `archive_dir` | string | | `"archive"` | Archive directory (relative to repo root) |
| `output_dir` | string | | `"output"` | Output directory for generated files |
| Custom fields | any | | - | Additional metadata accessible in templates |

### Example

```yaml
# Minimal
workspaces:
  - name: "aws"

# With common overrides
workspaces:
  - name: "aws"
    context_type: "cluster"
    workspace_dir: "clusters"
    context_config_files:
      - "clusters/**/*-values.yaml"
    # Custom fields
    account_id: "123456789012"
    region: "us-east-1"
```

## Context Values Files (*-cgvalues.yaml)

Defines individual contexts. The top-level key must match the workspace's `context_type`.

### Context Fields

| Field | Type | Required | Default | Description |
|-------|------|:--------:|---------|-------------|
| `name` | string | ✓ | - | Unique context identifier |
| `environment` | string \| null | | `null` | Deployment environment (dev, staging, prod, etc.); optional but strongly recommended. Defaults to null when omitted |
| `active` | boolean | | `false` | Whether context is processed by Coregen |
| `component_type` | string | | `"component"` | Key name for components list |
| `commit_dir` | string | | `"for-commit"` | Directory for components marked for commit |
| `archive_dir` | string | | (workspace) | Override workspace archive directory |
| `output_dir` | string | | (workspace) | Override workspace output directory |
| Custom fields | any | | - | Additional metadata accessible in templates |

### Example

```yaml
# Minimal (assuming workspace context_type: "cluster")
cluster:
  name: "dev-cluster-01"
  environment: "dev"

# With common overrides
cluster:
  name: "prod-cluster-01"
  environment: "prod"
  active: true
  component_type: "app"
  commit_dir: "manifests"
  # Custom fields
  region: "us-west-2"
  node_count: 5

  # Components
  app:
    - name: "frontend"
      config:
        active: true
        for_commit: true
```

## Component Configuration

Components are defined in a list under the key specified by `component_type` (default: `"component"`).

### Component Fields

| Field | Type | Required | Default | Description |
|-------|------|:--------:|---------|-------------|
| `name` | string | ✓ | - | Component identifier |
| `config` | object | | `{}` | Component configuration (see below) |
| Custom fields | any | | - | Additional metadata accessible in templates |

### Component Config Fields

| Field | Type | Required | Default | Description |
|-------|------|:--------:|---------|-------------|
| `active` | boolean | | `false` | Include component in outputs |
| `for_commit` | boolean | | `false` | Copy to commit directory |
| `required` | boolean | | `false` | Always generated with other components |
| `priority` | int \| null | | `null` | Deployment order (0 = first, null = unordered) |
| `path` | string \| null | | `null` | Custom template path; when unset, PathService resolves it. Custom paths must stay within the repository root |
| `dependencies` | list[object] | | `[]` | Component dependencies |

### Dependency Fields

| Field | Type | Required | Default | Description |
|-------|------|:--------:|---------|-------------|
| `name` | string | ✓ | - | Name of dependent component |
| `path` | string \| null | | `null` | Path to dependency directory; resolved by PathService when unset. Custom paths must stay within the repository root |

### Dependency Rules

- Dependencies must exist in the same context
- No circular dependencies
- Priority components can't depend on null-priority components
- Dependencies must have equal or better priority (lower number)

### Example

```yaml
app:
  # Minimal
  - name: "frontend"

  # Complete
  - name: "backend"
    config:
      active: true
      for_commit: true
      priority: 10
      path: "templates/backend"
      dependencies:
        - name: "database"
    # Custom fields
    replicas: 3
    image_tag: "v1.2.3"

  - name: "database"
    config:
      active: true
      for_commit: true
      required: true
      priority: 5
```

## Custom Fields

All configuration levels support custom fields for use in templates.

### Allowed Types

| Type | Examples | Template Access |
|------|----------|-----------------|
| `string` | `"us-east-1"`, `"production"` | `{{ context.region }}` |
| `int` | `5`, `100` | `{{ component.replicas }}` |
| `float` | `1.5`, `3.14` | `{{ context.ratio }}` |
| `bool` | `true`, `false` | `{{ context.ha_enabled }}` |
| `list` | `["tag1", "tag2"]` | `{{ workspace.tags }}` |
| `dict` | `{cpu: "500m", memory: "1Gi"}` | `{{ component.resources.cpu }}` |

### Template Access Patterns

```yaml
# Workspace custom fields
workspaces:
  - name: "aws"
    account_id: "123456789012"
```
Access: `{{ workspace.account_id }}`

```yaml
# Context custom fields (context_type: "cluster")
cluster:
  name: "prod"
  region: "us-west-2"
```
Access: `{{ context.region }}` or `{{ cluster.region }}`

```yaml
# Component custom fields (component_type: "app")
app:
  - name: "frontend"
    replicas: 3
```
Access: `{{ component.replicas }}` or `{{ app.frontend.replicas }}`

### Nested Custom Fields

**Contexts and workspaces** support nested dictionaries as custom fields, allowing organized metadata:

```yaml
# Context with nested custom fields
cluster:
  name: "prod-cluster"
  environment: "prod"
  # Nested dictionary for tool versions
  versions:
    helmfile: "v0.144.0"
    helm: "v3.11.3"
    kubectl: "v1.27.3"
  # Nested dictionary for infrastructure tools
  tool_versions:
    terraform: "1.5.0"
    ansible: "2.15.0"
```

**Template Access:**
```jinja2
Helmfile Version: {{ cluster.versions.helmfile }}
Helm Version: {{ cluster.versions.helm }}
Terraform Version: {{ cluster.tool_versions.terraform }}
```

**Filtering Support:**
```bash
# Filter by nested field value
coregen get contexts --filter "context.versions.helmfile=v0.144.0"

# Pattern matching on nested fields
coregen get contexts --filter "context.versions.helm~=v3"
```

**Components** support nested custom fields under the `vars` namespace:

```yaml
app:
  - name: "frontend"
    vars:
      helm_chart_version: "1.2.3"
      replicas: 3
      resources:
        cpu: "500m"
        memory: "1Gi"
```

**Template Access:**
```jinja2
Chart Version: {{ component.vars.helm_chart_version }}
Replicas: {{ component.vars.replicas }}
```

**Filtering:**
```bash
coregen get components --filter "component.vars.helm_chart_version=1.2.3"
```

**Note:** Nested fields support 2-level nesting (e.g., `versions.helmfile`). Deeper nesting requires accessing the full dict object.

### Reserved Names

**Don't use these as custom field names:**
- `contexts`, `components`, `config`, `internal_path`
- Any standard field names from the tables above

## Default Values Summary

### Quick Reference Table

| Category | Field | Default | Override Via |
|----------|-------|---------|--------------|
| **System** |
| | Config file | `.cgconfig.yaml` | CLI `--config-file` only |
| **Workspace** |
| | workspace_dir | `"contexts"` | `.cgconfig.yaml` |
| | archive_dir | `"archive"` | `.cgconfig.yaml` |
| | output_dir | `"output"` | `.cgconfig.yaml` |
| | context_type | `"context"` | `.cgconfig.yaml` |
| | context_config_files | `["**/*-cgvalues.yaml"]` | `.cgconfig.yaml` |
| **Context** |
| | active | `false` | Context values file |
| | component_type | `"component"` | Context values file |
| | commit_dir | `"for-commit"` | Context values file |
| | environment | `null` | Context values file (optional, strongly recommended) |
| **Component** |
| | active | `false` | Component config |
| | for_commit | `false` | Component config |
| | required | `false` | Component config |
| | priority | `null` | Component config |
| | path | `null` | Component config (resolved by PathService when unset) |
| | dependencies | `[]` | Component config |

### CLI Defaults

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | `false` | Show what would happen without making changes |
| `--quiet` | `false` | Minimal output |
| `--verbose` | `false` | Detailed output |
| `--include-inactive` | `false` | Include inactive contexts/components |
| `--name-only` | `false` | Output names only |

### Command Defaults

| Command | Setting | Default |
|---------|---------|---------|
| `detect-changes` | output_format | `table` |
| | base_branch | `main` |
| | format | `nested` |
| `get` | output_format | `yaml` |
| | format | `nested` |
| `config view` | output_format | `yaml` |
| `config schema` | output_format | `json` |

## Complete Examples

### Basic Configuration

```yaml
# .cgconfig.yaml
workspaces:
  - name: "production"
```

```yaml
# prod-cgvalues.yaml
context:
  name: "prod-app"
  environment: "prod"

  component:
    - name: "api"
    - name: "web"
```

### Advanced Configuration

```yaml
# .cgconfig.yaml
workspaces:
  - name: "aws"
    context_type: "cluster"
    workspace_dir: "k8s-clusters"
    context_config_files:
      - "k8s-clusters/**/*-values.yaml"
    # Custom
    account_id: "123456789012"
    region: "us-east-1"
```

```yaml
# k8s-clusters/prod-cluster-values.yaml
cluster:
  name: "prod-us-west-2"
  environment: "prod"
  active: true
  component_type: "service"
  # Custom fields
  region: "us-west-2"
  node_count: 10
  # Nested custom fields
  versions:
    helmfile: "v0.144.0"
    helm: "v3.11.3"
    kubectl: "v1.27.3"

  service:
    - name: "frontend"
      config:
        active: true
        for_commit: true
        priority: 20
      replicas: 5

    - name: "backend"
      config:
        active: true
        for_commit: true
        priority: 10
        dependencies:
          - name: "database"
      replicas: 3

    - name: "database"
      config:
        active: true
        for_commit: true
        required: true
        priority: 5
      storage: "100Gi"
```

## Must Specify

These fields have **no defaults** and must be explicitly set:

| Level | Required Fields |
|-------|----------------|
| Workspace | `name` |
| Context | `name` (`environment` is optional but strongly recommended) |
| Component | `name` |

## See Also

- [Quick Start Guide](./quick-start.md) - Getting started tutorial
- [CLI Reference](./cli-reference.md) - Command-line options
- [Templates Guide](./templates.md) - Using custom fields in templates
- [Context Values Files Reference](../developer/reference/context-values-files.md) - Detailed technical reference
