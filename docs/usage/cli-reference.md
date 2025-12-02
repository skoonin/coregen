# CLI Reference Guide

This guide provides a comprehensive overview of the Coregen Command-Line Interface (CLI), consolidating information from multiple CLI-related documents.

## Table of Contents

- [CLI Reference Guide](#cli-reference-guide)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Command Structure](#command-structure)
  - [Global Options](#global-options)
    - [File Action Options](#file-action-options)
  - [Path Options](#path-options)
  - [Core Commands](#core-commands)
    - [config Command](#config-command)
      - [config generate](#config-generate)
      - [config init](#config-init)
      - [config schema](#config-schema)
      - [config view](#config-view)
    - [generate Command](#generate-command)
    - [get Command](#get-command)
    - [check-pattern Command](#check-pattern-command)
    - [detect-changes Command](#detect-changes-command)
    - [version Command](#version-command)
  - [Pattern Matching System](#pattern-matching-system)
    - [Pattern Types](#pattern-types)
      - [Logical Patterns (with prefixes)](#logical-patterns-with-prefixes)
      - [Filesystem Patterns](#filesystem-patterns)
      - [Wildcard Patterns](#wildcard-patterns)
    - [Shell Expansion and Pattern Quoting](#shell-expansion-and-pattern-quoting)
    - [Pattern Examples](#pattern-examples)
  - [GlobalOptions Implementation](#globaloptions-implementation)
    - [Design Goals](#design-goals)
    - [How GlobalOptions Work](#how-globaloptions-work)
    - [GlobalOptions Class](#globaloptions-class)
  - [Common Use Cases](#common-use-cases)
    - [Generating Files for Multiple Environments](#generating-files-for-multiple-environments)
    - [Finding Components](#finding-components)
    - [Detecting Changes](#detecting-changes)
    - [Working with Configuration](#working-with-configuration)
  - [Command Examples](#command-examples)
    - [Basic Commands](#basic-commands)
    - [Working with Patterns](#working-with-patterns)
    - [Using Filters](#using-filters)
      - [Filter Syntax](#filter-syntax)
      - [Filter Examples](#filter-examples)
    - [Output Formatting](#output-formatting)
  - [Error Handling](#error-handling)
  - [References](#references)

## Overview

Coregen's CLI provides a comprehensive set of commands for managing configuration generation across multiple environments. The CLI follows a consistent pattern with standardized global options, clear command hierarchy, and a powerful pattern matching system.

Key design principles:

- Consistent global options across all commands
- Standardized option handling between CLI and services
- Flexible pattern matching for targeting configuration elements
- Comprehensive output format options (text, JSON, YAML, table)

## Command Structure

> **Note**: Use `make tree` (or directly `.ci-tools/cli-tree.py source/coregen/main.py`) to generate an up-to-date command tree visualization. Use `make tree-help` to include help text in the output.

Coregen follows a hierarchical command structure:

```
coregen [global options] <command> [command options] [arguments]
```

The main command tree:

```
coregen
│
├── config                         # Manage configuration settings
│   ├── generate                   # Generate configuration files
│   ├── init                       # Initialize a new configuration
│   ├── schema                     # Display JSON schema for models
│   └── view                       # Display current configuration
│
├── generate [PATHS...]            # Generate files based on configurations
├── get [PATTERNS...]              # Get configuration elements
├── check-pattern [PATTERNS...]    # Test and analyze pattern matching
├── detect-changes                 # Detect elements affected by file changes
└── version                        # Show the version of coregen
```

## Global Options

These global options are available with most commands (availability varies by command):

| Option          | Short Flag | Description                                                             | Default          |
| --------------- | ---------- | ----------------------------------------------------------------------- | ---------------- |
| `--help`        | `-h`       | Show help message and exit                                              | -                |
| `--no-color`    | `-nc`      | Disable colored output                                                  | `false`          |
| `--output`      | `-o`       | Output format (YAML, JSON, TABLE, MATRIX)                              | varies by command |
| `--quiet`       | `-q`       | Suppress output                                                         | `false`          |
| `--verbose`     | `-v`       | Enable verbose output                                                   | `false`          |

**Note:** The `--output` option is global but has command-specific defaults:
- `generate`: TEXT (output only)
- `get`: YAML
- `detect-changes`: TABLE
- `check-pattern`: TABLE
- `config view`: YAML
- `config schema`: JSON

**Command-Specific Options** (available on some commands):

| Option          | Short Flag | Description                                                             | Default          | Available On     |
| --------------- | ---------- | ----------------------------------------------------------------------- | ---------------- | ---------------- |
| `--dry-run`     | `-d`       | Show what would be done without making changes                          | `false`          | generate         |
| `--file-action` | `-fa`      | Action to take when file exists [ask\|skip\|overwrite\|archive\|delete] | `overwrite`      | generate         |
| `--config-file` | `-c`       | Path to config file                                                     | `.cgconfig.yaml` | most commands    |

**Note:** For debug logging, set the environment variable `CG_LOG_LEVEL=debug` instead of using a command flag.

## Environment Variable Support

All CLI options support environment variables with the `CG_` prefix for CI/CD integration:

**Global Options:**

- `CG_FILE_ACTION`: File action (skip, overwrite, archive, delete)
- `CG_CONFIG_FILE`: Path to configuration file
- `CG_DRY_RUN`: Enable dry-run mode
- `CG_OUTPUT_FORMAT`: Output format
- `CG_QUIET`: Suppress output
- `CG_VERBOSE`: Enable verbose output
- `CG_NO_COLOR`: Disable colored output

**Command-Specific:**

- `CG_FILTERS`: Filter expressions
- `CG_TYPE`: Filter by element type
- `CG_INCLUDE_INACTIVE`: Include inactive components
- `CG_NAME_ONLY`: Show only names
- `CG_LOG_LEVEL`: Set to `debug` for debug output

**Example:**

```bash
export CG_LOG_LEVEL=debug
export CG_OUTPUT_FORMAT=json
coregen get "w/aws"
```

### File Action Options

The `--file-action` flag controls what happens when a file already exists during generation:

| Value       | Description                                                       |
| ----------- | ----------------------------------------------------------------- |
| `ask`       | Prompt user for action (interactive mode)                         |
| `skip`      | Skip existing files                                               |
| `overwrite` | Replace existing files (default)                                  |
| `archive`   | Move existing files to archive directory before creating new ones |
| `delete`    | Delete existing files before creating new ones                    |

**Examples:**

```bash
# Skip existing files
coregen generate "w/*" --file-action skip

# Overwrite existing files (default behavior)
coregen generate "w/*" --file-action overwrite

# Archive existing files before generating new ones
coregen generate "w/*" --file-action archive
```

## Path Options

These options configure various paths used by commands:

| Option                      | Flag              | Default   | Description                                      |
| --------------------------- | ----------------- | --------- | ------------------------------------------------ |
| Archive Directory           | `--archive-dir`   | archive   | Directory for archived files                     |
| Workspace Directory         | `--workspace-dir` | (varies)  | Base directory for workspace files               |
| Context Generated Directory | `--generated-dir` | generated | Directory for generated files within a context   |
| Output Directory            | `--output-dir`    | output    | Directory for output files                       |

## Core Commands

### config Command

The `config` command manages configuration settings with several subcommands:

#### config generate

Generate a new configuration file.

```bash
coregen config generate [OPTIONS]
```

**Options:**

| Option                   | Short | Type      | Default                      | Description                                      |
| ------------------------ | ----- | --------- | ---------------------------- | ------------------------------------------------ |
| `--output-config`        | `-oc` | path      | `.cgconfig.yaml`             | Path for generated config file                   |
| `--config-file-only`     | `-cf` | flag      | false                        | Generate only config file, skip workspace        |
| `--workspace-name`       | `-wn` | string    | `contexts`                   | Name for the workspace                           |
| `--archive-dir`          | `-ad` | path      | `archive`                    | Archive directory path                           |
| `--output-dir`           | `-od` | path      | `output`                     | Output directory path                            |
| `--workspace-dir`        | `-wd` | path      | (workspace name)             | Workspace directory path                         |
| `--context-type`         | `-ct` | string    | `context`                    | Context type name                                |
| `--context-config-pattern` | `-ccp` | string  | `**/*-cgvalues.yaml`         | Pattern for context config files                 |
| `--set`                  | `-s`  | key=value | -                            | Set additional configuration values (repeatable) |

**Examples:**

```bash
# Generate default configuration
coregen config generate

# Generate with custom workspace name
coregen config generate --workspace-name my-project

# Generate config only, no directories
coregen config generate --config-file-only

# Generate with custom settings
coregen config generate --set workspace.region=us-west-2
```

#### config init

Initialize workspace directories from an existing configuration file.

```bash
coregen config init
```

**Options:**
- Standard global options only

**Behavior:**
- Requires an existing `.cgconfig.yaml` file
- Creates workspace and context directories based on the configuration
- Creates all required directory structures

**Note:** This command requires a configuration file to already exist. Use `coregen config generate` to create a new configuration file (which also initializes directories by default).

#### config schema

Display JSON schema for configuration models.

```bash
coregen config schema [SCHEMA_TYPES...] [OPTIONS]
```

**Arguments:**
- `[SCHEMA_TYPES...]`: Schema types to generate (settings, workspace, context, component, all)

**Options:**
- `--output, -o`: Output format (json, yaml) - Default: json

**Examples:**

```bash
# Get schema for all models
coregen config schema all

# Get schema for specific models
coregen config schema workspace context

# Output as YAML
coregen config schema settings --output yaml
```

#### config view

Display current configuration in various detail levels.

```bash
coregen config view [VIEW_MODE] [OPTIONS]
```

**Arguments:**
- `[VIEW_MODE]`: Level of detail to display (raw, discovered, resolved, enhanced) - Default: raw
  - `raw`: Show raw configuration as loaded from file
  - `discovered`: Show configuration with discovered contexts
  - `resolved`: Show configuration with resolved paths
  - `enhanced`: Show configuration with all computed values

**Options:**
- `--output, -o`: Output format (json, yaml) - Default: yaml

**Examples:**

```bash
# View raw configuration
coregen config view

# View with discovered contexts
coregen config view discovered

# View with all resolved values as JSON
coregen config view enhanced --output json
```

### generate Command

Generate files based on templates and configurations.

```bash
coregen generate [PATHS...] [OPTIONS]
```

**Arguments:**
- `[PATHS...]`: Patterns specifying which configurations to use (supports pattern prefixes: w/, c/, cm/)

**Options:**
- `--filter, -f`: Filter expressions (e.g., 'component.active=true')
- `--type, -t`: Filter to specific entity types (workspace, context, component)
- `--include-inactive, -ii`: Include inactive components/contexts
- `--skip-commit-dir, -sc`: Skip generating to context's commit_dir
- `--output-dir, -od`: Output directory for generated files
- `--dry-run, -d`: Show what would be done without making changes
- `--file-action, -fa`: File action (skip, overwrite, archive, delete)
- `--output, -o`: Output format (text, table) - Default: text

**Examples:**

```bash
# Generate all components in AWS workspace
coregen generate "w/aws"

# Generate only active components
coregen generate "w/aws" --filter "component.active=true"

# Dry run to preview changes
coregen generate "cm/nginx" --dry-run

# Archive existing files before generating
coregen generate "c/prod-cluster" --file-action archive
```

### get Command

Get configuration elements matching the provided patterns.

```bash
coregen get [PATTERNS...] [OPTIONS]
```

**Arguments:**
- `[PATTERNS...]`: Patterns to match configuration elements using prefixes: w/workspace c/context cm/component

**Options:**
- `--filter, -f`: Filter expressions (e.g., 'component.active=true', 'context.name~=aws' uses regex)
- `--from-json, -j`: JSON string with component specifications
- `--json-file, -jf`: Path to JSON file with component specifications
- `--name-only`: Return only names as simple arrays (de-duplicates component names)
- `--include-inactive, -ii`: Include inactive components and contexts in results
- `--type, -t`: Filter output to specific entity types (workspace, context, component)
- `--format-type, -ft`: Output structure type (flat/nested)
- `--output, -o`: Output format (YAML, JSON, TABLE, MATRIX)

### check-pattern Command

Test and analyze pattern matching.

```bash
coregen check-pattern [PATTERNS...] [OPTIONS]
```

**Arguments:**
- `[PATTERNS...]`: Patterns to test and analyze using prefixes: w/workspace c/context cm/component

**Options:**
- `--filter, -f`: Filter expressions (e.g. 'component.active=true', 'context.name~=aws' uses regex)
- `--show-rejected, -r`: Show elements that don't match the pattern
- `--analyze, -a`: Analyze why patterns match or don't match elements
- `--include-inactive, -ii`: Include inactive components and contexts in results
- `--type, -t`: Filter output to specific entity types (workspace, context, component)

### detect-changes Command

Detect components changed between current branch and base branch.

```bash
coregen detect-changes [OPTIONS]
```

- `--base-branch, -b`: Base branch to compare against (default: main)
- `--output, -o`: Output format: text, yaml, json, matrix, table (default: table)
- `--filter, -f`: Filter expressions passed to generate command
- `--include-inactive, -ii`: Include inactive components in results
- `--include-required-changes, -ir`: Include components required by changed components
- `--changed-only`: Show only changed components (exclude unchanged/deleted)
- `--deleted-only`: Show only deleted components
- `--name-only`: Output only names, not full details
- `--output-dir`: Custom temp directory for generated files (default: .cgtmp)
- `--keep-generated, -k`: Don't delete generated files after comparison (for debugging)

### version Command

Show the version of coregen.

```bash
coregen version
```

## Pattern Matching System

Coregen includes a powerful pattern matching system that processes patterns in two phases:

1. **Pattern Compilation**: Converting raw patterns to structured specifications
2. **Pattern Execution**: Applying specifications to match configuration elements

### Pattern Types

#### Logical Patterns (with prefixes)

Use logical names and relationships:

```
workspace/aws               # Match the AWS workspace and its contents
context/aws-cluster-dev     # Match a specific context
cm/metrics-server           # Match all metrics-server components
```

#### Filesystem Patterns

Reference configuration elements by file paths:

```
contexts/aws/               # Match by relative path
/Users/name/contexts/aws/   # Match by absolute path
```

#### Wildcard Patterns

Use wildcards for flexible matching:

- **Single Asterisk (`*`)**

  ```
  context/*dev            # Context names ending in "dev"
  cm/prom*                # Components starting with "prom"
  ```

### Shell Expansion and Pattern Quoting

**⚠️ IMPORTANT**: Always quote patterns containing wildcards to prevent shell expansion.

**The Problem**: Shells automatically expand unquoted glob patterns to matching file paths before passing them to Coregen:

```bash
# ✗ Wrong - shell expands to file paths
coregen get workspace/aws/*              # Shell expansion occurs!

# ✓ Correct - quoted to prevent expansion
coregen get "workspace/aws"           # Coregen receives the pattern
coregen get "context/*-dev"              # Proper quoting
coregen generate "cm/nginx*"             # Wildcard protected
```

**Shell Expansion Detection**: Coregen automatically detects shell expansion and provides helpful guidance:

```bash
$ coregen get workspace/aws/*
Error: Possible shell expansion detected!
   Did you mean one of these?
     • "workspace/aws"
     • "contexts/aws/**"

Pattern Tips:
   • Quote patterns with wildcards: "workspace/aws"
   • Use check-pattern to test: coregen check-pattern "your-pattern"
```

**Must Quote These Characters**: `*`, `**`, `?`, `[`, `{`

### Pattern Examples

```
# Workspace level (quoted for safety)
"workspace/aws"             # Match AWS workspace
"workspace/aws"          # AWS workspace and all nested elements

# Context level (quote wildcards)
"context/aws-cluster-dev"   # Specific context
"context/*dev"              # Contexts with names ending in "dev"
"contexts/aws/*"            # All contexts in AWS workspace

# Component level (quote wildcards)
"cm/nginx"                  # All nginx components
"cm/prom*"                  # Components starting with "prom"
"aws/dev/*/nginx"           # Nginx component in all dev contexts

# JSON specifications
contexts ["context1","context2"]           # Listed contexts only
components ["admiral","datadog"]           # Listed components only
```

> **Note**: All commands support global options and path options where applicable. Patterns with wildcards should be quoted to prevent shell expansion.

## GlobalOptions Implementation

Coregen implements a standardized approach for handling global options using the `GlobalOptions` class.

### Design Goals

1. **Consistency**: Use the same approach for all global options in all commands
2. **Maintainability**: Make it easy to add new global options or change existing ones
3. **Clarity**: Clearly define the flow of options from CLI to services
4. **Reliability**: Avoid common pitfalls that have caused bugs
5. **Single Source of Truth**: Ensure there's a single point where global options are defined

### How GlobalOptions Work

1. **Definition**: All global options are defined in a dedicated `GlobalOptions` class
2. **Propagation**: Options flow from CLI to commands via the context object
3. **Inheritance**: Subcommands inherit global options from parent commands
4. **Service Initialization**: Services receive standardized options via the `GlobalOptions` instance

### GlobalOptions Class

```python
@dataclass
class GlobalOptions:
    """Container for global CLI options."""

    dry_run: bool = False
    file_action: FileAction = FileAction.ASK
    no_color: bool = False
    output_format: OutputFormat = OutputFormat.TEXT
    quiet: bool = False
    verbose: bool = False
    config_file: Optional[Path] = None

    # Methods for converting to/from other formats
    def to_dict(self) -> dict: ...

    @classmethod
    def from_context(cls, ctx) -> 'GlobalOptions': ...

    @classmethod
    def from_dict(cls, data: dict) -> 'GlobalOptions': ...
```

## Common Use Cases

### Generating Files for Multiple Environments

```bash
# Generate files for all dev environments across workspaces
coregen generate "*/dev/*"

# Generate specific component across environments
coregen generate "*/*/monitoring" --dry-run
```

### Finding Components

```bash
# Find all active components in prod environments
coregen get "*/prod/*" --filter "component.active=true" --output json

# Find all components that depend on a specific component
coregen get "cm/*" --filter "component.dependencies.name=metrics-server" --output table
```

### Detecting Changes

```bash
# Detect changes between current branch and main
coregen detect-changes --base-branch main --output matrix

# Show only changed component names
coregen detect-changes --name-only --changed-only
```

### Working with Configuration

```bash
# View the current configuration
coregen config view --output yaml

# Initialize a new configuration
coregen config init my-workspace --template standard

# Generate a schema for the configuration model
coregen config schema --model WorkspaceConfig --output json
```

## Command Examples

### Basic Commands

```bash
# View help
coregen --help

# Show version
coregen version

# View current configuration
coregen config view
```

### Working with Patterns

```bash
# Test a pattern
coregen check-pattern "workspace/aws" --analyze

# Get components matching a pattern
coregen get "cm/nginx" --output-format table

# Generate configuration for specific contexts
coregen generate "context/*-prod" --dry-run
```

### Using Filters

Filter expressions allow you to refine results based on element properties. They use a simple syntax with support for various comparison operators.

#### Filter Syntax

Filters follow the pattern: `property operator value`

**Supported Operators:**

- `=` - Equals
- `!=` - Not equals
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal
- `<=` - Less than or equal
- `~=` or `=~` - Pattern matching (regex) - both operators work identically

#### Filter Examples

```bash
# Get active components in production
coregen get "*/prod/*" --filter "component.config.active=true"

# Find components with priority greater than or equal to 1
coregen get "cm/*" --filter "component.config.priority>=1"

# Find components with priority less than or equal to 5
coregen get "cm/*" --filter "component.config.priority<=5"

# Find components with unset priority (intuitive syntax)
coregen get "cm/*" --filter "component.config.priority=none"

# Find contexts in development environments
coregen get "context/*" --filter "context.environment=dev"

# Find components with specific names using regex
coregen get "cm/*" --filter "component.name~=nginx"
```

### Output Formatting

```bash
# Output as JSON
coregen get "workspace/aws" --output json

# Output as YAML
coregen config view --output yaml

# Output as table
coregen get "context/*" --output table

# Output as GitHub Actions matrix
coregen detect-changes --output matrix
```

## Error Handling

The CLI uses a consistent approach to error handling:

- **Exit Codes**: Non-zero exit codes for errors
- **Error Messages**: Clear, user-friendly error messages
- **Detailed Logs**: With `--verbose` for troubleshooting, or set `CG_LOG_LEVEL=debug` for debug logging
- **Structured Error Data**: JSON/YAML errors when using those output formats

Common error scenarios:

- **Configuration Errors**: Invalid configuration files
- **Pattern Errors**: Invalid pattern syntax
- **Path Errors**: Invalid or inaccessible paths
- **Permission Errors**: Insufficient permissions
- **Git Errors**: When working with git repositories

## References

- [Global Options Implementation Guide](../developer/reference/global-options-implementation-guide.md) - Guide for implementing options in commands and services
- [Pattern Matching Guide](pattern-matching.md) - Comprehensive guide to pattern matching
- [Detect Changes Reference](../developer/reference/detect-changes-reference.md) - Detailed detect-changes command documentation
