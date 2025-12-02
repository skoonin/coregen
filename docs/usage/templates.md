# Template Variables Reference Guide

This guide explains how to work with variables in Jinja2 templates within Coregen, including debugging techniques and troubleshooting common issues.

## Available Template Variables

Coregen provides three main namespaces in your Jinja2 templates:

### Understanding Component Type and Namespaces

The `component_type` field in your context configuration (e.g., `component_type: "app"`) determines how components are organized and accessed in templates:

1. **Primary Namespace**: The value of `component_type` becomes a namespace in templates
   - If `component_type: "app"` → access via `{{ app.component_name }}`
   - If `component_type: "service"` → access via `{{ service.component_name }}`
   - If `component_type: "component"` → access via `{{ component.component_name }}` (note: this can be confusing with the current component namespace)

2. **Convenience `app` Namespace**: Regardless of `component_type`, components are always accessible via `{{ app.component_name }}`

3. **Current Component**: The component being processed is available via `{{ component }}` namespace

### 1. `context` - Context Properties

Contains all context-level configuration properties:

```jinja
{{ context.name }}              # Context name (e.g., "dev-cluster")
{{ context.environment }}       # Environment (e.g., "dev", "prod")
{{ context.active }}           # Boolean active status
{{ context.account_id }}       # Account ID
{{ context.region }}           # AWS region (e.g., "us-west-2")
{{ context.region_short }}     # Short region code (e.g., "usw2")
{{ context.commit_dir }}       # Commit directory for components
{{ context.workspace }}        # Workspace name
{{ context.component_type }}   # Component type (e.g., "app")
{{ context.path }}             # Context path
{{ context.config_file_path }} # Full path to context config file
```

### 2. Dynamic Component Type Namespace & `app` Convenience Namespace

Coregen provides component access through two complementary namespaces:

#### Primary Component Type Namespace
The namespace name is determined by the `component_type` field in your context configuration (default: "component"). This becomes the primary namespace for accessing components:
- If `component_type: "app"` → components are in the `app` namespace
- If `component_type: "service"` → components are in the `service` namespace
- If `component_type: "component"` → components are in the `component` namespace

#### The `app` Convenience Namespace
Regardless of the actual `component_type`, Coregen **always** provides an `app` namespace that:
1. **Component Collections**: Contains all components from all component types
2. **Current Component Properties**: When processing a component template, also contains the current component's properties directly

```jinja
<!-- Example 1: When component_type is "app" (most common) -->
<!-- Primary namespace and convenience namespace are the same -->
{{ app.nginx.name }}                    # Component name via primary namespace
{{ app.nginx.config.active }}           # Component active status
{{ app.nginx.config.priority }}         # Component priority

<!-- Example 2: When component_type is "service" -->
<!-- Components are accessible through both namespaces -->
{{ service.nginx.name }}                # Via primary namespace (service)
{{ app.nginx.name }}                    # Via convenience namespace (app)
{{ service.prometheus.config.active }}  # Via primary namespace
{{ app.prometheus.config.active }}      # Via convenience namespace

<!-- Access component variables (works with any namespace) -->
{% if app.prometheus.vars %}
{{ app.prometheus.vars.helm_chart_version }}  # Custom variables
{% endif %}

<!-- IMPORTANT: Current Component Context -->
<!-- When processing a component template, both the primary namespace
     and app namespace contain the current component's properties directly -->

<!-- If component_type is "service": -->
{{ service.name }}                       # Current component's name (via primary)
{{ app.name }}                          # Current component's name (via convenience)
{{ service.config.active }}             # Current component's active status
{{ app.config.active }}                 # Same, via convenience namespace

<!-- Both collection and current component access work simultaneously -->
{{ app['metrics-server'].name }}         # Specific component from collection
{{ app.name }}                          # Current component being processed

<!-- Iterate through all apps -->
{% for app_name, app_data in app.items() %}
Processing app: {{ app_name }}
  Active: {{ app_data.config.active }}
  {% if app_data.vars %}
  Variables:
    {% for var_key, var_value in app_data.vars.items() %}
    {{ var_key }}: {{ var_value }}
    {% endfor %}
  {% endif %}
{% endfor %}
```

**Important Notes**:
- The `app` namespace is **always available** regardless of your `component_type` setting
- When `component_type` is "app", the primary namespace and convenience namespace are identical
- When `component_type` is something else (e.g., "service"), components are accessible through both the primary namespace (`service`) and the convenience namespace (`app`)
- Both namespaces intelligently merge component collections with the current component's properties

### 3. `component` - Current Component

Properties of the component currently being processed:

```jinja
{{ component.name }}                    # Current component name
{{ component.config.active }}           # Current component active status
{{ component.config.priority }}         # Current component priority
{{ component.config.path }}             # Current component path
{{ component.config.for_commit }}       # Whether current component is marked for commit
{{ component.config.required }}         # Whether current component is required

<!-- Access current component variables -->
{% if component.vars %}
{% for var_key, var_value in component.vars.items() %}
{{ var_key }}: {{ var_value }}
{% endfor %}
{% endif %}
```

## Template Examples

### Environment-Specific Configuration

```jinja
# deployment.yaml.j2
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ component.name }}
  namespace: {{ context.environment }}
spec:
  replicas: {% if context.environment == "prod" %}3{% else %}1{% endif %}
  template:
    metadata:
      labels:
        app: {{ component.name }}
        environment: {{ context.environment }}
    spec:
      containers:
      - name: {{ component.name }}
        image: myapp:latest
        env:
        - name: ENVIRONMENT
          value: "{{ context.environment }}"
        {% if context.environment == "prod" %}
        - name: DB_HOST
          value: "prod-db.{{ context.region }}.amazonaws.com"
        {% else %}
        - name: DB_HOST
          value: "dev-db.localhost"
        {% endif %}
```

### Component Dependencies

```jinja
# service.yaml.j2
apiVersion: v1
kind: Service
metadata:
  name: {{ component.name }}
  labels:
    app: {{ component.name }}
    {% if component.config.dependencies %}
    depends-on: {% for dep in component.config.dependencies %}{{ dep.name }}{% if not loop.last %},{% endif %}{% endfor %}
    {% endif %}
spec:
  selector:
    app: {{ component.name }}
  ports:
  - port: 80
    targetPort: 8080
```

### Using Custom Variables

```jinja
# helm-values.yaml.j2
{% if component.vars %}
# Custom component variables
{% for var_key, var_value in component.vars.items() %}
{{ var_key }}: {{ var_value }}
{% endfor %}
{% endif %}

# Context-specific overrides
environment: {{ context.environment }}
region: {{ context.region }}

{% if context.environment == "prod" %}
replicaCount: 3
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
{% else %}
replicaCount: 1
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
{% endif %}
```

### Finding Apps by Name Patterns

```jinja
{# Method 1: Find apps with "prometheus" in the name #}
{% set prometheus_apps = [] %}
{% for app_name, app_data in app.items() %}
  {% if "prometheus" in app_name %}
    {% set _ = prometheus_apps.append(app_data) %}
  {% endif %}
{% endfor %}

{# Now use the prometheus_apps list #}
{% if prometheus_apps %}
  {# Use the first prometheus app found #}
  {% set main_prometheus = prometheus_apps[0] %}

  # Prometheus configuration
  prometheus:
    enabled: true
    name: {{ main_prometheus.name }}
    {% if main_prometheus.vars %}
    helm_chart_version: {{ main_prometheus.vars.helm_chart_version }}
    {% endif %}

  {# Process all prometheus apps #}
  {% for prom_app in prometheus_apps %}
  - component: {{ prom_app.name }}
    active: {{ prom_app.config.active }}
    {% if prom_app.vars %}
    vars:
      {% for key, value in prom_app.vars.items() %}
      {{ key }}: {{ value }}
      {% endfor %}
    {% endif %}
  {% endfor %}
{% else %}
  # No prometheus apps found
  prometheus:
    enabled: false
{% endif %}

{# Method 2: Direct iteration and capture component for later use #}
{% set prometheus_component = namespace() %}
{% for app_name, app_data in app.items() %}
  {% if "prometheus" in app_name %}
    {% set prometheus_component.data = app_data %}
    {% break %}
  {% endif %}
{% endfor %}

{# Now use the captured prometheus component #}
{% if prometheus_component.data %}
# Prometheus component found
resource "helm_release" "prometheus" {
  name       = "{{ prometheus_component.data.name }}"
  chart      = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  {% if prometheus_component.data.vars and prometheus_component.data.vars.crd_chart_version %}
  version    = "{{ prometheus_component.data.vars.crd_chart_version }}"
  {% endif %}
  namespace  = "{{ context.environment }}"

  values = [
    yamlencode({
      prometheus = {
        enabled = {{ prometheus_component.data.config.active | lower }}
      }
    })
  ]
}
{% else %}
# No prometheus component found
{% endif %}

{# Alternative: Simpler direct output approach #}
{% for app_name, app_data in app.items() %}
  {% if "prometheus" in app_name %}
# Found prometheus app: {{ app_name }}
prometheus_{{ app_name.replace('-', '_') }}:
  name: {{ app_data.name }}
  active: {{ app_data.config.active }}
  {% if app_data.vars and app_data.vars.helm_chart_version %}
  version: {{ app_data.vars.helm_chart_version }}
  {% endif %}
  {% endif %}
{% endfor %}

{# Method 3: Check if any prometheus app exists (boolean) #}
{% set has_prometheus = false %}
{% for app_name in app.keys() %}
  {% if "prometheus" in app_name %}
    {% set has_prometheus = true %}
    {% break %}
  {% endif %}
{% endfor %}

{% if has_prometheus %}
# Prometheus monitoring is enabled
monitoring:
  prometheus: true
{% else %}
# No prometheus found - use alternative monitoring
monitoring:
  prometheus: false
  alternative: basic
{% endif %}

{# Method 4: Alternative - Direct access if you know the exact name #}
{% if app.prometheus is defined %}
# Direct prometheus access
prometheus:
  name: {{ app.prometheus.name }}
  active: {{ app.prometheus.config.active }}
{% elif app['prometheus-server'] is defined %}
# Access with hyphenated name
prometheus:
  name: {{ app['prometheus-server'].name }}
  active: {{ app['prometheus-server'].config.active }}
{% endif %}
```

## Debugging Template Variables

### Method 1: View All Available Variables

Create a debug template to see all available variables:

```jinja
=== TEMPLATE VARIABLES DEBUG ===

Context Properties:
{% for key, value in context.items() %}
{{ key }}: {{ value }}
{% endfor %}

Available Components (via app namespace):
{% for component_name, component_data in app.items() %}
{{ component_name }}:
  name: {{ component_data.name }}
  active: {{ component_data.config.active }}
  {% if component_data.vars %}
  variables:
    {% for var_key, var_value in component_data.vars.items() %}
    {{ var_key }}: {{ var_value }}
    {% endfor %}
  {% endif %}
{% endfor %}

{# Also show primary namespace if different from app #}
{% if context.component_type and context.component_type != 'app' %}
Available Components (via {{ context.component_type }} namespace):
{% set primary_ns = _self[context.component_type] %}
{% for component_name, component_data in primary_ns.items() %}
- {{ context.component_type }}.{{ component_name }}
{% endfor %}
{% endif %}

Current Component:
name: {{ component.name }}
{% if component.config %}
config:
  {% for config_key, config_value in component.config.items() %}
  {{ config_key }}: {{ config_value }}
  {% endfor %}
{% endif %}
{% if component.vars %}
variables:
  {% for var_key, var_value in component.vars.items() %}
  {{ var_key }}: {{ var_value }}
  {% endfor %}
{% endif %}

=== END DEBUG ===
```

### Method 2: Check Specific Namespaces

```jinja
<!-- Debug context keys -->
Available context keys:
{% for key in context.keys() %}
- {{ key }}
{% endfor %}

<!-- Debug component keys via app namespace -->
Available components (app namespace):
{% for key in app.keys() %}
- {{ key }}
{% endfor %}

{# Debug primary namespace if different #}
{% if context.component_type and context.component_type != 'app' %}
<!-- Debug component keys via primary namespace -->
Available components ({{ context.component_type }} namespace):
{% set primary_ns = _self[context.component_type] %}
{% for key in primary_ns.keys() %}
- {{ key }}
{% endfor %}
{% endif %}

<!-- Debug component keys -->
Current component properties:
{% for key in component.keys() %}
- {{ key }}
{% endfor %}
```

### Method 3: Conditional Debugging

```jinja
{% if context.environment == "dev" %}
<!-- Only show debug info in dev environment -->
=== DEBUG INFO ===
Context: {{ context.name }}
Environment: {{ context.environment }}
Component: {{ component.name }}
{% if component.vars %}
Component vars: {{ component.vars }}
{% endif %}
=== END DEBUG ===
{% endif %}
```

## Template Context Behavior

### Component Type Namespace Behavior

Coregen's template context system dynamically creates namespaces based on your configuration:

#### How Component Type Becomes a Namespace

1. **Configuration Setting**: The `component_type` field in your context configuration determines the primary namespace name
   ```yaml
   context:
     name: my-context
     component_type: service  # This becomes the namespace name
   ```

2. **Namespace Creation**: Components are then accessible via this namespace:
   ```jinja
   {{ service.nginx.name }}        # Primary namespace matches component_type
   {{ service.postgres.config }}   # All components in the service namespace
   ```

3. **The `app` Convenience Namespace**: Regardless of `component_type`, all components are **also** available via `app`:
   ```jinja
   {{ app.nginx.name }}            # Always works, regardless of component_type
   {{ app.postgres.config }}       # Convenience access
   ```

#### Dual Behavior for Current Component

Both the primary namespace and `app` namespace support dual behavior:

1. **Component Collections**: Access any component by name
2. **Current Component Properties**: When processing a template, the current component's properties merge into both namespaces

#### Example Scenarios

**Scenario 1: When `component_type: "app"` (default for many configs)**
```jinja
<!-- Primary and convenience namespaces are the same -->
{{ app.nginx.name }}              # nginx component from collection
{{ app.name }}                    # Current component being processed
{{ app.prometheus.config }}       # prometheus component from collection
```

**Scenario 2: When `component_type: "service"`**
```jinja
<!-- Components accessible through both namespaces -->
{{ service.nginx.name }}          # Via primary namespace
{{ app.nginx.name }}              # Via convenience namespace (always available)
{{ service.name }}                # Current component via primary
{{ app.name }}                    # Current component via convenience
```

**Scenario 3: Processing the `nginx` component with `component_type: "service"`**
```jinja
<!-- All of these work correctly -->
{{ service.name }}                # Returns "nginx" (current, via primary)
{{ app.name }}                    # Returns "nginx" (current, via convenience)
{{ service.prometheus.name }}     # Returns "prometheus" (collection, via primary)
{{ app['metrics-server'].name }}  # Returns "metrics-server" (collection, via convenience)
```

## Troubleshooting

### Common Issues and Solutions

#### 1. `'vars' is undefined` Error

**Problem**: Trying to use Python's built-in `vars()` function in templates.

**Solution**: Use the specific namespaces provided by Coregen instead:

```jinja
<!-- ❌ This doesn't work -->
{% for key, value in vars().items() %}
{{ key }}: {{ value }}
{% endfor %}

<!-- ✅ Use this instead -->
{% for key, value in context.items() %}
{{ key }}: {{ value }}
{% endfor %}
```

#### 2. `'globals' is undefined` Error

**Problem**: Trying to use Python's built-in `globals()` function.

**Solution**: Access variables through the provided namespaces:

```jinja
<!-- ❌ This doesn't work -->
{{ globals() }}

<!-- ✅ Use this instead -->
Context: {{ context }}
Components (app namespace): {{ app }}
{% if context.component_type and context.component_type != 'app' %}
Components ({{ context.component_type }} namespace): {{ _self[context.component_type] }}
{% endif %}
Current Component: {{ component }}
```

#### 3. Variable Not Found

**Problem**: Cannot access a variable you expect to be available.

**Solution**: Use the debug template to see all available variables, then check the correct namespace:

```jinja
<!-- First, debug to see what's available -->
{% for key in context.keys() %}
- context.{{ key }}
{% endfor %}

<!-- Then access the correct variable -->
{{ context.your_variable_name }}
```

#### 4. Hyphenated Variable Names

**Problem**: YAML keys with hyphens (e.g., `app-name`) cause Jinja errors.

**Solution**: Use bracket notation to access hyphenated keys:

```jinja
<!-- ❌ This doesn't work -->
{{ app.my-app.name }}

<!-- ✅ Use this instead -->
{{ app['my-app'].name }}
```

#### 5. Missing Component Variables

**Problem**: `component.vars` is empty or undefined.

**Solution**: Check if the component has variables defined in the context config:

```jinja
{% if component.vars %}
{% for var_key, var_value in component.vars.items() %}
{{ var_key }}: {{ var_value }}
{% endfor %}
{% else %}
<!-- Component has no custom variables -->
No custom variables defined for {{ component.name }}
{% endif %}
```

### Debugging Commands

Use these Coregen commands to help debug template issues:

```bash
# Test template generation with dry-run
coregen generate "component/your-component" --dry-run --verbose

# View the complete configuration
coregen config view --output yaml

# Check what components match your pattern
coregen get "component/*" --output table

# Test a specific context
coregen generate "component/*" --filter "context.name=your-context"
```

### Advanced Debugging

#### Enable Debug Logging

Set the log level to see detailed processing information:

```bash
export CG_LOG_LEVEL=debug
coregen generate "component/your-component"
```

#### Template Validation

Create a validation template to check variable types:

```jinja
=== VARIABLE TYPE VALIDATION ===

Context type checks:
- context is mapping: {{ context is mapping }}
- app is mapping: {{ app is mapping }}
- component is mapping: {{ component is mapping }}

Required fields check:
- context.name exists: {{ 'name' in context }}
- context.environment exists: {{ 'environment' in context }}
- component.name exists: {{ 'name' in component }}

Variable counts:
- Context properties: {{ context | length }}
- Available components (app namespace): {{ app | length }}
{% if context.component_type and context.component_type != 'app' %}
- Available components ({{ context.component_type }} namespace): {{ _self[context.component_type] | length }}
{% endif %}
- Current component properties: {{ component | length }}

=== END VALIDATION ===
```

## Best Practices

### 1. Use Descriptive Variable Names

```jinja
<!-- ✅ Good -->
{{ context.environment }}
{{ component.name }}
{{ app.database.vars.connection_string }}

<!-- ❌ Avoid -->
{{ ctx.env }}
{{ comp.nm }}
{{ db.conn }}
```

### 2. Handle Missing Variables Gracefully

```jinja
<!-- Check before using optional variables -->
{% if component.vars and 'custom_setting' in component.vars %}
custom_setting: {{ component.vars.custom_setting }}
{% else %}
custom_setting: default_value
{% endif %}
```

### 3. Use Environment-Specific Logic

```jinja
{% if context.environment == "prod" %}
# Production configuration
replicas: 3
monitoring: enabled
{% elif context.environment == "staging" %}
# Staging configuration
replicas: 2
monitoring: enabled
{% else %}
# Development configuration
replicas: 1
monitoring: disabled
{% endif %}
```

### 4. Document Your Template Variables

```jinja
{#
This template generates Kubernetes deployment configurations.

Required variables:
- context.environment: Target environment (dev/staging/prod)
- component.name: Name of the component to deploy
- component.vars.image_tag: Docker image tag to deploy

Optional variables:
- component.vars.replicas: Override default replica count
- component.vars.resources: Override default resource limits
#}

apiVersion: apps/v1
kind: Deployment
# ... rest of template
```

## Related Documentation

- [Quick Start Guide](quick-start.md): Getting started with Coregen
- [Context Values Files Reference](../developer/reference/context-values-files.md): Detailed configuration options
- [CLI Reference](cli-reference.md): All commands and options
