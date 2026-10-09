"""MCP Adapter Tool using official langchain-mcp-adapters with HTTP bridge fallback."""

import asyncio
import itertools
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from langchain_core.tools import BaseTool, StructuredTool, Tool
from pydantic import BaseModel, Field

from ..mcp_client_manager import mcp_client_manager


logger = logging.getLogger(__name__)

# Global MCP execution tracker
_mcp_execution_tracker: Dict[str, List[Dict[str, Any]]] = {}

# HTTP bridge discovery cache (avoids repeated list operations per request)
_BRIDGE_CACHE_TTL_SECONDS = 300
_bridge_tool_cache: Dict[str, Dict[str, Any]] = {}
_bridge_cache_lock = threading.RLock()


def _resolve_environment_variables(env_map: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Resolve environment variables, handling secret references."""
    resolved: Dict[str, str] = {}
    if not env_map:
        return resolved

    for key, value in env_map.items():
        if value is None:
            continue
        if isinstance(value, str) and value.startswith("secret://"):
            secret_ref = value[len("secret://") :].strip()
            if not secret_ref:
                continue
            secret_env_key = f"MCP_SECRET_{secret_ref.upper()}"
            secret_value = os.getenv(secret_env_key) or os.getenv(secret_ref)
            if secret_value:
                resolved[key] = secret_value
            else:
                logger.warning(
                    "[McpAdapter] Secret for env key '%s' not resolved - check environment variable configuration",
                    key,
                )
        else:
            resolved[key] = str(value)
    return resolved


class McpAdapterInput(BaseModel):
    """Input for interacting with an MCP server via the adapter."""

    action: str = Field(
        description="The action to perform (discover, tool_call, list_tools)"
    )
    tool_name: Optional[str] = Field(
        default=None, description="Name of the tool to call (for tool_call action)"
    )
    arguments: Optional[Dict[str, Any]] = Field(
        default=None, description="Arguments for the tool call"
    )


def _run_coroutine_sync(coro_factory, timeout: Optional[float] = None):
    """Execute an async coroutine factory in a synchronous context."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop in this thread
        return asyncio.run(coro_factory())

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: asyncio.run(coro_factory()))
        return future.result(timeout=timeout)


def _load_mcp_tools_sync(config: Dict[str, Any]) -> List[BaseTool]:
    """Load MCP tools synchronously using the shared client manager."""
    timeout = config.get("timeout_seconds", 30)

    async def loader():
        return await mcp_client_manager.load_tools_from_server(config)

    tools = _run_coroutine_sync(loader, timeout=timeout)
    return list(tools or [])


def _filter_tools(
    tools: List[BaseTool], tool_permissions: Optional[Dict[str, bool]]
) -> List[BaseTool]:
    if not tool_permissions:
        return list(tools)

    filtered: List[BaseTool] = []
    for tool in tools:
        tool_name = getattr(tool, "name", str(tool))
        if tool_permissions.get(tool_name, True):
            filtered.append(tool)
        else:
            logger.debug("[McpAdapter] Tool '%s' blocked by permissions", tool_name)
    return filtered


def _format_discovery_result(server_name: str, tools: List[BaseTool]) -> str:
    lines = [f"Discovered {len(tools)} tools from {server_name}:", ""]
    for tool in tools:
        tool_name = getattr(tool, "name", str(tool))
        description = getattr(tool, "description", "No description")
        lines.append(f"- {tool_name}: {description}")
    return "\n".join(lines)


def _normalise_tool_arguments(arguments: Any, default_key: str = "input") -> Any:
    if arguments is None:
        return {}
    if isinstance(arguments, str):
        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            return {default_key: arguments}
    if isinstance(arguments, (list, tuple)):
        if len(arguments) == 1:
            return {default_key: arguments[0]}
        return {default_key: list(arguments)}
    return arguments


def _invoke_tool_sync(
    tool: BaseTool, arguments: Any, timeout: Optional[float] = None
) -> Any:
    """Invoke a LangChain tool synchronously, supporting async implementations."""
    payload = arguments

    if hasattr(tool, "ainvoke"):

        async def async_invocation():
            return await tool.ainvoke(payload)

        return _run_coroutine_sync(async_invocation, timeout=timeout)

    if hasattr(tool, "invoke"):
        try:
            return tool.invoke(payload)
        except TypeError:
            if isinstance(payload, dict):
                return tool.invoke(**payload)
            raise

    if isinstance(tool, StructuredTool) and hasattr(tool, "func"):
        func = tool.func
        if isinstance(payload, dict):
            return func(**payload)
        return func(payload)

    if callable(tool):
        if isinstance(payload, dict):
            return tool(**payload)
        return tool(payload)

    raise TypeError(f"Unsupported tool invocation pattern for {tool}")


def _should_use_http_bridge(config: Dict[str, Any]) -> bool:
    connection_type = (config.get("connection_type") or "").lower()
    server_url = config.get("server_url") or ""
    return connection_type == "http" and server_url.startswith("http")


class _HttpBridgeClient:
    """Minimal HTTP bridge client for MCP servers exposed via simple POST interface."""

    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, config: Dict[str, Any]) -> None:
        server_url = (config.get("server_url") or "").strip()
        if not server_url:
            raise ValueError("server_url is required for HTTP bridge operations")

        from ..services.guardrails.ssrf_mcp import validate_mcp_server_url

        blocked_reason = validate_mcp_server_url(server_url)
        if blocked_reason:
            raise ValueError(blocked_reason)

        self.server_url = server_url
        self.timeout = config.get("timeout_seconds", 30)
        self.max_retries = max(1, int(config.get("max_retries", 3)))
        self.retry_delay = float(config.get("retry_delay", 1.0))
        self._session_id: Optional[str] = None
        self._lock = threading.RLock()
        self._request_counter = itertools.count(int(time.time() * 1000) % 100000)
        self.logger = logger.getChild("HttpBridge")
        node_id = config.get("node_id") or ""
        auth_marker = config.get("auth_type") or "none"
        self._cache_key = f"{self.server_url}::{node_id}::{auth_marker}"
        self._tool_schemas: Dict[str, Dict[str, Any]] = {}
        self._node_id = config.get("node_id")
        self._node_name = config.get("node_name")
        # Store auth config for OAuth token injection
        self._auth_type = (config.get("auth_type") or "none").lower()
        self._auth_config = config.get("auth_config") or {}

    def _next_request_id(self) -> int:
        return next(self._request_counter)

    def _get_oauth_token(self) -> Optional[str]:
        """Get OAuth token for the current user if auth_type is oauth."""
        if self._auth_type != "oauth":
            return None

        provider = self._auth_config.get("provider", "")
        user_id = self._auth_config.get("user_id", "")

        if provider == "notion" and user_id:
            try:
                from backend.services.oauth.notion_handler import notion_oauth_handler
                import asyncio

                # Run async token fetch in sync context
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    # No running loop - create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            notion_oauth_handler.get_valid_token(user_id)
                        )
                    finally:
                        loop.close()

                # If loop already running, use thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            notion_oauth_handler.get_valid_token(user_id)
                        )
                    )
                    return future.result(timeout=30)
            except Exception as exc:
                self.logger.error("[HttpBridge] OAuth token fetch failed: %s", exc)
                return None

        return None

    def _post(
        self, payload: Dict[str, Any], *, include_session: bool
    ) -> httpx.Response:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if include_session and self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        # Add OAuth token if available
        oauth_token = self._get_oauth_token()
        if oauth_token:
            headers["Authorization"] = f"Bearer {oauth_token}"
            self.logger.debug("[HttpBridge] Added OAuth token to request")

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.server_url, json=payload, headers=headers
                    )
                self.logger.debug(
                    "[HttpBridge] POST %s method=%s include_session=%s status=%s",
                    self.server_url,
                    payload.get("method"),
                    include_session,
                    response.status_code,
                )
                response.raise_for_status()
                session_header = response.headers.get(
                    "X-MCP-Session-Id"
                ) or response.headers.get("x-mcp-session-id")
                if session_header:
                    self._session_id = session_header
                return response
            except Exception as exc:  # pragma: no cover - network failure
                last_error = exc
                if attempt < self.max_retries - 1:
                    backoff = self.retry_delay * (attempt + 1)
                    self.logger.warning(
                        "[HttpBridge] Request failed (%s). Retrying in %.2fs",
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
        assert last_error is not None
        raise last_error

    def initialize(self, force: bool = False) -> Dict[str, Any]:
        with self._lock:
            if self._session_id and not force:
                return {"result": {"sessionId": self._session_id}}

            payload = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "mcp", "version": "0.1.0"},
                },
                "id": self._next_request_id(),
            }

            response = self._post(payload, include_session=False)
            data = response.json()
            if data.get("error"):
                message = data["error"].get("message", "Unknown error")
                raise RuntimeError(f"Initialize failed: {message}")

            if not self._session_id:
                raise RuntimeError("HTTP bridge did not return a session ID")
            return data

    def _send_request_locked(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        include_session: bool,
        allow_session_retry: bool = True,
    ) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else {},
            "id": self._next_request_id(),
        }

        response = self._post(payload, include_session=include_session)
        data = response.json()
        if data.get("error"):
            message = data["error"].get("message", "Unknown error")
            if (
                allow_session_retry
                and method != "initialize"
                and "session" in message.lower()
            ):
                self.logger.info(
                    "[HttpBridge] Session error detected (%s); retrying", message
                )
                self._session_id = None
                self.initialize(force=True)
                return self._send_request_locked(
                    method,
                    params,
                    include_session=True,
                    allow_session_retry=False,
                )
            raise RuntimeError(f"{method} failed: {message}")
        return data

    def list_tools(self) -> List[Dict[str, Any]]:
        with self._lock:
            self.logger.debug(
                "[HttpBridge] Listing tools from bridge at %s", self.server_url
            )
            self.initialize()
            data = self._send_request_locked(
                "tools/list",
                params={},
                include_session=True,
            )
            result = data.get("result", {})
            tools = list(result.get("tools", []))
            self.logger.info(
                "[HttpBridge] tools/list returned %s tool definitions", len(tools)
            )
            return tools

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        with self._lock:
            self.initialize()
            data = self._send_request_locked(
                "tools/call",
                params={"name": tool_name, "arguments": arguments or {}},
                include_session=True,
            )
            self.logger.debug(
                "[HttpBridge] tools/call %s returned keys: %s",
                tool_name,
                list(data.keys()),
            )
            result = data.get("result")
            if isinstance(result, (dict, list)):
                return json.dumps(result)
            if result is None:
                return ""
            return str(result)

    def discover_tools(
        self,
        tool_permissions: Optional[Dict[str, bool]] = None,
    ) -> Tuple[List[BaseTool], List[Dict[str, Any]]]:
        now = time.time()
        cached_defs: Optional[List[Dict[str, Any]]] = None

        with _bridge_cache_lock:
            cache_entry = _bridge_tool_cache.get(self._cache_key)
            if cache_entry:
                ttl = cache_entry.get("timestamp", 0)
                if now - ttl < _BRIDGE_CACHE_TTL_SECONDS:
                    cached_defs = list(cache_entry.get("tool_defs", []))
                else:
                    self.logger.debug(
                        "[HttpBridge] Expiring cached tool definitions for %s",
                        self.server_url,
                    )
                    _bridge_tool_cache.pop(self._cache_key, None)

        if cached_defs is not None:
            self.logger.debug(
                "[HttpBridge] Using cached tool definitions for %s (%s defs)",
                self.server_url,
                len(cached_defs),
            )
            for defn in cached_defs:
                name = defn.get("name") if isinstance(defn, dict) else None
                if name:
                    self._tool_schemas[name] = self._extract_input_schema(defn)
            filtered_defs = [
                defn
                for defn in cached_defs
                if not tool_permissions or tool_permissions.get(defn.get("name"), True)
            ]
            tools = [self._create_tool(defn) for defn in filtered_defs]
            return tools, filtered_defs

        tool_defs = self.list_tools()
        filtered_defs: List[Dict[str, Any]] = []
        tools: List[BaseTool] = []

        for tool_def in tool_defs:
            name = tool_def.get("name") or ""
            if name:
                self._tool_schemas[name] = self._extract_input_schema(tool_def)
            if (
                tool_permissions
                and name in tool_permissions
                and not tool_permissions[name]
            ):
                continue
            filtered_defs.append(tool_def)
            tools.append(self._create_tool(tool_def))

        with _bridge_cache_lock:
            _bridge_tool_cache[self._cache_key] = {
                "timestamp": now,
                "tool_defs": filtered_defs.copy(),
            }
        self.logger.info(
            "[HttpBridge] Cached %s tool definitions for %s",
            len(filtered_defs),
            self.server_url,
        )
        return tools, filtered_defs

    def _create_tool(self, tool_def: Dict[str, Any]) -> BaseTool:
        tool_name = tool_def.get("name") or "unknown"
        description = tool_def.get("description") or "No description"
        input_schema = self._tool_schemas.get(tool_name) or self._extract_input_schema(
            tool_def
        )
        primary_arg = self._infer_primary_arg(input_schema)

        if primary_arg:
            self.logger.debug(
                "[HttpBridge] Using primary argument '%s' for tool %s",
                primary_arg,
                tool_name,
            )

        def _manual_call(payload: Any = None, **kwargs: Any) -> str:
            call_payload = payload
            prepared_arguments: Any

            if kwargs:
                prepared_arguments = dict(kwargs)
            else:
                prepared_arguments = _normalise_tool_arguments(
                    call_payload,
                    default_key=primary_arg or "input",
                )

            if not isinstance(prepared_arguments, dict):
                prepared_arguments = {primary_arg or "input": prepared_arguments}

            if primary_arg and primary_arg not in prepared_arguments:
                if isinstance(call_payload, (str, int, float, bool)):
                    prepared_arguments[primary_arg] = call_payload
                elif isinstance(call_payload, (list, tuple)) and call_payload:
                    prepared_arguments[primary_arg] = call_payload[-1]

            return self.call_tool(tool_name, prepared_arguments)

        tool = Tool(name=tool_name, description=description, func=_manual_call)
        setattr(tool, "_mcp_input_schema", input_schema)
        setattr(tool, "_mcp_primary_arg", primary_arg)
        setattr(tool, "_mcp_node_id", self._node_id)
        setattr(tool, "_mcp_node_name", self._node_name)
        return tool

    @staticmethod
    def _extract_input_schema(tool_def: Dict[str, Any]) -> Dict[str, Any]:
        schema = tool_def.get("input_schema") or tool_def.get("inputSchema")
        if isinstance(schema, dict):
            return schema
        return {}

    @staticmethod
    def _infer_primary_arg(schema: Dict[str, Any]) -> Optional[str]:
        if not schema or not isinstance(schema, dict):
            return None
        if schema.get("type") != "object":
            return None
        required = schema.get("required") or []
        properties = schema.get("properties") or {}
        if len(required) == 1:
            return required[0]
        if len(properties) == 1:
            return next(iter(properties))
        return None


def _execute_mcp_action(
    action: Optional[str],
    tool_name: Optional[str],
    arguments: Any,
    config: Dict[str, Any],
    server_name: str,
    node_id: str,
    node_name: str,
    discovered_tools: List[BaseTool],
    execution_id: str,
    start_time: float,
    tool_permissions: Optional[Dict[str, bool]],
    manual_client: Optional[_HttpBridgeClient] = None,
) -> Union[str, List[str]]:
    """Execute an MCP action using the client manager or HTTP bridge."""
    try:
        if not action:
            return "Error: action is required"

        timeout = config.get("timeout_seconds", 30)
        use_manual = manual_client is not None

        if action == "discover":
            tools: List[BaseTool] = []
            manual_defs: List[Dict[str, Any]] = []
            native_error: Optional[Exception] = None

            try:
                if not use_manual or config.get("connection_type") != "http":
                    tools = _load_mcp_tools_sync(config)
            except Exception as exc:  # pragma: no cover - fallback path
                native_error = exc
                tools = []

            if use_manual and not tools:
                try:
                    tools, manual_defs = manual_client.discover_tools(tool_permissions)
                    if native_error:
                        logger.warning(
                            "[McpAdapter] Native MCP loading failed (%s); using HTTP bridge",
                            native_error,
                        )
                except Exception as manual_exc:  # pragma: no cover - network failure
                    logger.error(
                        "[McpAdapter] HTTP bridge discovery failed: %s",
                        manual_exc,
                    )
                    if native_error:
                        logger.error(
                            "[McpAdapter] Native discovery also failed: %s",
                            native_error,
                        )
                    return f"Error discovering MCP tools: {manual_exc}"
            else:
                manual_defs = [
                    {
                        "name": getattr(tool, "name", str(tool)),
                        "description": getattr(tool, "description", ""),
                    }
                    for tool in tools
                ]

            tools = _filter_tools(tools, tool_permissions)
            discovered_tools.clear()
            discovered_tools.extend(tools)

            result = _format_discovery_result(server_name, tools)

            execution_data = {
                "execution_id": execution_id,
                "node_id": node_id,
                "node_name": node_name,
                "server_name": server_name,
                "connection_type": config.get("connection_type"),
                "action": "discover",
                "target": "capabilities",
                "timestamp": datetime.utcnow().isoformat(),
                "duration": (time.time() - start_time) * 1000,
                "capabilities": {
                    "tools": [
                        {
                            "name": tool_info.get("name", ""),
                            "description": tool_info.get("description", ""),
                        }
                        for tool_info in manual_defs
                    ],
                },
                "result": result,
                "formatted_output": result,
            }

            _mcp_execution_tracker.setdefault(node_id, []).append(execution_data)
            logger.info("[MCP TRACKING] Stored discovery data for node %s", node_id)
            return result

        if action == "list_tools":
            if not discovered_tools:
                if use_manual:
                    tools, _ = manual_client.discover_tools(tool_permissions)
                    discovered_tools.extend(tools)
                else:
                    tools = _load_mcp_tools_sync(config)
                    discovered_tools.extend(_filter_tools(tools, tool_permissions))

            tool_names: List[str] = []
            for tool in discovered_tools:
                name = getattr(tool, "name", str(tool))
                if (
                    tool_permissions
                    and name in tool_permissions
                    and not tool_permissions[name]
                ):
                    continue
                tool_names.append(name)
            return tool_names

        if action == "tool_call":
            if not tool_name:
                return "Error: tool_name is required for tool_call action"

            if tool_permissions and not tool_permissions.get(tool_name, True):
                return f"Permission denied for tool: {tool_name}"

            if not discovered_tools:
                if use_manual:
                    tools, _ = manual_client.discover_tools(tool_permissions)
                    discovered_tools.extend(tools)
                else:
                    tools = _load_mcp_tools_sync(config)
                    discovered_tools.extend(_filter_tools(tools, tool_permissions))

            target_tool: Optional[BaseTool] = None
            for tool in discovered_tools:
                if getattr(tool, "name", str(tool)) == tool_name:
                    target_tool = tool
                    break

            if not target_tool:
                return f"Tool '{tool_name}' not found in available tools"

            payload = _normalise_tool_arguments(arguments)
            try:
                result = _invoke_tool_sync(target_tool, payload, timeout=timeout)
            except Exception as exc:  # pragma: no cover - logged before bubbling
                logger.error(
                    "[McpAdapter] Tool execution error for %s: %s", tool_name, exc
                )
                return f"Tool execution failed: {exc}"

            execution_data = {
                "execution_id": execution_id,
                "node_id": node_id,
                "node_name": node_name,
                "server_name": server_name,
                "connection_type": config.get("connection_type"),
                "action": "tool_call",
                "target": tool_name,
                "timestamp": datetime.utcnow().isoformat(),
                "duration": (time.time() - start_time) * 1000,
                "result": result,
                "formatted_output": str(result),
                "call_id": execution_id,
            }

            _mcp_execution_tracker.setdefault(node_id, []).append(execution_data)
            logger.info(
                "[MCP TRACKING] Stored tool execution data for node %s, tool %s",
                node_id,
                tool_name,
            )

            return str(result)

        return f"Unknown action: {action}"

    except Exception as exc:
        logger.error("[McpAdapter] Error executing action '%s': %s", action, exc)
        return f"Error executing MCP action: {exc}"


def create_mcp_adapter_tool(
    server_name: str = "MCP Server",
    connection_type: str = "stdio",
    server_url: str = "",
    command: str = "",
    args: Optional[List[str]] = None,
    working_directory: str = "",
    auth_type: str = "none",
    auth_config: Optional[Dict[str, str]] = None,
    timeout_seconds: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    capabilities_filter: Optional[List[str]] = None,
    resource_access: Optional[Dict[str, bool]] = None,
    tool_permissions: Optional[Dict[str, bool]] = None,
    environment_variables: Optional[Dict[str, str]] = None,
    node_id: str = "",
    node_name: str = "MCP Server",
    use_legacy: bool = False,
    **kwargs,
) -> BaseTool:
    """Create an MCP adapter tool that proxies discovery and tool calls."""
    if use_legacy:
        from .mcp_server_tool import create_mcp_server_tool as create_legacy_tool

        return create_legacy_tool(
            server_name=server_name,
            connection_type=connection_type,
            server_url=server_url,
            command=command,
            args=args,
            working_directory=working_directory,
            auth_type=auth_type,
            auth_config=auth_config,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_delay=retry_delay,
            capabilities_filter=capabilities_filter,
            resource_access=resource_access,
            tool_permissions=tool_permissions,
            environment_variables=environment_variables,
            node_id=node_id,
            node_name=node_name,
            **kwargs,
        )

    resolved_env = _resolve_environment_variables(environment_variables)

    config: Dict[str, Any] = {
        "server_name": server_name,
        "connection_type": connection_type,
        "server_url": server_url,
        "command": command,
        "args": list(args or []),
        "working_directory": working_directory,
        "auth_type": auth_type,
        "auth_config": auth_config or {},
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "capabilities_filter": capabilities_filter or [],
        "resource_access": resource_access or {},
        "tool_permissions": tool_permissions or {},
        "environment_variables": resolved_env,
        **kwargs,
    }

    discovered_tools: List[BaseTool] = []
    manual_client: Optional[_HttpBridgeClient] = None
    if _should_use_http_bridge(config):
        try:
            manual_client = _HttpBridgeClient(config)
        except Exception as exc:  # pragma: no cover - configuration error
            logger.error(
                "[McpAdapter] Failed to initialise HTTP bridge client: %s", exc
            )
            manual_client = None

    def interact_with_mcp_adapter(input_data: Any) -> Union[str, List[str]]:
        start_time = time.time()
        execution_id = f"mcp_{node_id}_{int(start_time * 1000)}"

        try:
            action: Optional[str] = None
            selected_tool: Optional[str] = None
            tool_arguments: Any = None

            if isinstance(input_data, str):
                action = input_data
            elif isinstance(input_data, list) and input_data:
                action = input_data[0]
                if len(input_data) > 1:
                    selected_tool = input_data[1]
                if len(input_data) > 2:
                    tool_arguments = input_data[2]
            elif isinstance(input_data, dict):
                if "action" in input_data:
                    action = input_data.get("action")
                    selected_tool = input_data.get("tool_name")
                    tool_arguments = input_data.get("arguments")
                else:
                    action = "tool_call"
                    tool_arguments = input_data
            else:
                return f"Error: Unexpected input type {type(input_data)}"

            if action and action not in {"discover", "list_tools", "tool_call"}:
                selected_tool = action
                action = "tool_call"

            logger.debug(
                "[McpAdapter] Parsed input - action=%s, tool=%s, args=%s",
                action,
                selected_tool,
                tool_arguments,
            )

            return _execute_mcp_action(
                action,
                selected_tool,
                tool_arguments,
                config,
                server_name,
                node_id,
                node_name,
                discovered_tools,
                execution_id,
                start_time,
                tool_permissions or {},
                manual_client=manual_client,
            )
        except Exception as exc:  # pragma: no cover - logged before returning
            logger.error("[McpAdapter] Error in interaction: %s", exc)
            return f"Error interacting with MCP server: {type(exc).__name__}"

    description_parts = [
        f"Connect to {server_name} MCP server",
        f"via {connection_type}",
        "using official langchain-mcp-adapters",
    ]
    if capabilities_filter:
        description_parts.append(f"with capabilities: {', '.join(capabilities_filter)}")

    tool_description = ". ".join(description_parts)

    class FlexibleMcpTool(BaseTool):
        """Tool wrapper that exposes discovery and tool invocation via simple prompts."""

        name: str = f"mcp_adapter_{node_id}" if node_id else "mcp_adapter"
        description: str = tool_description + (
            "\n\nUsage:"
            "\n- To discover capabilities: pass 'discover'"
            "\n- To list tools: pass 'list_tools'"
            "\n- To call a tool: pass ['tool_call', 'tool_name', {arguments}]"
            "\nExample: ['tool_call', 'read_text_file', {'path': 'file.txt'}]"
        )

        def _run(self, query: Any) -> Union[str, List[str]]:
            return interact_with_mcp_adapter(query)

        async def _arun(self, query: Any) -> Union[str, List[str]]:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._run, query)

        def invoke(
            self, input_data: Any, runtime_config: Any = None, **_unused_kwargs: Any
        ) -> Union[str, List[str]]:
            return self._run(input_data)

        async def ainvoke(
            self, input_data: Any, runtime_config: Any = None, **_unused_kwargs: Any
        ) -> Union[str, List[str]]:
            return await self._arun(input_data)

    return FlexibleMcpTool()


def get_mcp_execution_history(node_id: str) -> List[Dict[str, Any]]:
    """Get execution history for a specific MCP node."""
    return _mcp_execution_tracker.get(node_id, [])


def clear_mcp_execution_history(node_id: Optional[str] = None) -> None:
    """Clear execution history for all nodes or a specific node."""
    global _mcp_execution_tracker
    if node_id:
        _mcp_execution_tracker.pop(node_id, None)
    else:
        _mcp_execution_tracker = {}


async def get_mcp_tools_async(
    server_name: str = "MCP Server",
    connection_type: str = "stdio",
    server_url: str = "",
    command: str = "",
    args: Optional[List[str]] = None,
    working_directory: str = "",
    auth_type: str = "none",
    auth_config: Optional[Dict[str, str]] = None,
    tool_permissions: Optional[Dict[str, bool]] = None,
    environment_variables: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> List[BaseTool]:
    """Discover all MCP tools asynchronously using the appropriate transport."""
    config: Dict[str, Any] = {
        "server_name": server_name,
        "connection_type": connection_type,
        "server_url": server_url,
        "command": command,
        "args": list(args or []),
        "working_directory": working_directory,
        "auth_type": auth_type,
        "auth_config": auth_config or {},
        "tool_permissions": tool_permissions or {},
        "environment_variables": _resolve_environment_variables(environment_variables),
        **kwargs,
    }

    if _should_use_http_bridge(config):
        try:
            manual_client = _HttpBridgeClient(config)
        except Exception as exc:  # pragma: no cover - configuration error
            logger.error(
                "[McpAdapter] Failed to initialise HTTP bridge client: %s", exc
            )
            return []

        def _load() -> List[BaseTool]:
            tools, _ = manual_client.discover_tools(tool_permissions)
            return tools

        try:
            return await asyncio.to_thread(_load)
        except Exception as exc:  # pragma: no cover - network failure
            logger.error("[McpAdapter] HTTP bridge async discovery failed: %s", exc)
            return []

    try:
        tools = await mcp_client_manager.load_tools_from_server(config)
        tools = _filter_tools(list(tools or []), tool_permissions)
        logger.info("[McpAdapter] Retrieved %s tools from %s", len(tools), server_name)
        return tools
    except Exception as exc:  # pragma: no cover - network failure
        logger.error("[McpAdapter] Error getting tools from %s: %s", server_name, exc)
        return []
