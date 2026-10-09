"""End node configuration for workflow output handling.

This module defines the configuration for END nodes that determine
how workflow results are formatted and returned.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EndNodeConfig:
    """Configuration for END node output handling.

    Controls how workflow execution results are collected, formatted,
    and returned to the caller.

    Attributes:
        input_source: Input source mode (all, previous, specific, multiple)
        source_node_ids: Node IDs for specific/multiple modes
        output_structure: Output format (full, summary, custom, compact)
        include_metadata: Include execution metadata
        include_node_names: Include node names in output
        custom_output_template: Custom JSON template string
        include_fields: Only include these fields from outputs
        exclude_fields: Exclude these fields from outputs
        wrap_response: Wrap in standard response structure
        response_key: Key name for the main result
    """

    input_source: str = "all"
    source_node_ids: List[str] = field(default_factory=list)
    output_structure: str = "full"
    include_metadata: bool = True
    include_node_names: bool = True
    custom_output_template: Optional[str] = None
    include_fields: List[str] = field(default_factory=list)
    exclude_fields: List[str] = field(default_factory=list)
    wrap_response: bool = True
    response_key: str = "result"
