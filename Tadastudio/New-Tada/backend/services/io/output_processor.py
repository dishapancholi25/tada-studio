"""
Output Processor.

Processes END node output based on configuration.
"""

from typing import Any, Dict

from backend.models.workflow import EndNodeConfig, EnhancedNodeData, GraphData
from backend.services.workflow.state import WorkflowState


class OutputProcessor:
    """
    Processes END node output according to configuration.

    Supports multiple output structures:
    - full: Comprehensive output with all node details
    - summary: Simplified output with key information
    - compact: Minimal output with just responses
    - custom: Fallback to current behavior
    """

    @staticmethod
    def process(
        state: WorkflowState, end_node: EnhancedNodeData, graph: GraphData
    ) -> Dict[str, Any]:
        """
        Process END node output based on configuration.

        Args:
            state: Current workflow state
            end_node: The END node
            graph: The graph definition

        Returns:
            Formatted output respecting EndNodeConfig settings
        """
        # Get END node configuration or use defaults
        config = OutputProcessor._get_config(end_node)

        # Get data from state
        all_node_outputs = state.get("node_outputs", {})
        all_results = state.get("results", [])
        node_id_to_name = {node.uniq_id: node.name for node in graph.nodes}

        # Filter node IDs based on input_source
        filtered_node_ids = OutputProcessor._filter_nodes(
            config, end_node, graph, all_node_outputs
        )

        # Build output based on output_structure
        output = OutputProcessor._build_output(
            config, filtered_node_ids, all_node_outputs, all_results, node_id_to_name
        )

        # Add metadata if configured
        if config.include_metadata:
            output = OutputProcessor._add_metadata(
                output, state, filtered_node_ids, all_node_outputs
            )

        return output

    @staticmethod
    def _get_config(end_node: EnhancedNodeData) -> EndNodeConfig:
        """
        Get END node configuration.

        Args:
            end_node: The END node

        Returns:
            EndNodeConfig object
        """
        if end_node.end_node_config:
            if isinstance(end_node.end_node_config, dict):
                # Convert dict to EndNodeConfig object
                return EndNodeConfig(**end_node.end_node_config)
            else:
                return end_node.end_node_config
        else:
            return EndNodeConfig()

    @staticmethod
    def _filter_nodes(
        config: EndNodeConfig,
        end_node: EnhancedNodeData,
        graph: GraphData,
        all_node_outputs: dict,
    ) -> list:
        """
        Filter node IDs based on input_source configuration.

        Args:
            config: END node configuration
            end_node: The END node
            graph: The graph definition
            all_node_outputs: All node outputs from state

        Returns:
            List of filtered node IDs
        """
        if config.input_source == "all":
            return list(all_node_outputs.keys())

        elif config.input_source == "previous":
            # Get nodes that connect to the END node
            incoming_connections = [
                conn for conn in graph.connections if conn.target_id == end_node.uniq_id
            ]
            return [conn.source_id for conn in incoming_connections]

        elif config.input_source in ["specific", "multiple"]:
            return config.source_node_ids

        return []

    @staticmethod
    def _build_output(
        config: EndNodeConfig,
        filtered_node_ids: list,
        all_node_outputs: dict,
        all_results: list,
        node_id_to_name: dict,
    ) -> Any:
        """
        Build output based on output_structure configuration.

        Args:
            config: END node configuration
            filtered_node_ids: Filtered node IDs
            all_node_outputs: All node outputs
            all_results: All results
            node_id_to_name: Node ID to name mapping

        Returns:
            Formatted output
        """
        if config.output_structure == "full":
            return OutputProcessor._build_full_output(
                config,
                filtered_node_ids,
                all_node_outputs,
                all_results,
                node_id_to_name,
            )
        elif config.output_structure == "summary":
            return OutputProcessor._build_summary_output(
                config,
                filtered_node_ids,
                all_node_outputs,
                all_results,
                node_id_to_name,
            )
        elif config.output_structure == "compact":
            return OutputProcessor._build_compact_output(
                config, filtered_node_ids, all_node_outputs, node_id_to_name
            )
        else:  # custom or unknown - fall back to current behavior
            return {"results": all_results, "node_outputs": all_node_outputs}

    @staticmethod
    def _build_full_output(
        config: EndNodeConfig,
        filtered_node_ids: list,
        all_node_outputs: dict,
        all_results: list,
        node_id_to_name: dict,
    ) -> Dict[str, Any]:
        """
        Build comprehensive full output.

        Args:
            config: END node configuration
            filtered_node_ids: Filtered node IDs
            all_node_outputs: All node outputs
            all_results: All results
            node_id_to_name: Node ID to name mapping

        Returns:
            Full output dictionary
        """
        formatted_nodes = []

        for node_id in filtered_node_ids:
            if node_id in all_node_outputs:
                node_name = node_id_to_name.get(node_id, node_id)
                node_output = all_node_outputs[node_id]

                # Build comprehensive node entry
                node_entry = {
                    "node": node_name if config.include_node_names else node_id,
                    "node_id": node_id,
                    "response": node_output.get("raw", ""),
                }

                # Add structured data only if it exists
                if node_output.get("structured") is not None:
                    node_entry["structured"] = node_output["structured"]

                # Add fields only if they exist and are not empty
                if node_output.get("fields") and node_output["fields"]:
                    node_entry["fields"] = node_output["fields"]

                # Find corresponding result for tool execution info
                for result in all_results:
                    if result.get("agent") == node_name:
                        # Add tool information if present
                        if result.get("tools"):
                            node_entry["tools"] = result["tools"]
                        if result.get("tool_executions"):
                            node_entry["tool_executions"] = result["tool_executions"]
                        break

                formatted_nodes.append(node_entry)

        return {"nodes": formatted_nodes}

    @staticmethod
    def _build_summary_output(
        config: EndNodeConfig,
        filtered_node_ids: list,
        all_node_outputs: dict,
        all_results: list,
        node_id_to_name: dict,
    ) -> list:
        """
        Build summary output.

        Args:
            config: END node configuration
            filtered_node_ids: Filtered node IDs
            all_node_outputs: All node outputs
            all_results: All results
            node_id_to_name: Node ID to name mapping

        Returns:
            Summary output list
        """
        filtered_results = []

        for node_id in filtered_node_ids:
            node_name = node_id_to_name.get(node_id, node_id)
            if node_id in all_node_outputs:
                node_output = all_node_outputs[node_id]
                result_entry = {
                    "node": node_name if config.include_node_names else node_id,
                    "response": node_output.get("raw", ""),
                }

                # Find corresponding result for tool info
                for result in all_results:
                    if result.get("agent") == node_name:
                        if result.get("tool_executions"):
                            result_entry["tools_used"] = len(
                                result.get("tool_executions", [])
                            )
                        break

                filtered_results.append(result_entry)

        return filtered_results

    @staticmethod
    def _build_compact_output(
        config: EndNodeConfig,
        filtered_node_ids: list,
        all_node_outputs: dict,
        node_id_to_name: dict,
    ) -> Dict[str, str]:
        """
        Build compact output.

        Args:
            config: END node configuration
            filtered_node_ids: Filtered node IDs
            all_node_outputs: All node outputs
            node_id_to_name: Node ID to name mapping

        Returns:
            Compact output dictionary
        """
        output = {}

        for node_id in filtered_node_ids:
            if node_id in all_node_outputs:
                node_name = node_id_to_name.get(node_id, node_id)
                node_output = all_node_outputs[node_id]

                # Use node name as key if configured
                key = node_name if config.include_node_names else node_id
                output[key] = node_output.get("raw", "")

        return output

    @staticmethod
    def _add_metadata(
        output: Any,
        state: WorkflowState,
        filtered_node_ids: list,
        all_node_outputs: dict,
    ) -> Any:
        """
        Add metadata to output.

        Args:
            output: Current output
            state: Workflow state
            filtered_node_ids: Filtered node IDs
            all_node_outputs: All node outputs

        Returns:
            Output with metadata added
        """
        metadata = {
            "execution_id": state.get("execution_id"),
            "graph_name": state.get("graph_name"),
            "nodes_included": len(filtered_node_ids),
            "total_nodes": len(all_node_outputs),
        }

        if isinstance(output, dict):
            output["_metadata"] = metadata
        elif isinstance(output, list):
            # Convert to dict to add metadata
            output = {"results": output, "_metadata": metadata}

        return output
