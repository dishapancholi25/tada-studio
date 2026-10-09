"""RBAC feature name constants.

This module defines constants for all valid feature names used in the RBAC system.
Using these constants instead of string literals prevents typos and makes refactoring easier.
"""

from enum import Enum
from typing import Set


class FeatureName(str, Enum):
    """Enumeration of valid feature names for RBAC access control.

    Settings Features:
        Database settings, LLM providers, external services, etc.

    Navigation Features:
        Workflow editor, library, publish, data sources, etc.
    """

    # Settings Tab Features
    SETTINGS_DATABASE = "settings.database"
    SETTINGS_LLM_PROVIDERS = "settings.llm_providers"
    SETTINGS_EXTERNAL_SERVICES = "settings.external_services"
    SETTINGS_EXTERNAL_TOOLS = "settings.external_tools"
    SETTINGS_APPEARANCE = "settings.appearance"
    SETTINGS_API_TOKENS = "settings.api_tokens"

    # API Token Scope Restriction Feature
    API_TOKENS_RESTRICT_TO_WORKFLOW = "api_tokens.restrict_to_workflow"

    # Navigation Menu Features
    NAV_WORKFLOW = "nav.workflow"
    NAV_LIBRARY = "nav.library"
    NAV_PUBLISH = "nav.publish"
    NAV_DATASOURCES = "nav.datasources"
    NAV_EXECUTIONS = "nav.executions"
    NAV_MANAGE = "nav.manage"
    NAV_EVALUATIONS = "nav.evaluations"
    NAV_GUARDRAILS = "nav.guardrails"

    @classmethod
    def all_features(cls) -> Set[str]:
        """Get all valid feature names as a set.

        Returns:
            Set of all feature name strings
        """
        return {feature.value for feature in cls}

    @classmethod
    def settings_features(cls) -> Set[str]:
        """Get all settings feature names.

        Returns:
            Set of settings feature name strings
        """
        return {
            cls.SETTINGS_DATABASE.value,
            cls.SETTINGS_LLM_PROVIDERS.value,
            cls.SETTINGS_EXTERNAL_SERVICES.value,
            cls.SETTINGS_EXTERNAL_TOOLS.value,
            cls.SETTINGS_APPEARANCE.value,
            cls.SETTINGS_API_TOKENS.value,
        }

    @classmethod
    def navigation_features(cls) -> Set[str]:
        """Get all navigation feature names.

        Returns:
            Set of navigation feature name strings
        """
        return {
            cls.NAV_WORKFLOW.value,
            cls.NAV_LIBRARY.value,
            cls.NAV_PUBLISH.value,
            cls.NAV_DATASOURCES.value,
            cls.NAV_EXECUTIONS.value,
            cls.NAV_MANAGE.value,
            cls.NAV_EVALUATIONS.value,
            cls.NAV_GUARDRAILS.value,
        }


# Export individual constants for convenient imports
SETTINGS_DATABASE = FeatureName.SETTINGS_DATABASE.value
SETTINGS_LLM_PROVIDERS = FeatureName.SETTINGS_LLM_PROVIDERS.value
SETTINGS_EXTERNAL_SERVICES = FeatureName.SETTINGS_EXTERNAL_SERVICES.value
SETTINGS_EXTERNAL_TOOLS = FeatureName.SETTINGS_EXTERNAL_TOOLS.value
SETTINGS_APPEARANCE = FeatureName.SETTINGS_APPEARANCE.value
SETTINGS_API_TOKENS = FeatureName.SETTINGS_API_TOKENS.value

NAV_WORKFLOW = FeatureName.NAV_WORKFLOW.value
NAV_LIBRARY = FeatureName.NAV_LIBRARY.value
NAV_PUBLISH = FeatureName.NAV_PUBLISH.value
NAV_DATASOURCES = FeatureName.NAV_DATASOURCES.value
NAV_EXECUTIONS = FeatureName.NAV_EXECUTIONS.value
NAV_MANAGE = FeatureName.NAV_MANAGE.value
NAV_EVALUATIONS = FeatureName.NAV_EVALUATIONS.value
NAV_GUARDRAILS = FeatureName.NAV_GUARDRAILS.value
