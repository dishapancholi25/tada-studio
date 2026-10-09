"""Node type mapping and transformation utilities for trace visualization."""

from typing import Any, Dict, List


class NodeMapper:
    """Map and transform node types for trace tree visualization."""

    NODE_TYPE_MAPPING = {
        "AGENT": "agent",
        "TOOL": "tool",
        "CONDITION": "condition",
        "HUMAN": "human",
        "ORCHESTRATOR": "orchestrator",
        "SUBGRAPH": "subgraph",
        "CHECKPOINT": "checkpoint",
        "START": "start",
        "END": "end",
        # Specific tool types - keep as tool but preserve original for metadata
        "DOCUMENT_SEARCH": "tool",
        "DATABASE_QUERY": "tool",
        "DATABASE_INSERT": "tool",
        "HTTP_REQUEST": "tool",
        "HTTP_REQUEST_ACTION": "tool",
        "WEB_SEARCH": "tool",
        "EMAIL_SEND": "tool",
        "FILE_READ": "tool",
        "MCP_SERVER": "tool",
        "SUBWORKFLOW": "subgraph",
        "LLM": "llm",  # Special type for direct LLM calls
    }

    @classmethod
    def map_node_type(cls, node_type: str) -> str:
        """
        Map internal node types to trace viewer types.

        Args:
            node_type: Internal node type string

        Returns:
            Mapped node type for trace viewer
        """
        return cls.NODE_TYPE_MAPPING.get(node_type, "unknown")

    @classmethod
    def extract_llm_calls_from_agent(cls, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract LLM calls as separate nodes from agent execution.

        This creates child nodes representing individual LLM calls within an agent,
        allowing for detailed visualization of LLM interactions.

        Args:
            node: Agent node dictionary containing message structure and LLM metadata

        Returns:
            List of LLM call node dictionaries
        """
        llm_nodes = []

        # If this agent has message structure, create LLM call nodes
        if not node.get("message_structure") or not node.get("llm_metadata"):
            return llm_nodes

        messages = node["message_structure"].get("messages", [])

        # Find assistant messages (LLM responses)
        for i, msg in enumerate(messages):
            if msg.get("role") != "assistant":
                continue

            llm_node = {
                "id": f"{node['id']}_llm_{i}",
                "name": f"LLM Call ({node['llm_metadata'].get('model', 'unknown')})",
                "type": "llm",
                "status": node["status"],
                "startTime": node.get("start_time"),
                "endTime": node.get("end_time"),
                "duration": node.get("duration_seconds"),
                "children": [],
                "metadata": cls._build_llm_metadata(node, msg),
                "input": {
                    "messages": messages[
                        : i + 1
                    ]  # Include all messages up to this response
                },
                "output": msg.get("content"),
                "error": None,
                "parent_id": node["id"],  # Track parent for hierarchy
            }
            llm_nodes.append(llm_node)

        return llm_nodes

    @classmethod
    def _build_llm_metadata(
        cls, node: Dict[str, Any], msg: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build metadata dictionary for LLM call node.

        Args:
            node: Parent agent node
            msg: Message dictionary

        Returns:
            Metadata dictionary for LLM call
        """
        llm_metadata = node.get("llm_metadata", {})

        metadata = {
            "model": llm_metadata.get("model"),
            "provider": llm_metadata.get("provider"),
            "temperature": llm_metadata.get("temperature"),
            "tokens": {
                "input": node.get("input_tokens"),
                "output": node.get("output_tokens"),
                "total": node.get("total_tokens"),
            },
            "cost": node.get("total_cost"),
            "performance": {
                "time_to_first_token": llm_metadata.get("time_to_first_token"),
                "tokens_per_second": llm_metadata.get("tokens_per_second"),
                "total_latency_ms": llm_metadata.get("total_latency_ms"),
            },
        }

        if llm_metadata.get("pricing_source"):
            metadata["pricing_source"] = llm_metadata["pricing_source"]

        return metadata

    @classmethod
    def create_trace_node(cls, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a database node into a trace tree node.

        Args:
            node: Node dictionary from database

        Returns:
            Trace tree node dictionary
        """
        from .cost_calculator import CostCalculator

        trace_node = {
            "id": node["id"],  # Database ID for uniqueness in UI
            "nodeId": node["node_id"],  # Graph node ID for relationships
            "name": node["node_name"],
            "type": cls.map_node_type(node["node_type"]),
            "status": node["status"],
            "startTime": node.get("start_time"),
            "endTime": node.get("end_time"),
            "duration": node.get("duration_seconds"),
            "executionOrder": node.get("execution_order"),
            "children": [],
            "metadata": cls._build_node_metadata(node),
            "input": node.get("input_data"),
            "output": node.get("output_data"),
            "error": node.get("error_message"),
            "messages": node.get("message_structure", {}).get("messages")
            if node.get("message_structure")
            else None,
        }

        # Calculate cost from tokens if total_cost is null but tokens exist
        if not node.get("total_cost") and node.get("total_tokens"):
            input_tokens = node.get("input_tokens")
            output_tokens = node.get("output_tokens")
            llm_meta = node.get("llm_metadata") or {}
            model = llm_meta.get("model")
            custom_input_cost = llm_meta.get("custom_input_cost")
            custom_output_cost = llm_meta.get("custom_output_cost")

            model_key = model.lower() if model else "gpt-4o"
            _rates, pricing_source = CostCalculator._resolve_pricing(
                model_key, custom_input_cost, custom_output_cost
            )

            calculated_cost = CostCalculator.calculate_node_cost(
                input_tokens,
                output_tokens,
                model,
                custom_input_cost,
                custom_output_cost,
            )
            if calculated_cost:
                trace_node["metadata"]["cost"] = calculated_cost
                trace_node["metadata"]["cost_estimated"] = True
                trace_node["metadata"]["pricing_source"] = pricing_source
                if trace_node["metadata"].get("llm"):
                    trace_node["metadata"]["llm"]["pricing_source"] = pricing_source
                    trace_node["metadata"]["llm"]["cost_estimated"] = True

        return trace_node

    @classmethod
    def _build_node_metadata(cls, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build metadata dictionary for trace node.

        Args:
            node: Node dictionary from database

        Returns:
            Metadata dictionary
        """
        metadata = {
            "nodeType": node["node_type"],  # Original node type for specific icons
            "isSubAgent": node.get("is_sub_agent", False),
        }

        # Add token information if any token field is populated
        input_t = node.get("input_tokens") or 0
        output_t = node.get("output_tokens") or 0
        total_t = node.get("total_tokens") or 0
        if total_t or input_t or output_t:
            metadata["tokens"] = {
                "input": input_t,
                "output": output_t,
                "total": total_t or (input_t + output_t),
            }

        # Add cost if available
        if node.get("total_cost"):
            metadata["cost"] = node.get("total_cost")

        # Add metadata objects if present
        if node.get("llm_metadata"):
            metadata["llm"] = node.get("llm_metadata")
        if node.get("tool_metadata"):
            metadata["tool"] = node.get("tool_metadata")
        if node.get("orchestration_metadata"):
            metadata["orchestration"] = node.get("orchestration_metadata")
        if node.get("memory_metadata"):
            metadata["memory"] = node.get("memory_metadata")
        if node.get("environment_metadata"):
            metadata["environment"] = node.get("environment_metadata")

        # For DOCUMENT_SEARCH nodes, extract embedding data from node_metadata
        if node["node_type"] == "DOCUMENT_SEARCH":
            node_meta = node.get("node_metadata") or {}
            if node_meta.get("embedding_tokens") or node_meta.get("embedding_model"):
                metadata["embedding"] = {
                    "tokens": node_meta.get("embedding_tokens", 0),
                    "cost": node_meta.get("embedding_cost", 0.0),
                    "model": node_meta.get("embedding_model", ""),
                }

        return metadata
