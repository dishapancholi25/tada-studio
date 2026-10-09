"""Configuration for For Each iteration nodes.

This module defines the configuration dataclass for For Each nodes,
which iterate over arrays and execute a body subgraph per item.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ForEachConfig:
    """Configuration for a For Each iteration node.

    Attributes:
        source_mode: How the source node is resolved:
            - "previous": Auto-detect the node connected directly before this
              For Each node in the graph (recommended, mirrors Agent nodes'
              "Previous Node" input source mode).
            - "specific": Use the explicitly configured ``source_node_id``
              (default, preserves existing saved workflows).
            - "start": Use the workflow's START node output.
        source_node_id: Node whose output contains the array to iterate.
            Only used when ``source_mode == "specific"``.
        field_path: Dot-path to array in source output, e.g. "fields.rows"
        concurrency_limit: Max concurrent iterations
        rate_limit_per_second: Optional rate limit (None = no limit)
        item_limit: Optional deliberate subset - process only the first N items
            and skip the rest. Intended for testing a loop against a few rows
            of a large source. The skipped count is reported in the node output
            so a partial run is never mistaken for a full one. None processes
            every item. Distinct from ``max_iterations``, which is a safety
            cap that fails the node rather than dropping data.
        max_iterations: Safety cap on total iterations. Exceeding it fails the
            node; it never truncates.
        allowed_fields: Optional allow-list of item keys exposed to body nodes.
            When set (and an item is a dict), only these keys are serialized
            into the body's input (raw/structured/fields). Deterministic data
            residency control - keeps non-whitelisted columns out of the LLM.
            None means expose the whole item (current behaviour).
        max_item_bytes: Optional cap on the serialized size (UTF-8 bytes) of a
            single item's ``raw`` payload sent to body nodes. Oversized payloads
            are truncated with a marker so a fat row can't blow the context
            window. None means no limit.
        error_strategy: How to handle iteration errors
        max_retries_per_item: Retry count per failed iteration
        body_node_ids: Internal - node IDs inside the For Each body
        body_entry_node_id: Internal - first node in body
        body_exit_node_ids: Internal - terminal nodes in body
    """

    # Source configuration
    source_mode: Literal["previous", "specific", "start"] = "specific"
    source_node_id: str = ""
    field_path: str = "fields.rows"

    # Execution settings
    concurrency_limit: int = 5
    rate_limit_per_second: Optional[float] = None
    item_limit: Optional[int] = None
    max_iterations: int = 1000

    # Data residency / volume safety
    allowed_fields: Optional[list[str]] = None
    max_item_bytes: Optional[int] = None

    # Error handling
    error_strategy: Literal["continue_on_error", "fail_fast"] = "continue_on_error"
    max_retries_per_item: int = 0

    # Internal (set by graph builder, not user-configurable)
    body_node_ids: list[str] = field(default_factory=list)
    body_entry_node_id: Optional[str] = None
    body_exit_node_ids: list[str] = field(default_factory=list)
