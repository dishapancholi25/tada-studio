"""MCP Server Tool for connecting to Model Context Protocol servers."""

import asyncio
import json
import logging
import os
import subprocess
import time
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


def _resolve_environment_variables(env_map: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Resolve environment variables, expanding secret references."""
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
                    "[McpServer] Secret for env key '%s' not resolved - check environment variable configuration",
                    key,
                )
        else:
            resolved[key] = str(value)
    return resolved


class McpServerInput(BaseModel):
    """Input for interacting with MCP server."""

    action: str = Field(
        description="The action to perform (discover, tool, resource, prompt)"
    )
    target: str = Field(
        description="The target of the action (tool name, resource URI, prompt name, or 'capabilities')"
    )
    arguments: Optional[Dict[str, Any]] = Field(
        default=None, description="Arguments for the action (optional)"
    )


class McpServerConnection:
    """Manages connection to an MCP server."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize MCP server connection."""
        self.config = config
        self.connection_type = config.get("connection_type", "stdio")
        self.server_name = config.get("server_name", "MCP Server")
        self.process = None
        self.session = None
        self.websocket = None
        self.capabilities = None
        self.last_error = None
        self.environment_variables = config.get("environment_variables", {})

    def connect(self):
        """Establish connection to the MCP server."""
        try:
            if self.connection_type == "stdio":
                return self._connect_stdio()
            elif self.connection_type == "http":
                return self._connect_http()
            elif self.connection_type == "websocket":
                return self._connect_websocket()
            else:
                raise ValueError(f"Unsupported connection type: {self.connection_type}")
        except Exception as e:
            logger.error(f"[McpServer] Connection failed: {str(e)}")
            self.last_error = str(e)
            return False

    def _connect_stdio(self):
        """Connect via stdio (local process)."""
        try:
            command = self.config.get("command", "")
            args = self.config.get("args", [])
            working_dir = self.config.get("working_directory", None)

            # Handle empty working directory - convert to None
            if working_dir == "":
                working_dir = None

            if not command:
                raise ValueError("Command is required for stdio connection")

            # Handle Windows-specific command extensions
            import platform

            if platform.system() == "Windows":
                # On Windows, check if command needs .cmd or .exe extension
                if command.lower() in ["npx", "npm", "node"]:
                    command = f"{command}.cmd"

            # Build full command
            full_command = [command] + args

            resolved_env = _resolve_environment_variables(self.environment_variables)
            env = os.environ.copy()
            if resolved_env:
                env.update(resolved_env)
            logger.info(f"[McpServer] Starting local server: {' '.join(full_command)}")

            # Start the process
            # Use shell=True on Windows for better command resolution
            use_shell = platform.system() == "Windows"

            self.process = subprocess.Popen(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_dir,
                env=env,
                text=True,
                bufsize=0,
                shell=use_shell,
            )

            # Send initialization
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "clientInfo": {"name": "AgenticStudio", "version": "1.0"},
                    "capabilities": {},  # Add empty capabilities as required by the protocol
                },
                "id": 1,
            }

            self.process.stdin.write(json.dumps(init_request) + "\n")
            self.process.stdin.flush()

            # Read response with timeout

            # For Windows, we need a different approach
            if platform.system() == "Windows":
                # Give the server time to start

                time.sleep(2)

                # Check if process is still running
                if self.process.poll() is not None:
                    # Process terminated
                    stderr_output = self.process.stderr.read()
                    logger.error(f"[McpServer] Process terminated: {stderr_output}")
                    self.last_error = f"Process terminated: {stderr_output}"
                    return False

                # Try to read with a simple approach
                try:
                    # Set a short timeout for reading
                    import threading

                    response_line = None

                    def read_line():
                        nonlocal response_line
                        response_line = self.process.stdout.readline()

                    thread = threading.Thread(target=read_line)
                    thread.daemon = True
                    thread.start()
                    thread.join(timeout=5)  # 5 second timeout

                    if response_line:
                        response = json.loads(response_line)
                        if "result" in response:
                            self.capabilities = response["result"].get(
                                "capabilities", {}
                            )
                            logger.info(
                                f"[McpServer] Connected to {self.server_name} via stdio"
                            )
                            return True
                    else:
                        logger.warning(
                            "[McpServer] No response from server within timeout"
                        )
                        self.last_error = "Server did not respond within timeout"
                except Exception as e:
                    logger.error(f"[McpServer] Error reading response: {str(e)}")
                    self.last_error = str(e)
            else:
                # Unix-like systems can use select
                response_line = self.process.stdout.readline()
                if response_line:
                    response = json.loads(response_line)
                    if "result" in response:
                        self.capabilities = response["result"].get("capabilities", {})
                        logger.info(
                            f"[McpServer] Connected to {self.server_name} via stdio"
                        )
                        return True

            return False

        except Exception as e:
            logger.error(f"[McpServer] Stdio connection error: {str(e)}")
            self.last_error = str(e)
            return False

    def _connect_http(self):
        """Connect via HTTP."""
        try:
            server_url = self.config.get("server_url", "")
            auth_type = self.config.get("auth_type", "none")
            auth_config = self.config.get("auth_config", {})
            timeout = self.config.get("timeout_seconds", 30)

            if not server_url:
                raise ValueError("Server URL is required for HTTP connection")

            # Prepare headers
            headers = {"Content-Type": "application/json"}

            # Add authentication
            if auth_type == "api_key":
                api_key = auth_config.get("api_key", "")
                header_name = auth_config.get("header_name", "X-API-Key")
                if api_key:
                    headers[header_name] = api_key
            elif auth_type == "bearer":
                token = auth_config.get("token", "")
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            elif auth_type == "oauth2":
                # OAuth2 flow would be more complex - simplified here
                access_token = auth_config.get("access_token", "")
                if access_token:
                    headers["Authorization"] = f"Bearer {access_token}"

            # Send initialization request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "clientInfo": {"name": "AgenticStudio", "version": "1.0"},
                },
                "id": 1,
            }

            response = requests.post(
                f"{server_url}/rpc",
                json=init_request,
                headers=headers,
                timeout=timeout,
                verify=self.config.get("verify_ssl", True),
            )

            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    self.capabilities = result["result"].get("capabilities", {})
                    logger.info(f"[McpServer] Connected to {self.server_name} via HTTP")
                    return True

            return False

        except Exception as e:
            logger.error(f"[McpServer] HTTP connection error: {str(e)}")
            self.last_error = str(e)
            return False

    @staticmethod
    def _connect_websocket():
        """Connect via WebSocket."""
        # WebSocket connection would use asyncio
        # Simplified implementation for now
        logger.warning("[McpServer] WebSocket connection not fully implemented yet")
        return False

    def discover_capabilities(self):
        """Discover server capabilities."""
        try:
            # Try different methods to discover capabilities
            methods_to_try = [
                {"method": "capabilities/list", "params": {}},
                {"method": "tools/list", "params": {}},
                {"method": "resources/list", "params": {}},
                {"method": "prompts/list", "params": {}},
            ]

            capabilities = {}

            for method_info in methods_to_try:
                request = {
                    "jsonrpc": "2.0",
                    "method": method_info["method"],
                    "params": method_info["params"],
                    "id": int(time.time() * 1000),
                }

                response = self._send_request(request)
                if response and "result" in response:
                    # Extract the capability type from method name
                    capability_type = method_info["method"].split("/")[0]
                    result = response["result"]

                    # Handle different response formats
                    if isinstance(result, dict):
                        # If it's a dict with items, extract them
                        if capability_type in result:
                            capabilities[capability_type] = result[capability_type]
                        else:
                            capabilities[capability_type] = result
                    elif isinstance(result, list):
                        capabilities[capability_type] = result
                    else:
                        # For empty or other types, check if we got capabilities from init
                        if (
                            capability_type == "tools"
                            and self.capabilities
                            and "tools" in self.capabilities
                        ):
                            # File system server indicates tool support but provides them dynamically
                            # Create placeholder tools for common filesystem operations
                            capabilities["tools"] = [
                                {
                                    "name": "read_file",
                                    "description": "Read contents of a file",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "path": {
                                                "type": "string",
                                                "description": "Path to file",
                                            }
                                        },
                                        "required": ["path"],
                                    },
                                },
                                {
                                    "name": "write_file",
                                    "description": "Write contents to a file",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "path": {
                                                "type": "string",
                                                "description": "Path to file",
                                            },
                                            "content": {
                                                "type": "string",
                                                "description": "Content to write",
                                            },
                                        },
                                        "required": ["path", "content"],
                                    },
                                },
                                {
                                    "name": "list_directory",
                                    "description": "List contents of a directory",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "path": {
                                                "type": "string",
                                                "description": "Path to directory",
                                            }
                                        },
                                        "required": ["path"],
                                    },
                                },
                                {
                                    "name": "create_directory",
                                    "description": "Create a new directory",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "path": {
                                                "type": "string",
                                                "description": "Path to directory",
                                            }
                                        },
                                        "required": ["path"],
                                    },
                                },
                                {
                                    "name": "delete_file",
                                    "description": "Delete a file",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "path": {
                                                "type": "string",
                                                "description": "Path to file",
                                            }
                                        },
                                        "required": ["path"],
                                    },
                                },
                                {
                                    "name": "move_file",
                                    "description": "Move or rename a file",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "source": {
                                                "type": "string",
                                                "description": "Source path",
                                            },
                                            "destination": {
                                                "type": "string",
                                                "description": "Destination path",
                                            },
                                        },
                                        "required": ["source", "destination"],
                                    },
                                },
                            ]
                            logger.info(
                                "[McpServer] Generated filesystem tool definitions"
                            )
                        else:
                            capabilities[capability_type] = result

                    logger.info(
                        f"[McpServer] Discovered {capability_type}: {len(capabilities.get(capability_type, []))} items"
                    )

            # Store combined capabilities
            if capabilities:
                self.capabilities = capabilities
            elif not self.capabilities:
                # Try the initialize response capabilities
                self.capabilities = self.capabilities or {}

            return self.capabilities

        except Exception as e:
            logger.error(f"[McpServer] Error discovering capabilities: {str(e)}")
            return None

    def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to the MCP server."""
        try:
            if self.connection_type == "stdio":
                if self.process and self.process.poll() is None:
                    self.process.stdin.write(json.dumps(request) + "\n")
                    self.process.stdin.flush()
                    response_line = self.process.stdout.readline()
                    if response_line:
                        return json.loads(response_line)

            elif self.connection_type == "http":
                server_url = self.config.get("server_url", "")
                auth_type = self.config.get("auth_type", "none")
                auth_config = self.config.get("auth_config", {})

                headers = {"Content-Type": "application/json"}

                # Add authentication
                if auth_type == "api_key":
                    api_key = auth_config.get("api_key", "")
                    header_name = auth_config.get("header_name", "X-API-Key")
                    if api_key:
                        headers[header_name] = api_key
                elif auth_type == "bearer":
                    token = auth_config.get("token", "")
                    if token:
                        headers["Authorization"] = f"Bearer {token}"

                response = requests.post(
                    f"{server_url}/rpc",
                    json=request,
                    headers=headers,
                    timeout=self.config.get("timeout_seconds", 30),
                    verify=self.config.get("verify_ssl", True),
                )

                if response.status_code == 200:
                    return response.json()

        except Exception as e:
            logger.error(f"[McpServer] Error sending request: {str(e)}")

        return None

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """Call a tool on the MCP server."""
        try:
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
                "id": int(time.time() * 1000),
            }

            response = self._send_request(request)
            if response and "result" in response:
                return json.dumps(response["result"])
            elif response and "error" in response:
                return f"Error: {response['error'].get('message', 'Unknown error')}"

        except Exception as e:
            logger.error(f"[McpServer] Error calling tool {tool_name}: {str(e)}")
            return f"Error calling tool: {str(e)}"

        return None

    def get_resource(self, resource_uri: str) -> Optional[str]:
        """Get a resource from the MCP server."""
        try:
            request = {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": resource_uri},
                "id": int(time.time() * 1000),
            }

            response = self._send_request(request)
            if response and "result" in response:
                return json.dumps(response["result"])
            elif response and "error" in response:
                return f"Error: {response['error'].get('message', 'Unknown error')}"

        except Exception as e:
            logger.error(f"[McpServer] Error getting resource {resource_uri}: {str(e)}")
            return f"Error getting resource: {str(e)}"

        return None

    def use_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """Use a prompt template from the MCP server."""
        try:
            request = {
                "jsonrpc": "2.0",
                "method": "prompts/get",
                "params": {"name": prompt_name, "arguments": arguments},
                "id": int(time.time() * 1000),
            }

            response = self._send_request(request)
            if response and "result" in response:
                return response["result"].get("messages", [])
            elif response and "error" in response:
                return f"Error: {response['error'].get('message', 'Unknown error')}"

        except Exception as e:
            logger.error(f"[McpServer] Error using prompt {prompt_name}: {str(e)}")
            return f"Error using prompt: {str(e)}"

        return None

    def disconnect(self):
        """Disconnect from the MCP server."""
        try:
            if self.connection_type == "stdio" and self.process:
                self.process.terminate()
                self.process = None
            elif self.connection_type == "http" and self.session:
                self.session.close()
                self.session = None
            elif self.connection_type == "websocket" and self.websocket:
                asyncio.run(self.websocket.close())
                self.websocket = None

            logger.info(f"[McpServer] Disconnected from {self.server_name}")

        except Exception as e:
            logger.error(f"[McpServer] Error disconnecting: {str(e)}")


def create_mcp_server_tool(
    server_name: str = "MCP Server",
    connection_type: str = "stdio",
    server_url: str = "",
    command: str = "",
    args: List[str] = None,
    working_directory: str = "",
    auth_type: str = "none",
    auth_config: Dict[str, str] = None,
    timeout_seconds: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    capabilities_filter: List[str] = None,
    resource_access: Dict[str, bool] = None,
    tool_permissions: Dict[str, bool] = None,
    environment_variables: Dict[str, str] = None,
    node_id: str = "",
    node_name: str = "MCP Server",
    **kwargs,
):
    """Create an MCP server tool with the given configuration.

    Args:
        server_name: Display name for the MCP server
        connection_type: Connection type (stdio, http, websocket)
        server_url: URL for HTTP/WebSocket connections
        command: Command for stdio connections
        args: Arguments for stdio command
        working_directory: Working directory for stdio
        auth_type: Authentication type
        auth_config: Authentication configuration
        timeout_seconds: Connection timeout
        max_retries: Number of retry attempts
        retry_delay: Delay between retries
        capabilities_filter: Filter which capabilities to expose
        resource_access: Permissions for resource access
        tool_permissions: Permissions for tool execution
        environment_variables: Environment variables passed to the server process
        node_id: Node ID for tracking
        node_name: Node name for display
        **kwargs: Additional configuration options
    """
    # Build configuration
    config = {
        "server_name": server_name,
        "connection_type": connection_type,
        "server_url": server_url,
        "command": command,
        "args": args or [],
        "working_directory": working_directory,
        "auth_type": auth_type,
        "auth_config": auth_config or {},
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "capabilities_filter": capabilities_filter or [],
        "resource_access": resource_access or {},
        "tool_permissions": tool_permissions or {},
        "environment_variables": environment_variables or {},
        **kwargs,
    }

    # Create connection manager
    connection = McpServerConnection(config)

    # Build tool description
    description_parts = [
        f"Connect to {server_name} MCP server",
        f"via {connection_type}",
    ]

    if capabilities_filter:
        description_parts.append(f"with capabilities: {', '.join(capabilities_filter)}")

    tool_description = ". ".join(description_parts)

    def interact_with_mcp_server(
        action: str, target: str, arguments: Optional[Dict[str, Any]] = None
    ) -> str:
        """Interact with an MCP server.

        Args:
            action: The action to perform (discover, tool, resource, prompt)
            target: The target of the action (tool name, resource URI, prompt name, or 'capabilities')
            arguments: Arguments for the action (optional)

        Returns:
            Result from the MCP server
        """
        try:
            logger.info(f"[McpServer] Action: {action}, Target: {target}")

            # Connect if not already connected
            if not connection.capabilities:
                retry_count = 0
                while retry_count < max_retries:
                    if connection.connect():
                        break
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(retry_delay)
                        logger.info(
                            f"[McpServer] Retrying connection ({retry_count}/{max_retries})..."
                        )

                if not connection.capabilities and retry_count >= max_retries:
                    return f"Failed to connect to {server_name} after {max_retries} attempts. Last error: {connection.last_error}"

            # Handle different actions
            if action == "discover":
                # Discover capabilities
                capabilities = connection.discover_capabilities()
                if capabilities:
                    # Filter capabilities if needed
                    if capabilities_filter:
                        filtered = {}
                        for cap in capabilities_filter:
                            if cap in capabilities:
                                filtered[cap] = capabilities[cap]
                        capabilities = filtered

                    # Format capabilities for display
                    result = f"Capabilities of {server_name}:\n"
                    result += f"Connection: {connection_type}"
                    if connection_type == "stdio":
                        result += f" ({command})"
                    elif connection_type in ["http", "websocket"]:
                        result += f" ({server_url})"
                    result += "\n"

                    if "tools" in capabilities:
                        tools_list = (
                            capabilities["tools"]
                            if isinstance(capabilities["tools"], list)
                            else []
                        )
                        result += f"\nTools ({len(tools_list)}):\n"
                        for tool in tools_list:
                            tool_name = (
                                tool.get("name", "unnamed")
                                if isinstance(tool, dict)
                                else str(tool)
                            )
                            tool_desc = (
                                tool.get("description", "No description")
                                if isinstance(tool, dict)
                                else ""
                            )
                            result += f"  - {tool_name}"
                            if tool_desc:
                                result += f": {tool_desc}"
                            result += "\n"
                            # Show input schema if available
                            if isinstance(tool, dict) and "inputSchema" in tool:
                                result += f"    Input: {json.dumps(tool['inputSchema'], indent=6)[:100]}...\n"

                    if "resources" in capabilities:
                        resources_list = (
                            capabilities["resources"]
                            if isinstance(capabilities["resources"], list)
                            else []
                        )
                        result += f"\nResources ({len(resources_list)}):\n"
                        for resource in resources_list:
                            if isinstance(resource, dict):
                                result += f"  - {resource.get('uri', 'unknown')}: {resource.get('name', 'unnamed')}\n"
                                if "mimeType" in resource:
                                    result += f"    Type: {resource['mimeType']}\n"
                            else:
                                result += f"  - {resource}\n"

                    if "prompts" in capabilities:
                        prompts_list = (
                            capabilities["prompts"]
                            if isinstance(capabilities["prompts"], list)
                            else []
                        )
                        result += f"\nPrompts ({len(prompts_list)}):\n"
                        for prompt in prompts_list:
                            if isinstance(prompt, dict):
                                result += f"  - {prompt.get('name', 'unnamed')}: {prompt.get('description', 'No description')}\n"
                                if "arguments" in prompt:
                                    result += f"    Arguments: {', '.join(prompt['arguments'])}\n"
                            else:
                                result += f"  - {prompt}\n"

                    # Store execution metadata
                    interact_with_mcp_server._last_execution = {
                        "action": action,
                        "server": server_name,
                        "capabilities": capabilities,
                        "connection_type": connection_type,
                    }

                    return result
                else:
                    return f"Failed to discover capabilities for {server_name}"

            elif action == "tool":
                # Check tool permissions
                if (
                    tool_permissions
                    and target in tool_permissions
                    and not tool_permissions[target]
                ):
                    return f"Permission denied for tool: {target}"

                # Call a tool
                result = connection.call_tool(target, arguments or {})
                if result:
                    # Store execution metadata
                    interact_with_mcp_server._last_execution = {
                        "action": action,
                        "server": server_name,
                        "tool": target,
                        "arguments": arguments,
                        "result": result,
                    }
                    return result
                else:
                    return f"Failed to call tool {target} on {server_name}"

            elif action == "resource":
                # Check resource access
                if (
                    resource_access
                    and target in resource_access
                    and not resource_access[target]
                ):
                    return f"Access denied for resource: {target}"

                # Get a resource
                result = connection.get_resource(target)
                if result:
                    # Store execution metadata
                    interact_with_mcp_server._last_execution = {
                        "action": action,
                        "server": server_name,
                        "resource": target,
                        "result": result,
                    }
                    return result
                else:
                    return f"Failed to get resource {target} from {server_name}"

            elif action == "prompt":
                # Use a prompt
                result = connection.use_prompt(target, arguments or {})
                if result:
                    # Store execution metadata
                    interact_with_mcp_server._last_execution = {
                        "action": action,
                        "server": server_name,
                        "prompt": target,
                        "arguments": arguments,
                        "result": result,
                    }

                    # Format prompt messages
                    if isinstance(result, list):
                        formatted = f"Prompt '{target}' from {server_name}:\n"
                        for msg in result:
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")
                            formatted += f"\n[{role}]: {content}\n"
                        return formatted
                    else:
                        return str(result)
                else:
                    return f"Failed to use prompt {target} from {server_name}"

            else:
                return f"Unknown action: {action}. Supported actions: discover, tool, resource, prompt"

        except Exception as e:
            logger.error(f"[McpServer] Error in interaction: {str(e)}")
            return f"Error interacting with MCP server: {str(e)}"
        finally:
            # Optionally disconnect after each interaction (based on keep_alive setting)
            if not config.get("keep_alive", True):
                connection.disconnect()

    # Create and return StructuredTool
    return StructuredTool(
        name=f"mcp_server_{node_id}" if node_id else "mcp_server",
        description=tool_description,
        func=interact_with_mcp_server,
        args_schema=McpServerInput,
    )
