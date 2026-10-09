"""Generates tool factory functions for the exported Python file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.models.workflow import NodeType
from backend.services.export.utils import safe_name

if TYPE_CHECKING:
    from backend.models.workflow import EnhancedNodeData
    from backend.services.export.workflow_analyzer import WorkflowAnalysis


class ToolGenerators:
    """Generates tool factory functions for HTTP, Web Search, and Doc Search."""

    def generate(self, analysis: WorkflowAnalysis) -> str:
        if not analysis.tool_nodes:
            return ""

        lines = [
            "# " + "=" * 70,
            "# Tool Factory Functions",
            "# " + "=" * 70,
        ]

        for node in analysis.tool_nodes:
            lines.append("")
            lines.append("")
            if node.type == NodeType.HTTP_REQUEST:
                lines.append(self._generate_http_tool(node))
            elif node.type == NodeType.WEB_SEARCH:
                lines.append(self._generate_web_search_tool(node))
            elif node.type == NodeType.DOCUMENT_SEARCH:
                lines.append(self._generate_doc_search_tool(node))

        return "\n".join(lines)

    def _generate_http_tool(self, node: EnhancedNodeData) -> str:
        sn = safe_name(node.name)
        cfg = node.http_request_config
        if not cfg:
            return f'# HTTP tool "{node.name}" has no configuration'

        url = getattr(cfg, "url_template", "") or ""
        method = getattr(cfg, "method", "GET") or "GET"
        headers = getattr(cfg, "headers", {}) or {}
        body_template = getattr(cfg, "request_body_template", "") or ""
        timeout = getattr(cfg, "timeout_seconds", 30) or 30
        auth_type = getattr(cfg, "auth_type", "none") or "none"
        auth_config = getattr(cfg, "auth_config", {}) or {}
        desc = node.description or f"Make an HTTP {method} request to {url}"

        # Escape strings for embedding in source code
        url_escaped = url.replace("\\", "\\\\").replace('"', '\\"')
        desc_escaped = desc.replace("\\", "\\\\").replace('"', '\\"')
        body_escaped = body_template.replace("\\", "\\\\").replace('"', '\\"')

        parts = [
            f"def create_tool_{sn}():",
            f'    """Create HTTP request tool: {node.name}"""',
            f"    async def http_{sn}(query: str) -> str:",
            f'        """HTTP {method} request. {desc_escaped}"""',
            f'        url = "{url_escaped}"',
            f"        headers = {repr(headers)}",
        ]

        # Auth handling
        if auth_type == "bearer":
            token_var = auth_config.get("token_env_var", "API_TOKEN")
            parts.append(
                f'        headers["Authorization"] = f"Bearer {{os.environ[\\"{token_var}\\"]}}"'
            )
        elif auth_type == "api_key_header":
            key_name = auth_config.get("header_name", "X-API-Key")
            key_var = auth_config.get("key_env_var", "API_KEY")
            parts.append(f'        headers["{key_name}"] = os.environ["{key_var}"]')

        parts.extend(
            [
                f"        async with httpx.AsyncClient(timeout={timeout}) as client:",
            ]
        )

        if method.upper() in ("POST", "PUT", "PATCH") and body_template:
            parts.append(f'            body = "{body_escaped}"')
            parts.append(
                f'            response = await client.request("{method}", url, headers=headers, content=body)'
            )
        else:
            parts.append(
                f'            response = await client.request("{method}", url, headers=headers)'
            )

        parts.extend(
            [
                "            response.raise_for_status()",
                "            return response.text",
                "    return StructuredTool.from_function(",
                f"        coroutine=http_{sn},",
                f'        name="http_{sn}",',
                f'        description="{desc_escaped}",',
                "    )",
            ]
        )
        return "\n".join(parts)

    def _generate_web_search_tool(self, node: EnhancedNodeData) -> str:
        sn = safe_name(node.name)
        cfg = node.web_search_config
        if not cfg:
            return f'# Web search tool "{node.name}" has no configuration'

        provider = getattr(cfg, "search_provider", "duckduckgo") or "duckduckgo"
        max_results = getattr(cfg, "max_results", 5) or 5

        if provider == "tavily":
            return "\n".join(
                [
                    f"def create_tool_{sn}():",
                    f'    """Create web search tool: {node.name}"""',
                    "    return TavilySearchResults(",
                    '        api_key=os.environ["TAVILY_API_KEY"],',
                    f"        max_results={max_results},",
                    "    )",
                ]
            )
        else:
            return "\n".join(
                [
                    f"def create_tool_{sn}():",
                    f'    """Create web search tool: {node.name}"""',
                    "    return DuckDuckGoSearchResults(",
                    f"        max_results={max_results},",
                    "    )",
                ]
            )

    def _generate_doc_search_tool(self, node: EnhancedNodeData) -> str:
        sn = safe_name(node.name)
        cfg = node.document_search_config
        if not cfg:
            return f'# Document search tool "{node.name}" has no configuration'

        collections = getattr(cfg, "document_collections", []) or []
        desc = node.description or "Search documents for relevant information"
        desc_escaped = desc.replace("\\", "\\\\").replace('"', '\\"')

        return "\n".join(
            [
                f"def create_tool_{sn}():",
                f'    """Create document search tool: {node.name}"""',
                "    # NOTE: Document search requires a PostgreSQL database with pgvector.",
                "    # Configure DATABASE_URL environment variable.",
                f"    # Collections: {collections}",
                f"    async def search_{sn}(query: str) -> str:",
                f'        """Search documents. {desc_escaped}"""',
                "        # TODO: Implement vector search against your document store",
                '        return f"Document search for: {query} (not implemented - requires database setup)"',
                "    return StructuredTool.from_function(",
                f"        coroutine=search_{sn},",
                f'        name="doc_search_{sn}",',
                f'        description="{desc_escaped}",',
                "    )",
            ]
        )
