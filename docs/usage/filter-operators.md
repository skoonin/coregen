# Filter Operators Reference

This document provides a comprehensive guide to using filters in Coregen commands.

## Overview

Filters allow you to narrow down results based on specific criteria. They work with `get`, `detect-changes`, and `check-pattern` commands.

## Basic Syntax

```bash
--filter "entity.field=value"
```

Where:
- `entity` is optional and can be `workspace`, `context`, or `component`
- `field` is the property name (supports nested properties with dots)
- `value` is what to compare against

## Available Operators

### Equality Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Exact match | `--filter "context.active=true"` |
| `!=` | Not equals | `--filter "context.active!=false"` |

### Pattern Matching Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `~=` or `=~` | Regex pattern match (bash-style) | `--filter "context.name~=aws"` or `--filter "context.name=~aws"` |

[!IMPORTANT]
> Both `~=` and `=~` operators use **regular expression (regex) matching**, following bash `[[ ]]` syntax. The pattern is matched anywhere in the string (substring matching) unless you use anchors. Both operators work identically - use whichever feels more natural to you.

#### Regex Pattern Syntax

| Pattern | Description | Example |
|---------|-------------|---------|
| `prom` | Matches substring | `prom` matches "prometheus", "kube-prometheus-stack" |
| `^aws` | Matches start of string | `^aws` matches "aws-cluster" but not "my-aws" |
| `prod$` | Matches end of string | `prod$` matches "cluster-prod" but not "prod-cluster" |
| `.` | Matches any single character | `aws.dev` matches "aws-dev", "aws_dev" |
| `.*` | Matches any characters (zero or more) | `aws.*prod` matches "aws-cluster-prod" |
| `[0-9]` | Matches any digit | `nginx-[0-9]` matches "nginx-1", "nginx-9" |
| `[a-z]+` | Matches one or more lowercase letters | `^[a-z]+$` matches "prod", "dev" |
| `\.` | Matches literal dot (escaped) | `1\.2\.3` matches "1.2.3" |

#### Common Filter Patterns

```bash
# Contains substring (both operators work identically)
--filter "context.name~=aws"                # Matches contexts containing "aws"
--filter "context.name=~prod"               # Matches contexts containing "prod"

# Starts with
--filter "context.name~=^aws-"              # Matches "aws-cluster", "aws-app", etc.

# Ends with
--filter "context.name~=-prod$"             # Matches "cluster-prod", "app-prod", etc.

# Exact match
--filter "context.name~=^prometheus$"       # Matches only exactly "prometheus"

# Complex patterns
--filter "context.name~=^aws-.*-prod$"      # Matches "aws-cluster-prod", "aws-app-prod"
--filter "component.name~=nginx-[0-9]+"     # Matches "nginx-1", "nginx-10", etc.
--filter "component.vars.version~=^1\.2"    # Matches versions starting with "1.2"
```

### Numeric Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `>` | Greater than | `--filter "component.config.priority>10"` |
| `<` | Less than | `--filter "component.config.priority<100"` |
| `>=` | Greater than or equal | `--filter "component.config.priority>=10"` |
| `<=` | Less than or equal | `--filter "component.config.priority<=100"` |

### Special Values

```bash
# Match null/None values (works with any field)
--filter "component.config.priority=none"
--filter "component.description=null"       # Both "none" and "null" work
--filter "context.custom_field=none"        # Case-insensitive: none, None, NONE

# Boolean values
--filter "context.active=true"
--filter "context.active=false"
```

[!NOTE]
> The keywords `none` and `null` (case-insensitive) are converted to Python `None` for **any field**, not just priority. This allows filtering for unset or null values across all entity types and properties.

## Entity-Scoped vs Unscoped Filters

You can optionally prefix filters with an entity type:

```bash
# Entity-scoped (explicit)
--filter "workspace.name=aws"
--filter "context.environment=production"
--filter "component.config.active=true"

# Unscoped (searches all entity types)
--filter "name=aws"                # Searches workspace, context, and component names
--filter "active=true"              # Searches all entities with an 'active' field
```

## Nested Properties

Access nested properties using dot notation:

```bash
--filter "component.config.active=true"
--filter "component.config.priority>10"
--filter "component.vars.helm_version=1.2.3"
```

## Multiple Filters

Apply multiple filters by using the `--filter` option multiple times:

```bash
coregen get "c/*" \
  --filter "context.environment=production" \
  --filter "context.active=true" \
  --filter "context.name~=aws"
```

All filters must match (AND logic).

## Examples by Command

### Get Command

```bash
# Get all active components
coregen get "cm/*" --filter "component.config.active=true"

# Get AWS production contexts
coregen get "c/*" --filter "context.name~=aws" --filter "context.environment=production"

# Get high-priority components
coregen get "cm/*" --filter "component.config.priority>=50"
```

### Detect Changes Command

```bash
# Detect changes only in production contexts
coregen detect-changes --base-branch main --filter "context.environment=production"

# Detect changes in AWS-related components
coregen detect-changes --base-branch HEAD~1 --filter "context.name~=aws"

# Detect changes in active, high-priority components
coregen detect-changes --base-branch main \
  --filter "component.config.active=true" \
  --filter "component.config.priority>10"
```

### Check Pattern Command

```bash
# Test pattern with filters
coregen check-pattern "w/aws" --filter "component.config.active=true"

# Analyze pattern matching for production contexts
coregen check-pattern "c/*-prod" --filter "context.environment=production" --analyze
```

## Pattern Prefixes and Filter Compatibility

[!IMPORTANT]
> Filters must match the entity type selected by your pattern prefix. Mismatches will result in zero matches.

### Understanding Pattern Prefixes

Patterns use prefixes to specify which entity type to select:

| Pattern Prefix | Entity Type | Description | Example |
|---------------|-------------|-------------|---------|
| `c/*` or `context/*` | Contexts | Selects contexts (and their components) | `coregen get "c/*"` |
| `cm/*` or `component/*` | Components | Selects components only | `coregen get "cm/*"` |
| `w/*` or `workspace/*` | Workspaces | Selects workspaces (and their hierarchy) | `coregen get "w/*"` |

### Filter Entity Prefixes Must Match Pattern Type

When using entity-scoped filters (e.g., `component.config.priority`), the filter entity type must match your pattern:

```bash
# CORRECT - Pattern and filter both target components
coregen get "cm/*" --filter "component.config.priority=none"

# WRONG - Pattern targets contexts, filter targets components
coregen get "c/*" --filter "component.config.priority=none"
# This returns ZERO results because contexts don't have component.config fields

# CORRECT - Pattern targets contexts, filter targets contexts
coregen get "c/*" --filter "context.active=true"
```

### Common Pattern/Filter Mismatches

#### Mistake: Using `c/*` with `component.*` filters

```bash
# WRONG - c/* selects contexts, not components
coregen get "c/*" --filter "component.config.active=true"
# Result: Zero matches (contexts don't have component.config fields)

# CORRECT - Use cm/* to select components
coregen get "cm/*" --filter "component.config.active=true"
# Result: Returns matching components
```

#### Mistake: Using `cm/*` with `context.*` filters

```bash
# WRONG - cm/* selects components, not contexts
coregen get "cm/*" --filter "context.environment=production"
# Result: Zero matches (components don't have context.environment fields)

# CORRECT - Use c/* to select contexts
coregen get "c/*" --filter "context.environment=production"
# Result: Returns matching contexts and their components
```

### When to Use Unscoped Filters

If you want to avoid entity type mismatches, use unscoped filters (without entity prefix):

```bash
# Works with any pattern - searches the selected entity's fields
coregen get "c/*" --filter "active=true"    # Searches context.active
coregen get "cm/*" --filter "active=true"   # Searches component.config.active
coregen get "w/*" --filter "active=true"    # Searches workspace fields
```

However, unscoped filters are less explicit and may match unexpected fields.

## Common Mistakes

### 1. Using Wrong Operators for Pattern Matching

```bash
# WRONG - Using = for pattern matching
--filter "context.name=aws"      # This requires exact match "aws"

# CORRECT - Using ~= for substring matching
--filter "context.name~=aws"     # This uses regex (matches substring)
```

### 2. Forgetting Anchors for Exact Match

```bash
# WRONG - This matches any context containing "aws"
--filter "context.name~=aws"     # Matches "aws-prod", "my-aws", etc.

# CORRECT - Use anchors for exact match
--filter "context.name~=^aws$"   # Matches only exactly "aws"
```

### 3. Incorrect Boolean Values

```bash
# WRONG
--filter "context.active=True"    # Capital T
--filter "context.active=1"       # Numeric

# CORRECT
--filter "context.active=true"    # Lowercase
```

## Tips and Best Practices

1. **Test filters incrementally**: Start with simple filters and add complexity
2. **Use check-pattern for debugging**: Test your patterns before using them in automation
3. **Remember regex is substring by default**: Use `^` and `$` anchors for exact matching
4. **Quote your filters**: Use quotes to prevent shell expansion of special characters
5. **Combine patterns and filters**: Use patterns for structure, filters for properties
6. **Escape special regex characters**: Use `\.` for literal dots, `\[` for literal brackets, etc.

## Field Discovery

To see available fields for filtering:

```bash
# List all contexts to see their fields
coregen get "c/*" --output json | jq '.[0]' | head -20

# Use check-pattern to explore
coregen check-pattern "c/*" --analyze
```

## Related Documentation

- [Pattern Matching Guide](../usage/pattern-matching.md)
- [CLI Reference](../usage/cli-reference.md)
