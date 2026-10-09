"""Subworkflow configuration for nested workflow execution.

This module defines the configuration for sub-workflow nodes that
can be executed as tools by agents.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SubWorkflowConfig:
    """Configuration for sub-workflow nodes that can be executed as tools by agents.

    Enables nested workflow execution with input/output schemas and
    execution control.

    Attributes:
        workflow_name: Display name for the workflow
        delegation_description: When agent should trigger this workflow
        input_schema: Expected inputs from agent
        output_schema: Expected outputs to agent
        input_description: Human-readable description of expected inputs
        output_description: Human-readable description of outputs
        timeout: Timeout in seconds for workflow execution
        share_context: Share parent execution context with workflow
        max_retries: Number of retry attempts on failure
        allow_parallel_execution: Allow multiple instances to run in parallel
        cache_results: Cache results for identical inputs
        cache_ttl: Cache time-to-live in seconds
        parent_agent_id: ID of the agent this workflow belongs to
        workflow_nodes: Node IDs that are part of this workflow
        end_node_id: ID of the END node for this workflow
        target_workflow_id: If set, executes this saved workflow instead of
            traversing nodes in the current graph. Must terminate in an END node.
    """

    workflow_name: str = ""
    delegation_description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    input_description: str = ""
    output_description: str = ""
    timeout: int = 600
    share_context: bool = True
    max_retries: int = 1
    allow_parallel_execution: bool = False
    cache_results: bool = False
    cache_ttl: int = 3600
    parent_agent_id: Optional[str] = None
    workflow_nodes: List[str] = field(default_factory=list)
    end_node_id: Optional[str] = None
    target_workflow_id: Optional[str] = None
