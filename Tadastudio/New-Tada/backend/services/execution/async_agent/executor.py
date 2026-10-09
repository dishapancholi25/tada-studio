"""Main async agent executor.

This module provides the main AsyncAgentExecutor class that orchestrates
all async agent execution components including LLM building, message
construction, tool execution, memory management, and token counting.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from langgraph.errors import GraphInterrupt

from backend.models.workflow import AgentConfig, EnhancedNodeData
from backend.models.workflow.configs.guardrails import GuardrailsConfig
from backend.services.config import ExecutionConfig, get_logger
from backend.services.guardrails import get_guardrails_engine
from backend.services.guardrails.checkpoint import GuardrailCheckpoint, GuardrailContext
from backend.services.guardrails.exceptions import GuardrailViolationError
from backend.services.guardrails.models import Violation

from .exceptions import AsyncAgentExecutionError, LLMBuildError
from .http_metadata_handler import HTTPMetadataHandler
from .llm_builder import AsyncLLMBuilder
from .memory_handler import AsyncMemoryHandler
from .message_builder import MessageBuilder
from .models import ExecutionConfig as AsyncExecutionConfig
from .models import ExecutionResult
from .structured_output_handler import StructuredOutputHandler
from .token_handler import TokenHandler
from .tool_executor import AsyncToolExecutor
from .utils import extract_response_content

from langchain_core.messages import AIMessage

from backend.services.streaming.event_emitter import StreamingEventEmitter

if TYPE_CHECKING:
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

try:
    # Optional: only imported when streaming is enabled
    from backend.services.websocket import notifier as ws_notifier  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ws_notifier = None

# LangGraph streaming context detection - used to avoid duplicate token emission
try:
    from langgraph.config import get_stream_writer as _get_langgraph_stream_writer
except ImportError:
    _get_langgraph_stream_writer = None

# Get logger for this module
executor_logger = get_logger("async_agent.executor")


class AsyncAgentExecutor:
    """Main orchestrator for async agent execution.

    This class coordinates all aspects of async agent execution by delegating
    to specialized handlers for LLM building, memory, tokens, tools, etc.
    """

    def __init__(
        self,
        llm_factory: "LLMFactory",
        model_service: "ModelDeploymentService",
        get_tools_callback: Optional[callable] = None,
    ):
        """Initialize the async agent executor.

        Args:
            llm_factory: Factory for creating LLM instances
            model_service: Service for model deployment management
            get_tools_callback: Optional callback to get tools for an agent
        """
        self.llm_factory = llm_factory
        self.model_service = model_service
        self.get_tools_callback = get_tools_callback
        self.logger = executor_logger

        # Initialize handlers
        self.llm_builder = AsyncLLMBuilder(llm_factory, model_service)
        self.memory_handler = AsyncMemoryHandler()
        self.token_handler = TokenHandler()
        self.message_builder = MessageBuilder()
        self.http_metadata_handler = HTTPMetadataHandler()
        self.tool_executor = AsyncToolExecutor(self.http_metadata_handler)
        self.structured_output_handler = StructuredOutputHandler()

    def _in_langgraph_streaming_context(self) -> bool:
        """Check if LangGraph's native streaming will handle tokens.

        When running inside app.astream(), LangGraph's "messages" mode captures
        tokens automatically. We only need explicit emit_content_chunk() when
        in isolated contexts (subagents) where get_stream_writer() returns None.

        Returns:
            True if in LangGraph streaming context, False otherwise.
        """
        if _get_langgraph_stream_writer is None:
            return False
        try:
            return _get_langgraph_stream_writer() is not None
        except Exception:
            return False

    async def execute_agent(
        self,
        agent_node: EnhancedNodeData,
        user_message: str,
        config: Optional[AsyncExecutionConfig] = None,
        graph_name: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute an agent asynchronously.

        This is the main entry point for async agent execution. It coordinates
        all execution steps and returns a structured result.

        Args:
            agent_node: The agent node to execute
            user_message: The user's message
            config: Optional execution configuration
            graph_name: Optional graph name for tool discovery

        Returns:
            ExecutionResult with response, token counts, and metadata

        Raises:
            AsyncAgentExecutionError: If execution fails
        """
        config = config or AsyncExecutionConfig()
        agent_name = agent_node.name
        resolved_guardrails: Optional[List[GuardrailsConfig]] = None
        guardrail_ctx = GuardrailContext()

        self.logger.info(
            f"[ASYNC-EXECUTOR] Executing agent {agent_name} asynchronously"
        )

        try:
            # Step 1: Validate and prepare agent configuration
            agent_config = self._get_agent_config(agent_node)

            # Step 2: Build LLM
            llm = await self.llm_builder.build_llm(agent_config, agent_name)

            # Step 3: Initialize token counting
            token_counts = self.token_handler.initialize_counts(llm)

            # Step 4: Get memory context if enabled
            memory_context = await self._get_memory_if_enabled(
                agent_node, agent_config, config
            )

            # Step 5: Get tools if not using structured output
            tools = self._get_tools_if_needed(
                agent_node, agent_config, config, graph_name
            )

            # Step 5.5: Resolve guardrails config (unified resolution)
            agent_guardrails_enabled = getattr(agent_config, "guardrails_enabled", True)
            llm_cfg = getattr(agent_config, "llm_config", None)
            model_id = (
                (llm_cfg.model_deployment_id or llm_cfg.model_name) if llm_cfg else None
            )
            guardrails_engine = get_guardrails_engine(
                llm_factory=self.llm_factory,
                model_service=self.model_service,
            )
            tool_node_ids = None
            if config.tool_node_mapping:
                tool_node_ids = list(
                    {
                        info["node_id"]
                        for info in config.tool_node_mapping.values()
                        if isinstance(info, dict) and info.get("node_id")
                    }
                )
            resolved = guardrails_engine.resolve_unified(
                workflow_id=config.workflow_id,
                node_id=config.node_id,
                model_id=model_id,
                tool_names=tool_node_ids,
                agent_guardrails_enabled=agent_guardrails_enabled,
            )
            resolved_guardrails = resolved.agent_pipeline   # List[GuardrailsConfig]
            tool_guardrails_map = resolved.tool_pipelines   # Dict[str, List[GuardrailsConfig]]
            self.logger.info(
                f"[ASYNC-EXECUTOR] Guardrails for {agent_name}: "
                f"enabled_at_agent={agent_guardrails_enabled}, "
                f"resolved={len(resolved_guardrails)} policies"
                + (
                    f", modes={[c.enforcement_mode for c in resolved_guardrails if c.enabled]}"
                    if resolved_guardrails
                    else ""
                )
                + (
                    f", tool_pipelines={len(tool_guardrails_map)}"
                    if tool_guardrails_map
                    else ""
                )
            )

            # Build guardrail context and checkpoint (used for input + tool checks)
            guardrail_ctx = GuardrailContext(
                execution_id=config.execution_id,
                db_execution_id=config.db_execution_id,
                node_execution_id=config.node_execution_id,
                workflow_id=config.workflow_id,
                agent_node_id=agent_node.uniq_id,
                agent_node_name=agent_name,
                user_id=config.user_id,
            )
            guardrail_checkpoint = GuardrailCheckpoint(guardrails_engine)

            # Step 5.6: Input guardrails check
            input_result = None
            _guardrails_state: dict = {}
            if resolved_guardrails:
                # check() reports violations and raises on enforce mode
                input_result = await guardrail_checkpoint.check(
                    user_message,
                    resolved_guardrails,
                    "input",
                    guardrail_ctx,
                    state=_guardrails_state,
                )

                if not input_result.passed:
                    violation_msg = (
                        input_result.violations[0].message
                        if input_result.violations
                        else "Input blocked"
                    )
                    self.logger.warning(
                        f"[ASYNC-EXECUTOR] Input blocked by guardrails for {agent_name}: {violation_msg}"
                    )
                    # Audit mode: return graceful blocked response
                    # (enforce mode already raised via checkpoint.check)
                    blocked_response = (
                        f"[Input blocked by guardrail policy: {violation_msg}]"
                    )
                    return ExecutionResult(
                        response=AIMessage(content=blocked_response),
                        token_counts=None,
                        tool_executions=[],
                        metadata={
                            "agent_name": agent_name,
                            "agent_id": agent_node.uniq_id,
                            "guardrail_blocked": True,
                            "guardrail_violations": [
                                v.to_dict() for v in input_result.violations
                            ],
                        },
                    )

            # Step 6: Build messages (use transformed content if guardrails modified it)
            effective_message = user_message
            if input_result and input_result.sanitized_content:
                effective_message = input_result.sanitized_content
                self.logger.info(
                    f"[ASYNC-EXECUTOR] Input transformed by guardrails for {agent_name}"
                )
            messages = await self.message_builder.build_messages(
                effective_message, agent_config, memory_context, tools,
                conversation_history=config.conversation_history if config else None,
                workflow_id=config.workflow_id if config else None,
            )

            # Step 7: Count input tokens
            input_counts = self.token_handler.count_input_tokens(
                messages, token_counts.model
            )
            token_counts.input_tokens = input_counts.input_tokens

            # Step 8: Execute LLM (with tools or structured output)
            # Note: messages list is mutated in-place by tool executor during multi-turn loops
            response = await self._execute_llm(
                llm,
                messages,
                agent_config,
                tools,
                config,
                agent_name,
                guardrails_config=resolved_guardrails,
                guardrails_state=_guardrails_state,
                guardrail_checkpoint=guardrail_checkpoint,
                guardrail_ctx=guardrail_ctx,
                tool_guardrails_map=tool_guardrails_map,
            )

            # Step 8.5: Capture full conversation history for trace viewer
            # messages now contains the complete multi-turn conversation including
            # tool calls, tool results, and intermediate LLM responses
            message_structure = _serialize_messages(messages, response)

            # Step 9: Extract token metadata
            token_counts = self.token_handler.extract_token_metadata(
                response, token_counts
            )

            # Step 10: Store memory if enabled
            await self._store_memory_if_enabled(
                agent_node, agent_config, config, user_message, response
            )

            # Step 11: Build result
            result_metadata = {
                "agent_name": agent_name,
                "agent_id": agent_node.uniq_id,
                "memory_used": memory_context is not None,
                "tools_count": len(tools) if tools else 0,
            }

            # Include audit-mode violations in metadata for persistence
            if (
                resolved_guardrails
                and input_result
                and input_result.violations
            ):
                result_metadata["guardrail_violations"] = [
                    v.to_dict() for v in input_result.violations
                ]

            # Propagate guardrails state (e.g. vault_id) so the
            # agent executor can pass it to output guardrails for
            # cross-phase deanonymization.
            if _guardrails_state:
                result_metadata["guardrails_state"] = _guardrails_state

            result = ExecutionResult(
                response=response,
                token_counts=token_counts if config.return_token_counts else None,
                tool_executions=config.tool_execution_tracker or [],
                metadata=result_metadata,
                message_structure=message_structure,
            )

            self.logger.info(
                f"[ASYNC-EXECUTOR] Agent {agent_name} execution completed successfully"
            )
            return result

        except LLMBuildError as e:
            self.logger.error(f"[ASYNC-EXECUTOR] LLM build failed: {str(e)}")
            raise
        except asyncio.CancelledError:
            # Re-raise CancelledError for hard stop support
            # This allows task cancellation to propagate through the async chain
            self.logger.info(
                f"[ASYNC-EXECUTOR] Agent {agent_name} execution cancelled (hard stop)"
            )
            raise
        except GraphInterrupt:
            # Re-raise GraphInterrupt to propagate pause to parent workflow
            # This is used by sub-agent review checkpoints
            self.logger.info(
                f"[ASYNC-EXECUTOR] GraphInterrupt received for {agent_name}, "
                "propagating to parent workflow"
            )
            raise
        except GuardrailViolationError:
            # Re-raise to propagate guardrail enforcement to parent workflow
            raise
        except Exception as e:
            # Check if this is a provider content filter error (Azure/OpenAI)
            content_filter = self._parse_content_filter_error(e)
            if content_filter:
                self.logger.warning(
                    f"[ASYNC-EXECUTOR] Provider content filter blocked {agent_name}: "
                    f"categories={[c['category'] for c in content_filter['categories']]} "
                    f"provider_message={content_filter.get('message', 'N/A')}"
                )

                # Determine if the provider_content_filter guardrail is active
                # Use first active config for provider content filter (single-config edge case)
                from backend.services.guardrails.compat import select_first_active_config as _select_first
                active_cfg = _select_first(resolved_guardrails) if resolved_guardrails else None
                pcf_config = (
                    active_cfg.provider_content_filter
                    if active_cfg
                    else None
                )
                pcf_enabled = pcf_config and pcf_config.enabled

                # Filter to configured categories (empty = all)
                triggered_cats = content_filter["categories"]
                if pcf_enabled and pcf_config.categories:
                    allowed = {c.lower() for c in pcf_config.categories}
                    triggered_cats = [
                        c for c in triggered_cats if c["category"].lower() in allowed
                    ]

                friendly_categories = ", ".join(
                    c["category"] for c in content_filter["categories"]
                )

                if pcf_enabled and triggered_cats:
                    enforcement = active_cfg.enforcement_mode if active_cfg else "enforce"
                    severity = "block" if enforcement == "enforce" else "warn"
                    action = "blocked" if enforcement == "enforce" else "warned"

                    # Build Violation objects and use checkpoint to report them
                    cf_violations = [
                        Violation(
                            category="content_filter",
                            rule_name=cat["category"],
                            severity=severity,
                            message=f"Provider content filter: {cat['category']} detected",
                        )
                        for cat in triggered_cats
                    ]
                    GuardrailCheckpoint.report_prebuilt_violations(
                        cf_violations,
                        active_cfg,
                        "content_filter",
                        guardrail_ctx,
                        action_taken=action,
                    )

                    if enforcement == "enforce":
                        raise GuardrailViolationError(
                            f"Provider content filter violation on {agent_name}: {friendly_categories}",
                            violations=cf_violations,
                        ) from e

                # Return graceful blocked response (no guardrail, audit mode, or no matching categories)
                friendly_msg = (
                    f"Request blocked by provider content filter ({friendly_categories}). "
                    "The input triggered the AI provider's safety policy."
                )

                # Emit the safety message as a content chunk so the streaming
                # chat renders it. On a provider content-filter block the agent
                # produces no tokens, so without this the turn shows an empty
                # bubble. Self-guards: no-ops if there is no active stream writer.
                StreamingEventEmitter.emit_content_chunk(
                    content=friendly_msg,
                    agent_name=agent_name,
                    node_id=config.node_id,
                    execution_id=config.execution_id,
                    execution_order=config.execution_order,
                    db_node_id=config.db_node_id,
                )

                return ExecutionResult(
                    response=friendly_msg,
                    token_counts=token_counts if config.return_token_counts else None,
                    tool_executions=config.tool_execution_tracker or [],
                    metadata={
                        "agent_name": agent_name,
                        "agent_id": agent_node.uniq_id,
                        "content_filter_blocked": True,
                        "content_filter_categories": content_filter["categories"],
                        "content_filter_provider": content_filter["provider"],
                        "content_filter_violations_persisted": bool(
                            pcf_enabled and triggered_cats
                        ),
                    },
                )

            error_msg = f"Async agent execution failed for {agent_name}: {str(e)}"
            self.logger.error(f"[ASYNC-EXECUTOR] {error_msg}", exc_info=True)
            raise AsyncAgentExecutionError(error_msg, agent_name=agent_name) from e

    @staticmethod
    def _parse_content_filter_error(exc: Exception) -> Optional[Dict[str, Any]]:
        """Parse Azure/OpenAI content filter errors into structured violation data.

        Walks the exception __cause__ chain so that wrapped errors (e.g.
        ToolExecutionError wrapping BadRequestError) are still detected.

        Returns dict with 'categories' list, 'message', and 'provider'
        if the exception is a content filter error, else None.
        """
        # Walk the exception cause/context chain — the original BadRequestError
        # may be wrapped by ToolExecutionError, StructuredOutputError, etc.
        # Check both __cause__ (explicit `raise X from Y`) and __context__
        # (implicit chaining during except handlers).
        seen: set[int] = set()
        queue: list[BaseException] = [exc]
        while queue:
            current = queue.pop(0)
            exc_id = id(current)
            if exc_id in seen:
                continue
            seen.add(exc_id)
            if len(seen) > 10:
                break

            body = getattr(current, "body", None)
            if isinstance(body, dict) and body.get("code") == "content_filter":
                inner = body.get("innererror", {})
                filter_result = inner.get("content_filter_result", {})

                triggered = []
                for category, details in filter_result.items():
                    if isinstance(details, dict) and details.get("filtered"):
                        triggered.append(
                            {
                                "category": category,
                                "severity": details.get("severity", "filtered"),
                                "detected": details.get("detected", True),
                            }
                        )

                return {
                    "categories": triggered,
                    "message": body.get("message", str(current)),
                    "provider": "azure_openai",
                }

            # Follow both cause and context chains
            if current.__cause__ is not None:
                queue.append(current.__cause__)
            if current.__context__ is not None:
                queue.append(current.__context__)

        # String-based fallback: detect content filter errors even when the
        # structured body attribute is missing (e.g. non-OpenAI SDK wrappers).
        error_str = str(exc).lower()
        if "content_filter" in error_str or "content management policy" in error_str:
            return {
                "categories": [
                    {
                        "category": "content_filter",
                        "severity": "filtered",
                        "detected": True,
                    }
                ],
                "message": str(exc),
                "provider": "azure_openai",
            }

        return None

    def _get_agent_config(self, agent_node: EnhancedNodeData) -> AgentConfig:
        """Get and validate agent configuration.

        Args:
            agent_node: Agent node data

        Returns:
            AgentConfig instance

        Raises:
            AsyncAgentExecutionError: If config is missing or invalid
        """
        agent_config = agent_node.agent_config

        if not agent_config:
            raise AsyncAgentExecutionError(
                f"Agent node {agent_node.name} has no configuration",
                agent_name=agent_node.name,
            )

        # Convert dict to AgentConfig if needed, filtering removed fields
        if isinstance(agent_config, dict):
            from dataclasses import fields as dc_fields

            valid_fields = {f.name for f in dc_fields(AgentConfig)}
            agent_config = AgentConfig(
                **{k: v for k, v in agent_config.items() if k in valid_fields}
            )

        return agent_config

    async def _get_memory_if_enabled(
        self,
        agent_node: EnhancedNodeData,
        agent_config: AgentConfig,
        config: AsyncExecutionConfig,
    ) -> Optional[str]:
        """Get memory context if enabled.

        Args:
            agent_node: Agent node
            agent_config: Agent configuration
            config: Execution configuration

        Returns:
            Memory context string or None
        """
        # Check if memory should be used
        use_memory = (
            config.enable_memory
            and ExecutionConfig.use_memory()
            and agent_config.memory_enabled
        )

        if not use_memory:
            return None

        memory_window_size = getattr(agent_config, "memory_window_size", None)
        memory_strategy = getattr(agent_config, "memory_strategy", "thread_scoped")

        return await self.memory_handler.get_memory_context(
            node_id=agent_node.uniq_id,
            db_execution_id=config.db_execution_id,
            memory_strategy=memory_strategy,
            memory_window_size=memory_window_size,
            limit=(memory_window_size * 2) if memory_window_size else 10,
        )

    def _get_tools_if_needed(
        self,
        agent_node: EnhancedNodeData,
        agent_config: AgentConfig,
        config: AsyncExecutionConfig,
        graph_name: Optional[str] = None,
    ) -> Optional[List[Any]]:
        """Get tools for the agent.

        Tools are always loaded when available. When both tools and structured
        output are configured, two-phase execution is used (tools first, then
        format with structured output).

        Args:
            agent_node: Agent node
            agent_config: Agent configuration
            config: Execution configuration
            graph_name: Optional graph name for tool discovery

        Returns:
            List of tools or None
        """
        # Use callback if provided
        if self.get_tools_callback:
            tools = self.get_tools_callback(
                tool_list=agent_config.tools if agent_config.tools else [],
                agent_config=agent_config,
                agent_node_id=agent_node.uniq_id,
                graph_name=graph_name,
                user_id=config.user_id,
            )

            if tools:
                self.logger.info(
                    f"[ASYNC-EXECUTOR] Agent {agent_node.name} has {len(tools)} tools"
                )
            return tools

        return None

    async def _execute_llm(
        self,
        llm: Any,
        messages: List[Any],
        agent_config: AgentConfig,
        tools: Optional[List[Any]],
        config: AsyncExecutionConfig,
        agent_name: str,
        guardrails_config: Optional[List["GuardrailsConfig"]] = None,
        guardrails_state: Optional[Dict[str, Any]] = None,
        guardrail_checkpoint: Optional["GuardrailCheckpoint"] = None,
        guardrail_ctx: Optional["GuardrailContext"] = None,
        tool_guardrails_map: Optional[Dict[str, List["GuardrailsConfig"]]] = None,
    ) -> Any:
        """Execute LLM with appropriate strategy.

        Supports four execution modes:
        1. Both tools AND structured output → Two-phase execution (tools first, then format)
        2. Only structured output (no tools) → Direct structured output
        3. Only tools (no structured output) → Tool execution with ReAct pattern
        4. Neither → Regular execution (with optional streaming)
        """
        # Determine execution mode
        has_tools = tools and len(tools) > 0
        should_use_structured = (
            self.structured_output_handler.should_use_structured_output(
                agent_config, config.format_output
            )
        )

        # Prepare streaming context for tool executor
        stream_notifier = (
            ws_notifier
            if ExecutionConfig.enable_streaming() and bool(config.execution_id)
            else None
        )

        # CASE 1: Both tools AND structured output → Two-phase execution
        if has_tools and should_use_structured:
            self.logger.info(
                f"[ASYNC-EXECUTOR] Two-phase execution for {agent_name}: "
                f"{len(tools)} tools then structured output"
            )
            emit_explicitly = (
                config.is_subagent or not self._in_langgraph_streaming_context()
            )
            return await self.structured_output_handler.execute_with_tools_then_format(
                llm,
                messages,
                tools,
                agent_config,
                self.tool_executor,
                config.tool_execution_tracker,
                agent_name,
                max_iterations=agent_config.max_iterations,
                ws_notifier=stream_notifier,
                execution_id=config.execution_id,
                node_id=config.node_id,
                graph_name=config.graph_name,
                tool_node_mapping=config.tool_node_mapping,
                review_iteration=config.review_iteration,
                node_execution_id=config.node_execution_id,
                invocation_index=config.invocation_index,
                parent_subagent_id=config.parent_subagent_id,
                guardrails_config=guardrails_config,
                guardrails_state=guardrails_state,
                emit_content_chunks=emit_explicitly,
                db_execution_id=config.db_execution_id,
                workflow_id=config.workflow_id,
                guardrail_checkpoint=guardrail_checkpoint,
                guardrail_ctx=guardrail_ctx,
                tool_guardrails_map=tool_guardrails_map,
            )

        # CASE 2: Only structured output (no tools) → Direct structured output
        if should_use_structured:
            self.logger.info(
                f"[ASYNC-EXECUTOR] Using structured output for {agent_name}"
            )
            return await self.structured_output_handler.execute_with_structured_output(
                llm, messages, agent_config
            )

        # CASE 3: Only tools (no structured output) → Tool execution
        if has_tools:
            self.logger.info(
                f"[ASYNC-EXECUTOR] Executing with {len(tools)} tools for {agent_name}"
            )
            # Only emit content chunks explicitly when LangGraph's "messages"
            # stream mode isn't already capturing them (avoids duplicate tokens).
            emit_explicitly = (
                config.is_subagent or not self._in_langgraph_streaming_context()
            )
            return await self.tool_executor.execute_with_tools(
                llm,
                messages,
                tools,
                config.tool_execution_tracker,
                agent_name,
                max_iterations=agent_config.max_iterations,
                ws_notifier=stream_notifier,
                execution_id=config.execution_id,
                node_id=config.node_id,
                graph_name=config.graph_name,
                tool_node_mapping=config.tool_node_mapping,
                review_iteration=config.review_iteration,
                node_execution_id=config.node_execution_id,
                invocation_index=config.invocation_index,
                parent_subagent_id=config.parent_subagent_id,
                guardrails_config=guardrails_config,
                guardrails_state=guardrails_state,
                emit_content_chunks=emit_explicitly,
                db_execution_id=config.db_execution_id,
                workflow_id=config.workflow_id,
                guardrail_checkpoint=guardrail_checkpoint,
                guardrail_ctx=guardrail_ctx,
                tool_guardrails_map=tool_guardrails_map,
            )

        # CASE 4: Neither tools nor structured output → Regular execution
        # Decide whether to stream tokens to websocket listeners
        should_stream_tokens = (
            ExecutionConfig.enable_streaming()
            and bool(config.execution_id)
            and ws_notifier is not None
        )

        self.logger.info(
            f"[ASYNC-EXECUTOR] Regular execution for {agent_name} (stream={should_stream_tokens})"
        )

        if should_stream_tokens and hasattr(llm, "astream"):
            collected_chunks: List[str] = []
            last_chunk = None
            first_token_time: Optional[float] = None
            stream_start_time = time.perf_counter()
            # Check once before loop - context won't change mid-execution
            # Subagents always emit explicitly since parent's LangGraph context
            # doesn't capture direct llm.astream() calls
            emit_explicitly = (
                config.is_subagent or not self._in_langgraph_streaming_context()
            )

            try:
                async for chunk in llm.astream(messages):
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    last_chunk = chunk
                    # Extract textual content from chunk
                    content = None
                    if hasattr(chunk, "content"):
                        content = chunk.content
                    elif isinstance(chunk, dict) and "content" in chunk:
                        content = chunk["content"]
                    if isinstance(content, list):
                        content = "".join(
                            part if isinstance(part, str) else str(part)
                            for part in content
                        )
                    if content:
                        collected_chunks.append(content)
                        if emit_explicitly:
                            StreamingEventEmitter.emit_content_chunk(
                                content=content,
                                agent_name=agent_name,
                                node_id=config.node_id,
                                execution_id=config.execution_id,
                                execution_order=config.execution_order,
                                db_node_id=config.db_node_id,
                            )
                # Return full message, preserving metadata from the final chunk
                final_text = "".join(collected_chunks)
                response_metadata = dict(
                    getattr(last_chunk, "response_metadata", None) or {}
                )
                usage_metadata = getattr(last_chunk, "usage_metadata", None)
                # Attach TTFT (in milliseconds) to response metadata
                if first_token_time is not None:
                    response_metadata["time_to_first_token"] = (
                        first_token_time - stream_start_time
                    ) * 1000
                return AIMessage(
                    content=final_text,
                    response_metadata=response_metadata,
                    usage_metadata=usage_metadata,
                )
            except Exception as stream_exc:
                self.logger.warning(
                    "[ASYNC-EXECUTOR] Streaming failed, falling back to ainvoke: %s",
                    stream_exc,
                )
                # fall through to non-streaming

        return await llm.ainvoke(messages)

    async def _store_memory_if_enabled(
        self,
        agent_node: EnhancedNodeData,
        agent_config: AgentConfig,
        config: AsyncExecutionConfig,
        user_message: str,
        response: Any,
    ) -> None:
        """Store memory if enabled.

        Args:
            agent_node: Agent node
            agent_config: Agent configuration
            config: Execution configuration
            user_message: User's message
            response: Agent's response
        """
        # Check if memory should be stored
        use_memory = (
            config.enable_memory
            and ExecutionConfig.use_memory()
            and agent_config.memory_enabled
        )

        if not use_memory:
            return

        # Extract response content
        response_content = extract_response_content(response)

        # Store conversation
        await self.memory_handler.store_conversation(
            agent_node.uniq_id,
            agent_node.name,
            user_message,
            response_content,
            config.db_execution_id,
        )


def _serialize_messages(
    messages: List[Any],
    final_response: Any,
) -> Dict[str, Any]:
    """Serialize LangChain messages into trace-viewer message_structure format.

    Converts the full multi-turn conversation (including intermediate tool calls
    and tool results) into a compact dict suitable for database storage.

    Args:
        messages: The full conversation message list (mutated in-place by tool executor)
        final_response: The final AIMessage response (may not be in messages yet)

    Returns:
        Message structure dict with messages list for the trace viewer
    """
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )

    serialized = []

    for msg in messages:
        entry: Dict[str, Any] = {}

        # Determine role from message type
        if isinstance(msg, SystemMessage):
            entry["role"] = "system"
        elif isinstance(msg, HumanMessage):
            entry["role"] = "human"
        elif isinstance(msg, AIMessage):
            entry["role"] = "assistant"
        elif isinstance(msg, ToolMessage):
            entry["role"] = "tool"
            entry["tool_name"] = getattr(msg, "name", None)
        else:
            entry["role"] = msg.__class__.__name__.replace("Message", "").lower()

        # Content (truncated for storage)
        content = getattr(msg, "content", "")
        if isinstance(content, str):
            entry["content"] = content[:1000]
        elif isinstance(content, list):
            # Multi-modal content — just store text parts
            text_parts = [
                p.get("text", "")
                for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            ]
            entry["content"] = " ".join(text_parts)[:1000]
        else:
            entry["content"] = str(content)[:1000]

        # Token count from usage_metadata if available
        usage = getattr(msg, "usage_metadata", None)
        if usage and isinstance(usage, dict):
            entry["token_count"] = usage.get("total_tokens") or usage.get(
                "output_tokens", 0
            )

        # Tool calls on AIMessages
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            entry["tool_calls"] = [
                {"name": tc.get("name", "unknown"), "id": tc.get("id")}
                for tc in tool_calls
            ]

        serialized.append(entry)

    # Append the final response if it's not already the last message
    if final_response and isinstance(final_response, AIMessage):
        already_included = (
            serialized
            and serialized[-1].get("role") == "assistant"
            and serialized[-1].get("content") == (final_response.content or "")[:1000]
        )
        if not already_included:
            final_entry: Dict[str, Any] = {
                "role": "assistant",
                "content": (final_response.content or "")[:1000],
            }
            usage = getattr(final_response, "usage_metadata", None)
            if usage and isinstance(usage, dict):
                final_entry["token_count"] = usage.get("total_tokens") or usage.get(
                    "output_tokens", 0
                )
            tool_calls = getattr(final_response, "tool_calls", None)
            if tool_calls:
                final_entry["tool_calls"] = [
                    {"name": tc.get("name", "unknown"), "id": tc.get("id")}
                    for tc in tool_calls
                ]
            serialized.append(final_entry)

    return {
        "messages": serialized,
        "message_count": len(serialized),
    }
