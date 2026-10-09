"""Tool configuration for custom tool nodes.

This module defines the ToolConfig dataclass for configuring
custom tool executions in workflows.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolConfig:
    """Configuration for tool nodes.

    Attributes:
        tool_name: Display name of the tool
        tool_code: Python code implementing the tool
        parameters: Parameter values for the tool
        parameter_types: Type definitions for each parameter
        description: Tool description for documentation
        imports: Required Python imports for the tool
        tool_type: Tool type identifier (default: 'custom')
        is_async: Whether the tool is asynchronous
    """

    tool_name: str = ""
    tool_code: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    parameter_types: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    imports: List[str] = field(default_factory=list)
    tool_type: str = "custom"
    is_async: bool = False
