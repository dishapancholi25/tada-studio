"""Chat response extractor for extracting chat-friendly text from execution output.

This module provides smart extraction of workflow execution output into a format
suitable for display in a chat interface, with multiple fallback strategies.
"""

import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger("chat_response_extractor")

# Keys commonly used for the primary response in END node output
RESPONSE_KEYS = ("response", "message", "answer", "result", "output", "text", "reply")


class ChatResponseExtractor:
    """Extracts chat-friendly text from workflow execution output.

    Uses a smart fallback chain:
    1. END node output_data with known response keys
    2. Last AGENT node's response
    3. Raw output_data from the execution record
    4. Default message
    """

    @staticmethod
    def extract(execution_data: Dict[str, Any]) -> str:
        """Extract a chat-friendly response from execution data.

        Args:
            execution_data: Execution data dict from ExecutionHistoryService.
                Expected to contain 'output_data' and/or 'node_executions'.

        Returns:
            A string suitable for display in a chat bubble.
        """
        if not execution_data:
            return "The workflow completed but produced no response."

        # Strategy 1: Try END node output from node_executions
        node_executions = execution_data.get("node_executions")
        if node_executions:
            end_response = ChatResponseExtractor._extract_from_end_node(node_executions)
            if end_response:
                return end_response

            # Strategy 2: Last AGENT node's response
            agent_response = ChatResponseExtractor._extract_from_last_agent(node_executions)
            if agent_response:
                return agent_response

        # Strategy 3: Use output_data from execution record directly
        output_data = execution_data.get("output_data")
        if output_data:
            extracted = ChatResponseExtractor._extract_from_output_data(output_data)
            if extracted:
                return extracted

        return "The workflow completed but produced no response."

    @staticmethod
    def _extract_from_end_node(node_executions: List[Dict[str, Any]]) -> Optional[str]:
        """Try to extract response from END node output_data."""
        for node in node_executions:
            if node.get("node_type") == "END" and node.get("output_data"):
                output = node["output_data"]
                return ChatResponseExtractor._extract_from_output_data(output)
        return None

    @staticmethod
    def _extract_from_last_agent(node_executions: List[Dict[str, Any]]) -> Optional[str]:
        """Extract response from the last completed AGENT node."""
        agent_nodes = [
            n for n in node_executions
            if n.get("node_type") == "AGENT" and n.get("status") == "completed"
        ]

        if not agent_nodes:
            return None

        # Sort by end_time to get the last one
        agent_nodes.sort(key=lambda x: x.get("end_time") or "")
        last_agent = agent_nodes[-1]

        output = last_agent.get("output_data")
        if output:
            return ChatResponseExtractor._extract_from_output_data(output)

        return None

    @staticmethod
    def _extract_from_nodes_list(nodes: List[Dict[str, Any]]) -> Optional[str]:
        """Extract chat response from a list of node output dicts.

        Handles the OutputProcessor "full" and "summary" formats where output
        is a list of node entries with 'node' and 'response' keys.

        Filters out START nodes (they just echo user input) and formats
        remaining nodes as markdown sections for multi-agent workflows.
        """
        if not nodes:
            return None

        # Filter out START nodes
        agent_nodes = [
            n for n in nodes
            if isinstance(n, dict) and n.get("node", "").lower() != "start"
        ]

        if not agent_nodes:
            return None

        # Always return only the last agent's response — no node-name section headers
        last_node = agent_nodes[-1]
        response = last_node.get("response", "")
        return response if isinstance(response, str) and response.strip() else None

    @staticmethod
    def _extract_from_output_data(output: Any) -> Optional[str]:
        """Extract a string from output_data using smart key lookup.

        Handles dict, string, and other types.
        """
        if isinstance(output, str):
            return output if output.strip() else None

        if isinstance(output, dict):
            # Handle OutputProcessor "full" format: {"nodes": [...], "_metadata": {...}}
            if "nodes" in output and isinstance(output["nodes"], list):
                extracted = ChatResponseExtractor._extract_from_nodes_list(output["nodes"])
                if extracted:
                    return extracted

            # Handle OutputProcessor "summary" format: {"results": [...], "_metadata": {...}}
            if "results" in output and isinstance(output["results"], list):
                extracted = ChatResponseExtractor._extract_from_nodes_list(output["results"])
                if extracted:
                    return extracted

            # Check known response keys at top level
            for key in RESPONSE_KEYS:
                if key in output:
                    value = output[key]
                    if isinstance(value, str) and value.strip():
                        return value
                    if value is not None:
                        return str(value)

            # Check nested "data" dict
            if "data" in output and isinstance(output["data"], dict):
                for key in RESPONSE_KEYS:
                    if key in output["data"]:
                        value = output["data"][key]
                        if isinstance(value, str) and value.strip():
                            return value
                        if value is not None:
                            return str(value)

            # Multi-node output: return the last node's meaningful response (no headers)
            if all(isinstance(v, dict) for v in output.values()) and len(output) > 1:
                last_text = None
                for node_name, node_output in output.items():
                    if isinstance(node_output, dict):
                        node_text = None
                        for key in RESPONSE_KEYS:
                            if key in node_output:
                                node_text = str(node_output[key])
                                break
                        if not node_text:
                            raw = node_output.get("raw")
                            node_text = str(raw) if raw else None
                        if node_text and node_text.strip():
                            last_text = node_text
                    elif isinstance(node_output, str) and node_output.strip():
                        last_text = node_output
                return last_text or str(output)

            # Single value dict — return the value
            if len(output) == 1:
                value = next(iter(output.values()))
                if isinstance(value, str) and value.strip():
                    return value
                if value is not None:
                    return str(value)

            # Fallback: stringify the dict
            return str(output)

        if output is not None:
            return str(output)

        return None
