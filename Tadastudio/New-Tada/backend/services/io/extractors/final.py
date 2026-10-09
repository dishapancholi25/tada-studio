"""
Final Output Extractor.

Extracts the final output from workflow state.
"""

from typing import Any, Optional

from langchain_core.messages import AIMessage
from backend.services.workflow.state import WorkflowState


class FinalOutputExtractor:
    """
    Extracts the final output from workflow state.

    Tries multiple sources: last message, last node output.
    """

    @staticmethod
    def extract(state: WorkflowState) -> Optional[Any]:
        """
        Extract the final output from the workflow state.

        Args:
            state: The workflow state

        Returns:
            The final output or None if not found
        """
        # Get the last message as final output
        if state.get("messages"):
            last_message = state["messages"][-1]
            if isinstance(last_message, AIMessage):
                return last_message.content

        # Fallback to last node output
        if state.get("node_outputs"):
            last_output = list(state["node_outputs"].values())[-1]
            return last_output.get("raw", "")

        return None
