"""Configuration utilities for web search tool."""

from typing import List

from .schemas import WebSearchConfig


class ToolDescriptionBuilder:
    """Builder for creating tool descriptions based on configuration."""

    @staticmethod
    def build_description(config: WebSearchConfig) -> str:
        """Build a dynamic tool description based on configuration.

        Args:
            config: Web search configuration

        Returns:
            Formatted tool description string
        """
        provider_desc = (
            "Tavily (AI-optimized)"
            if config.search_provider == "tavily"
            else "DuckDuckGo (free)"
        )

        description_parts = [
            f"Search the web using {provider_desc} for current, up-to-date information",
            f"Returns up to {config.max_results} results",
        ]

        if config.search_provider == "tavily" and config.include_answer:
            description_parts.append("with AI-generated answer")

        if config.include_images:
            description_parts.append("including images")

        return ". ".join(description_parts)


class ConfigValidator:
    """Validator for web search configuration."""

    @staticmethod
    def validate(config: WebSearchConfig) -> tuple[bool, List[str], List[str]]:
        """Validate search configuration.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # Validate provider
        if config.search_provider not in ["duckduckgo", "tavily"]:
            errors.append(
                f"Invalid search provider: {config.search_provider}. "
                "Must be 'duckduckgo' or 'tavily'"
            )

        # Validate Tavily-specific settings
        if config.search_provider == "tavily":
            if not config.api_key:
                warnings.append(
                    "Tavily provider selected but no API key provided. "
                    "Will fall back to DuckDuckGo."
                )

            if config.search_depth not in ["basic", "advanced"]:
                errors.append(
                    f"Invalid search depth: {config.search_depth}. "
                    "Must be 'basic' or 'advanced'"
                )

        # Validate DuckDuckGo-specific settings
        if config.search_provider == "duckduckgo":
            if config.safe_search not in ["off", "moderate", "strict"]:
                errors.append(
                    f"Invalid safe_search: {config.safe_search}. "
                    "Must be 'off', 'moderate', or 'strict'"
                )

            if config.time_range and config.time_range not in ["d", "w", "m", "y"]:
                errors.append(
                    f"Invalid time_range: {config.time_range}. "
                    "Must be 'd', 'w', 'm', 'y', or empty"
                )

        # Validate ranges
        if config.max_results < 1 or config.max_results > 20:
            errors.append("max_results must be between 1 and 20")

        if config.timeout_seconds < 1 or config.timeout_seconds > 60:
            errors.append("timeout_seconds must be between 1 and 60")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings


# Default configurations
DEFAULT_DUCKDUCKGO_CONFIG = WebSearchConfig(
    search_provider="duckduckgo",
    max_results=5,
    region="wt-wt",
    safe_search="moderate",
    timeout_seconds=10,
)

DEFAULT_TAVILY_CONFIG = WebSearchConfig(
    search_provider="tavily",
    max_results=5,
    search_depth="basic",
    include_answer=False,
    timeout_seconds=10,
)
