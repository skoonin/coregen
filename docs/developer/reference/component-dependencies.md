# Component Dependencies Reference

## Overview

Component dependencies in Coregen define which components should always be generated together. When a component declares dependencies, those dependent components will automatically be included in generation operations.

## Purpose

Dependencies serve a single, clear purpose:
- **Ensure related components are always generated together**
- When generating a parent component, all its dependencies are automatically included
- This maintains consistency and prevents partial deployments

## Configuration

Dependencies are configured in the component's configuration:

```yaml
components:
  - name: "monitoring"
    config:
      active: true
      for_commit: true
      dependencies:
        - name: "prometheus-operator"
        - name: "metrics-server"
```

## How Dependencies Work

1. **Name Reference Only**: Dependencies only need the component name
   - Components are already fully defined in their context
   - No need to duplicate paths or configuration
   - Environment is inherited from the context

2. **Generation Behavior**:
   - When `monitoring` is selected for generation
   - Both `prometheus-operator` and `metrics-server` are automatically included
   - This happens regardless of how the parent was selected (pattern, filter, etc.)

3. **Dependency Resolution**:
   - Dependencies are resolved within the same context
   - The system looks up the component by name in the current context
   - Uses that component's full configuration for generation

## Example Usage

### Simple Dependencies

```yaml
context:
  name: "aws-cluster-prod"
  environment: "prod"
  components:
    - name: "nginx"
      config:
        active: true
        dependencies:
          - name: "nginx-config"  # Config maps
          - name: "nginx-certs"   # TLS certificates

    - name: "nginx-config"
      config:
        active: true

    - name: "nginx-certs"
      config:
        active: true
```

When generating `nginx`, both `nginx-config` and `nginx-certs` are automatically included.

### Service Stack Dependencies

```yaml
components:
  - name: "api-service"
    config:
      active: true
      dependencies:
        - name: "database"
        - name: "cache"
        - name: "message-queue"
```

Generating `api-service` ensures all required backend services are also generated.

## Validation Rules

Coregen enforces strict validation rules to ensure dependency configurations are valid and deployable:

> **Note:** These validation rules are ALWAYS enforced and cannot be disabled. They ensure safe deployment ordering and prevent configuration errors.

### Rule 1: No Duplicate Priorities Within a Context

Components within the same context cannot have duplicate priority values.

```yaml
# ❌ INVALID
components:
  - name: app
    config:
      priority: 1
  - name: service
    config:
      priority: 1  # Error: Duplicate priority
```

### Rule 2: Priority Components Cannot Depend on Null Priority

Priority components deploy before null-priority components, so they cannot depend on components that deploy later.

```yaml
# ❌ INVALID
components:
  - name: networking
    config:
      priority: 0
      dependencies: [monitoring]  # Error: priority→null dependency

  - name: monitoring
    config:
      priority: null

# ✅ VALID - Reverse the dependency or assign priority
components:
  - name: networking
    config:
      priority: 0

  - name: monitoring
    config:
      priority: null
      dependencies: [networking]  # OK: null→priority is allowed
```

### Rule 3: Dependencies Must Have Equal or Better Priority

Dependencies must have the same priority or a lower priority number (better priority).

```yaml
# ❌ INVALID
components:
  - name: api
    config:
      priority: 1
      dependencies: [database]

  - name: database
    config:
      priority: 5  # Error: Higher number = later deployment

# ✅ VALID
components:
  - name: api
    config:
      priority: 5
      dependencies: [database]

  - name: database
    config:
      priority: 1  # Lower number = earlier deployment
```

### Rule 4: Null Priority Components Cannot Depend on Other Null Components

Null-priority components have no defined ordering, so they cannot depend on each other.

```yaml
# ❌ INVALID
components:
  - name: monitoring
    config:
      priority: null
      dependencies: [logging]  # Error: null→null dependency

  - name: logging
    config:
      priority: null

# ✅ VALID - Remove dependency or assign priorities
components:
  - name: monitoring
    config:
      priority: null

  - name: logging
    config:
      priority: null
  # No dependencies between them
```

### Rule 5: No Circular Dependencies

Circular dependency chains are detected and rejected.

```yaml
# ❌ INVALID
components:
  - name: api
    config:
      priority: 1
      dependencies: [cache]

  - name: cache
    config:
      priority: 1
      dependencies: [api]  # Error: Circular dependency

# ✅ VALID
components:
  - name: api
    config:
      priority: 1
      dependencies: [cache]

  - name: cache
    config:
      priority: 1
  # One-way dependency only
```

## Important Notes

1. **Dependencies are NOT**:
   - Build dependencies (handled by your build system)
   - Taken into account when sorting components by priority
   - Runtime dependencies (handled by your orchestrator)
   - Package dependencies (handled by package managers)

2. **Dependencies ARE**:
   - Generation-time groupings
   - Ensuring related configs/templates are processed together
   - Maintaining deployment consistency
   - Subject to strict validation rules for safe deployment

## Deployment Order and Priority

Priority values determine deployment order:

- **Priority 0**: Deploys first (foundation components)
- **Priority 1, 2, 3, ...**: Deploy sequentially in order
- **Priority null**: Deploys last, all in parallel (alphabetically sorted)

```yaml
components:
  - name: networking
    config:
      priority: 0  # Deploys first

  - name: database
    config:
      priority: 1  # Deploys after networking

  - name: api
    config:
      priority: 2  # Deploys after database
      dependencies: [database]

  - name: monitoring
    config:
      priority: null  # Deploys last, in parallel with logging
      dependencies: [database]

  - name: logging
    config:
      priority: null  # Deploys last, in parallel with monitoring
      dependencies: [database]
```

**Deployment sequence**:
1. Priority 0 components (sequential)
2. Priority 1 components (sequential)
3. Priority 2 components (sequential)
4. All null-priority components (parallel, alphabetically sorted)

## Best Practices

1. **Assign Priorities Wisely**:
   - Use priority 0 for foundation components (networking, storage)
   - Use priority 1-5 for services and applications
   - Use null priority for optional components (monitoring, logging)

2. **Follow the Rules**:
   - Priority components can only depend on priority components with equal/better priority
   - Null components can depend on priority components (but not other null components)
   - No circular dependencies

3. **Keep It Simple**: Only declare direct dependencies

4. **Avoid Deep Chains**: Prefer flat dependency structures

5. **Group Related Components**: Use dependencies for tightly coupled configs

6. **Document Why**: Add comments explaining dependency relationships

```yaml
components:
  - name: "app"
    config:
      priority: 5
      dependencies:
        # App requires these configs to be generated together
        - name: "app-config"      # Configuration maps
        - name: "app-secrets"     # Secret management
        - name: "app-rbac"        # RBAC policies
```

## Migration from Complex Dependencies

If you previously used complex dependency definitions with paths and environments:

**Before**:
```yaml
dependencies:
  - name: "nginx"
    path: "common-templates/nginx"
    environment: "prod"  # No longer needed
```

**After**:
```yaml
dependencies:
  - name: "nginx"  # Simple name reference
```

The component's path and configuration are already defined where the component is declared. The environment comes from the context, not individual dependencies.
