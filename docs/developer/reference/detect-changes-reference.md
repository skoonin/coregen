# Detect-Changes Command Reference

- [Detect-Changes Command Reference](#detect-changes-command-reference)
  - [Overview](#overview)
  - [Key Features](#key-features)
  - [Output Values](#output-values)
  - [Command Syntax](#command-syntax)
  - [Options](#options)
  - [Usage Examples](#usage-examples)
    - [Basic Usage](#basic-usage)
    - [Different Base Branch](#different-base-branch)
    - [Output Formats](#output-formats)
    - [Filtering Results](#filtering-results)
    - [Debugging](#debugging)
  - [Output Formats](#output-formats-1)
    - [Table Output (default)](#table-output-default)
    - [JSON Output](#json-output)
    - [YAML Output](#yaml-output)
    - [Matrix Output](#matrix-output)
    - [Name-Only Output](#name-only-output)
  - [Output Field Reference](#output-field-reference)
  - [Component Sorting](#component-sorting)
    - [Sorting Rules](#sorting-rules)
    - [Why Sorting Matters](#why-sorting-matters)
    - [Sorting Phases](#sorting-phases)
    - [Multiple Output Arrays](#multiple-output-arrays)
    - [Understanding required\_changes Array](#understanding-required_changes-array)
  - [Change Detection Logic](#change-detection-logic)
    - [Direct Changes](#direct-changes)
    - [Required Component Cascade](#required-component-cascade)
    - [Context Addition/Removal](#context-additionremoval)
    - [Comparison Rules](#comparison-rules)
  - [CI/CD Integration](#cicd-integration)
    - [GitHub Actions Example](#github-actions-example)
  - [Performance Considerations](#performance-considerations)
  - [Error Handling](#error-handling)
  - [Best Practices](#best-practices)
  - [Technical Notes](#technical-notes)
    - [Git Archive Approach](#git-archive-approach)
    - [Temporary File Management](#temporary-file-management)

## Overview

The `detect-changes` command identifies which components have changed between the current branch (including unstaged changes) and a base branch by comparing generated output. This generation-based approach ensures complete accuracy in detecting all changes, including template modifications, context variable changes, and dependency impacts.

## Key Features

- **Generation-based comparison**: Compares actual generated output rather than source files
- **Complete change detection**: Captures all changes including template, context, and dependency changes
- **Required component cascade**: When a required component changes, all components in that context are marked as changed
- **Unstaged changes included**: Works with the repository as-is, including uncommitted changes
- **Non-invasive operation**: Never modifies your repository state

## Output Values

Changes are labeled with the following status and reason codes:

Status:

- `changed`: Component files were modified
- `deleted`: Component files were deleted

Reason:

- `direct` : Components that were changed directly
- `deleted` : Components that were deleted
- `required_cascade` : When a 'required' component is changed, **ALL** of a context's components are also considered changed.

## Command Syntax

```bash
coregen detect-changes [OPTIONS]
```

## Options

| Option                       | Short | Default          | Description                                                   |
| ---------------------------- | ----- | ---------------- | ------------------------------------------------------------- |
| `--base-branch`              | `-b`  | `main`           | Base branch to compare against                                |
| `--output`                   | `-o`  | `table`          | Output format: text, yaml, json, matrix, table                |
| `--filter`                   | `-f`  | -                | Filter expressions passed to generate command                 |
| `--include-inactive`         | `-ii` | `false`          | Include inactive components in results                        |
| `--changed-only`             | -     | `false`          | Show only changed components (exclude unchanged/deleted)      |
| `--deleted-only`             | -     | `false`          | Show only deleted components                                  |
| `--name-only`                | -     | `false`          | Output only names, not full details                           |
| `--include-required-changes` | `-ir` | `false`          | Include required_changes array in JSON/YAML output            |
| `--output-dir`               | -     | `.cgtmp`         | Custom temp directory for generated files                     |
| `--keep-generated`           | `-k`  | `false`          | Don't delete generated files after comparison (for debugging) |
| `--dry-run`                  | `-d`  | `false`          | Show what would be done without making changes                |
| `--no-color`                 | `-nc` | `false`          | Disable colored output                                        |
| `--config-file`              | `-c`  | `.cgconfig.yaml` | Path to config file                                           |
| `--quiet`                    | `-q`  | `false`          | Suppress output                                               |
| `--verbose`                  | `-v`  | `false`          | Show detailed progress during generation and comparison       |

## Usage Examples

### Basic Usage

Compare current branch to default branch with text output:

```bash
coregen detect-changes
```

### Different Base Branch

Compare to a specific branch:

```bash
coregen detect-changes --base-branch develop
```

### Output Formats

Generate GitHub Actions matrix output:

```bash
coregen detect-changes --output matrix
```

Get JSON output for scripting:

```bash
coregen detect-changes --output json
```

### Filtering Results

Show only changed component names:

```bash
coregen detect-changes --name-only --changed-only
```

Show only deleted components:

```bash
coregen detect-changes --deleted-only
```

Filter for specific workspaces/contexts:

```bash
coregen detect-changes --filter "workspace.name=aws"
```

Include required_changes array in output (useful for debugging cascade logic):

```bash
coregen detect-changes --output json --include-required-changes
```

### Debugging

Keep generated files for manual inspection:

```bash
coregen detect-changes --keep-generated --output-dir ./debug-output
```

## Output Formats

### Table Output (default)

Compact tabular display for terminal viewing:

```text
┌──────────────┬────────┬─────────────────┬─────┬───────────────┬──────┬────────┬─────┬─────┬────────┐
│ Name         │ Status │ Reason          │ WS  │ CTX           │ Env  │ Active │ Req │ Pri │ Config │
├──────────────┼────────┼─────────────────┼─────┼───────────────┼──────┼────────┼─────┼─────┼────────┤
│ nginx        │ changed│ direct          │ aws │ prod-cluster  │ prod │ true   │ false│ 0   │ Link   │
│ redis        │ changed│ required_cascade│ aws │ prod-cluster  │ prod │ true   │ false│ 1   │ Link   │
│ base-config  │ changed│ direct          │ aws │ prod-cluster  │ prod │ true   │ true │ -   │ Link   │
│ old-service  │ deleted│ deleted         │ aws │ dev-cluster   │ dev  │ false  │ false│ -   │ -      │
└──────────────┴────────┴─────────────────┴─────┴───────────────┴──────┴────────┴─────┴─────┴────────┘
```

### JSON Output

Structured format for programmatic consumption:

```json
{
  "changes": [
    {
      "component_name": "prometheus",
      "command": "cm/prometheus --filter workspace.name=aws --filter context.name=aws-cluster-01",
      "component_active": true,
      "component_path": "/Users/shawnk/git/coregen-hpc/test_data/common-templates/prometheus",
      "component_priority": 0,
      "component_dependencies": [],
      "component_required": false,
      "component": "prometheus",
      "context_name": "aws-cluster-01",
      "context": "aws-cluster-01",
      "context_config_file_path": "/Users/shawnk/git/coregen-hpc/test_data/clusters/aws/aws-cluster-01/aws-cluster-01-values.yaml",
      "context_environment": "dev",
      "environment": "dev",
      "reason": "direct",
      "status": "changed",
      "workspace_name": "aws",
      "workspace": "aws"
    }
  ],
  "deleted": []
}
```

### YAML Output

Similar to JSON but in YAML format for better readability:

```yaml
changes:
  - component_name: prometheus
    command: cm/prometheus --filter workspace.name=aws --filter context.name=aws-cluster-01
    component_active: true
    component_path: /Users/shawnk/git/coregen-hpc/test_data/common-templates/prometheus
    component_priority: 0
    component_dependencies: []
    component_required: false
    component: prometheus
    context_name: aws-cluster-01
    context: aws-cluster-01
    context_config_file_path: /Users/shawnk/git/coregen-hpc/test_data/clusters/aws/aws-cluster-01/aws-cluster-01-values.yaml
    context_environment: dev
    environment: dev
    reason: direct
    status: changed
    workspace_name: aws
    workspace: aws
deleted: []
```

### Matrix Output

GitHub Actions matrix format for CI/CD pipelines:

```json
{
  "include": [
    {
      "component_name": "prometheus",
      "command": "cm/prometheus --filter workspace.name=aws --filter context.name=aws-cluster-01",
      "component_active": true,
      "component_path": "/Users/shawnk/git/coregen-hpc/test_data/common-templates/prometheus",
      "component_priority": 0,
      "component_dependencies": [],
      "component_required": false,
      "component": "prometheus",
      "context_name": "aws-cluster-01",
      "context": "aws-cluster-01",
      "context_config_file_path": "/Users/shawnk/git/coregen-hpc/test_data/clusters/aws/aws-cluster-01/aws-cluster-01-values.yaml",
      "context_environment": "dev",
      "environment": "dev",
      "reason": "direct",
      "status": "changed",
      "workspace_name": "aws",
      "workspace": "aws"
    }
  ]
}
```

### Name-Only Output

When using `--name-only`, the output is simplified to just component names:

With `--name-only --changed-only`:

```yaml
changed:
  - metrics-server
  - nginx
  - prometheus
  - prometheus-1-dep
  - prometheus-2-deps
```

With `--name-only` (all components grouped):

```yaml
changed:
  - metrics-server
  - nginx
  - prometheus
  - prometheus-1-dep
  - prometheus-2-deps
required:
  - prometheus
deleted:
  - old-service
```

## Output Field Reference

| Field                      | Type        | Description                                            |
| -------------------------- | ----------- | ------------------------------------------------------ |
| `command`                  | string/null | Command to execute (null for deleted)                  |
| `component_active`         | boolean     | Whether component is active                            |
| `component_dependencies`   | array       | List of component dependencies                         |
| `component_name`           | string      | Name of the component                                  |
| `component_path`           | string/null | File system path to component                          |
| `component_priority`       | number/null | Execution priority (0 = highest)                       |
| `component_required`       | boolean     | Whether component is required                          |
| `component`                | string      | Component (same as component_name)                     |
| `context_config_file_path` | string      | Path to context configuration file                     |
| `context_environment`      | string/null | Environment from parent context                        |
| `context_name`             | string      | Context identifier                                     |
| `context`                  | string      | Context (same as context_name)                         |
| `environment`              | string/null | Environment (same as context_environment)              |
| `reason`                   | string      | Change reason: `direct`, `required_cascade`, `deleted` |
| `status`                   | string      | Component status: `changed`, `deleted`                 |
| `workspace_name`           | string      | Workspace identifier                                   |
| `workspace`                | string      | Workspace (same as workspace_name)                     |

## Component Sorting

The detect-changes command applies consistent sorting to all output formats to ensure components are grouped logically and dependencies are properly ordered.

### Sorting Rules

Components in the output are sorted by:

1. **Workspace** (alphabetically)
2. **Context** (alphabetically within workspace)
3. **Priority** (0, 1, 2, ..., None) within context
4. **Dependencies** (dependencies always before dependents)
5. **Name** (alphabetically as tiebreaker)

### Why Sorting Matters

Proper sorting ensures:

- **Context Grouping**: All components from the same context appear together
- **Dependency Order**: Dependencies are always listed before components that depend on them
- **Predictable Output**: Same changes always produce the same output order
- **CI/CD Reliability**: Matrix jobs execute in correct dependency order

### Sorting Phases

The sorting happens in a specific sequence to ensure correctness:

1. **Detection Phase**: Components are detected by comparing generated outputs (unsorted)
2. **Cascade Phase**: Required component logic appends additional components (unsorted)
3. **Filter Phase**: Filters remove unwanted components (unsorted)
4. **Sort Phase**: Final sorting applied to all three arrays: `changes`, `deleted`, `required_changes`

### Multiple Output Arrays

The detect-changes command sorts THREE separate arrays independently:

1. **changes**: All changed and deleted components (main output)
2. **deleted**: Subset containing only deleted components (for `--deleted-only`)
3. **required_changes**: Components that triggered required cascade (appears in JSON/YAML)

Each array is sorted independently to maintain consistency in all output formats.

### Understanding required_changes Array

The `required_changes` array is **optional** and **disabled by default**. To include it in JSON/YAML output, use the `--include-required-changes` flag.

The `required_changes` includes components that are both required and have changes. They trigger updates in dependent components called `required_cascade`. Components in this array also appear in the `changes` array.

When using tools like `grep` on the output, you might see components appear twice - once in each array. This is expected behavior, not a sorting issue.

When enabled with `--include-required-changes`, you'll see both `changes` and `required_changes` arrays:

```yaml
changes:
  - component: app-config
    required: false
    reason: required_cascade
  - component: base-setup # This is the required component
    required: true
    reason: direct
  - component: database
    required: false
    reason: required_cascade

required_changes:
  - component: base-setup # Duplicated here because it triggered cascade
    required: true
    reason: direct
```

## Change Detection Logic

The detect-changes command uses **generation-based comparison**: it generates all components for both the current branch and base branch, then compares the generated output to identify changes.

### Direct Changes

A component is marked as changed when its generated output differs between branches. **Any change that affects the generated component files will be detected.** This includes changes from many sources:

- Component template files
- Context config values used in templates (e.g., `context.vpc: "1829"` referenced as `{{ context.vpc }}`)
- Component config fields that may affect what or how files are generated (e.g., `active`, `path`, `required`)
- Dependency changes

### What is IGNORED During Comparison

detect-changes ignores specific items when comparing generated output:

**Comparison normalization:**
- Whitespace and formatting differences (normalized)
- Comments in generated files (stripped before comparison)
  - Comment syntaxes: `#`, `//`, `/* */`, `<!-- -->`

**File patterns excluded from comparison:**
- `.DS_Store`, `.gitkeep`
- Editor temp files: `*.swp`, `*.swo`, `*~`, `.#*`, `#*#`
- OS files: `Thumbs.db`, `desktop.ini`
- Markdown files: `*.md`
- Log files: `*.log`

**Changes outside coregen configuration directory**

### Required Component Cascade

When a component marked as `required: true` changes:

- ALL components in the same context are marked as changed
- Reason is set to `required_cascade`
- The required component appears in both `changes` and `required_changes` sections

### Context Addition/Removal

- New contexts (exist in current, not in base) → all components marked as `changed`
- Removed contexts (exist in base, not in current) → all components marked as `deleted`

### Comparison Rules

- Whitespace and formatting differences are ignored
- Comments are stripped before comparison (supports `#`, `//`, `/* */`, `<!-- -->`)
- JSON/YAML files are parsed and re-serialized for canonical comparison
- Binary files are detected and compared byte-for-byte
- Only actual code/configuration changes matter

## CI/CD Integration

### GitHub Actions Example

```yaml
jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.changes.outputs.matrix }}
      has_changes: ${{ steps.changes.outputs.has_changes }}
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0 # Important: fetch full history

      - name: Detect changed components
        id: changes
        run: |
          # Get matrix output
          matrix=$(coregen detect-changes --base-branch ${{ github.base_ref }} --output matrix)
          echo "matrix=$matrix" >> $GITHUB_OUTPUT

          # Check if there are changes
          if [ "$matrix" != '{"include":[]}' ]; then
            echo "has_changes=true" >> $GITHUB_OUTPUT
          else
            echo "has_changes=false" >> $GITHUB_OUTPUT
          fi

  deploy:
    needs: detect-changes
    if: needs.detect-changes.outputs.has_changes == 'true'
    strategy:
      matrix: ${{ fromJSON(needs.detect-changes.outputs.matrix) }}
    runs-on: ubuntu-latest
    steps:
      - name: Deploy component
        run: |
          echo "Deploying ${{ matrix.component_name }} in ${{ matrix.context_name }}"
          # Add your deployment logic here
```

## Performance Considerations

- **Full generation required**: The command generates all components for accuracy
- **Temporary files**: Created in `.cgtmp/detect-changes-{timestamp}/` by default
- **Automatic cleanup**: Temporary files are removed automatically unless `--keep-generated` is used
- **Parallel processing**: Multiple detect-changes runs can execute concurrently without interference

## Error Handling

The command will exit with appropriate error codes if:

- Not in a git repository
- Base branch doesn't exist or is invalid
- `.cgconfig.yaml` is missing or invalid
- Generation fails for either current state or base branch
- Insufficient permissions for temp directory

## Best Practices

1. **Use in CI/CD**: Integrate with your deployment pipeline to only deploy changed components
2. **Debug with --keep-generated**: When troubleshooting, keep generated files for manual inspection
3. **Filter for performance**: Use `--filter` to limit scope when working with large repositories
4. **Choose appropriate output format**: Use `matrix` for GitHub Actions, `json` for scripting, `text` for human review

## Technical Notes

### Git Archive Approach

The command uses git archive to extract base branch files without modifying your repository state. This ensures:

- No disruption to your working directory
- Unstaged changes are preserved and included in current branch analysis
- Safe concurrent execution
- No need for git stash or branch switching

### Temporary File Management

- Default location: `.cgtmp/detect-changes-{timestamp}/`
- Timestamped directories prevent conflicts
- Automatic cleanup on completion or error
- Use `--output-dir` to specify custom location
- Use `--keep-generated` to retain files for debugging
