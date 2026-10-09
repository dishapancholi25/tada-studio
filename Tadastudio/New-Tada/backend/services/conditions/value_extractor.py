"""
Value Extractor for Condition Evaluation.

Extracts values from workflow state based on condition configuration.
"""

import json
import re
from typing import Any

from backend.services.config import get_logger
from backend.services.execution.logging import execution_logger
from backend.services.workflow.state import WorkflowState

value_extractor_logger = get_logger("conditions.value_extractor")


class ValueExtractor:
    """
    Extracts values from workflow state for condition evaluation.

    Handles multiple input sources:
    - previous: Last message content
    - specific: Specific node output
    - start: Original workflow message
    - static: Static value
    """

    def extract(self, state: WorkflowState, condition_config: Any) -> Any:
        """
        Extract value from state based on condition configuration.

        Args:
            state: The workflow state
            condition_config: Configuration specifying source and extraction rules

        Returns:
            The extracted value
        """
        # Parse configuration
        config = self._parse_config(condition_config)
        input_source = config["input_source"]
        source_node_id = config["source_node_id"]
        field_path = config["field_path"]

        value_extractor_logger.info(
            f"  Extracting value: source={input_source!r}, "
            f"source_node_id={source_node_id!r}, field_path={field_path!r}"
        )

        # Route to appropriate extraction method
        if input_source == "previous":
            result = self._extract_from_previous(state, field_path)
        elif input_source == "specific":
            result = self._extract_from_specific_node(state, source_node_id, field_path)
        elif input_source == "start":
            result = self._extract_from_start(state)
        elif input_source == "static":
            result = self._extract_static_value(condition_config)
        elif input_source == "custom":
            result = self._extract_from_custom_template(state, condition_config)
        elif input_source == "field":
            result = self._extract_from_field(state, field_path)
        else:
            execution_logger.warning(f"Unknown input source: {input_source}")
            result = ""

        # Truncate long values for logging
        result_repr = repr(result)
        if len(result_repr) > 200:
            result_repr = result_repr[:200] + "..."
        value_extractor_logger.info(
            f"  Extracted result: {result_repr} (type={type(result).__name__})"
        )
        return result

    def _parse_config(self, condition_config: Any) -> dict:
        """
        Parse condition configuration to extract common fields.

        Handles both dict and dataclass formats.
        """
        # Handle both dict and dataclass formats
        if hasattr(condition_config, "__dict__"):
            # It's a dataclass
            simple_conditions = getattr(condition_config, "simple_conditions", [])
        else:
            # It's a dict
            simple_conditions = condition_config.get("simple_conditions", [])

        # Extract configuration from first simple condition if available
        if simple_conditions and len(simple_conditions) > 0:
            condition = simple_conditions[0]
            if hasattr(condition, "__dict__"):
                # Dataclass format
                return {
                    "input_source": getattr(condition, "input_source", "previous"),
                    "source_node_id": getattr(condition, "source_node_id", None),
                    "field_path": getattr(condition, "field_path", ""),
                }
            else:
                # Dict format
                return {
                    "input_source": condition.get("input_source", "previous"),
                    "source_node_id": condition.get("source_node_id"),
                    "field_path": condition.get("field_path", ""),
                }
        else:
            # Fall back to condition_config itself
            if hasattr(condition_config, "__dict__"):
                # Dataclass format
                return {
                    "input_source": getattr(
                        condition_config, "input_source", "previous"
                    ),
                    "source_node_id": getattr(condition_config, "source_node_id", None),
                    "field_path": getattr(condition_config, "field_path", ""),
                }
            else:
                # Dict format
                return {
                    "input_source": condition_config.get("input_source", "previous"),
                    "source_node_id": condition_config.get("source_node_id"),
                    "field_path": condition_config.get("field_path", ""),
                }

    def _extract_from_previous(self, state: WorkflowState, field_path: str) -> Any:
        """
        Extract value from the last message in state.

        Args:
            state: The workflow state
            field_path: Optional field path for nested extraction

        Returns:
            The extracted value or empty string
        """
        if state.get("messages"):
            last_msg = state["messages"][-1]
            # Check if the message has structured content
            if hasattr(last_msg, "content"):
                content = last_msg.content
                # Try to parse as JSON for structured data
                if isinstance(content, str) and field_path:
                    try:
                        data = json.loads(content)
                        return self._extract_field_value(data, field_path)
                    except (json.JSONDecodeError, TypeError):
                        pass
                return content
        return ""

    def _extract_from_specific_node(
        self, state: WorkflowState, source_node_id: str, field_path: str
    ) -> Any:
        """
        Extract value from a specific node's output.

        Tries multiple locations in order:
        1. fields dictionary
        2. structured_output
        3. raw output (parsed as JSON if needed)

        Args:
            state: The workflow state
            source_node_id: ID of the source node
            field_path: Optional field path for nested extraction

        Returns:
            The extracted value or empty string
        """
        if source_node_id and source_node_id in state.get("node_outputs", {}):
            output = state["node_outputs"][source_node_id]
            available_keys = list(output.keys()) if isinstance(output, dict) else []
            value_extractor_logger.debug(
                f"    Node output keys for {source_node_id}: {available_keys}"
            )

            # Enhanced field extraction
            if field_path:
                # First try fields dictionary
                if output.get("fields"):
                    value = self._extract_field_value(output["fields"], field_path)
                    if value is not None:
                        value_extractor_logger.info(
                            f"    Found via fields[{field_path!r}]: {value!r}"
                        )
                        return value

                # Then try structured_output
                if output.get("structured_output"):
                    value = self._extract_field_value(
                        output["structured_output"], field_path
                    )
                    if value is not None:
                        value_extractor_logger.info(
                            f"    Found via structured_output[{field_path!r}]: {value!r}"
                        )
                        return value

                # Finally try raw output as JSON
                raw = output.get("raw", "")
                if raw:
                    try:
                        data = json.loads(raw) if isinstance(raw, str) else raw
                        value = self._extract_field_value(data, field_path)
                        if value is not None:
                            value_extractor_logger.info(
                                f"    Found via raw JSON[{field_path!r}]: {value!r}"
                            )
                            return value
                    except (json.JSONDecodeError, TypeError):
                        pass

                value_extractor_logger.warning(
                    f"    Field path {field_path!r} not found in node {source_node_id} output"
                )

            # Fall back to raw output
            raw_value = output.get("raw", "")
            value_extractor_logger.info(
                f"    Falling back to raw output (len={len(str(raw_value))})"
            )
            return raw_value
        else:
            available_nodes = list(state.get("node_outputs", {}).keys())
            value_extractor_logger.warning(
                f"    Node {source_node_id!r} not found in node_outputs. "
                f"Available: {available_nodes}"
            )
        return ""

    def _extract_from_start(self, state: WorkflowState) -> Any:
        """
        Extract value from the original workflow message.

        Args:
            state: The workflow state

        Returns:
            The original message or empty string
        """
        return state.get("original_message", "")

    def _extract_static_value(self, condition_config: Any) -> Any:
        """
        Extract static value from configuration.

        Args:
            condition_config: The condition configuration

        Returns:
            The static value or empty string
        """
        # Handle both dict and dataclass formats
        if hasattr(condition_config, "__dict__"):
            return getattr(condition_config, "value", "")
        else:
            return condition_config.get("value", "")

    def _extract_from_custom_template(
        self, state: WorkflowState, condition_config: Any
    ) -> Any:
        """
        Extract value using custom template with variable substitution.

        Supports placeholders:
        - {original} - Original workflow input
        - {previous} - Last message content
        - {node_id} - Raw output from a specific node
        - {node_id.field} - Specific field from a node's output

        Args:
            state: The workflow state
            condition_config: Configuration with custom_template

        Returns:
            The template with substituted values
        """
        if hasattr(condition_config, "__dict__"):
            template = getattr(condition_config, "custom_template", "")
        else:
            template = condition_config.get("custom_template", "")

        if not template:
            return ""

        # Replace {original} with original message
        template = template.replace("{original}", state.get("original_message", ""))

        # Replace {previous} with last message content
        messages = state.get("messages", [])
        if messages:
            last_content = getattr(messages[-1], "content", "")
            template = template.replace("{previous}", str(last_content))

        # Replace {node_id.field} patterns first (more specific)
        node_outputs = state.get("node_outputs", {})
        field_pattern = re.compile(r"\{([^}]+)\.([^}]+)\}")
        for match in field_pattern.finditer(template):
            node_id = match.group(1)
            field = match.group(2)
            if node_id in node_outputs:
                output = node_outputs[node_id]
                # Try fields dict first, then structured_output, then raw as JSON
                value = None
                if output.get("fields"):
                    value = self._extract_field_value(output["fields"], field)
                if value is None and output.get("structured_output"):
                    value = self._extract_field_value(
                        output["structured_output"], field
                    )
                if value is None:
                    raw = output.get("raw", "")
                    if raw:
                        try:
                            data = json.loads(raw) if isinstance(raw, str) else raw
                            value = self._extract_field_value(data, field)
                        except (json.JSONDecodeError, TypeError):
                            pass
                template = template.replace(
                    match.group(0), str(value) if value is not None else ""
                )

        # Replace {node_id} patterns (raw output)
        node_pattern = re.compile(r"\{([^}.]+)\}")
        for match in node_pattern.finditer(template):
            node_id = match.group(1)
            if node_id in node_outputs:
                template = template.replace(
                    match.group(0), node_outputs[node_id].get("raw", "")
                )

        return template

    def _extract_from_field(self, state: WorkflowState, field_path: str) -> Any:
        """
        Extract value from workflow state using dot notation field path.

        Args:
            state: The workflow state
            field_path: Dot-separated path into the state

        Returns:
            The extracted value or empty string
        """
        if not field_path:
            return ""

        try:
            current = state
            for part in field_path.split("."):
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return ""
                if current is None:
                    return ""
            return str(current) if current is not None else ""
        except Exception:
            return ""

    @staticmethod
    def _extract_field_value(data: Any, field_path: str) -> Any:
        """
        Extract a value from nested data using dot notation field path.

        Supports:
        - Dictionary keys: data.key
        - List indices: data.0
        - Object attributes: data.attr
        - Nested paths: data.key.0.attr

        Args:
            data: The data structure to extract from
            field_path: Dot-separated path to the field

        Returns:
            The extracted value or None if path is invalid
        """
        if not field_path or data is None:
            return data

        # Split the field path by dots for nested access
        parts = field_path.split(".")
        current = data

        for part in parts:
            if current is None:
                return None

            # Handle dictionary access
            if isinstance(current, dict):
                current = current.get(part)
            # Handle list/array access with index
            elif isinstance(current, (list, tuple)) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            # Handle object attribute access
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current
