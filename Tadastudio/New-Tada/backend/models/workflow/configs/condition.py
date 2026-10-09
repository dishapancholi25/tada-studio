"""Condition configuration for conditional branching nodes.

This module defines configuration for condition nodes that enable
conditional logic and multi-branch workflows.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .llm import LLMConfig


@dataclass
class BranchConfig:
    """Configuration for a single branch in a condition node.

    Attributes:
        label: Display label for the branch
        color: Visual color for the branch (hex or CSS)
        handle_id: Unique handle identifier
        condition: Condition logic for this branch
    """

    label: str = ""
    color: str = "#8b5cf6"
    handle_id: str = ""
    condition: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConditionConfig:
    """Configuration for condition nodes with enhanced branching support.

    Supports multiple branching modes and condition types including
    simple comparisons, expressions, and LLM-based evaluation.

    Attributes:
        branch_mode: Branching mode (binary, multi, switch)
        branches: List of branch configurations
        condition_type: Evaluation method (simple, expression, llm, multiple)
        simple_conditions: List of simple condition definitions
        expression: Python expression for evaluation
        llm_prompt: Prompt for LLM-based evaluation
        llm_config: LLM configuration for evaluation
        logic_operator: Logical operator for multiple conditions (AND, OR, XOR)
        branch_count: Number of output branches
        branch_labels: Labels for each branch
        branch_conditions: Conditions for multi-branch scenarios
        has_default_branch: Whether to include a default/fallback branch
        default_branch_label: Label for default branch
        condition_prompt: [Deprecated] Use llm_prompt
        true_label: [Deprecated] Use branch_labels[0]
        false_label: [Deprecated] Use branch_labels[1]
        simple_condition: [Deprecated] Use simple_conditions
        comparison_operator: [Deprecated]
        comparison_value: [Deprecated]
        code_condition: [Deprecated] Use expression
    """

    branch_mode: str = "binary"
    branches: List[BranchConfig] = field(default_factory=list)
    condition_type: str = "simple"
    simple_conditions: List[Dict[str, Any]] = field(default_factory=list)
    expression: str = ""
    llm_prompt: str = ""
    llm_config: Optional[LLMConfig] = None
    logic_operator: str = "AND"
    branch_count: int = 2
    branch_labels: List[str] = field(default_factory=lambda: ["True", "False"])
    branch_conditions: List[Dict[str, Any]] = field(default_factory=list)
    has_default_branch: bool = False
    default_branch_label: str = "Default"
    # Passthrough mode fields (for binary mode without comparison operators)
    # When these are set and simple_conditions is empty, the input value
    # is directly interpreted as a boolean (case-insensitive "true"/"false")
    input_source: str = "previous"
    source_node_id: Optional[str] = None
    field_path: str = ""
    # Custom template for "custom" input source mode
    # Supports: {original}, {previous}, {node_id}, {node_id.field}
    custom_template: str = ""
    # Legacy fields for backward compatibility
    condition_prompt: str = ""
    true_label: str = "True"
    false_label: str = "False"
    simple_condition: Dict[str, Any] = field(default_factory=dict)
    comparison_operator: str = "=="
    comparison_value: Any = None
    code_condition: str = ""
