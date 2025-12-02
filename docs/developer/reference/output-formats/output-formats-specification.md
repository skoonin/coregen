# Coregen Output Formats Specification

This document defines the expected output formats for all coregen commands after standardization. Based on analysis in `current-output-analysis.md`, this specification aims to create consistent, predictable outputs across all commands.

## Design Principles

1. **Consistency**: Same JSON structure across all commands
2. **Predictability**: Alphabetically sorted keys, consistent field names
3. **Simplicity**: No duplicate data, clean entity separation
4. **Inheritance**: Components show inherited fields for filtering
5. **Compatibility**: Maintain essential functionality while improving structure
6. **Default Inclusion**: When user requests data, include everything by default (workspace + context + component)
7. **Smart Field Inheritance**: Inherited fields with prefixes, override-aware field resolution

---

## Output Organization Structure

### Default Organization

By default our outputs for `get` will follow this structure:

**Key Requirements**:

- **Alphabetically sorted keys** at all levels
- **All entities as objects** (not strings)
- **No duplicate data** (components only in components array)
- **Inherited fields with prefixes** for clear attribution
- **Override-aware field resolution** (no duplicate workspace/context fields)
- **Clean structure** (no internal/debug fields)
- **Nested (default output)**: [json_output_nested_example.json](json_output_nested_example.json)
  - Hierarchical structure with components nested inside contexts, contexts inside workspaces
- **Flat Format**: [json_output_flat_example.json](json_output_flat_example.json)
  - Applied when `--format-type flat` is specified
  - Returns pure arrays for easy iteration: workspaces[], contexts[], components[]
  - Each entity contains parent references (e.g., components have context and workspace fields)

### Type (`--type`) Filtering

When a Type is specified (`--type`), only the type requested will be returned. No parent or child data will be included.

- Intuitive ordering (workspaces, contexts, components)
- Grouped structure for easy access to specific entity types
- Easy way to filter out parent data AND child data

Formats:

- **Nested** (default): Will follow the same structure as above, but only include the specified type and no parent or child data.
  - eg. `--type context` will only return contexts and no workspaces or components.
- **Flat** Format: Will follow the same structure as above, but only include the specified type and no parent or child data.
  - eg. `--type component --format-type flat` will return only components in flat array format.


## Output **Override Rules**:

Parent fields are inherited by child entities, but can be overridden by context definitions. Components cannot override parent fields, but can inherit from context and workspace.

- If context defines `archive_dir` or `output_dir`, use context value (no workspace prefix)
- If context doesn't define these, inherit from workspace (no prefix)
- Contexts always include `context.workspace` field for reference
- Components when in Flat Format or Type Component will always include `context` (name) and `context.environment` `workspace`(name) fields for reference
- For custom fields, children will override parent fields

### Matrix Outputs

Matrix outputs will follow specific rules to ensure compatibility with GitHub Actions and other CI/CD tools. The construction of the data for the raw output will happen in the service layer and passed to the console for matrix formatting.

**Matrix Output Rules**

- **Base fields**: `pattern` (full pattern), `workspace`, `context`, `component`, `component_name`
- **Convenience fields**: `component`, `context`, `workspace`, `environment`, `pattern`
- **GitHub Actions compatibility**: Each component becomes one matrix entry
- **Metadata support**: For detect-changes, includes `changed_files` and `categories` arrays
- **Context fields**: `context_` prefix (active, component_type, environment, name, commit_dir)
- **Workspace fields**: `workspace_` prefix (name only, since context can override others)
- **Component fields**: `component_` prefix (active, required, for_commit, priority, path, dependencies)
- All of these fields will need to be assembled at the service layer and passed to the console for matrix formatting, where it adds the "include:" prefix to the output.

```bash
coregen get cm/* --output matrix
```

```json
{
  "Include": [
    {
      "component": "nginx",
      "component_active": true,
      "component_custom_field": "custom_value", // user-defined field
      "component_dependencies": [
        {
          "name": "prometheus",
          "path": "common-templates/prometheus"
        },
        {
          "name": "metrics-server",
          "path": "common-templates/metrics-server"
        }
      ],
      "component_dependency_01_name": "prometheus",
      "component_dependency_01_path": "common-templates/prometheus",
      "component_dependency_02_name": "metrics-server",
      "component_dependency_02_path": "common-templates/metrics-server",
      "component_for_commit": false,
      "component_name": "nginx",
      "component_path": "contexts/aws/clusters/aws-cluster-prod/nginx",
      "component_priority": 9999,
      "component_required": false,
      "context": "aws-cluster-prod",
      "context_active": true,
      "context_component_type": "app",
      "context_custom_field": "custom_value", // user-defined field
      "context_environment": "prod",
      "context_commit_dir": "generated",
      "context_name": "aws-cluster-prod",
      "context_output_dir": "custom-output", // either inherited from workspace or context override
      "environment": "prod",
      "pattern": "aws/aws-cluster-prod/nginx",
      "workspace": "aws",
      "workspace_archive_dir": "archive", // No context override, inherited from workspace
      "workspace_context_type": "cluster",
      "workspace_custom_field": "custom_value", // user-defined field
      "workspace_name": "aws"
    }
  ]
}
```

## Standard Entity Fields

### Workspace Entity

```json
{
  "name": "aws",
  "archive_dir": "archive",
  "context_config_files": ["**/*aws*values.yaml"],
  "context_type": "cluster",
  "output_dir": "output",
  "workspace_dir": "contexts"
  "custom_field": "custom_value" // user-defined field
}
```

**Core Fields**: `name`, `workspace_dir`, `archive_dir`, `output_dir`, `context_type`, `context_config_files`
**Custom Fields**: Any user-defined fields (schema allows additional properties)
**Simple Filters**: `name=aws`, `context_type=cluster`, `workspace_dir=contexts`, `archive_dir=archive`, `output_dir=output`

**Note**: Workspaces do not have an `active` field in the schema.

### Context Entity

```json
{
  "name": "aws-cluster-prod",
  "active": true,
  "component_type": "app",
  "environment": "prod",
  "commit_dir": "generated",
  "workspace": "aws",
  "output_dir": "output", // from workspace, can be overridden by context
  "archive_dir": "archive", // from workspace, can be overridden by context
  "components":
    "app": [
      {...}
    ],
  // custom fields
  "account_id": "03999999",
  "region": "us-west-2",
  "region_short": "usw2",
  "root_dir": "clusters",
}
```

**Schema Core Fields**: `name`, `environment`, `active`, `commit_dir`, `component_type`
**Inherited Fields**: `workspace` (name of parent workspace), `output_dir`, `archive_dir` (from parent workspace, can be overridden by context)
**Custom Fields**: `account_id`, `region`, `region_short`, `root_dir`, `cloud`, plus user-defined
**Simple Filters**: `name=aws-cluster-prod`, `environment=prod`, `active=true`, `workspace=aws`, `component_type=app`, `region=us-west-2`

**Internal Fields to Exclude**: `_config_file_path`, `internal_path`, `resolved_paths`, `components` (nested data), `app` (duplicate), `bypass_validation`

### Component Entity

```json
{
  "metrics-server": {
    "name": "metrics-server",
    "context": "aws-cluster-01", // name of parent context
    "workspace": "aws", // ineherited from context
    "environment": "prod", // inherited from context
    "config": {
      "active": true,
      "dependencies": [
        - name: "nginx",
          path: "common-templates/nginx",
      ],
      "for_commit": true,
      "path": "common-templates/metrics-server",
      "priority": null,
      "required": false
    },
}
```

**Schema Core Fields**: `name` (required)
**Config Fields**: `active`, `required`, `for_commit`, `priority`, `path`, `dependencies`
**Inherited Fields**: `workspace`, `environment`, `context` (from parent context/workspace)
**Custom Fields**: Any user-defined template variables (schema allows additional properties)
**Simple Filter**: `name=nginx`, `active=true`, `required=false`, `for_commit=false`, `priority=9999`, `workspace=aws`, `environment=prod`, `context=aws-cluster-prod`

---

**Rules**:

- Always include `environment` field (inherited from parent context)
- `env` is treated as a custom field only (not an alias for environment)
- For filtering, use `environment=prod` to filter by environment

---

## Output Format Options

### Name-Only Output Format (`--name-only`)

Standard Name-Only (All Types, Always Flat Format)

When using `--name-only` option, the output will be a flat list of names for all entities matching the pattern. This is useful for quick lookups or when only names are needed.

```bash
coregen get w/* --name-only --output json
coregen detect-changes --name-only --output json
```

```json
// Flat format
{
  "workspaces": ["aws", "local"],
  "contexts": ["aws-cluster-prod", "aws-cluster-dev", "cluster-dev"],
  "components": ["nginx", "prometheus", "metrics-server"]
}
```

#### Name Only with Type Filtering (`--type` option)

When using the `--type` option, the output will be filtered to only include the specified type. This allows for focused queries on specific entity types.

```bash
# When --type option is added to GET command
coregen get "w/*" --name-only --type workspace --output json
```

```json
["aws", "local"]
```

---

### Table Output (may need revision)

#### Workspace Table Output

```bash
coregen get w/* --output table
```

```
Name  | Context Type | Workspace Dir | Output Dir | Archive Dir | # Contexts
------|--------------|---------------|------------|-------------|------------
aws   | cluster      | contexts      | output     | archive     | 4
local | cluster      | contexts      | output     | archive     | 2
```

**Workspace Table Fields**:

- Core identification: `Name`, `Context Type`
- Directory configuration: `Workspace Dir`, `Output Dir`, `Archive Dir`
- Computed field: `# Contexts` (count of contexts in workspace)

#### Context Table Output

```bash
coregen get c/* --output table
```

```
Name              | Workspace | Env  | Active | Component Type | Commit Dir    | Output Dir    | # Components
------------------|-----------|------|--------|----------------|---------------|-----------|-------------
aws-cluster-prod  | aws       | prod | true   | app            | generated     | output | 15
aws-cluster-dev   | aws       | dev  | true   | app            | generated     | output | 12
cluster-dev       | local     | dev  | false  | app            | generated     | output | 8
```

**Context Table Fields**:

- Core identification: `Name`, `Workspace`, `Env` (shortened for width)
- Status: `Active`
- Configuration: `Component Type`, `Commit Dir`
- Directory: `Output Dir` workspace or overriden context output directory
- Computed field: `# Components` (count of components in context)

#### Component Table Output

```bash
coregen get cm/* --output table
```

```
Name       | Active | Required | Context          | Env  | Workspace | Priority | For Commit | Path
-----------|--------|----------|------------------|------|-----------|----------|-----------|-----
nginx      | true   | false    | aws-cluster-prod | prod | aws       | 9999     | false     | -
prometheus | true   | true     | aws-cluster-prod | prod | aws       | 0        | false     | -
grafana    | false  | false    | aws-cluster-dev  | dev  | aws       | 100      | true      | custom/grafana
```

**Component Table Fields**:

- Core identification: `Name`
- Component flags: `Active`, `Required`, `For Commit`
- Hierarchy: `Context`, `Env`, `Workspace`
- Processing: `Priority`
- Custom path: `Path` (shows `-` if using default)

**General Table Output Rules**:

- **Field selection**: Show most actionable fields for each entity type
- **Column width**: Use shortened names where appropriate (`Env` not `Environment`)
- **Null handling**: Show `-` for undefined/null values
- **Boolean display**: Show `true`/`false` as strings
- **Computed fields**: Include useful counts (# Contexts, # Components)
- **Custom fields**: Include commonly used fields like `Region` where appropriate
- **Sorting**: Default sort by name unless specified otherwise
- **Headers**: Use readable names with proper spacing
- **Alignment**: Left-align text, right-align numbers

---

## Format Type (`--format-type` option)

### Nested (default)

**Nested (default output)**: [json_output_nested_example.json](json_output_nested_example.json)

By default our program uses the nested format `--format-type nested`, it maintains the same field structure as our model:

```json
{
  "workspaces": [
    {
      "active": true,
      "name": "aws",
      "contexts": [
        {
          "active": true,
          "environment": "prod",
          "name": "aws-cluster-prod",
          "workspace": "aws",
          "components": [
            {
              "active": true,
              "context": "aws-cluster-prod",
              "environment": "prod",
              "name": "nginx",
              "workspace": "aws"
            }
          ]
        }
      ]
    }
  ]
}
```

### Flat Format

**Flat Format**: [json_output_flat_example.json](json_output_flat_example.json)

When using `--format-type flat`, the output will be a single-level structure with all entities types listed separately. By default it will include all child data, but can be filtered by type using the `--type` option.

```json
{
  "workspaces": [
    {
      "name": "aws",
      "active": true,
      "context_type": "cluster",
      "workspace_dir": "contexts",
      "archive_dir": "archive",
      "output_dir": "output"
    }
  ],
  "contexts": [
    {
      "name": "aws-cluster-prod",
      "active": true,
      "environment": "prod",
      "workspace": "aws",
      "commit_dir": "generated",
      "output_dir": "output"
    }
  ],
  "components": [
    {
      "name": "nginx",
      "active": true,
      "context": "aws-cluster-prod",
      "environment": "prod",
      "workspace": "aws"
    }
  ]
}
```

---

## Field Inheritance Rules

### Context Inheritance from Workspace

**Basic Rule**: Contexts inherit workspace fields unless they override them

**Override-Aware Resolution**:

- If context defines `archive_dir` or `output_dir`: use context value, no workspace prefix
- If context doesn't define these: inherit from workspace, no prefix
- Always include `workspace` field (workspace name reference)
- Always include `workspace_dir` from workspace (contexts cannot override)
- All custom fields are overriden by their child fields.

### Field Aliases

**Environment Field Handling**:

- `environment` field is always inherited from parent context
- `env` is treated as a regular custom field (no special aliasing)
- Filter using `environment=prod` for environment-based filtering
