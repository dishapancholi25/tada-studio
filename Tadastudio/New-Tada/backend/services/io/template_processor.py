"""
Template Processor.

Processes template strings with variable substitution.
"""

import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from backend.services.workflow.state import WorkflowState

from .extractors import FieldExtractor


class TemplateProcessor:
    """
    Processes template strings with {{variable}} placeholders.

    Replaces variables with values from workflow state, including:
    - message: Last message content
    - original_message: First message content
    - Direct state fields
    - Node output fields
    """

    def __init__(self):
        """Initialize the template processor."""
        self.field_extractor = FieldExtractor()

    def process(self, template: str, state: WorkflowState) -> str:
        """
        Replace {{variable}} templates with values from state.

        Args:
            template: Template string with {{variable}} placeholders
            state: Current workflow state

        Returns:
            String with variables replaced
        """
        if not template:
            return template

        # Find all template variables
        matches = self._find_template_variables(template)

        # Replace each variable
        result = template
        for match in matches:
            value = self._extract_variable_value(match, state)
            result = result.replace(f"{{{{{match}}}}}", str(value))

        return result

    def _find_template_variables(self, template: str) -> list:
        """
        Find all {{variable}} patterns in template.

        Args:
            template: Template string

        Returns:
            List of variable names
        """
        # Dots are allowed so nested paths work, e.g. {{data.access_token}}
        pattern = r"\{\{([\w.]+)\}\}"
        return re.findall(pattern, template)

    def _extract_variable_value(self, variable_name: str, state: WorkflowState) -> str:
        """
        Extract value for a template variable.

        Args:
            variable_name: Name of the variable
            state: Workflow state

        Returns:
            Variable value as string
        """
        # Check special variables first
        if variable_name == "message":
            return self._extract_last_message(state)
        elif variable_name == "original_message":
            return self._extract_first_message(state)
        elif variable_name in state:
            return state[variable_name]
        else:
            return self._extract_from_node_outputs(variable_name, state)

    def _extract_last_message(self, state: WorkflowState) -> str:
        """
        Extract the last message content.

        Args:
            state: Workflow state

        Returns:
            Last message content or empty string
        """
        if state.get("messages"):
            last_message = state["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
        return ""

    def _extract_first_message(self, state: WorkflowState) -> str:
        """
        Extract the first message content.

        Args:
            state: Workflow state

        Returns:
            First message content or empty string
        """
        if state.get("messages"):
            first_message = state["messages"][0]
            if isinstance(first_message, HumanMessage):
                return first_message.content
        return ""

    def _extract_from_node_outputs(
        self, variable_name: str, state: WorkflowState
    ) -> str:
        """
        Extract variable from node outputs.

        Args:
            variable_name: Variable name to find
            state: Workflow state

        Returns:
            Variable value or empty string
        """
        node_outputs = state.get("node_outputs", {})

        # Pass 1: exact path match (supports dot notation, e.g. data.access_token)
        for output in node_outputs.values():
            if isinstance(output, dict):
                extracted = self.field_extractor.extract(output, variable_name, None)
                if extracted is not None:
                    return extracted

        # Pass 2: bare names may live nested in the response, e.g. an OAuth
        # token at data.access_token referenced as {{access_token}}. Search
        # each node output depth-first and return the first match.
        if "." not in variable_name:
            for output in node_outputs.values():
                found = self._search_nested(output, variable_name)
                if found is not None:
                    return found
        return ""

    def _search_nested(self, data: Any, key: str) -> Optional[Any]:
        """
        Depth-first search for a scalar value stored under ``key``.

        Args:
            data: Arbitrary nested structure (dict/list/scalar)
            key: The field name to look for

        Returns:
            The first scalar value found under that key, else None
        """
        if isinstance(data, dict):
            value = data.get(key)
            if value is not None and not isinstance(value, (dict, list)):
                return value
            for nested in data.values():
                found = self._search_nested(nested, key)
                if found is not None:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._search_nested(item, key)
                if found is not None:
                    return found
        return None
