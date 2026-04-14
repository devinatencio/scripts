"""
Help content registry for managing help modules.

Provides centralized registration and access to help content modules.
"""

from typing import Dict, Type, Optional
from .base_help_content import BaseHelpContent


class HelpRegistry:
    """Registry for help content modules."""

    def __init__(self):
        """Initialize the help registry."""
        self._help_modules: Dict[str, Type[BaseHelpContent]] = {}
        self._register_default_modules()

    def _register_default_modules(self) -> None:
        """Register default help modules."""
        # Import help modules here to avoid circular imports
        try:
            from .indices_help import IndicesHelpContent
            from .templates_help import TemplatesHelpContent
            from .health_help import HealthHelpContent
            from .allocation_help import AllocationHelpContent
            from .exclude_help import ExcludeHelpContent
            from .snapshots_help import SnapshotsHelpContent
            from .repositories_help import RepositoriesHelpContent
            from .dangling_help import DanglingHelpContent
            from .shards_help import ShardsHelpContent
            from .security_help import SecurityHelpContent
            from .freeze_help import FreezeHelpContent
            from .unfreeze_help import UnfreezeHelpContent
            from .indice_add_metadata_help import IndiceAddMetadataHelpContent
            from .ilm_help import ILMHelpContent
            from .nodes_help import NodesHelpContent
            from .actions_help import ActionsHelp
            from .indices_watch_collect_help import IndicesWatchCollectHelpContent
            from .indices_watch_report_help import IndicesWatchReportHelpContent
            from .indices_analyze_help import IndicesAnalyzeHelpContent
            from .indices_s3_estimate_help import IndicesS3EstimateHelpContent
            from .template_backup_help import TemplateBackupHelpContent
            from .template_modify_help import TemplateModifyHelpContent
            from .template_restore_help import TemplateRestoreHelpContent
            from .store_password_help import StorePasswordHelpContent
            from .estop_help import EsTopHelpContent

            # Register core modules
            self.register(IndicesHelpContent)
            self.register(TemplatesHelpContent)
            self.register(HealthHelpContent)
            self.register(AllocationHelpContent)
            self.register(ExcludeHelpContent)
            self.register(SnapshotsHelpContent)
            self.register(RepositoriesHelpContent)
            self.register(DanglingHelpContent)
            self.register(ShardsHelpContent)
            self.register(SecurityHelpContent)
            self.register(FreezeHelpContent)
            self.register(UnfreezeHelpContent)
            self.register(IndiceAddMetadataHelpContent)
            self.register(ILMHelpContent)
            self.register(NodesHelpContent)
            self.register(ActionsHelp)
            self.register(IndicesWatchCollectHelpContent)
            self.register(IndicesWatchReportHelpContent)
            self.register(IndicesAnalyzeHelpContent)
            self.register(IndicesS3EstimateHelpContent)
            self.register(TemplateBackupHelpContent)
            self.register(TemplateModifyHelpContent)
            self.register(TemplateRestoreHelpContent)
            self.register(StorePasswordHelpContent)
            self.register(EsTopHelpContent)
            # Register "top" as an alias that resolves to the same help content
            self._help_modules["top"] = EsTopHelpContent

        except ImportError as e:
            # If core modules can't be imported, we have a bigger problem
            print(f"Warning: Could not import core help modules: {e}")

    def register(self, help_class: Type[BaseHelpContent]) -> None:
        """
        Register a help content module.

        Args:
            help_class: The help content class to register
        """
        if not issubclass(help_class, BaseHelpContent):
            raise ValueError("Help module must inherit from BaseHelpContent")

        # Create instance to get topic name
        instance = help_class()
        topic_name = instance.get_topic_name()

        self._help_modules[topic_name] = help_class

    def get_help_module(self, topic: str, theme_manager=None) -> Optional[BaseHelpContent]:
        """
        Get a help module instance for a specific topic.

        Args:
            topic: The help topic name
            theme_manager: Optional theme manager for styling

        Returns:
            BaseHelpContent instance or None if topic not found
        """
        help_class = self._help_modules.get(topic)
        if help_class:
            return help_class(theme_manager)
        return None

    def get_available_topics(self) -> Dict[str, str]:
        """
        Get all available help topics with their descriptions.

        Returns:
            Dictionary mapping topic names to descriptions
        """
        topics = {}
        for topic_name, help_class in self._help_modules.items():
            instance = help_class()
            topics[topic_name] = instance.get_topic_description()
        return topics

    def has_topic(self, topic: str) -> bool:
        """
        Check if a help topic is available.

        Args:
            topic: The topic name to check

        Returns:
            True if topic is available, False otherwise
        """
        return topic in self._help_modules

    def list_topics(self) -> list:
        """
        Get a list of all available topic names.

        Returns:
            List of topic names
        """
        return list(self._help_modules.keys())


# Global registry instance
_help_registry = HelpRegistry()


def get_help_registry() -> HelpRegistry:
    """Get the global help registry instance."""
    return _help_registry


def register_help_module(help_class: Type[BaseHelpContent]) -> None:
    """
    Register a help module with the global registry.

    Args:
        help_class: The help content class to register
    """
    _help_registry.register(help_class)


def get_help_for_topic(topic: str, theme_manager=None) -> Optional[BaseHelpContent]:
    """
    Get help content for a specific topic.

    Args:
        topic: The help topic name
        theme_manager: Optional theme manager for styling

    Returns:
        BaseHelpContent instance or None if topic not found
    """
    return _help_registry.get_help_module(topic, theme_manager)
