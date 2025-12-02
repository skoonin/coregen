# Context Values Files Reference

Context values files (`*-cgvalues.yaml`) define configuration for individual contexts within a workspace.

## Discovery

Files are discovered using patterns in workspace configuration:

```yaml
# .cgconfig.yaml
workspaces:
  - name: "aws"
    context_type: "cluster"  # Required: top-level key for context organization
    context_config_files:
      - "${workspace_name}/**/*-cgvalues.yaml"
```

## File Structure

Context values files are organized under the `context_type` key defined in workspace configuration:

```yaml
# When workspace has context_type: "cluster"
cluster:  # Top-level key matches workspace context_type
  # Required fields
  name: "context" # Unique context identifier
  environment: "dev" # Deployment environment
  active: true # Whether context is processed

  # Optional fields
  archive_dir: "archive" # Archive directory
  output_dir: "output" # Output directory
  commit_dir: "generated" # Commit directory for components
  component_type: "component" # Component organization type

  # Custom fields
  region: "us-west-2"
  cluster_size: "large"

  # Components
  components:
    - name: "web-app"
      config:
        active: true
        for_commit: true
        required: false
        priority: 10
        path: "templates/web"
        dependencies:
          - name: "database"
```

## Required Fields

| Field         | Type   | Description                                           | Example                        |
| ------------- | ------ | ----------------------------------------------------- | ------------------------------ |
| `name`        | string | Unique context identifier within workspace            | `"prod-cluster"`               |
| `environment` | string | Deployment environment for conditionals and filtering | `"prod"`, `"dev"`, `"staging"` |

## Context Type Organization

The `context_type` field is defined at the **workspace level** and determines the top-level key structure for context files:

```yaml
# Workspace configuration (.cgconfig.yaml)
workspaces:
  - name: "aws"
    context_type: "cluster"  # Required workspace field

# Context file uses the context_type as top-level key
cluster:  # <- This key matches the workspace context_type
  name: "aws-prod-cluster"
  environment: "prod"
  # ... rest of context configuration
```

### Context Type Examples

| Context Type | Use Case | Template Access |
| ------------ | -------- | --------------- |
| `"cluster"` (default) | Kubernetes/container environments | `{{ cluster.name }}` |
| `"account"` | Cloud account management | `{{ account.name }}` |
| `"environment"` | Environment-based organization | `{{ environment.name }}` |
| `"region"` | Geographic organization | `{{ region.name }}` |

**Important**: Cannot use `"contexts"` as it conflicts with internal model fields.

## Optional Fields

| Field            | Type    | Default       | Description                             |
| ---------------- | ------- | ------------- | --------------------------------------- |
| `active`         | boolean | `true`        | Whether context is processed by Coregen |
| `archive_dir`    | string  | `"archive"`   | Archive directory (overrides workspace) |
| `output_dir`     | string  | `"output"`    | Output directory (overrides workspace)  |
| `commit_dir`     | string  | `"generated"` | Commit directory for components         |
| `component_type` | string  | `"component"` | Component organization type name (becomes template namespace) |

When `active: false`, context is ignored unless `--include-inactive` is used.

## Components

Components are defined in the `components` array. Each component has a `name` and `config` section:

### Component Configuration

| Field                 | Type    | Default               | Description                            |
| --------------------- | ------- | --------------------- | -------------------------------------- |
| `name`                | string  | _required_            | Component identifier                   |
| `config.active`       | boolean | `false`               | Whether component is active            |
| `config.for_commit`   | boolean | `false`               | Whether component is marked for commit  |
| `config.required`     | boolean | `false`               | Always generated with other components |
| `config.priority`     | number  | `null`                | Deployment order (lower = first)       |
| `config.path`         | string  | `"context/component"` | Custom template path                   |
| `config.dependencies` | array   | `[]`                  | Components to generate together        |

### Component Example

```yaml
components:
  - name: "frontend"
    config:
      active: true
      for_commit: true
      priority: 20
      dependencies:
        - name: "backend"

  - name: "backend"
    config:
      active: true
      for_commit: true
      priority: 10
      dependencies:
        - name: "database"

  - name: "database"
    config:
      active: true
      for_commit: true
      priority: 5
```

## Custom Fields

Add custom fields to contexts for use in templates:

```yaml
name: "prod-cluster"
environment: "prod"
region: "us-west-2"
cluster_size: "large"
monitoring_enabled: true
```

Access in templates: `{{ context.region }}`, `{{ context.cluster_size }}`

## Field Inheritance

| Source    | Priority     | Description                   |
| --------- | ------------ | ----------------------------- |
| Context   | 1 (highest)  | Values in the context file    |
| Workspace | 2 (fallback) | Default values from workspace |

## Template Access

### Context Variables

Context variables are accessible through multiple namespaces:

| Variable                          | Description        | Example        |
| --------------------------------- | ------------------ | -------------- |
| `{{ context.name }}`              | Context name (standard namespace) | `prod-cluster` |
| `{{ context.environment }}`       | Environment (standard namespace) | `prod`         |
| `{{ context.component_type }}`    | Component type     | `app`          |
| `{{ context.region }}`            | Custom field       | `us-west-2`    |
| `{{ cluster.name }}`              | Context name via context_type namespace | `prod-cluster` |
| `{{ cluster.environment }}`       | Environment via context_type namespace | `prod` |

**Note**: When workspace has `context_type: "cluster"`, context properties are accessible via both `{{ context.* }}` and `{{ cluster.* }}`.

### Component Variables

The `component_type` field determines the primary namespace for accessing components:

- If `component_type: "app"`, components are accessible via `{{ app.frontend.name }}`
- If `component_type: "service"`, components are accessible via `{{ service.frontend.name }}`
- Components are **always** accessible via the convenience namespace `{{ app.frontend.name }}` regardless of `component_type`

| Variable                          | Description                | Example        |
| --------------------------------- | -------------------------- | -------------- |
| `{{ component.name }}`            | Current component name     | `frontend`     |
| `{{ component.config.priority }}` | Current component priority | `10`           |
| `{{ app.frontend.name }}`         | Access component via app namespace | `frontend` |
| `{{ app.backend.config.active }}` | Component config via app namespace | `true` |

## Examples

### Development Context

```yaml
# File: dev-cluster-cgvalues.yaml
# Assumes workspace context_type: "cluster"
cluster:
  name: "dev-cluster"
  environment: "dev"
  components:
    - name: "frontend"
      config:
        active: true
        for_commit: true
    - name: "backend"
      config:
        active: true
        for_commit: true
        dependencies:
          - name: "database"
```

### Production Context

```yaml
# File: prod-cluster-cgvalues.yaml
# Assumes workspace context_type: "cluster"
cluster:
  name: "prod-cluster"
  environment: "prod"
  region: "us-west-2"
  high_availability: true

  components:
    - name: "frontend"
      config:
        active: true
        for_commit: true
        priority: 20
    - name: "backend"
      config:
        active: true
        for_commit: true
        required: true
        priority: 10
        dependencies:
          - name: "database"
```

### Alternative Context Type Example

```yaml
# File: aws-account-cgvalues.yaml
# Assumes workspace context_type: "account"
account:
  name: "aws-prod-account"
  environment: "prod"
  account_id: "123456789012"

  components:
    - name: "vpc"
      config:
        active: true
        for_commit: true
```

## Best Practices

| Practice     | Good                     | Avoid          |
| ------------ | ------------------------ | -------------- |
| Naming       | `aws-prod-cluster`       | `cluster1`     |
| Environment  | `dev`, `staging`, `prod` | `development`  |
| Dependencies | Direct only              | Transitive     |
| Priorities   | Lower = first            | Random numbers |

## Validation

Coregen validates:

- Required fields (`name`, `environment`)
- Unique context names within workspace
- Valid component configurations
- No circular dependencies
