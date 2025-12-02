# Configuration Model Tests

This directory contains tests for the Coregen configuration system. The test suite ensures that the configuration models, validation logic, access mechanisms, and provider functionality are working as expected.

## Overview

The configuration system uses a three-level validation architecture:

1. **Schema Validation**: Fast checks for correct structure and types
2. **Model Validation**: Deeper checks for relationships and business rules
3. **Path Validation**: Environment-specific checks for filesystem state

These tests verify that each level of validation functions correctly and that the models properly enforce the rules defined in the system.

## Test Files

### Model Tests

#### `models/test_components.py`

Tests for the component model classes (`Component`, `ComponentConfig`, and `ComponentDependency`).

**ComponentDependency Tests**:

- Creating dependencies with valid data
- Creating dependencies with all possible fields
- Validation errors for empty name values
- Validation errors for whitespace-only name values

**ComponentConfig Tests**:

- Creating config with default values
- Creating config with custom values
- Validation rule: generated components must be active
- String priority validation handling
- Negative priority validation errors

**Component Tests**:

- Creating a component with valid data
- Creating components with custom fields (extra fields)
- Creating components with specific config values
- Creating components from dictionaries
- Getting component dependencies as list of dictionaries
- Checking if a component has a specific dependency
- Adding dependencies to a component
- Validating extra fields in components
- Validation errors for empty component names

#### `models/test_context.py`

Tests for the `Context` model class.

**Context Tests**:

- Creating contexts with default values
- Creating contexts with custom values
- Getting all components from a context (flattening nested structure)
- Context path property and internal path setting
- Validation of active contexts requiring active components
- Custom fields in context objects

#### `models/test_config.py`

Tests for the `CoregenConfig` model class.

**CoregenConfig Tests**:

- Creating config with valid workspaces
- Validation error when creating with empty workspaces list
- Settings property returns CoregenSettings instance
- Creating with nested workspace, context, and component structure
- Navigating the nested component hierarchy

#### `models/test_settings.py`

Tests for the `CoregenSettings` class.

**CoregenSettings Tests**:

- Singleton pattern returns same instance
- Settings has all expected sections
- Getting flattened dictionary of defaults
- Generating JSON schema for models
- Generating YAML schema for models

#### `models/test_validation.py`

Tests for the `ModelValidator` class.

**ModelValidator Tests**:

- Validating various priority values (valid and invalid)
- Component config validation (generated must be active)
- Context validation (active contexts need active components)
- Validation of extra fields types against allowed types

### Other Configuration Tests

#### `test_access.py`

Tests for the `ConfigAccess` class which provides path-based access to configuration elements.

**ConfigAccess Tests**:

- Finding components by patterns
- Finding contexts by patterns
- Finding workspaces by patterns
- Applying filters to configuration elements
- Navigating the component hierarchy
- Environment-based filtering

#### `test_creator.py`

Tests for the `ConfigCreator` class which creates new configuration dictionaries.

**ConfigCreator Tests**:

- Creating default configuration dictionaries
- Creating customized configuration dictionaries
- Applying default values from settings
- Overriding default values with custom values

#### `test_dictionary_validator.py`

Tests for the `ConfigDictValidator` class which validates raw configuration dictionaries.

**Dictionary Validator Tests**:

- Validating minimal valid configurations
- Validating comprehensive configurations
- Error detection for invalid structure
- Error detection for missing required fields

#### `test_loader.py`

Tests for the `ConfigLoader` class which loads configuration files.

**ConfigLoader Tests**:

- Loading YAML configuration files
- Discovering context configuration files
- Handling file not found errors
- Loading multiple configuration files

#### `test_provider.py`

Tests for the `ConfigurationProvider` class which serves as a facade for the entire configuration system.

**ConfigurationProvider Tests**:

- Loading and processing configurations
- Resolving paths for model instances
- Handling validation errors
- Creating new configurations

## Key Assumptions

1. **Default Values**: Tests assume specific default values as defined in the settings module
2. **Validation Rules**:
   - Generated components must be active
   - Active contexts must have at least one active component
   - Priority must be a non-negative integer or numeric string
   - Name fields cannot be empty or whitespace-only
3. **Structure**:
   - Components are stored in a nested structure: `context.components = { component_type: { component_name: Component } }`
   - Workspaces contain contexts, contexts contain components
4. **Type Handling**:
   - String priority values are preserved as strings
   - Priority value of 9999 is the default
   - Extra fields have specific allowed types (string, int, float, bool, list, dict)
5. **Interaction**:
   - ConfigAccess provides path-based, filtered access to configuration elements
   - ConfigurationProvider coordinates loading, processing, and accessing configurations

## Running the Tests

To run all configuration tests:

```bash
pytest tests/test_config
```

To run a specific test file:

```bash
pytest tests/test_config/models/test_components.py
```

To run with verbose output:

```bash
pytest -v tests/test_config
```
