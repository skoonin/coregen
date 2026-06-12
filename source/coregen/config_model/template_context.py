"""
Template context adapter for configuration data.

This module provides adapters that transform configuration data into formats
suitable for template rendering. It flattens nested structures and provides
contextual views of configuration.

When rendering a template for a specific context

```
def render_template_for_context(context, template_path):
    # Create adapter
    adapter = TemplateContextAdapter(context, context_type=context.context_type)

    # Load template
    with open(template_path) as f:
        template_content = f.read()

    # Render template with adapter
    template = jinja2.Template(template_content)
    rendered = template.render(**adapter.to_dict())

    return rendered
```
"""

from typing import Any

from coregen.config_model.models.components import Component
from coregen.config_model.models.context import Context


class TemplateContextAdapter:
    """
    Adapts a Context model into a simplified view for templates.

    This class takes a Context from the configuration and transforms it
    into a flattened structure suitable for template rendering, where:

    1. Context properties are accessible directly via context_type (e.g., {{ cluster.name }})
    2. Components are accessible via component_type (e.g., {{ apps.nginx.name }})

    Example template usage:
    {{ cluster.name }}                # Context name via context_type
    {{ cluster.environment }}         # Context environment
    {{ apps.nginx.name }}             # Component name via component_type
    {{ apps.nginx.config.active }}    # Component config property

    Note on hyphenated keys:
    While YAML supports hyphens in keys (e.g., aws-cluster, aws-app),
    Jinja does not support hyphens in variable names.
    We provide an error in the Generator class for this.

    """

    def __init__(
        self,
        context: Context,
        context_type: str | None = None,
        current_component: Component | None = None,
    ):
        """
        Initialize the adapter with a context object.

        Args:
            context: The Context object to adapt
            context_type: Optional context type name override
            current_component: Optional current component being processed
        """
        self._context = context
        self._current_component = current_component

        # Use provided context_type or get it from context if available
        context_context_type = getattr(context, "context_type", None)
        self._context_type = context_type or context_context_type or "context"

        # Initialize namespaces
        self._init_namespaces()

    def _init_namespaces(self) -> None:
        """Initialize namespaces based on context and component types."""
        context = self._context

        # Create a namespace for the context using its context_type
        # Use model_dump() to get all fields including extra fields
        context_dict = context.model_dump(exclude_defaults=False)

        # Build context namespace with all properties except components and internal fields
        context_ns = {}
        for key, value in context_dict.items():
            if key != "components" and not key.startswith("_"):
                context_ns[key] = value

        # Ensure path is included if available
        if hasattr(context, "path") and context.path:
            context_ns["path"] = context.path

        # Add the context namespace to this object using the context_type
        setattr(self, self._context_type, context_ns)

        # For each component type (e.g., "apps")
        for component_type, components in context.components.items():
            # Create a namespace for this component type
            component_ns = {}

            # Add each component to the namespace
            for component_name, component in components.items():
                component_ns[component_name] = component

            # Add the namespace to this object
            setattr(self, component_type, component_ns)

            # Duplicate component keys to app namespace for template convenience
            # This allows templates to use either {{ component_type.name }} or {{ app.name }}
            if component_type != "app":
                # Create or get the app namespace
                if not hasattr(self, "app"):
                    setattr(self, "app", {})
                app_ns = getattr(self, "app")

                # Add all components from this component_type to the app namespace
                for component_name, component in components.items():
                    app_ns[component_name] = component

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the template context to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the template context
        """
        result = {}
        for attr_name in dir(self):
            if not attr_name.startswith("_") and not callable(getattr(self, attr_name)):
                result[attr_name] = getattr(self, attr_name)

        # Add current component context if provided
        if self._current_component:
            # Add the specific component being generated
            component_data = (
                self._current_component.model_dump(exclude_defaults=False)
                if hasattr(self._current_component, "model_dump")
                else self._current_component.dict(exclude_defaults=False)
            )
            result["component"] = component_data

            # Check if there's already an "app" namespace with component collections
            if "app" in result and isinstance(result["app"], dict):
                # Preserve the existing app namespace (component collections)
                # and also add current component properties directly to app
                # This allows both {{ app['metrics-server'].name }} (collections)
                # and {{ app.name }} (current component properties)
                existing_app = result["app"].copy()

                # Add current component properties to the app namespace
                for key, value in component_data.items():
                    existing_app[key] = value

                result["app"] = existing_app
            else:
                # No existing app namespace, just use component data
                result["app"] = component_data.copy()

        return result


def create_template_context(context: Context) -> dict[str, Any]:
    """
    Create a template context dictionary from a Context object.

    This is a convenience function for template rendering that flattens the context
    structure and makes it suitable for use with template engines like Jinja2.

    Args:
        context: The Context object to create a template context for

    Returns:
        Dict[str, Any]: Dictionary suitable for template rendering
    """
    adapter = TemplateContextAdapter(context)
    return adapter.to_dict()
