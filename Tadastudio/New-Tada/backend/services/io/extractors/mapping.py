"""
Mapping Value Extractor.

Extracts values for column/parameter mappings from various sources.
"""

from typing import Any, List, Optional

from langchain_core.messages import HumanMessage
from backend.services.workflow.state import WorkflowState

from .field import FieldExtractor


class MappingValueExtractor:
    """
    Extracts values for column/parameter mappings.

    Supports multiple source modes:
    - static: Use static value
    - previous: Get from previous node
    - specific: Get from specific node
    - field: Get a specific field from a specific node's structured output
    - template: Render a {{variable}} template against workflow state
    - start: Get from workflow start
    """

    def __init__(self):
        """Initialize the mapping value extractor."""
        self.field_extractor = FieldExtractor()

    def extract(
        self,
        source_mode: str,
        state: WorkflowState,
        static_value: Any = None,
        default_value: Any = None,
        source_node_id: Optional[str] = None,
        source_field_path: Optional[str] = None,
        idx: int = 0,
        sql_expressions: Optional[List[int]] = None,
        custom_template: Optional[str] = None,
    ) -> Any:
        """
        Extract a value for a column/parameter mapping based on source configuration.

        Args:
            source_mode: How to get the value (static, previous, specific, start)
            state: Current workflow state
            static_value: Static value to use if source_mode is "static"
            default_value: Default value to use if extraction fails
            source_node_id: ID of node to extract from if source_mode is "specific"
            source_field_path: Path to field in node output (e.g., "Country")
            idx: Index for SQL expression tracking
            sql_expressions: List to track SQL expression indices

        Returns:
            The extracted value
        """
        if source_mode == "static":
            return self._extract_static(static_value, idx, sql_expressions)
        elif source_mode == "previous":
            return self._extract_from_previous(state, default_value)
        elif source_mode in ("specific", "field"):
            # "field" is the same lookup as "specific"; the UI just offers a
            # field picker instead of a free-text path.
            return self._extract_from_specific(
                state, source_node_id, source_field_path, default_value
            )
        elif source_mode == "template":
            return self._extract_from_template(custom_template, state, default_value)
        elif source_mode == "start":
            return self._extract_from_start(state, default_value)
        else:
            return default_value

    def _extract_from_template(
        self, custom_template: Optional[str], state: WorkflowState, default_value: Any
    ) -> Any:
        """
        Render a {{variable}} template against the workflow state.

        Args:
            custom_template: Template string, e.g. "Bearer {{access_token}}"
            state: Current workflow state
            default_value: Default value if no template is configured

        Returns:
            The rendered string, or default_value when no template is set
        """
        if not custom_template:
            return default_value

        from backend.services.io.template_processor import TemplateProcessor

        return TemplateProcessor().process(custom_template, state)

    def _extract_static(
        self, static_value: Any, idx: int, sql_expressions: Optional[List[int]]
    ) -> Any:
        """
        Extract static value, handling SQL functions.

        Args:
            static_value: The static value
            idx: Index for SQL expression tracking
            sql_expressions: List to track SQL expression indices

        Returns:
            The static value (normalized if SQL function)
        """
        # Check if this is a SQL function/expression
        if (
            static_value
            and isinstance(static_value, str)
            and static_value.upper()
            in ["CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME", "NOW()"]
        ):
            # Mark this as a SQL expression
            if sql_expressions is not None:
                sql_expressions.append(idx)
            return static_value.upper()  # Normalize to uppercase
        else:
            return static_value

    def _extract_from_previous(self, state: WorkflowState, default_value: Any) -> Any:
        """
        Extract value from previous node output.

        Args:
            state: Current workflow state
            default_value: Default value if extraction fails

        Returns:
            The extracted value
        """
        if state.get("results"):
            prev_result = state["results"][-1]
            return prev_result.get("output", default_value)
        return default_value

    def _extract_from_specific(
        self,
        state: WorkflowState,
        source_node_id: Optional[str],
        source_field_path: Optional[str],
        default_value: Any,
    ) -> Any:
        """
        Extract value from specific node output.

        Args:
            state: Current workflow state
            source_node_id: ID of the source node
            source_field_path: Path to field in output
            default_value: Default value if extraction fails

        Returns:
            The extracted value
        """
        if not source_node_id:
            return default_value

        node_outputs = state.get("node_outputs", {})
        if source_node_id in node_outputs:
            output = node_outputs[source_node_id]
            return self.field_extractor.extract(
                output, source_field_path, default_value
            )
        return default_value

    def _extract_from_start(self, state: WorkflowState, default_value: Any) -> Any:
        """
        Extract value from workflow start.

        Args:
            state: Current workflow state
            default_value: Default value if extraction fails

        Returns:
            The extracted value
        """
        # Check messages first
        if state.get("messages"):
            first_message = state["messages"][0]
            if isinstance(first_message, HumanMessage):
                return first_message.content
        return state.get("original_message", default_value)
