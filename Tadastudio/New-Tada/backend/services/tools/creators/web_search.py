"""
Web search tool creators.

Handles creation of various web search tools including custom web search,
DuckDuckGo, arXiv, and Wikipedia.
"""

from typing import Any, Dict

from langchain_community.tools import (
    ArxivQueryRun,
    DuckDuckGoSearchRun,
    WikipediaQueryRun,
)
from langchain_community.utilities import (
    ArxivAPIWrapper,
    DuckDuckGoSearchAPIWrapper,
    WikipediaAPIWrapper,
)
from langchain_core.tools import BaseTool

from ...config import get_logger
from .base import BaseToolCreator


logger = get_logger("tool-creators")


class WebSearchCreator(BaseToolCreator):
    """Creator for web search tools."""

    def get_tool_names(self) -> list[str]:
        """Get list of web search tool names."""
        return ["web_search", "duckduckgo", "arxiv", "wikipedia"]

    def create(self, tool_name: str, config: Dict[str, Any]) -> BaseTool:
        """
        Create a web search tool.

        Args:
            tool_name: Name of the web search tool
            config: Tool configuration

        Returns:
            Configured web search tool

        Raises:
            ValueError: If tool_name is unknown
        """
        if tool_name == "web_search":
            return self._create_web_search_tool(config)
        elif tool_name == "duckduckgo":
            return self._create_duckduckgo_tool(config)
        elif tool_name == "arxiv":
            return self._create_arxiv_tool(config)
        elif tool_name == "wikipedia":
            return self._create_wikipedia_tool(config)
        else:
            raise ValueError(f"Unknown web search tool: {tool_name}")

    def _create_web_search_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create a custom web search tool.

        Args:
            config: Tool configuration

        Returns:
            Web search tool instance
        """
        try:
            from ....tools.web_search import create_web_search_tool

            return create_web_search_tool(
                search_provider=self.get_config_value(
                    config, "search_provider", "duckduckgo"
                ),
                api_key=self.get_config_value(config, "api_key", ""),
                max_results=self.get_config_value(config, "max_results", 5),
                search_depth=self.get_config_value(config, "search_depth", "basic"),
                include_answer=self.get_config_value(config, "include_answer", False),
                include_raw_content=self.get_config_value(
                    config, "include_raw_content", False
                ),
                include_images=self.get_config_value(config, "include_images", False),
                timeout_seconds=self.get_config_value(config, "timeout_seconds", 10),
                region=self.get_config_value(config, "region", "wt-wt"),
                safe_search=self.get_config_value(config, "safe_search", "moderate"),
                time_range=self.get_config_value(config, "time_range", ""),
                node_id=self.get_config_value(config, "node_id", ""),
                node_name=self.get_config_value(config, "node_name", "Web Search"),
                tool_name=self.get_config_value(config, "tool_name", None),
            )
        except Exception as e:
            logger.error(f"[WEB-SEARCH-CREATOR] Failed to create web_search: {e}")
            raise

    def _create_duckduckgo_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create a DuckDuckGo search tool.

        Args:
            config: Tool configuration

        Returns:
            DuckDuckGo tool instance
        """
        try:
            wrapper = DuckDuckGoSearchAPIWrapper(
                max_results=self.get_config_value(config, "max_results", 5),
                region=self.get_config_value(config, "region", "us-en"),
                safesearch=self.get_config_value(config, "safesearch", "moderate"),
            )
            return DuckDuckGoSearchRun(api_wrapper=wrapper)
        except Exception as e:
            logger.error(f"[WEB-SEARCH-CREATOR] Failed to create duckduckgo: {e}")
            raise

    def _create_arxiv_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create an arXiv search tool.

        Args:
            config: Tool configuration

        Returns:
            arXiv tool instance
        """
        try:
            wrapper = ArxivAPIWrapper(
                top_k_results=self.get_config_value(config, "top_k", 3),
                doc_content_chars_max=self.get_config_value(config, "max_chars", 1000),
            )
            return ArxivQueryRun(api_wrapper=wrapper)
        except Exception as e:
            logger.error(f"[WEB-SEARCH-CREATOR] Failed to create arxiv: {e}")
            raise

    def _create_wikipedia_tool(self, config: Dict[str, Any]) -> BaseTool:
        """
        Create a Wikipedia search tool.

        Args:
            config: Tool configuration

        Returns:
            Wikipedia tool instance
        """
        try:
            wrapper = WikipediaAPIWrapper(
                top_k_results=self.get_config_value(config, "top_k", 3),
                doc_content_chars_max=self.get_config_value(config, "max_chars", 1000),
            )
            return WikipediaQueryRun(api_wrapper=wrapper)
        except Exception as e:
            logger.error(f"[WEB-SEARCH-CREATOR] Failed to create wikipedia: {e}")
            raise
