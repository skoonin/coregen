# Coregen Configuration System

## Table of Contents

- [Overview](#overview)
- [Configuration System](#configuration-system)
  - [Key Concepts](#key-concepts)
  - [Configuration Example](#configuration-example)
- [Configuration Structure](#configuration-structure)
  - [Root Configuration](#root-configuration)
  - [Workspace Settings](#workspace-settings)
  - [Contexts](#contexts)
  - [Components](#components)
  - [Component Config](#component-config)
  - [Dependencies](#dependencies)
- [Configuration Examples](#configuration-examples)
- [Configuration Validation](#configuration-validation)
- [Related Documentation](#related-documentation)

## Overview

The Coregen configuration system provides a flexible way to define and manage multi-environment deployments. It uses a hierarchical structure with workspaces containing contexts, which in turn contain components.

The configuration system separates user-facing configuration (what users write) from internal models (how the system processes them), allowing for flexible, semantic naming while maintaining a consistent internal structure.

## Configuration System

### Key Concepts

- **Internal Model vs User Configuration**: The system uses fixed internal keys (`contexts`, `components`) while allowing users to customize how these appear in their configs via `context_type` and `component_type`
- **Discovery Patterns**: Contexts are discovered from files matching patterns defined in `context_config_files`
- **Flexible Typing**: Users can use semantic names (e.g., "clusters", "apps") instead of generic terms
- **Path Management**: Clear separation between logical structure and filesystem paths
- **Template Variables**: Support for `${variable}` substitution in paths and configurations

### Configuration Example

For a complete example configuration, see: `/workspace/test_data/.cgconfig.yaml`

```yaml
workspaces:
  - name: "aws"
    context_type: "context" # Contexts will be under 'context' key
    context_config_files:
      - "contexts/*-cgvalues.yaml" # Discovery pattern
```

## Configuration Structure

### Root Configuration

The root configuration file (`.cgconfig.yaml`) defines workspaces and their discovery patterns. This is the entry point for all Coregen operations.

**Example Root Configuration:**

```yaml
workspaces:
  - name: "aws"
    context_type: "context"
    context_config_files:
      - "contexts/*-cgvalues.yaml"
    workspace_dir: "aws"
    archive_dir: "archive"
    output_dir: "output"
```

### Workspace Settings

> **IMPORTANT**: Paths here are relative. Use `./<path>` to specify an absolute path.

Define workspaces for your project. Each workspace has the following keys:

| Key                  | Description                                               | Required | Type         | Default                                    |
| -------------------- | --------------------------------------------------------- | :------: | ------------ | ------------------------------------------ |
| name                 | Unique name for the workspace                             |   yes    | string       | -                                          |
| context_type         | Root key name for contexts                                |          | string       | `"context"`                                |
| context_config_files | File patterns for context discovery. Globs are supported. |          | list[string] | `["${workspace_name}/**/*-cgvalues.yaml"]` |
| workspace_dir        | Workspace directory path <br>_(relative to root_path)_    |          | string       | `${name}`                                  |
| archive_dir          | Archive directory path<br>_(relative to root_path)_       |          | string       | `archive`                                  |
| output_dir           | Output directory for generated files                      |          | string       | `output`                                   |
| custom\_\*           | Additional workspace metadata                             |          | any          | -                                          |

**Example Custom Keys:**

```yaml
account_id: 03999999
workspace_region: use2
workspace_region_long: us-east-2
```

Custom keys can be used in templates and are available in the workspace context.

### Contexts

**Define contexts for the workspace.**

> **IMPORTANT**: Paths here are relative. Use `./<path>` to specify an absolute path.

- Programmatically, the `contexts` key is automatically included in the workspace configuration.
- Users can only define their contexts individually in context config files.
- These contexts are nested under the `context_type` field.
- Contexts will be auto-discovered from files matching the `context_config_files` patterns.

| Key                    | Type    | Required | Default        | Description                                                                            |
| ---------------------- | ------- | -------- | -------------- | -------------------------------------------------------------------------------------- |
| name                   | string  | yes      |                | Unique name for the context                                                            |
| component_type         | string  |          | `"component"`  | Customize the key name for components in this context                                  |
| internal_path          | string  |          | (computed)     | Computed context path (read-only, not user-settable)                                   |
| commit_dir             | string  |          | `for-commit`   | Directory where components marked for commit are placed <br>_(relative to `context_path/`)_ |
| environment            | string  |          |                | Environment setting for the context, defaults to None                                  |
| active                 | boolean |          |                | Whether the context is active                                                          |
| custom key-value pairs |         |          |                | Custom key-value pairs for the context (optional)                                      |

**Example Context Configuration:**

```yaml
context:
  name: "aws-dev-use1-cluster-app-01"
  environment: "dev"
  active: true
  component_type: "apps"
  commit_dir: "manifests"
  custom_region: "us-east-1"
  apps:
    - name: "nginx"
      config:
        active: true
        for_commit: true
        priority: 0
    - name: "monitoring"
      config:
        active: true
        for_commit: true
        priority: 1
        dependencies:
          - name: "nginx"
```

> **Note**:
>
> - Contexts are discovered from files matching the patterns in `context_config_files`
> - In templates, use semantic names directly: `{{ cluster.name }}` instead of nested paths
> - Components are referenced by their semantic type: `{{ apps.nginx.config }}` not `{{ components.nginx.config }}`

### Components

> **IMPORTANT**: Paths here are relative. Use `./<path>` to specify an absolute path.

Define components for the context. Components must be listed under the key specified by `component_type` (default is "components") within a single context. Each component must have the following keys:

| Key                    | Type                    | Required | Default | Description                                         |
| ---------------------- | ----------------------- | -------- | ------- | --------------------------------------------------- |
| name                   | string                  | yes      |         | Unique name for the component                       |
| config                 | component config {dict} |          |         | Component configuration                             |
| custom key-value pairs |                         |          |         | Custom key-value pairs for the component (optional) |

**Example Custom Keys:**

```yaml
account_id: 03999999
vars:
  workspace_region: use2
workspace_region_long: us-east-2
```

Custom keys are available in templates and can be used for component-specific configuration.

### Component Config

Each component's config must have the following keys. (remember, default values are used if not specified)

| Key          | Type                       | Required | Default   | Description                                                                                                                                           |
| ------------ | -------------------------- | -------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| for_commit   | boolean                    |          | `false`   | Whether the component is marked for commit <br>_(gets copied into the context/commit_dir)_                                                                 |
| active       | boolean                    |          | `false`   | Whether the component is included in program outputs (files or metadata)                                                                              |
| priority     | int                        |          | `""`      | Priority of the component for use in deployment scheduling                                                                                            |
| path         | string                     |          | `${name}` | Path to the component directory<br>_(relative to `context_name/component_name`)_                                                                      |
| dependencies | list of dependency objects |          | `[]`      | Dependencies for the component                                                                                                                        |
| required     | boolean                    |          | `false`   | Whether the component is required for all other components in the context. Required components are always generated with all other context components |

**Example Component Configuration:**

```yaml
apps:
  - name: "nginx"
    config:
      active: true
      for_commit: true
      priority: 0
      path: "nginx"
  - name: "api"
    config:
      active: true
      for_commit: true
      priority: 1
      dependencies:
        - name: "nginx"
          path: "nginx"
```

### Dependencies

Each dependency in the dependencies list must have the following keys:

| Key  | Type   | Required | Default  | Description                                                                       |
| ---- | ------ | -------- | -------- | --------------------------------------------------------------------------------- |
| name | string | yes      |          | Dependency name                                                                   |
| path | string |          | `{name}` | Path to the dependency directory<br>_(relative to `context_name/component_name`)_ |

**Validation Rules**: Dependencies are subject to strict validation to ensure safe deployment:

1. **No Duplicate Priorities**: Components within the same context cannot have duplicate priority values
2. **Priority Cannot Depend on Null**: Priority components cannot depend on null-priority components
3. **Dependencies Must Have Equal/Better Priority**: Dependencies must have the same priority or lower priority number (better priority)
4. **Null Cannot Depend on Null**: Null-priority components cannot depend on other null-priority components
5. **No Circular Dependencies**: Circular dependency chains are detected and rejected

See [Component Dependencies Reference](../reference/component-dependencies.md) for detailed rules, examples, and error messages.

**Example Dependency Configuration:**

```yaml
apps:
  - name: "frontend"
    config:
      priority: 2
      dependencies:
        - name: "api"
          path: "api"
        - name: "auth"
          path: "auth"
  - name: "api"
    config:
      priority: 1
      dependencies:
        - name: "database"
          path: "database"
  - name: "auth"
    config:
      priority: 1
      dependencies:
        - name: "database"
          path: "database"
  - name: "database"
    config:
      priority: 0
```

## Configuration Examples

For complete working examples, see:

- **Root Configuration**: `/workspace/test_data/.cgconfig.yaml`
- **Context Configuration**: `/workspace/test_data/contexts/aws-dev-use1-cluster-app-01-cgvalues.yaml`
- **Component Templates**: `/workspace/test_data/common-templates/`

**Complete Example Configuration:**

```yaml
# .cgconfig.yaml
workspaces:
  - name: "aws"
    context_type: "context"
    context_config_files:
      - "contexts/*-cgvalues.yaml"
    workspace_dir: "aws"
    output_dir: "output"
    account_id: 123456789
    workspace_region: "us-east-1"
```

```yaml
# contexts/dev-cluster-cgvalues.yaml
context:
  name: "dev-cluster-01"
  environment: "dev"
  active: true
  component_type: "apps"
  commit_dir: "for-commit"

  apps:
    - name: "nginx"
      config:
        active: true
        for_commit: true
        priority: 0

    - name: "api"
      config:
        active: true
        for_commit: true
        priority: 1
        dependencies:
          - name: "nginx"

    - name: "monitoring"
      config:
        active: true
        for_commit: false
        priority: 2
        dependencies:
          - name: "nginx"
```

## Configuration Validation

Coregen performs comprehensive validation on all configuration:

1. **Schema Validation**:
   - All configuration files must match the expected schema
   - Required fields must be present
   - Field types must be correct

2. **Path Validation**:
   - Paths must be valid and accessible (in strict mode)
   - Path traversal attempts are rejected
   - Paths must be within repository boundaries

3. **Dependency Validation**:
   - No circular dependencies
   - Dependencies must exist within the same context
   - Priority rules must be satisfied
   - See [Component Dependencies Reference](../reference/component-dependencies.md)

4. **Name Validation**:
   - Names must be unique within their scope
   - Names must follow valid identifier rules
   - No reserved names or special characters

5. **Template Variable Validation**:
   - All referenced variables must exist
   - Variable substitution must result in valid paths
   - Template syntax must be valid

**Validation Modes:**

- **Strict Mode** (default): All paths must exist, all validations enforced
- **Lenient Mode** (`config generate`): Allows non-existent paths for initial setup

## Related Documentation

- [Architecture Overview](./overview.md) - High-level architecture and core concepts
- [Pattern Matching System](./pattern-system.md) - Pattern syntax and matching
- [Component Dependencies Reference](../reference/component-dependencies.md) - Dependency validation rules
- [CLI Reference](../../usage/cli-reference.md) - Command-line interface documentation
