"""Entity type enumeration for filtering output sections."""

import enum


class EntityType(str, enum.Enum):
    """
    Enumeration of entity types for filtering output sections.

    Used by both GET and DETECT-CHANGES commands to filter which types
    of entities should be included in the output.

    Attributes:
        COMPONENT: Include only components
        CONTEXT: Include only contexts
        WORKSPACE: Include only workspaces
    """

    COMPONENT = "component"
    CONTEXT = "context"
    WORKSPACE = "workspace"
