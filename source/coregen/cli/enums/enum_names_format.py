# enums/names_format.py

import enum


class NamesFormat(str, enum.Enum):
    """
    Enumeration of name-only output formats for detect-changes command.

    Attributes:
        ALL: Show all names (components, contexts, workspaces)
        COMPONENT: Show only component names
        CONTEXT: Show only context names
        WORKSPACE: Show only workspace names
    """

    ALL = "all"
    COMPONENT = "component"
    CONTEXT = "context"
    WORKSPACE = "workspace"
