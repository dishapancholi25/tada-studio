"""Base data structures for workflow graphs.

This module provides fundamental building blocks used across workflow
definitions, including positions, connections, and input sources.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .enums import ConnectionType


@dataclass
class Position:
    """Node position on canvas.

    Attributes:
        x: Horizontal position coordinate
        y: Vertical position coordinate
    """

    x: float = 0.0
    y: float = 0.0


@dataclass
class Connection:
    """Represents a connection between nodes.

    Attributes:
        source_id: ID of the source node
        target_id: ID of the target node
        source_handle: Optional handle identifier for source (e.g., for condition branches)
        target_handle: Optional handle identifier for target
        label: Optional connection label
        connection_type: Type of connection (workflow, delegation, or tool)
    """

    source_id: str
    target_id: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    label: Optional[str] = None
    connection_type: ConnectionType = ConnectionType.WORKFLOW


@dataclass
class InputSourceConfig:
    """Configuration for input source selection.

    Defines how a node receives its input data from previous nodes
    or workflow inputs.

    Attributes:
        source_mode: How to select input source (previous, specific, start, custom, multiple)
        source_node_id: [Deprecated] ID of specific source node (use source_node_ids)
        source_node_ids: IDs of multiple nodes to use as sources
        use_structured_field: Whether to extract specific fields from structured output
        selected_fields: Fields to extract from structured output
        combine_fields_as_json: If multiple fields selected, combine as JSON object
        include_original_input: Optionally include the original workflow input
        custom_template: Custom template for formatting input
        include_node_labels: Include node names as labels when combining multiple sources
    """

    source_mode: str = "previous"
    source_node_id: Optional[str] = None
    source_node_ids: List[str] = field(default_factory=list)
    use_structured_field: bool = False
    selected_fields: List[str] = field(default_factory=list)
    combine_fields_as_json: bool = True
    include_original_input: bool = False
    custom_template: Optional[str] = None
    include_node_labels: bool = True
