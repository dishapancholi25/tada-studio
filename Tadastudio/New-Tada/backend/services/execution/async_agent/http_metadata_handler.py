"""HTTP metadata handler for async agent execution.

This module handles the complexity of capturing HTTP request metadata
from thread-local storage when executing HTTP request tools.
"""

from typing import Any, Dict, Optional, Tuple

from backend.services.config import get_logger

from .utils import extract_node_id_from_tool_name, is_http_request_tool


# Get logger for this module
http_metadata_logger = get_logger("async_agent.http_metadata")


class HTTPMetadataHandler:
    """Handles HTTP request tool metadata capture.

    This class manages the complex logic of retrieving HTTP request/response
    metadata from thread-local storage, which requires careful synchronization
    between tool execution and metadata retrieval.
    """

    def __init__(self):
        """Initialize the HTTP metadata handler."""
        self.logger = http_metadata_logger

    async def execute_with_metadata(
        self,
        tool: Any,
        tool_args: Dict[str, Any],
        tool_name: str,
    ) -> Tuple[Any, Optional[Dict[str, Any]]]:
        """Execute tool and capture HTTP metadata if applicable.

        For HTTP request tools, this method executes the tool and captures
        the HTTP request/response metadata from thread-local storage in the
        same execution context.

        Args:
            tool: Tool instance to execute
            tool_args: Arguments to pass to the tool
            tool_name: Name of the tool (for HTTP detection)

        Returns:
            Tuple of (tool_result, http_metadata or None)
        """
        # Check if this is an HTTP request tool
        if not is_http_request_tool(tool_name):
            # Not an HTTP tool, execute normally without metadata capture
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(tool_args)
            else:
                import asyncio

                result = await asyncio.get_event_loop().run_in_executor(
                    None, tool.invoke, tool_args
                )
            return result, None

        # HTTP request tool - need to capture metadata
        self.logger.debug(f"[HTTP-METADATA] Executing HTTP tool: {tool_name}")

        # Get node_id from tool if available (preferred over extracting from name)
        node_id = getattr(tool, "node_id", None)

        if hasattr(tool, "ainvoke"):
            # Async tool execution
            result = await tool.ainvoke(tool_args)

            # Get metadata from shared storage (now accessible across threads)
            metadata = self._get_http_metadata_sync(tool_name, node_id)
        else:
            # Sync tool - execute and get metadata in same thread
            import asyncio

            result, metadata = await asyncio.get_event_loop().run_in_executor(
                None,
                self._execute_tool_with_metadata_sync,
                tool,
                tool_args,
                tool_name,
                node_id,
            )

        if metadata:
            self.logger.info(
                f"[HTTP-METADATA] Successfully captured metadata for {tool_name}"
            )
        else:
            self.logger.warning(
                f"[HTTP-METADATA] Failed to capture metadata for {tool_name}"
            )

        return result, metadata

    def _execute_tool_with_metadata_sync(
        self,
        tool: Any,
        tool_args: Dict[str, Any],
        tool_name: str,
        node_id: Optional[str] = None,
    ) -> Tuple[Any, Optional[Dict[str, Any]]]:
        """Execute tool and capture metadata synchronously in same thread.

        This method runs in a thread pool executor to ensure both tool
        execution and metadata retrieval happen in the same thread, allowing
        access to thread-local storage.

        Args:
            tool: The tool to execute
            tool_args: Tool arguments
            tool_name: Tool name for logging
            node_id: Optional node ID for metadata lookup (preferred over extracting from name)

        Returns:
            Tuple of (tool_result, http_metadata or None)
        """
        # Execute the tool
        result = tool.invoke(tool_args)

        # Immediately capture metadata while still in the same thread
        metadata = self._get_http_metadata_sync(tool_name, node_id)

        if metadata:
            self.logger.debug(
                f"[HTTP-METADATA] Captured in same thread for {tool_name}"
            )
        else:
            self.logger.warning(
                f"[HTTP-METADATA] No metadata found in thread for {tool_name}"
            )

        return result, metadata

    def _get_http_metadata_sync(
        self, tool_name: str, node_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get HTTP metadata synchronously from thread-local storage.

        Args:
            tool_name: Name of the HTTP request tool
            node_id: Optional node ID for lookup (preferred over extracting from name)

        Returns:
            HTTP execution metadata or None
        """
        try:
            from backend.tools.http_request import (
                get_http_execution_for_node,
                get_last_http_execution,
            )

            # Use provided node_id if available, otherwise try to extract from tool name
            lookup_id = node_id
            if not lookup_id:
                lookup_id = extract_node_id_from_tool_name(tool_name)

            if not lookup_id:
                self.logger.warning(
                    f"[HTTP-METADATA] Could not determine node_id for {tool_name}"
                )
                # Still try last execution as fallback
                return get_last_http_execution()

            # Try to get metadata for specific node first
            metadata = get_http_execution_for_node(lookup_id)

            if not metadata:
                # Fallback to last execution
                self.logger.debug(
                    "[HTTP-METADATA] No node-specific metadata, trying last execution"
                )
                metadata = get_last_http_execution()

            return metadata

        except ImportError:
            self.logger.warning(
                "[HTTP-METADATA] HTTP request tools not available (import failed)"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"[HTTP-METADATA] Error getting metadata: {str(e)}",
                exc_info=True,
            )
            return None

    def format_http_execution_record(
        self,
        tool_name: str,
        tool_call_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Format HTTP metadata into execution record format.

        Args:
            tool_name: Name of the HTTP tool
            tool_call_id: ID of the tool call from LLM
            metadata: HTTP metadata dictionary

        Returns:
            Formatted execution record
        """
        record = {
            "tool": tool_name,
            "request": metadata.get("request", {}),
            "response": metadata.get("response", {}),
            "config": metadata.get("config", {}),
            "timestamp": metadata.get("timestamp"),
            "call_id": metadata.get("call_id", tool_call_id),
            "duration": metadata.get("response", {}).get("elapsed", 0),
            "execution_index": 0,
        }

        self.logger.debug(f"[HTTP-METADATA] Formatted execution record for {tool_name}")

        return record
