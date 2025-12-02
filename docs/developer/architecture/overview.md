# Coregen Architecture Overview

## Table of Contents

- [Introduction](#introduction)
- [Key Concepts and Terminology](#key-concepts-and-terminology)
  - [Glossary](#glossary)
  - [Hierarchical Structure](#hierarchical-structure)
  - [Configuration Flow](#configuration-flow)
  - [Error Handling and Exit Codes](#error-handling-and-exit-codes)
  - [Security Considerations](#security-considerations)
- [Core Architecture](#core-architecture)
  - [Workspace-Based Architecture](#workspace-based-architecture)
  - [Configuration System](#configuration-system)
  - [Path Management System](#path-management-system)
  - [Pattern Matching System](#pattern-matching-system)
  - [Component Management](#component-management)
  - [Output Pipeline and Console Usage](#output-pipeline-and-console-usage)
- [Common Use Cases](#common-use-cases)
- [Related Documentation](#related-documentation)

## Architecture Patterns

**IMPORTANT**: Before implementing features or fixing bugs, consult the [Architecture Patterns Documentation](patterns/README.md). These patterns ensure consistency across the codebase and address known issues.

### Critical Patterns

- **[Global Options Pattern](patterns/global-options-pattern.md)** - How to properly handle CLI global options
- **[Output Pipeline Pattern](patterns/output-pipeline-pattern.md)** - Proper stdout/stderr routing for structured output
- **[Service Layer Pattern](patterns/service-layer-pattern.md)** - Separation of business logic from CLI
- **[CLI Command Pattern](patterns/cli-command-pattern.md)** - Standard structure for CLI commands
- **[Configuration Pattern](patterns/configuration-pattern.md)** - Settings management and defaults

See the [patterns directory](patterns/) for all documented patterns.

## Introduction

`coregen` is a configuration management and code generation tool designed for managing multi-environment deployments at scale. Configure once in YAML, deploy everywhere:

```yaml
workspaces:
  - name: "aws" # Cloud provider or platform
    context_type: "cluster" # Semantic name for contexts
    context_config_files: # Discovery patterns
      - "contexts/*-cgvalues.yaml"
      - "${workspace_name}/*-cluster.yaml"
```

It solves common DevOps challenges:

1. **Simple Configuration**

   - Root configuration file defines workspaces and discovery patterns
   - Intuitive hierarchy (workspace → context → component)
   - Automatic context discovery via file patterns
   - Flexible directory structures

2. **The Power of Templates**

   - Jinja2 template support (`.j2` files)
   - Access to workspace, context, and component variables
   - Built-in dependency management
   - Component inheritance and overrides

3. **CI/CD Ready**
   - Pattern-based bulk operations
   - Change detection built in
   - Multiple output formats (JSON, YAML, MATRIX)
   - Dry-run mode for safety
   - Exit codes for automation

## Key Concepts and Terminology

### Glossary

- **Workspace**: A top-level organizational unit representing a distinct environment group (e.g., AWS, GCP). Contains contexts organized by their discovery patterns.

- **Context**: A specific deployment instance (e.g., a Kubernetes cluster, a service mesh). Contains components and context-specific configurations. Each context has an `environment` property (e.g., "dev", "stage", "prod") for logical grouping.

- **Component**: A deployable unit within a context (e.g., an application, a service). Has its own configuration and can depend on other components.

- **Environment**: A property of contexts that indicates their deployment stage (dev, stage, prod). Used for filtering and logical organization, but not for directory structure.

### Hierarchical Structure

```
Workspace (e.g., aws)
├── Context (e.g., dev-cluster-01)
│   ├── Component (e.g., nginx)
│   └── Component (e.g., monitoring)
├── Context (e.g., dev-cluster-02)
│   ├── Component (e.g., nginx)
│   └── Component (e.g., monitoring)
└── Context (e.g., prod-cluster-01)
    ├── Component (e.g., nginx)
    └── Component (e.g., monitoring)
```

> **Note**: While contexts have an `environment` property (e.g., "dev", "prod"), they are not nested under environment directories. The hierarchy is workspace → context → component.

### Configuration Flow

_Defaults are used unless overriden by the user._

1. Root Configuration (`.cgconfig.yaml`)

   - Defines workspaces and global settings
   - Sets default values and patterns

2. Context Configuration Files

   - Located within workspace directories
   - Define context-specific settings

3. Component Templates
   - Define component structure
   - Use context and workspace values
   - Support dependency resolution

### Error Handling and Exit Codes

#### Exit Codes

Coregen uses standard exit codes for different error scenarios:

- **0**: Success - Command completed successfully
- **1**: General Error - Command failed due to runtime error or invalid state
- **2**: Input/Validation Error - Invalid user input, pattern syntax errors, or validation failures

#### Error Types and Handling

1. **Configuration Errors**:

   - Invalid YAML syntax
   - Missing required fields
   - Schema validation failures
   - Exit code: 1 (general error)

2. **Pattern Errors**:

   - Invalid pattern syntax
   - Missing required prefixes
   - Exit code: 2 (validation error)

3. **Path Errors**:

   - Missing directories
   - Permission issues
   - Exit code: 1 (general error)

4. **Template Errors**:

   - Invalid Jinja2 syntax
   - Missing variables
   - Exit code: 2 (validation error)

5. **Dependency Errors**:
   - Circular dependencies
   - Missing dependencies
   - Exit code: 1 (general error)

#### Error Response Strategy

- Detailed error messages with context
- Validation before execution (fail fast)
- Safe rollback of partial changes
- Comprehensive logging to stderr
- Structured error output for JSON/YAML formats

### Security Considerations

As a local CLI tool focused on file operations, security concerns are primarily around safe file handling:

1. **Path Safety**:

   - Prevent path traversal (e.g., using `../` to access parent directories)
   - Validate all paths are within the repository boundary

2. **Template Safety**:
   - Validate template syntax before rendering
   - Prevent template injection vulnerabilities
   - Sanitize any user-provided template variables

## Core Architecture

Coregen follows a layered architecture with clear separation of concerns:

1. **CLI Layer**: Command parsing, option handling, output formatting
2. **Service Layer**: Business logic, no direct output or formatting
3. **Configuration Layer**: Model validation, path resolution, pattern matching
4. **File Management Layer**: Template processing, file operations

### Workspace-Based Architecture

A workspace represents a distinct environment group (e.g., aws, gcp) with its own:

- Configuration patterns
- Environment structure
- Context definitions
- Component definitions
- Component Code (can be static or templated)

### Configuration System

The configuration system provides a flexible way to define and manage multi-environment deployments.

#### Key Concepts

- **Internal Model vs User Configuration**: The system uses fixed internal keys (`contexts`, `components`) while allowing users to customize how these appear in their configs via `context_type` and `component_type`
- **Discovery Patterns**: Contexts are discovered from files matching patterns defined in `context_config_files`
- **Flexible Typing**: Users can use semantic names (e.g., "clusters", "apps") instead of generic terms

#### Configuration Example

For a complete example configuration, see: `/workspace/test_data/.cgconfig.yaml`

```yaml
workspaces:
  - name: "aws"
    context_type: "cluster" # Contexts will be under 'cluster' key
    context_config_files:
      - "contexts/*-cgvalues.yaml" # Discovery pattern
```

See [Configuration System](./configuration.md) for complete configuration documentation.

### Path Management System

The path management system handles all path-related operations with clear separation from configuration models.

#### Path Resolution Strategy

- **Workspace Paths**: Default to workspace name, customizable via `path` field
- **Context Paths**: Determined by discovery location or explicit `path` field
- **Component Paths**: Relative to context path, customizable via component `path` field
- **Template Variables**: Support for `${variable}` substitution in paths

#### Path Validation Modes

- **Strict Mode**: Normal operations require all paths to exist
- **Lenient Mode**: Config generation allows non-existent paths

### Pattern Matching System

The pattern matching system uses a two-phase approach with mandatory prefixes for clear, unambiguous pattern specification.

All patterns must start with a recognized prefix:

| Type          | Short | Long         | Example         | Description       |
| ------------- | ----- | ------------ | --------------- | ----------------- |
| **Workspace** | `w/`  | `workspace/` | `w/aws`         | Match workspaces  |
| **Context**   | `c/`  | `context/`   | `c/cluster-dev` | Match contexts    |
| **Component** | `cm/` | `component/` | `cm/nginx`      | Match components  |
| **Directory** | `d/`  | `dir/`       | `d/contexts/*`  | Match directories |
| **Path**      | `p/`  | `path/`      | `p/*.yaml`      | Match file paths  |

See [Pattern Matching System](./pattern-system.md) for detailed pattern documentation.

### Component Management

Components are the deployable units within contexts, supporting:

- **Dependencies**: Components can depend on other components (subject to strict validation rules)
- **Priority-based Ordering**: Components are processed in priority order (0→1→2→...→null)
- **Strict Validation**: Enforces 5 core rules to ensure valid and safe deployments
- **Active/Generated Flags**: Control which components are processed
- **Template Support**: Components can be static files or Jinja2 templates (`.j2`)

**Dependency Validation Rules**: See [Component Dependencies Reference](../reference/component-dependencies.md) for complete validation rules, deployment ordering, and configuration examples.

### Output Pipeline and Console Usage

Coregen uses a sophisticated output pipeline to ensure proper routing of output based on format.

#### Console Class Usage

```python
from common.console import Console

# CORRECT: Use class reference (Console uses class methods)
console = Console

# WRONG: Do not instantiate
# console = Console()
```

#### Output Pipeline Pattern

All commands must follow the output pipeline pattern to ensure proper stdout/stderr routing:

```python
try:
    # Validate and set output format
    self.validate_output_format(output_format)
    console.set_output_format(output_format)

    # Command logic here
    result = self.service.process()

    # Output final result
    console.print(result, output_format=output_format)

finally:
    # CRITICAL: Always reset
    console.set_output_format(None)
```

#### Output Routing

| Format | Verbose/Debug/Info | Final Output | Spinner Support |
| ------ | ------------------ | ------------ | --------------- |
| TEXT   | stdout             | stdout       | Yes             |
| JSON   | stderr             | stdout       | No              |
| YAML   | stderr             | stdout       | No              |
| TABLE  | stderr             | stdout       | No              |
| MATRIX | stderr             | stdout       | No              |

## Common Use Cases

1. **Kubernetes Multi-Cluster Management**

   ```plaintext
   aws/
   ├── dev/
   │   ├── cluster-01/  # EKS Dev Cluster
   │   └── cluster-02/  # EKS Test Cluster
   └── prod/
       └── cluster-01/  # EKS Prod Cluster
   ```

   - Centralized management of cluster configurations
   - Environment-specific service deployments
   - Consistent monitoring and logging setup

2. **Service Mesh Configuration**

   - Template-based proxy configurations
   - Environment-aware service discovery
   - Traffic management policies

3. **Infrastructure as Code**

   - Template-based resource definitions
   - Environment-specific variables
   - Cross-environment consistency

4. **CI/CD Integration**

   ```bash
   # Generate files for dev environments
   coregen generate "w/aws" --filter "context.environment=dev"

   # Generate files for a specific service across workspaces
   coregen generate "cm/monitoring"
   ```

5. **Multi-Region Cloud Deployments**

   - Region-specific configurations
   - Cross-region service dependencies
   - Shared base configurations

   ```plaintext
   aws/
   ├── us-east-1/
   │   ├── web-tier/
   │   └── data-tier/
   └── us-west-2/
       ├── web-tier/
       └── data-tier/
   ```

6. **Microservices Orchestration**

   - Service dependency management
   - Shared configurations and secrets
   - Environment-specific scaling

   ```plaintext
   services/
   ├── frontend/
   │   ├── nginx/
   │   └── gateway/
   └── backend/
       ├── auth/
       └── api/
   ```

7. **Configuration Management**

   - Centralized secrets management
   - Feature flag deployment
   - A/B testing configurations

   ```plaintext
   config/
   ├── features/
   │   ├── beta/
   │   └── stable/
   └── experiments/
       ├── group-a/
       └── group-b/
   ```

8. **Multi-Environment Application Deployment**

   - Development to production promotion
   - Staging environment configurations
   - QA environment setups

   ```plaintext
   app/
   ├── dev/
   │   ├── config/
   │   └── services/
   ├── stage/
   └── prod/
   ```

9. **Database Infrastructure**

   - Multi-region database clusters
   - Read replica configurations
   - Backup and recovery settings

   ```plaintext
   databases/
   ├── primary/
   │   ├── master/
   │   └── replicas/
   └── secondary/
       ├── master/
       └── replicas/
   ```

10. **Network Infrastructure**

    - VPC and subnet configurations
    - Security group management
    - Load balancer setups

    ```plaintext
    network/
    ├── internal/
    │   ├── vpcs/
    │   └── subnets/
    └── external/
        ├── load-balancers/
        └── firewalls/
    ```

## Related Documentation

- [Configuration System](./configuration.md) - Detailed configuration structure and examples
- [Pattern Matching System](./pattern-system.md) - Pattern syntax, features, and examples
- [CLI Reference](../../usage/cli-reference.md) - Complete CLI command documentation
- [Component Dependencies Reference](../reference/component-dependencies.md) - Dependency validation rules
- [Architecture Patterns](patterns/README.md) - Implementation patterns and best practices
