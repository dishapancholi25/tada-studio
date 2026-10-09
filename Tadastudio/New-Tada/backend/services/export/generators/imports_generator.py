"""Generates import statements for the exported Python file."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.export.workflow_analyzer import WorkflowAnalysis


class ImportsGenerator:
    """Generates the imports section of the exported file."""

    def generate(self, analysis: WorkflowAnalysis) -> str:
        lines = [
            "import json",
            "import os",
            "import re",
            "from typing import Annotated, Any, Dict, List, Optional, Sequence",
            "",
            "from dotenv import load_dotenv",
            "from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage",
            "from langgraph.graph import END, StateGraph",
            "from langgraph.graph.message import add_messages",
            "from typing_extensions import TypedDict",
            "",
            "load_dotenv()  # Load .env file if present",
        ]

        # LLM provider imports
        providers = analysis.llm_providers_used
        if "azure_openai" in providers:
            lines.append("from langchain_openai import AzureChatOpenAI")
        if "openai" in providers:
            lines.append("from langchain_openai import ChatOpenAI")
        if "anthropic" in providers:
            lines.append("from langchain_anthropic import ChatAnthropic")
        if "google" in providers:
            lines.append("from langchain_google_genai import ChatGoogleGenerativeAI")

        # Tool imports
        if "WEB_SEARCH" in analysis.tool_types_used:
            lines.append("")
            lines.append("# Web search")
            lines.append("try:")
            lines.append(
                "    from langchain_community.tools.tavily_search import TavilySearchResults"
            )
            lines.append("except ImportError:")
            lines.append("    TavilySearchResults = None")
            lines.append("try:")
            lines.append(
                "    from langchain_community.tools import DuckDuckGoSearchResults"
            )
            lines.append("except ImportError:")
            lines.append("    DuckDuckGoSearchResults = None")

        if "HTTP_REQUEST" in analysis.tool_types_used:
            lines.append("")
            lines.append("# HTTP requests")
            lines.append("import httpx")
            lines.append("from langchain_core.tools import StructuredTool")
            lines.append("from pydantic import BaseModel, Field")

        if "DOCUMENT_SEARCH" in analysis.tool_types_used:
            lines.append("")
            lines.append("# Document search")
            lines.append("from langchain_core.tools import StructuredTool")
            lines.append("from pydantic import BaseModel, Field")

        return "\n".join(lines)
