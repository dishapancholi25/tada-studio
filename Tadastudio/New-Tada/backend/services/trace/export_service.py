"""Export service for trace data in various formats.

Supports JSON, YAML, and OpenTelemetry formats.
"""

from typing import Any, Dict, List, Optional

from ...services.config import get_logger


logger = get_logger("trace_export")


class ExportService:
    """Export trace data in various formats."""

    @classmethod
    def export_as_json(cls, trace_tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export trace tree as JSON.

        Args:
            trace_tree: Trace tree dictionary

        Returns:
            Trace tree (pass-through for JSON)
        """
        return trace_tree

    @classmethod
    def export_as_yaml(cls, trace_tree: Dict[str, Any]) -> str:
        """
        Export trace tree as YAML string.

        Args:
            trace_tree: Trace tree dictionary

        Returns:
            YAML string representation
        """
        import yaml

        return yaml.dump(trace_tree, default_flow_style=False)

    @classmethod
    def export_as_opentelemetry(cls, trace_tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert trace tree to OpenTelemetry format.

        Args:
            trace_tree: Trace tree dictionary

        Returns:
            OpenTelemetry format dictionary
        """
        converter = OpenTelemetryConverter(trace_tree)
        return converter.convert()


class OpenTelemetryConverter:
    """Convert trace tree to OpenTelemetry format."""

    def __init__(self, trace_tree: Dict[str, Any]):
        """Initialize OpenTelemetry converter."""
        self.trace_tree = trace_tree
        self.spans: List[Dict[str, Any]] = []

    def convert(self) -> Dict[str, Any]:
        """
        Convert trace tree to OpenTelemetry format.

        Returns:
            OpenTelemetry format dictionary
        """
        # Process all root nodes
        for root_node in self.trace_tree.get("nodes", []):
            self._create_span(root_node)

        return {
            "data": [
                {
                    "traceID": self.trace_tree["executionId"],
                    "spans": self.spans,
                    "processes": {
                        "nexusagent": {"serviceName": "nexusagent", "tags": []}
                    },
                }
            ]
        }

    def _create_span(
        self, node: Dict[str, Any], parent_span_id: Optional[str] = None
    ) -> None:
        """
        Create OpenTelemetry span from trace node.

        Args:
            node: Trace tree node
            parent_span_id: Parent span ID (if any)
        """
        span = {
            "traceId": self.trace_tree["executionId"],
            "spanId": node["id"],
            "parentSpanId": parent_span_id,
            "operationName": node["name"],
            "startTime": node.get("startTime"),
            "endTime": node.get("endTime"),
            "duration": node.get("duration"),
            "tags": self._build_tags(node),
            "logs": [],
            "process": self._build_process(node),
        }

        self.spans.append(span)

        # Process children recursively
        for child in node.get("children", []):
            self._create_span(child, node["id"])

    def _build_tags(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build OpenTelemetry tags from node metadata.

        Args:
            node: Trace tree node

        Returns:
            Tags dictionary
        """
        tags = {
            "node.type": node["type"],
            "node.status": node["status"],
        }

        # Add token information if available
        tokens = node.get("metadata", {}).get("tokens")
        if tokens:
            tags["tokens.total"] = tokens.get("total")
            tags["tokens.input"] = tokens.get("input")
            tags["tokens.output"] = tokens.get("output")

        # Add cost if available
        cost = node.get("metadata", {}).get("cost")
        if cost:
            tags["cost.total"] = cost

        # Add LLM metadata if available
        llm = node.get("metadata", {}).get("llm")
        if llm:
            tags["llm.model"] = llm.get("model")
            tags["llm.provider"] = llm.get("provider")

        return tags

    def _build_process(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build OpenTelemetry process information.

        Args:
            node: Trace tree node

        Returns:
            Process dictionary
        """
        environment = node.get("metadata", {}).get("environment", {})

        return {
            "serviceName": "nexusagent",
            "tags": environment,
        }
