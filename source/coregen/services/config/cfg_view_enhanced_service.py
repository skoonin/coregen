"""
Enhanced configuration view service for Coregen.

Provides an enhanced view combining hierarchical structure with resolved paths
and default values for configuration objects.
"""

import copy
from pathlib import Path
from typing import Any

from coregen.config_model.models.config import CoregenConfig
from coregen.config_model.provider import ConfigurationProvider
from coregen.services.config.cfg_view_base_service import ConfigViewBaseService


class ConfigEnhancedViewService(ConfigViewBaseService):
    """Provide an enhanced view combining hierarchical structure with resolved paths.

    This service provides an enhanced view combining hierarchical discovered
    structure with resolved paths and default values from resolved mode.
    """

    def view_enhanced_config(self, config_file_path: Path) -> dict[str, Any]:
        """Generate an enhanced configuration view.

        Args:
            config_file_path: Path to the configuration file.

        Returns:
            Enhanced configuration dictionary.
        """
        try:
            discovered_dict = self._view_discovered_config(config_file_path)

            provider = ConfigurationProvider(
                config_mode=False,
                lenient_validation=False,
                root_path=config_file_path.parent,
            )

            # Process the already-discovered dict instead of loading again
            config = provider.process_config_dict(discovered_dict)
            enhanced_dict = self._enhance_discovered_config(
                discovered_dict, config, provider
            )

            return enhanced_dict

        except Exception as e:
            self.logger.error(f"Error loading enhanced configuration: {e}")
            raise

    def _enhance_discovered_config(
        self,
        discovered_dict: dict[str, Any],
        config: CoregenConfig,
        provider: ConfigurationProvider,
    ) -> dict[str, Any]:
        """
        Enhances the discovered configuration with resolved paths and defaults.

        Args:
            discovered_dict: Original discovered config dictionary.
            config: Fully processed configuration object.
            provider: Configuration provider instance.

        Returns:
            Enhanced configuration dictionary.
        """
        enhanced_dict = copy.deepcopy(discovered_dict)

        for workspace in enhanced_dict.get("workspaces", []):
            processed_ws = next(
                (w for w in config.workspaces if w.name == workspace.get("name")), None
            )
            if not processed_ws:
                continue

            workspace["resolved_paths"] = {
                k: str(v)
                for k, v in provider.path_service.resolve_workspace_paths(
                    processed_ws
                ).items()
            }

            context_type = workspace.get("context_type", "context")
            contexts = workspace.get(context_type, {})

            if isinstance(contexts, dict):
                for ctx_name, ctx_dict in contexts.items():
                    self._enhance_context(ctx_dict, ctx_name, processed_ws, provider)
            elif isinstance(contexts, list):
                for ctx_dict in contexts:
                    ctx_name = ctx_dict.get("name")
                    if ctx_name:
                        self._enhance_context(
                            ctx_dict, ctx_name, processed_ws, provider
                        )

        return enhanced_dict

    def _enhance_context(
        self,
        ctx_dict: dict[str, Any],
        ctx_name: str,
        processed_ws: Any,
        provider: ConfigurationProvider,
    ) -> None:
        """
        Enhances a single context with resolved paths and defaults.

        Args:
            ctx_dict: Context dictionary to enhance.
            ctx_name: Name of the context.
            processed_ws: Processed workspace containing this context.
            provider: Configuration provider instance.
        """
        processed_ctx = next(
            (c[ctx_name] for c in processed_ws.contexts.values() if ctx_name in c), None
        )
        if not processed_ctx:
            return

        ctx_dict["resolved_paths"] = {
            k: str(v)
            for k, v in provider.path_service.resolve_context_paths(
                processed_ctx, processed_ws
            ).items()
        }
        ctx_dict["path"] = str(processed_ctx.path)

        for key, value in processed_ctx.model_dump(
            exclude_unset=False, exclude_defaults=False
        ).items():
            if key not in ctx_dict and key not in ("components", "config_file_path"):
                ctx_dict[key] = value

        component_type = ctx_dict.get("component_type", "component")
        components = ctx_dict.get(component_type, {})

        if isinstance(components, dict):
            for comp_name, comp_dict in components.items():
                self._enhance_component(
                    comp_dict, comp_name, processed_ctx, processed_ws, provider
                )
        elif isinstance(components, list):
            for comp_dict in components:
                comp_name = comp_dict.get("name")
                if comp_name:
                    self._enhance_component(
                        comp_dict, comp_name, processed_ctx, processed_ws, provider
                    )

    def _enhance_component(
        self,
        comp_dict: dict[str, Any],
        comp_name: str,
        processed_ctx: Any,
        processed_ws: Any,
        provider: ConfigurationProvider,
    ) -> None:
        """
        Enhances a single component with resolved paths and default values.

        Args:
            comp_dict: Component dictionary to enhance.
            comp_name: Name of the component.
            processed_ctx: Processed context containing this component.
            processed_ws: Processed workspace.
            provider: Configuration provider instance.
        """
        processed_comp = next(
            (
                comp[comp_name]
                for comp in processed_ctx.components.values()
                if comp_name in comp
            ),
            None,
        )
        if not processed_comp:
            return

        comp_dict["resolved_paths"] = {
            k: str(v)
            for k, v in provider.path_service.resolve_component_paths(
                processed_comp, processed_ctx, processed_ws
            ).items()
        }

        for key, value in processed_comp.model_dump(
            exclude_unset=False, exclude_defaults=False
        ).items():
            if key not in comp_dict and key not in ("config", "config_file_path"):
                comp_dict[key] = value

        comp_dict.setdefault("config", {})

        if hasattr(processed_comp, "config"):
            for key, value in processed_comp.config.model_dump(
                exclude_unset=False, exclude_defaults=False
            ).items():
                comp_dict["config"].setdefault(key, value)
