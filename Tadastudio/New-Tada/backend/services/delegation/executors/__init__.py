"""Execution strategies for delegation."""

from .simple_executor import SimpleDelegationExecutor
from .subgraph_executor import SubgraphDelegationExecutor

__all__ = [
    "SimpleDelegationExecutor",
    "SubgraphDelegationExecutor",
]
