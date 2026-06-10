"""Component ordering helper.

Provides the single place that turns a context's nested ``components`` mapping
into a flat, deployment-ordered ``{component_name: Component}`` dictionary.

Ordering is delegated to :class:`ComponentSorterService` (priority then name).
The grouped dependency validation runs here exactly once per call, operating on
live ``Component`` objects -- no ``model_dump`` round-trips and no quadratic
name re-matching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from coregen.common.component_sorter_service import ComponentSorterService

if TYPE_CHECKING:
    from coregen.config_model.models.components import Component


def order_components(
    components: dict[str, dict[str, Component]],
    *,
    context_name: str,
    workspace: str,
    skip_validation: bool,
) -> dict[str, Component]:
    """Return components flattened and sorted in deployment order.

    Args:
        components: Nested mapping of ``component_type -> name -> Component``.
        context_name: Owning context name (used for sort/validation grouping).
        workspace: Owning workspace name (used for sort/validation grouping).
        skip_validation: When True, skip the grouped dependency validation
            (used for base-branch comparison in detect-changes).

    Returns:
        Ordered ``{component_name: Component}`` dictionary. The sorter reads
        priority, name, and dependencies directly off the live Component
        objects, so no serialization occurs.
    """
    if not isinstance(components, dict):
        return {}

    component_objects: list[Component] = []
    for component_type_dict in components.values():
        if isinstance(component_type_dict, dict):
            component_objects.extend(component_type_dict.values())

    if not component_objects:
        return {}

    # The sorter groups by workspace/context for validation. Populate the real
    # Component.context/.workspace fields (read by the sorter's _get_field
    # fallback) so all components land in one group. These are declared model
    # fields -- ConfigAccess sets them to the same values later -- so this does
    # not leak extra keys into serialization.
    for component in component_objects:
        component.context = context_name
        component.workspace = workspace

    sorter = ComponentSorterService()
    sorted_components = sorter.sort_entities(
        component_objects,
        entity_type="component",
        skip_validation=skip_validation,
    )

    result: dict[str, Component] = {}
    for component in sorted_components:
        result[component.name] = component
    return result
