"""Enhanced execution tracking service for trace viewer.

Captures rich metadata about LLM calls, tool invocations, and execution context.
"""

import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, SystemMessage

from ...services.config import get_logger


logger = get_logger("trace_metadata")

# Cost per 1K tokens for different models (AUD pricing)
# GPT-4o pricing: Input: $3.85446/1M tokens = $0.00385446/1K tokens
#                 Output: $15.4179/1M tokens = $0.0154179/1K tokens
TOKEN_COSTS = {
    "gpt-4o": {"input": 0.00385446, "output": 0.0154179},  # AUD pricing
    "gpt-4o-latest": {"input": 0.00385446, "output": 0.0154179},  # Same as gpt-4o
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},  # Keep USD for now
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},  # Keep USD for now
    "gpt-4": {"input": 0.03, "output": 0.06},  # Keep USD for now
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},  # Keep USD for now
    "claude-3-opus": {"input": 0.015, "output": 0.075},  # Keep USD for now
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},  # Keep USD for now
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},  # Keep USD for now
}


@dataclass
class LLMMetadata:
    """Metadata for LLM calls."""

    model: str
    provider: str  # azure, openai, anthropic
    deployment_name: Optional[str] = None

    # Request configuration
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    seed: Optional[int] = None

    # Response metadata
    finish_reason: Optional[str] = None
    model_version: Optional[str] = None
    system_fingerprint: Optional[str] = None

    # Cost tracking
    prompt_cost: Optional[float] = None
    completion_cost: Optional[float] = None
    total_cost: Optional[float] = None

    # Performance
    time_to_first_token: Optional[float] = None
    tokens_per_second: Optional[float] = None
    cache_hit: Optional[bool] = None

    # Request timing
    request_start: Optional[float] = None
    request_end: Optional[float] = None
    total_latency_ms: Optional[float] = None


@dataclass
class MessageStructure:
    """Structure of messages in a conversation."""

    messages: List[Dict[str, Any]]
    message_count: int
    system_prompt_tokens: Optional[int] = None
    conversation_history_tokens: Optional[int] = None

    # Template information
    prompt_template_id: Optional[str] = None
    prompt_template_version: Optional[str] = None
    prompt_variables: Optional[Dict[str, Any]] = None


@dataclass
class ToolMetadata:
    """Metadata for tool/function calls."""

    # Required fields first (no defaults)
    tool_name: str
    arguments: Dict[str, Any]
    execution_time_ms: float
    return_value: Any

    # Optional fields with defaults
    tool_version: Optional[str] = None
    tool_description: Optional[str] = None
    argument_schema: Optional[Dict[str, Any]] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    return_type: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    external_api_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class OrchestrationMetadata:
    """Metadata for orchestration and delegation."""

    delegated_to: Optional[List[str]] = None
    delegation_reason: Optional[str] = None
    delegation_strategy: Optional[str] = None

    # Subagent management
    subagents_created: int = 0
    subagents_completed: int = 0
    subagents_failed: int = 0

    # Coordination
    coordination_messages: Optional[List[Dict[str, Any]]] = None

    # Resource usage
    total_subagent_tokens: Optional[int] = None
    total_subagent_cost: Optional[float] = None
    max_parallel_agents: Optional[int] = None


@dataclass
class MemoryMetadata:
    """Metadata for memory operations."""

    memory_retrievals: Optional[List[Dict[str, Any]]] = None
    memory_writes: Optional[List[Dict[str, Any]]] = None

    # Context window management
    context_window_size: Optional[int] = None
    context_used: Optional[int] = None
    context_pruning_applied: bool = False
    pruned_messages_count: Optional[int] = None

    # Vector operations
    embeddings_generated: Optional[int] = None
    vector_search_performed: bool = False
    vector_db_latency_ms: Optional[float] = None


@dataclass
class EnvironmentMetadata:
    """Metadata about the execution environment."""

    python_version: Optional[str] = None
    langchain_version: Optional[str] = None
    langgraph_version: Optional[str] = None

    # Resource constraints
    memory_limit_mb: Optional[int] = None
    cpu_cores: Optional[int] = None
    gpu_available: bool = False

    # Feature flags
    feature_flags: Optional[Dict[str, bool]] = None

    # Deployment info
    environment: str = "development"
    region: Optional[str] = None
    instance_id: Optional[str] = None
    deployment_id: Optional[str] = None


class TraceMetadataService:
    """Service for capturing and enriching execution metadata."""

    @staticmethod
    def capture_llm_metadata(
        model: str,
        provider: str,
        config: Dict[str, Any],
        response: Optional[Any] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Capture LLM call metadata."""
        # Calculate costs if tokens are provided
        prompt_cost = None
        completion_cost = None
        total_cost = None

        model_key = model.lower()
        if model_key in TOKEN_COSTS and input_tokens and output_tokens:
            costs = TOKEN_COSTS[model_key]
            prompt_cost = (input_tokens / 1000) * costs["input"]
            completion_cost = (output_tokens / 1000) * costs["output"]
            total_cost = prompt_cost + completion_cost

        # Calculate performance metrics
        total_latency_ms = None
        tokens_per_second = None
        if start_time and end_time:
            total_latency_ms = (end_time - start_time) * 1000
            if output_tokens and total_latency_ms > 0:
                tokens_per_second = output_tokens / (total_latency_ms / 1000)

        metadata = LLMMetadata(
            model=model,
            provider=provider,
            deployment_name=config.get("deployment_name"),
            temperature=config.get("temperature"),
            max_tokens=config.get("max_tokens"),
            top_p=config.get("top_p"),
            frequency_penalty=config.get("frequency_penalty"),
            presence_penalty=config.get("presence_penalty"),
            seed=config.get("seed"),
            finish_reason=getattr(response, "finish_reason", None)
            if response
            else None,
            model_version=getattr(response, "model", None) if response else None,
            system_fingerprint=getattr(response, "system_fingerprint", None)
            if response
            else None,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=total_cost,
            time_to_first_token=None,  # This could be calculated if we had streaming response data
            tokens_per_second=tokens_per_second,
            cache_hit=None,  # This could be detected from response headers
            request_start=start_time,
            request_end=end_time,
            total_latency_ms=total_latency_ms,
        )

        return asdict(metadata)

    @staticmethod
    def capture_message_structure(
        messages: List[BaseMessage],
        prompt_template_id: Optional[str] = None,
        prompt_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Capture message structure and token counts."""
        message_list = []
        system_prompt_tokens = 0
        conversation_history_tokens = 0

        for msg in messages:
            message_dict = {
                "role": msg.__class__.__name__.replace("Message", "").lower(),
                "content": msg.content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Add tool calls if present
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls

            # Estimate token count (rough approximation)
            token_count = len(msg.content.split()) * 1.3  # Rough estimate
            message_dict["token_count"] = int(token_count)

            if isinstance(msg, SystemMessage):
                system_prompt_tokens += token_count
            else:
                conversation_history_tokens += token_count

            message_list.append(message_dict)

        structure = MessageStructure(
            messages=message_list,
            message_count=len(messages),
            system_prompt_tokens=int(system_prompt_tokens),
            conversation_history_tokens=int(conversation_history_tokens),
            prompt_template_id=prompt_template_id,
            prompt_template_version=None,  # Could be tracked separately
            prompt_variables=prompt_variables,
        )

        return asdict(structure)

    @staticmethod
    def capture_tool_metadata(
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        start_time: float,
        end_time: float,
        error: Optional[Exception] = None,
    ) -> Dict[str, Any]:
        """Capture tool invocation metadata."""
        execution_time_ms = (end_time - start_time) * 1000

        error_details = None
        if error:
            error_details = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "stack_trace": None,  # Could capture traceback if needed
            }

        metadata = ToolMetadata(
            tool_name=tool_name,
            arguments=arguments,
            execution_time_ms=execution_time_ms,
            return_value=result,
            tool_version=None,  # Could be extracted from tool definition
            tool_description=None,  # Could be extracted from tool definition
            argument_schema=None,  # Could be extracted from tool schema
            memory_usage_mb=None,  # Could use psutil to measure
            cpu_usage_percent=None,  # Could use psutil to measure
            return_type=type(result).__name__ if result else None,
            error_details=error_details,
            external_api_calls=None,  # Could be tracked with request hooks
        )

        return asdict(metadata)

    @staticmethod
    def capture_orchestration_metadata(
        delegated_agents: Optional[List[str]] = None,
        delegation_reason: Optional[str] = None,
        subagent_stats: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Capture orchestration and delegation metadata."""
        metadata = OrchestrationMetadata(
            delegated_to=delegated_agents,
            delegation_reason=delegation_reason,
            delegation_strategy=None,  # Could be inferred from delegation pattern
            subagents_created=subagent_stats.get("created", 0) if subagent_stats else 0,
            subagents_completed=subagent_stats.get("completed", 0)
            if subagent_stats
            else 0,
            subagents_failed=subagent_stats.get("failed", 0) if subagent_stats else 0,
            coordination_messages=None,  # Could track inter-agent messages
            total_subagent_tokens=None,  # Could aggregate from subagents
            total_subagent_cost=None,  # Could aggregate from subagents
            max_parallel_agents=None,  # Could track max concurrent subagents
        )

        return asdict(metadata)

    @staticmethod
    def capture_memory_metadata(
        memory_operations: Optional[Dict[str, Any]] = None,
        context_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Capture memory and context management metadata."""
        metadata = MemoryMetadata(
            memory_retrievals=memory_operations.get("retrievals")
            if memory_operations
            else None,
            memory_writes=memory_operations.get("writes")
            if memory_operations
            else None,
            context_window_size=context_info.get("window_size")
            if context_info
            else None,
            context_used=context_info.get("used") if context_info else None,
            context_pruning_applied=context_info.get("pruning_applied", False)
            if context_info
            else False,
            pruned_messages_count=context_info.get("pruned_count")
            if context_info
            else None,
            embeddings_generated=memory_operations.get("embeddings_count")
            if memory_operations
            else None,
            vector_search_performed=memory_operations.get("vector_search", False)
            if memory_operations
            else False,
            vector_db_latency_ms=memory_operations.get("vector_latency_ms")
            if memory_operations
            else None,
        )

        return asdict(metadata)

    @staticmethod
    def capture_environment_metadata() -> Dict[str, Any]:
        """Capture environment and runtime metadata."""
        import platform
        import sys

        try:
            import langchain

            langchain_version = langchain.__version__
        except ImportError:
            langchain_version = None

        try:
            import langgraph

            langgraph_version = langgraph.__version__
        except ImportError:
            langgraph_version = None

        metadata = EnvironmentMetadata(
            python_version=sys.version,
            langchain_version=langchain_version,
            langgraph_version=langgraph_version,
            memory_limit_mb=None,  # Could use resource module
            cpu_cores=os.cpu_count(),
            gpu_available=False,  # Could check with torch/tensorflow
            feature_flags={
                "execution_engine_enabled": True,  # Always true now
                "ENABLE_POSTGRES_CHECKPOINTING": os.getenv(
                    "ENABLE_POSTGRES_CHECKPOINTING", "true"
                ).lower()
                == "true",
                "ENABLE_NATIVE_TOOL_NODES": os.getenv(
                    "ENABLE_NATIVE_TOOL_NODES", "true"
                ).lower()
                == "true",
                "ENABLE_PERFORMANCE_LOGGING": os.getenv(
                    "ENABLE_PERFORMANCE_LOGGING", "true"
                ).lower()
                == "true",
            },
            environment=os.getenv("ENVIRONMENT", "development"),
            region=os.getenv("AZURE_REGION", None),
            instance_id=platform.node(),
            deployment_id=os.getenv("DEPLOYMENT_ID", None),
        )

        return asdict(metadata)

    @staticmethod
    def enrich_node_execution(
        node_execution_data: Dict[str, Any],
        llm_response: Optional[Any] = None,
        messages: Optional[List[BaseMessage]] = None,
        tool_result: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Enrich node execution data with all available metadata."""
        enriched = node_execution_data.copy()

        # Capture LLM metadata if this is an agent node
        if node_execution_data.get("node_type") == "AGENT" and llm_response:
            enriched["llm_metadata"] = TraceMetadataService.capture_llm_metadata(
                model=config.get("model", "unknown") if config else "unknown",
                provider=config.get("provider", "unknown") if config else "unknown",
                config=config or {},
                response=llm_response,
                input_tokens=enriched.get("input_tokens"),
                output_tokens=enriched.get("output_tokens"),
            )

            # Update cost fields
            if enriched["llm_metadata"].get("total_cost"):
                enriched["total_cost"] = enriched["llm_metadata"]["total_cost"]
                enriched["prompt_cost"] = enriched["llm_metadata"]["prompt_cost"]
                enriched["completion_cost"] = enriched["llm_metadata"][
                    "completion_cost"
                ]

        # Capture message structure if messages are provided
        if messages:
            enriched["message_structure"] = (
                TraceMetadataService.capture_message_structure(messages)
            )

        # Capture tool metadata if this is a tool node
        if node_execution_data.get("node_type") == "TOOL" and tool_result is not None:
            enriched["tool_metadata"] = TraceMetadataService.capture_tool_metadata(
                tool_name=node_execution_data.get("node_name", "unknown"),
                arguments=node_execution_data.get("input_data", {}),
                result=tool_result,
                start_time=time.time(),  # Should be tracked properly
                end_time=time.time(),
            )

        # Always capture environment metadata
        enriched["environment_metadata"] = (
            TraceMetadataService.capture_environment_metadata()
        )

        return enriched
