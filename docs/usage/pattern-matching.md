# Pattern Matching Guide

## Overview

Coregen's pattern matching system enables you to select configuration elements (workspaces, contexts, and components) using flexible pattern expressions. **All patterns require recognized prefixes** - this eliminates ambiguity and provides better error handling.

The system uses a two-phase approach:

1. **Pattern Compilation**: Converting raw patterns into structured specifications

   - Parses the raw pattern string
   - Determines the pattern type (logical or filesystem)
   - Extracts prefixes, segments, and tokens
   - Creates a structured pattern specification

2. **Pattern Execution**: Applying the specifications to match configuration elements
   - Selects the appropriate matcher for the pattern type
   - Applies the specification to the configuration hierarchy
   - Collects matching workspaces, contexts, and components
   - Returns structured results with diagnostic information

## Pattern Types

Coregen uses logical patterns to reference configuration elements using their logical names and relationships. All patterns must start with a prefix indicating the type of element you're targeting.

**Syntax**: `prefix/path/to/element`

**Supported Prefixes**:

- `w/` or `workspace/` - Match workspaces
- `c/` or `context/` - Match contexts
- `cm/` or `component/` - Match components

**Examples**:

```
w/aws                        # Match the AWS workspace and all its contexts & components
workspace/aws                # Same as above, using long form
c/aws-cluster-dev            # Match the aws-cluster-dev context and its components
cm/metrics-server            # Match all metrics-server components across all contexts
component/metrics-server     # Same as above, using long form
```

**Important**: All patterns MUST start with one of these recognized prefixes. Patterns without prefixes will be rejected with an error message.


## Pattern Prefix Filtering

When using the `get` command with patterns, the pattern prefix determines which entities are included in the output. This provides an intuitive way to filter results without needing the `--type` option in most cases.

### How Prefix Filtering Works

The pattern prefix automatically filters parent entities from the output:

- **`w/*` or `workspace/*`** → Returns workspaces with all nested data (no parent filtering needed)
- **`c/*` or `context/*`** → Returns contexts and their components (removes workspace parents)
- **`cm/*` or `component/*`** → Returns only components (removes workspace and context parents)

### Prefix Filtering Examples

#### Workspace Patterns

```bash
# Returns only workspaces with nested contexts and components
coregen get w/*

# Output structure (nested format):
{
  "workspaces": {
    "aws": {
      "contexts": { ... },  # Nested data included
      ...
    }
  }
}
```

#### Context Patterns

```bash
# Returns contexts with their components (no workspaces)
coregen get c/*

# Output structure (nested format):
{
  "contexts": {
    "aws-cluster-01": {
      "components": { ... },  # Nested components included
      ...
    }
  }
}
```

#### Component Patterns

```bash
# Returns only components (no workspaces or contexts)
coregen get cm/*

# Output structure:
components:
  - name: prometheus
    context: aws-cluster-01
    workspace: aws
    config:
      active: true
      dependencies:
      - name: nginx
        path: null
      - name: metrics-server
        path: null
      for_commit: false
      path: common-templates/prometheus
      priority: 0
      required: false
    resolved_paths:
      component_path: /Users/shawnk/git/coregen/test_data/common-templates/prometheus
    vars:
      crd_chart_version: 0.1.0
      helm_chart_version: 0.9.1
```

### Interaction with Format Options

#### Nested Format (Default)

- Returns only the primary entity type based on the pattern prefix
- Includes all nested child data

#### Flat Format

- Returns the primary entity type and its children as separate sections
- Example: `c/* --format-type flat` returns both `contexts` and `components` sections

### Interaction with Type Filtering

The `--type` option provides additional filtering that:

1. Removes BOTH parent and child data
2. Is applied LAST in the processing pipeline

#### Key Differences

- **Pattern prefix**: Removes parent data only, keeps children
- **`--type` option**: Removes both parent and child data

#### Type Filtering Examples

```bash
# Pattern only - contexts with nested components
coregen get c/*
# Result: contexts with their components nested inside

# Pattern + type - contexts without nested components
coregen get c/* --type context
# Result: contexts only, no nested components

# Pattern + flat format + type
coregen get w/* --format-type flat --type workspace
# Result: only workspaces section, no nested contexts or components
```

### Best Practices for Pattern Filtering

1. **Use pattern prefixes** for most filtering needs - they provide intuitive results
2. **Use `--type`** when you need to exclude nested data
3. **Combine with `--format-type flat`** when you need separate sections for each entity type

## Multi-Segment Patterns

Multi-segment patterns allow you to filter results more precisely by specifying additional path segments after the initial pattern. The behavior varies depending on the pattern prefix:

### Workspace Multi-Segment Patterns

For workspace patterns, additional segments act as filters to show only specific contexts within the matched workspaces.

**Syntax**: `w/workspace-name/context-name`

**Example**:
```bash
# Show only the "cluster-prod" context within the "aws" workspace
coregen get w/aws/cluster-prod

# Result: Returns the aws workspace but filtered to show only cluster-prod context
```

### Context Multi-Segment Patterns

For context patterns, additional segments filter to show only contexts that contain the specified component.

**Syntax**: `c/context-name/component-name`

**Example**:
```bash
# Show only contexts named "cluster-dev" that contain a "nginx" component
coregen get c/cluster-dev/nginx

# Result: Returns cluster-dev contexts, but only if they contain nginx component
```

### Component Multi-Segment Patterns

Component patterns only support single segments. Additional segments will result in an error.

**Syntax**: `cm/component-name` (single segment only)

**Example**:
```bash
# Valid: Match all nginx components
coregen get cm/nginx

# Invalid: Will be rejected
coregen get cm/nginx/extra
# Error: Component patterns only support single segment matching
```

### Important Notes

1. **Filtering vs. Navigation**: Multi-segment patterns act as filters, not navigational paths
2. **Pattern Validation**: Invalid multi-segment patterns are rejected with helpful error messages
3. **Wildcard Compatibility**: Wildcards can be used in any segment of multi-segment patterns

## Wildcard Support

Coregen supports powerful glob patterns with two types of wildcards:

### 1. Single Asterisk (`*`)

A single asterisk matches any sequence of characters across all levels of the hierarchy.

**Examples**:

```
w/aws*dev                    # Match workspaces with names ending in "dev"
c/aws-*                      # Match contexts with names starting with "aws-"
cm/*.yaml                    # Match components with names ending in ".yaml"
```

## Pattern Matching Examples

### Workspace Patterns

```bash
# Match a specific workspace
coregen get w/aws --output table

# Match all workspaces with names starting with "a"
coregen get w/a* --output table

# Match a workspace and all its nested elements
coregen get w/aws* --output table
```

### Context Patterns

```bash
# Match a specific context
coregen get c/aws-cluster-dev --output table

# Match all contexts with names containing "cluster"
coregen get c/*cluster* --output table

# Match all contexts under a specific workspace
coregen get w/aws* --filter type=context --output table
```

### Component Patterns

```bash
# Match a specific component across all contexts
coregen get cm/metrics-server --output table

# Match components with names starting with "prom"
coregen get cm/prom* --output table
```


## How Pattern Matching Works

Our pattern matching system follows these steps when matching a pattern:

### Phase 1: Pattern Compilation

1. **Pattern Type Detection**: The system validates that the pattern starts with a recognized prefix (`workspace/`, `context/`, or `component/`). Patterns without valid prefixes are rejected.

2. **Pattern Parsing**: The pattern is parsed into segments and tokens:

   - Segments are the parts between slashes (`/`)
   - Tokens identify wildcard characters (`*`, `**`) and literal strings

3. **Pattern Specification Creation**: A structured `LogicalPatternSpec` is created based on the pattern type and tokens.

### Phase 2: Pattern Execution

1. **Matcher Selection**: The system selects the appropriate matcher for the pattern type:

   - `WorkspaceMatcher` for workspace patterns
   - `ContextMatcher` for context patterns
   - `ComponentMatcher` for component patterns

2. **Hierarchical Matching**: The matcher navigates through the configuration hierarchy (workspaces, contexts, and components)

3. **Result Collection**: The matcher collects all matching elements and organizes them by type:
   - Workspaces
   - Contexts
   - Components

## Pattern Search Consistency

Logical patterns work against the configuration hierarchy, providing consistent behavior regardless of your current directory or filesystem location.

### Why This Matters

- **Consistent Behavior**: Your patterns work the same regardless of your current directory
- **CI/CD Friendly**: Build scripts can run from any directory with predictable results
- **Config File Portability**: Moving your project maintains all pattern relationships
- **No Ambiguity**: Required prefixes eliminate confusion between configuration elements and filesystem paths

## Analyzing Patterns

Use the `check-pattern` command with the `--analyze` flag to see detailed information about how your pattern is processed:

```bash
coregen check-pattern w/aws/** --analyze
```

This will show you:

- The pattern structure and type
- Details about both compilation and execution phases
- Examples of items that matched and why they matched
- Examples of items that didn't match and why they were rejected
- Suggestions for improving your pattern if it doesn't match as expected

## Troubleshooting

### Pattern Doesn't Match Anything

If your pattern doesn't match anything, try:

1. **Use the `check-pattern` command** to analyze your pattern
2. **Verify your pattern has a valid prefix**:
   - All patterns must start with w/, c/, cm/ or workspace/, context/, component/
   - Patterns without prefixes will be rejected
3. **Add wildcards** to make your pattern less specific:
   - Replace specific names with `*`

### Too Many Matches

If your pattern matches too many elements, try:

1. **Make your pattern more specific** by adding more path components
2. **Replace wildcards** with specific names
3. **Utilizing the --filter option**

## Common Pattern Matching Examples

Here are some common pattern matching scenarios and how to solve them:

### Finding All Dev Environments

```bash
# Match all dev contexts across all workspaces
coregen get c/*dev* --output table

# Alternative approach using filters
coregen get c/* --filter environment=dev --output table
```

### Matching Components with Dependencies

```bash
# Find components that depend on metrics-server
coregen get cm/* --filter dependencies.name=metrics-server --output table
```

### Combining Patterns with Filters

```bash
# Match all prometheus components in production environments
coregen get cm/prom* --filter environment=prod --output table

# Find components with specific dependencies
coregen get cm/* --filter "dependencies.name=nginx" --output table
```

## Implementation Details and Standardization

The pattern matching system has been standardized to ensure consistent behavior across all parts of Coregen.

### Unified Pattern Matching Utility

All pattern matching in Coregen uses a standardized implementation found in `common/pattern/utils.py`. This ensures consistent behavior for glob pattern matching across different services and commands.

```python
# The standard pattern matching implementation
from common.pattern.utils import match_path_to_pattern

# Usage
if match_path_to_pattern(path, pattern):
    # Path matches the pattern
```

### Cross-Platform Compatibility

The pattern matching implementation is designed to work consistently across different platforms (Linux and macOS):

- Path separator normalization
- Case sensitivity handling
- Special pattern handling for recursive patterns (`**`)

### Standard Glob Pattern Features

Our pattern matching implementation supports:

1. **Basic Wildcards**: `*` for any characters within a segment
2. **Recursive Wildcards**: `**` for traversing multiple directory levels
3. **Character Classes**: `[abc]` for matching specific characters
4. **Range Expressions**: `[a-z]` for matching character ranges
5. **Negation**: `[!abc]` or `[^abc]` for excluding specific characters
6. **Alternation**: `{a,b,c}` for matching any of the comma-separated patterns

### Special Pattern Handling

- Support for wildcard matching in names and paths
- Proper handling of hierarchical relationships
- Multi-segment patterns for more precise filtering

### Optimized for Performance

The pattern matching implementation is optimized for:

- Fast compilation of patterns (done once per pattern)
- Efficient matching against multiple paths
- Early termination when a match cannot possibly succeed

## Under the Hood

Our standardized pattern matching consists of these key components:

1. **PatternParser**: Parses raw pattern strings into tokens
2. **PatternSpec**: Structured representation of a pattern
3. **Matchers**: Different matcher implementations for each pattern type
4. **PatternMatcher**: Facade that orchestrates the two-phase matching process

The standardization ensures that all commands and services that deal with pattern matching (including `check-pattern`, `get`, `generate`, and `detect-changes`) behave consistently.
