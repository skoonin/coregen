# Coregen Configuration Model Guide

## Overview

Coregen uses Pydantic models for configuration validation and processing. The model system follows a three-level validation architecture:

1. **Schema Validation**: Fast checks for correct structure and types
2. **Model Validation**: Deeper checks for relationships and business rules
3. **Path Validation**: Environment-specific checks for filesystem state

## Model Architecture

The configuration model is organized hierarchically:

```
CoregenConfig
└── WorkspaceConfig[]
    └── Context{}
        └── Component{}
```

- `CoregenConfig`: Root configuration containing workspaces
- `WorkspaceConfig`: Workspace configuration with contexts
- `Context`: Context configuration with environment and components
- `Component`: Component definition with configuration settings
- `ComponentConfig`: Component configuration settings
- `ComponentDependency`: Component dependency definition
- `CoregenSettings`: Global config settings with defaults

## Key Files and Responsibilities

The configuration model is split across multiple files for maintainability:

- **`/source/coregen/config_model/models/__init__.py`**: Entry point for all models
- **`/source/coregen/config_model/models/config.py`**: Root `CoregenConfig` model and re-exports
- **`/source/coregen/config_model/models/settings.py`**: Default settings with `CoregenSettings` model
- **`/source/coregen/config_model/models/workspace.py`**: `WorkspaceConfig` model
- **`/source/coregen/config_model/models/context.py`**: `Context` model
- **`/source/coregen/config_model/models/components.py`**: `Component` and `ComponentConfig` models
- **`/source/coregen/config_model/models/validation.py`**: Shared validation logic

## Support Services

The models are supported by several service modules:

- **`/source/coregen/config_model/loader.py`**: Loads configuration files
- **`/source/coregen/config_model/processor.py`**: Processes raw dictionaries into model instances
- **`/source/coregen/config_model/creator.py`**: Creates new configuration dictionaries
- **`/source/coregen/config_model/access.py`**: Provides path-based access to configuration
- **`/source/coregen/config_model/dictionary_validator.py`**: Pre-validates raw dictionaries
- **`/source/coregen/config_model/template_context.py`**: Handles template variable substitution
- **`/source/coregen/common/path_service.py`**: Manages paths without modifying models
- **`/source/coregen/common/path_resolver.py`**: Low-level path resolution

## Configuration Models in Detail

### CoregenConfig

The root configuration model containing all workspaces:

```python
class CoregenConfig(BaseModel):
    """Root configuration containing workspaces"""
    model_config = ConfigDict(extra="forbid")

    workspaces: List[WorkspaceConfig] = Field(
        ...,
        description="Program-required: List of at least one workspace configuration"
    )
```

### WorkspaceConfig

Workspace configuration model with contexts:

```python
class WorkspaceConfig(BaseModel):
    """Workspace configuration model"""
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Required: Workspace name")
    context_type: str = Field(default="context", description="Type name for contexts")
    context_config_files: List[str] = Field(
        default_factory=lambda: CoregenSettings().config_pattern,
        description="Patterns for discovering context config files"
    )
    # Path fields
    workspace_dir: str = Field(default="", description="Path to workspace directory")
    archive_dir: str = Field(default="archive", description="Path to archive directory")
    output_dir: str = Field(default="output", description="Path to output directory")
    # Supports nested contexts
    contexts: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Dictionary of context types to dictionaries of contexts"
    )
```

**Reserved Keywords**: The `context_type` field cannot be set to `"contexts"` as this conflicts with the model's `contexts` field and will cause configuration validation to fail.

### Context

Context configuration model with components:

```python
class Context(BaseModel):
    """Context configuration model"""
    model_config = ConfigDict(extra="allow")

    # Required fields
    name: str = Field(..., description="Required: Context name")
    environment: str = Field(..., description="Required: Environment this context belongs to")

    # Processing flags
    active: bool = Field(
        default_factory=lambda: CoregenSettings().active,
        description="Whether this context should be processed"
    )

    # Path fields
    internal_path: str = Field(
        default="",
        description="Computed context path (read-only, not user-settable)"
    )
    commit_dir: str = Field(
        default_factory=lambda: CoregenSettings().commit_dir,
        description="Directory for components marked for commit"
    )

    # Component definition
    component_type: str = Field(
        default_factory=lambda: CoregenSettings().component_type,
        description="Type name for components in this context"
    )

    # Components collection - nested dictionary structure
    # components: { component_type: { component_name: Component } }
    components: Dict[str, Dict[str, Component]] = Field(
        default_factory=dict,
        description="Dictionary of component types to dictionaries of components"
    )
```

**Reserved Keywords**: The `component_type` field cannot be set to `"components"` as this conflicts with the model's `components` field and will cause configuration validation to fail.

### Context Additional Fields

The Context model includes several computed and inherited fields not shown in the basic definition:

| Field          | Type            | Source    | Description                                 |
|----------------|-----------------|-----------|---------------------------------------------|
| workspace      | WorkspaceConfig | Reference | Reference to parent workspace               |
| workspace_ref  | WorkspaceConfig | Reference | Alias for workspace                         |
| archive_dir    | string          | Inherited | Inherited from workspace.archive_dir        |
| output_dir     | string          | Inherited | Inherited from workspace.output_dir         |
| skip_validation| bool            | Config    | Skip path validation for this context       |

These fields are set automatically during configuration processing and provide convenient access to workspace-level settings.

### Component

Component configuration model:

```python
class Component(BaseModel):
    """Component configuration model"""
    model_config = ConfigDict(extra="allow")

    # Required fields
    name: str = Field(..., description="Required: Component name")

    # Component configuration
    config: ComponentConfig = Field(
        default_factory=ComponentConfig,
        description="Component configuration settings"
    )
```

### ComponentConfig

Component configuration settings:

```python
class ComponentConfig(BaseModel):
    """Component configuration settings"""
    model_config = ConfigDict(extra="allow")

    # Processing flags
    active: bool = Field(
        default_factory=lambda: CoregenSettings().active,
        description="Whether this component is active and should be processed"
    )
    for_commit: bool = Field(
        default_factory=lambda: CoregenSettings().for_commit,
        description="Whether this component should be marked for commit"
    )
    required: bool = Field(
        default_factory=lambda: CoregenSettings().required,
        description="Whether this component is required for other components"
    )

    # Processing metadata
    priority: Optional[int] = Field(
        default=None,
        description="Component priority for ordering operations"
    )

    # Path configuration
    path: str = Field(
        default="",
        description="Custom path to component directory"
    )

    # Dependencies
    dependencies: List[ComponentDependency] = Field(
        default_factory=list,
        description="List of component dependencies that will be generated together"
    )
```

### ComponentDependency

Dependency definition with name and optional path:

```python
class ComponentDependency(BaseModel):
    """Component dependency definition"""
    name: str = Field(description="Name of the dependent component")
    path: str = Field(default="", description="Path to dependency directory")
```

| Field | Type   | Required | Default  | Description                           |
|-------|--------|----------|----------|---------------------------------------|
| name  | string | yes      | -        | Name of dependent component           |
| path  | string | no       | `${name}`| Path to dependency directory          |

Dependencies ensure that related components are always generated together. When a component with dependencies is selected for generation, all its dependencies are automatically included. See [Component Dependencies Reference](../reference/component-dependencies.md) for detailed usage.

### CoregenSettings

Global settings with defaults using nested structure:

```python
class CoregenSettings(BaseSettings):
    """Global settings with defaults for the application"""
    model_config = SettingsConfigDict(env_prefix="COREGEN_")

    component: ComponentDefaults = ComponentDefaults()
    context: ContextDefaults = ContextDefaults()
    workspace: WorkspaceDefaults = WorkspaceDefaults()
```

**Access Patterns:**

```python
# Access component defaults (NOT flat structure)
settings.component.active       # NOT settings.active
settings.component.for_commit   # NOT settings.for_commit
settings.component.type         # NOT settings.component_type

# Access context defaults
settings.context.type           # context type default

# Access workspace defaults
settings.workspace.name         # workspace name default
```

This nested structure keeps related defaults organized and namespaced.

## Component Sorting

Components within a context are automatically sorted by:
1. **Priority** (null priority last): 0 → 1 → 2 → ... → null
2. **Dependencies** (dependencies before dependents): Dependencies are resolved to ensure components are processed before their dependents
3. **Name** (alphabetically): When priority and dependencies are equal, sort by name

This ensures components are processed in the correct order during generation.

**Example:**
```python
# Components will be sorted as:
# 1. database (priority: 0)
# 2. auth (priority: 1, depends on database)
# 3. api (priority: 1, depends on database)
# 4. frontend (priority: 2, depends on api)
# 5. monitoring (priority: null, depends on api)
```

## Field Inheritance

Contexts inherit certain fields from their parent workspace:
- **archive_dir**: Falls back to workspace.archive_dir if not set
- **output_dir**: Falls back to workspace.output_dir if not set

This allows workspace-level defaults while permitting context overrides.

**Example:**
```yaml
workspaces:
  - name: aws
    archive_dir: archive    # Workspace default
    output_dir: output      # Workspace default
    context:
      - name: dev
        # Inherits archive_dir and output_dir from workspace
      - name: prod
        output_dir: prod-output  # Overrides workspace default
        # Still inherits archive_dir from workspace
```

## Validation Rules

### Component Names
- Must be unique within a context across all component types
- Cannot be empty strings
- Must follow valid identifier patterns

### Dependencies
- Active components can depend on active or inactive components
- Inactive components can only depend on other inactive components
- Cannot have circular dependency chains
- Dependencies must reference existing components in the same context

### Priority Validation
- No duplicate priority values within the same context
- Priority components cannot depend on null-priority components
- Null-priority components cannot depend on other null-priority components
- Dependencies must have equal or better priority (lower number)

**Example Validation:**
```yaml
# Valid configuration
component:
  - name: database
    config:
      priority: 0
      active: true
  - name: api
    config:
      priority: 1
      active: true
      dependencies:
        - name: database  # Valid: depends on lower priority (0)

# Invalid configuration
component:
  - name: api
    config:
      priority: 0
      active: true
      dependencies:
        - name: frontend  # Invalid: priority 0 cannot depend on priority 1
  - name: frontend
    config:
      priority: 1
      active: true
```

## How to Add New Fields

### Adding a New Field to an Existing Model

1. **Identify the target model** in the appropriate file (e.g., `workspace.py` for `WorkspaceConfig`)
2. **Add the field definition** with type annotation and a `Field` descriptor
3. **Add validation** if needed using Pydantic's validators
4. **Update any imports** if the field uses types from other modules

Example:

```python
# In source/coregen/config_model/models/workspace.py
from pydantic import Field
from typing import Optional

# Add to the WorkspaceConfig class:
my_new_field: Optional[str] = Field(
    None,
    description="Description of my new field"
)
```

### Adding Default Values to Settings

1. **Open `settings.py`** which contains the `CoregenSettings` class
2. **Add a new field** with a default value in the appropriate section
3. **Add documentation** in the Field descriptor

Example:

```python
# In source/coregen/config_model/models/settings.py
my_setting: str = Field(
    "default_value",
    description="Description of my new setting"
)
```

### Adding a New Configuration Type

For a completely new configuration element type:

1. **Create a new model class** in the appropriate file or create a new file
2. **Update `__init__.py`** to export the new model
3. **Update `config.py`** if this model should be part of the main export
4. **Add any needed validation** in the model or in `validation.py`
5. **Update any services** that need to handle the new model type

## Complete Working Example: Adding a Default Workspace Name

Here's a complete example of adding a new `workspace_name` default setting that's used by `WorkspaceConfig`:

1. **Step 1: Add the default value to CoregenSettings in `settings.py`**:

```python
# In source/coregen/config_model/models/settings.py
workspace_name: str = Field(
    "workspace-01",
    description="Default workspace name when creating a new configuration"
)
```

2. **Step 2: Update the model that should use this default in `workspace.py`**:

```python
# In source/coregen/config_model/models/workspace.py
# Change from a required field with no default:
name: str = Field(..., description="Required: Workspace name")

# To a field that uses the default from settings:
name: str = Field(
    default_factory=lambda: CoregenSettings().workspace_name,
    description="Workspace name, defaults to workspace_name in settings"
)
```

3. **Step 3: The field is available throughout the system**:
   - It will be used when creating new workspaces with no explicit name
   - It can be referenced by other components that need the default value
   - The `default_factory=lambda:` pattern ensures the default is evaluated when needed

This pattern keeps all default values centralized in `CoregenSettings` while allowing individual models to use them through `default_factory` functions.

## Custom Fields in Workspaces, Contexts, and Components

Workspaces, contexts, and components all support additional custom key-value pairs beyond their standard fields:

### Configuration Models Supporting Custom Fields

```python
# These models have model_config = ConfigDict(extra="allow") set:
WorkspaceConfig    # in workspace.py
Context            # in context.py
Component          # in components.py
```

### Example YAML Configuration with Custom Fields

```yaml
# Custom fields in a workspace
name: aws
context_type: account
my_workspace_field: value        # Custom field
aws_account_id: "123456789012"   # Custom field

# Custom fields in a context
name: dev
environment: development
active: true
my_context_field: value          # Custom field
region: "us-west-2"              # Custom field

# Custom fields in a component
name: vpc
config:
  active: true
my_component_field: value        # Custom field
cidr_block: "10.0.0.0/16"        # Custom field
```

### Accessing Custom Fields

Custom fields are accessible directly as attributes:

```python
workspace = config_access.get_workspace("aws")
aws_account_id = workspace.aws_account_id  # Accessing custom field

context = config_access.get_context("aws", "dev")
region = context.region  # Accessing custom field

component = config_access.get_component("aws", "dev", "vpc")
cidr_block = component.cidr_block  # Accessing custom field
```

## Reserved Keywords and Validation

### Reserved Keywords

Certain field values are reserved and cannot be used as type names because they conflict with model field names:

- **`context_type` cannot be `"contexts"`**: The `WorkspaceConfig` model has a `contexts` field that would conflict with this type name
- **`component_type` cannot be `"components"`**: The `Context` model has a `components` field that would conflict with this type name

### Global Uniqueness Requirements

As of the current implementation, these names must be unique globally across the entire configuration:

- **Context names must be globally unique**: Context names cannot be duplicated across different workspaces. Each context must have a unique name throughout the entire configuration.
- **Workspace names must be globally unique**: All workspace names must be unique.
- **Component names must be unique within each context**: Component names must be unique within their parent context across all component types.

When these reserved keywords or uniqueness rules are violated, the system will fail with a clear validation error:

```bash
# This will fail with a validation error:
workspaces:
  - name: example
    context_type: contexts  # ✗ Reserved keyword

# This will also fail:
cluster:
  name: example
  component_type: components  # ✗ Reserved keyword

# This will fail due to duplicate context names across workspaces:
workspaces:
  - name: aws
    cluster:
      - name: dev-cluster  # ✗ Context name repeated
  - name: gcp
    cluster:
      - name: dev-cluster  # ✗ Same context name in different workspace
```

### Valid Alternative Names

Use descriptive type names that don't conflict with reserved keywords:

```yaml
# ✓ Valid workspace configuration:
workspaces:
  - name: example
    context_type: context     # ✓ Default, recommended
    # or
    context_type: cluster     # ✓ Alternative
    # or
    context_type: environment # ✓ Another alternative
    # or
    context_type: account     # ✓ Another alternative

# ✓ Valid context configuration:
context:
  name: example
  component_type: component  # ✓ Default, recommended
  # or
  component_type: service    # ✓ Alternative
  # or
  component_type: app        # ✓ Another alternative
```

## Validation in the Configuration Model

### When to Add Validation

Add validation in these scenarios:

1. **Type Validation**: When a field must be a specific type or format (handled automatically by Pydantic)
2. **Relationship Validation**: When fields must relate to each other in specific ways
3. **Business Rule Validation**: When domain-specific rules must be enforced
4. **Consistency Checks**: When values must be consistent across different parts of the configuration

### Types of Validators

#### 1. Field-Level Validators

Use `field_validator` for validating a single field:

```python
@field_validator('priority')
def validate_priority(cls, value: Optional[int]) -> Optional[int]:
    """Validate component priority."""
    if value is None:
        return None
    if value < 0:
        raise ValueError("Priority must be a non-negative integer")
    return value
```

#### 2. Model-Level Validators

Use `model_validator` for validating multiple fields together:

```python
@model_validator(mode='after')
def validate_context(self) -> 'Context':
    """Validate context configuration."""
    # Check if active context has active components
    if self.active:
        has_active = False
        for component_dict in self.components.values():
            for component in component_dict.values():
                if component.config.active:
                    has_active = True
                    break
        if not has_active:
            raise ValueError("Active context must have at least one active component")
    return self
```

#### 3. External Validation

For complex validation involving the filesystem or external state, use separate validator classes:

```python
# In dictionary_validator.py
def validate_config(self, config_dict: Dict[str, Any]) -> List[str]:
    """Validate a configuration dictionary and return validation errors."""
    errors = []

    # Validate workspaces
    try:
        self._validate_workspaces(config_dict)
    except ValueError as e:
        errors.append(str(e))

    return errors
```

### Adding a New Validator

To add a new validator:

1. **Identify where it belongs**:

   - Field-specific validation: `@field_validator` in the model class
   - Cross-field validation: `@model_validator` in the model class
   - Cross-model validation: Use the `ModelValidator` class in `validation.py`
   - Raw dictionary validation: Use the `ConfigDictValidator` class

2. **Implement the validator**:

```python
# Example: Adding validation for a new field in workspace.py
@field_validator('my_new_field')
def validate_my_new_field(cls, value: str) -> str:
    """Validate that my_new_field is formatted correctly."""
    if value and not value.startswith('prefix-'):
        raise ValueError("my_new_field must start with 'prefix-'")
    return value
```

3. **For complex validation**, add a method to `ModelValidator` in `validation.py`:

```python
@classmethod
def validate_my_complex_rule(cls, workspace: WorkspaceConfig, context: Context) -> None:
    """Validate complex relationship between workspace and context."""
    if workspace.my_setting and context.other_setting:
        if workspace.my_setting != context.other_setting:
            raise ValueError("workspace.my_setting must match context.other_setting")
```

### Best Practices for Validation

1. **Keep validators focused**: Each validator should check one aspect of the model
2. **Provide clear error messages**: Include field names and what went wrong
3. **Return the value**: Always return the validated value (possibly modified)
4. **Handle None values**: Check if optional fields are None before validating
5. **Use class methods**: For field validators, use `@classmethod` (Pydantic v2 requirement)

## Configuration Access Layer

The `ConfigAccess` class provides a high-level API for accessing configuration elements:

```python
class ConfigAccess:
    """Main API for accessing processed configuration."""

    def get(self, path: str) -> Any:
        """Get configuration element by path."""
        # Implementation details...

    def find_contexts(self, pattern: str = "*/*", **filters) -> List[Context]:
        """Find contexts matching pattern and filters."""
        # Implementation details...

    def find_components(self, pattern: str = "*/*/*", **filters) -> List[Component]:
        """Find components matching pattern and filters."""
        # Implementation details...

    def get_workspace(self, workspace_name: str) -> WorkspaceConfig:
        """Get a specific workspace by name."""
        # Implementation details...

    def get_context(self, workspace_name: str, context_name: str) -> Context:
        """Get a specific context by workspace and context name."""
        # Implementation details...

    def get_component(self, workspace_name: str, context_name: str, component_name: str) -> Component:
        """Get a specific component by workspace, context, and component name."""
        # Implementation details...
```

### Using the ConfigAccess API

```python
# Get a specific element by path
workspace = config_access.get("aws")
context = config_access.get("aws/dev/cluster-01")
component = config_access.get("aws/dev/cluster-01/nginx")

# Find elements matching patterns
dev_contexts = config_access.find_contexts("*/dev/*")
nginx_components = config_access.find_components("*/*/nginx")

# Find elements with filters
active_components = config_access.find_components(active=True)
prod_contexts = config_access.find_contexts(environment="prod")

# Direct access methods
workspace = config_access.get_workspace("aws")
context = config_access.get_context("aws", "dev")
component = config_access.get_component("aws", "dev", "nginx")
```

## Working with Path Resolution

Path resolution is intentionally separated from models:

1. Models focus on data validation and structure
2. `PathService` handles all path resolution logic
3. `PathResolver` handles low-level path operations

When adding new path-related fields, make sure they are properly validated but rely on the path services for actual resolution:

```python
# In a service class:
def get_component_path(self, workspace_name: str, context_name: str, component_name: str) -> Path:
    """Get the absolute path to a component."""
    # Use PathService for path resolution
    return self.path_service.get_component_path(workspace_name, context_name, component_name)
```

## Template Context

The `TemplateContext` class provides a specialized adapter for template rendering:

```python
class TemplateContext:
    """Adapter for template rendering with context-specific data."""

    def __init__(self, context: Context, config_access: ConfigAccess):
        """Initialize with a context and config access."""
        # Implementation details...

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for template rendering."""
        # Implementation details...

    def get_component_dict(self, component_name: str) -> Dict[str, Any]:
        """Get component data as a dictionary."""
        # Implementation details...
```

This class simplifies template variable access by creating a namespace-like structure that matches the context and component names instead of requiring the full path.

## Common Patterns

1. **Default factory functions** for consistent defaults:

   ```python
   field: str = Field(
       default_factory=lambda: CoregenSettings().field_name,
       description="Description"
   )
   ```

2. **Property methods** for derived values:

   ```python
   @property
   def some_property(self) -> str:
       return self._compute_value()
   ```

3. **Helper methods** for common operations:
   ```python
   def get_all_components(self) -> Dict[str, Component]:
       # Flatten nested component dictionaries
       result = {}
       for component_type, components in self.components.items():
           result.update(components)
       return result
   ```

## References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Core Architecture Guide](overview.md)
- [CLI Reference Guide](../../usage/cli-reference.md)
