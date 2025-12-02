# Coregen Pattern Matching System

## Table of Contents

- [Overview](#overview)
- [Pattern Matching System](#pattern-matching-system)
  - [Two-Phase Approach](#two-phase-approach)
  - [Pattern Prefixes (Required)](#pattern-prefixes-required)
  - [Pattern Features](#pattern-features)
- [Pattern Examples](#pattern-examples)
  - [Basic Patterns](#basic-patterns)
  - [Wildcard Patterns](#wildcard-patterns)
  - [Hierarchical Matching](#hierarchical-matching)
  - [Filesystem Patterns](#filesystem-patterns)
- [Shell Expansion and Quoting](#shell-expansion-and-quoting)
  - [Why Quoting Matters](#why-quoting-matters)
  - [Characters That Must Be Quoted](#characters-that-must-be-quoted)
- [Pattern Validation](#pattern-validation)
- [Testing Patterns](#testing-patterns)
- [Related Documentation](#related-documentation)

## Overview

The Coregen pattern matching system provides a powerful and flexible way to select configuration elements (workspaces, contexts, components) for operations. It uses a two-phase approach with mandatory prefixes to ensure clear, unambiguous pattern specification.

## Pattern Matching System

### Two-Phase Approach

The pattern matching system processes patterns in two distinct phases:

1. **Pattern Compilation**: Converting raw patterns into structured specifications
   - Validates pattern syntax
   - Identifies pattern type from prefix
   - Compiles wildcards and matching rules

2. **Pattern Execution**: Applying specifications to match configuration elements
   - Evaluates patterns against elements
   - Applies filters and constraints
   - Returns matched elements
   - Provides detailed match reasoning

This separation allows for:
- Better error messages
- Pattern validation before execution
- Clear understanding of pattern behavior
- Educational feedback for users

### Pattern Prefixes (Required)

**All patterns must start with a recognized prefix** to eliminate ambiguity and improve error handling.

| Type          | Short | Long         | Example         | Description       |
| ------------- | ----- | ------------ | --------------- | ----------------- |
| **Workspace** | `w/`  | `workspace/` | `w/aws`         | Match workspaces  |
| **Context**   | `c/`  | `context/`   | `c/cluster-dev` | Match contexts    |
| **Component** | `cm/` | `component/` | `cm/nginx`      | Match components  |

> **Note:** Only logical patterns (workspace, context, component) are supported. Filesystem patterns (`d/` and `p/` prefixes) are not implemented.

**Why Prefixes Are Required:**

- **Clarity**: Immediately clear what type of element you're matching
- **No Ambiguity**: No confusion between logical names and filesystem paths
- **Better Errors**: System can provide specific guidance for each pattern type
- **Future-Proof**: Allows for new pattern types without breaking existing patterns

### Pattern Features

#### Wildcards

- **Single Asterisk (`*`)**: Match any characters within a level
  - `w/a*` - Workspaces starting with "a"
  - `c/*-dev` - Contexts ending in "-dev"
  - `cm/nginx*` - Components starting with "nginx"

- **No Recursive Operator Needed**: Unlike standard glob, `*` matches across all hierarchy levels
  - `w/aws/*` - All contexts in AWS workspace
  - `c/*/nginx` - All nginx components in any context

#### Case Sensitivity

Pattern matching is case-sensitive by default:
- `w/AWS` does not match workspace "aws"
- `c/dev-cluster` does not match "Dev-Cluster"

#### Mandatory Prefixes

All patterns must start with a recognized prefix. Patterns without prefixes will be rejected with helpful error messages:

```bash
# ✗ Wrong - no prefix
coregen get aws

# ✓ Correct - with prefix
coregen get "w/aws"
```

#### Pattern Specificity

Patterns can target specific levels in the hierarchy:

- **Workspace Level**: `w/aws` - Matches workspace and all its contents
- **Context Level**: `c/cluster-dev` - Matches specific context and its components
- **Component Level**: `cm/nginx` - Matches component across all contexts

## Pattern Examples

### Basic Patterns

```bash
# Match specific workspace
coregen get "w/aws"

# Match specific context
coregen get "c/aws-cluster-dev"

# Match specific component across all contexts
coregen get "cm/nginx"
```

### Wildcard Patterns

```bash
# Match all workspaces starting with 'a'
coregen get "w/a*"

# Match all dev contexts
coregen get "c/*-dev"

# Match all components starting with 'nginx'
coregen get "cm/nginx*"
```

### Hierarchical Matching

```bash
# Match all contexts in AWS workspace
coregen get "w/aws/*"

# Match all dev contexts across all workspaces
coregen get "c/*-dev"

# Match nginx component in all contexts
coregen get "cm/nginx"
```

## Shell Expansion and Quoting

### Why Quoting Matters

**⚠️ CRITICAL**: Always quote patterns containing wildcards or special characters to prevent shell expansion.

**The Problem**: Shells automatically expand unquoted glob patterns to matching file paths before passing them to Coregen:

```bash
# ✗ Wrong - shell expands to file paths
coregen get w/aws/*              # Shell expansion occurs!

# ✓ Correct - quoted to prevent expansion
coregen get "w/aws/*"            # Coregen receives the pattern
coregen get "c/*-dev"            # Proper quoting
coregen generate "cm/nginx*"     # Wildcard protected
```

### Characters That Must Be Quoted

Always quote patterns containing these characters:

- `*` - Asterisk (wildcard)
- `**` - Double asterisk (recursive in filesystem patterns)
- `?` - Question mark (single character wildcard)
- `[` and `]` - Bracket expressions
- `{` and `}` - Brace expansion

**Examples:**

```bash
# All of these must be quoted
coregen get "w/*"
coregen get "c/cluster-*"
coregen get "cm/nginx*"
```

## Pattern Validation

The pattern matching system validates patterns before execution:

1. **Prefix Validation**:
   - Pattern must start with a recognized prefix
   - Provides suggestions for invalid prefixes

2. **Syntax Validation**:
   - Wildcard syntax must be valid
   - Path separators must be correct
   - No invalid characters

3. **Logical Validation**:
   - Pattern type must be appropriate for the operation
   - Pattern must be possible to match given the configuration

**Invalid Pattern Examples:**

```bash
# ✗ No prefix
coregen get aws

# ✗ Invalid prefix
coregen get x/aws

# ✗ Invalid syntax
coregen get "w/[aws"

# ✓ Valid patterns
coregen get "w/aws"
coregen get "c/*-dev"
coregen get "cm/nginx*"
```

## Testing Patterns

Use the `check-pattern` command to test and understand pattern behavior:

```bash
# Test basic pattern matching
coregen check-pattern "w/aws" --analyze

# Test wildcard patterns
coregen check-pattern "c/*-dev" --analyze

# Test with filters
coregen check-pattern "w/aws/*" --filter "component.active=true"

# Show elements that don't match
coregen check-pattern "cm/nginx*" --show-rejected

# Test multiple patterns
coregen check-pattern "w/aws" "c/*-dev" "cm/nginx" --analyze
```

The `check-pattern` command provides:
- Pattern compilation analysis
- Pattern execution results
- Match reasoning (why elements match or don't match)
- Suggestions for improving patterns
- Rejection analysis (why elements didn't match)

**Example Output:**

```
Pattern Analysis
================

Pattern: "w/aws"
Type: workspace
Compiled: workspace pattern matching "aws"

Matched Elements
----------------
✓ Workspace: aws
  Reason: Exact match on workspace name

  Nested Contexts: 3
  Nested Components: 12

Pattern: "c/*-dev"
Type: context
Compiled: context pattern matching "*-dev"

Matched Elements
----------------
✓ Context: aws-cluster-dev
  Reason: Name matches wildcard pattern "*-dev"

✓ Context: gcp-cluster-dev
  Reason: Name matches wildcard pattern "*-dev"

No Matches: 5 contexts
```

## Related Documentation

- [Architecture Overview](./overview.md) - High-level architecture and core concepts
- [Configuration System](./configuration.md) - Configuration structure and examples
- [CLI Reference](../../usage/cli-reference.md) - Complete CLI documentation
- [Pattern Matching Guide](../../usage/pattern-matching.md) - Comprehensive pattern guide
