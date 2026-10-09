"""
Resume Handler for checkpoint resumption.

This module handles resuming workflow execution from checkpoints,
including subworkflow checkpoints and email checkpoint handling.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from backend.services.checkpoint import checkpoint_metadata_manager
from backend.models.workflow import NodeType
from backend.services.execution.context import set_execution_context
from backend.services.execution.history import ExecutionHistoryService
from backend.services.common.utils.websocket_notifier import ws_notifier
from backend.services.config import get_logger
from backend.services.config.execution import ExecutionConfig
from backend.services.io.extractors.final import FinalOutputExtractor
from backend.services.io.output_processor import OutputProcessor
from backend.services.execution.checkpointer_manager import get_thread_checkpointer

if TYPE_CHECKING:
    from backend.services.execution.engine import ExecutionEngine

# Initialize logger
execution_logger = get_logger("execution.resume")


class ResumeHandler:
    """
    Handles resuming workflow execution from checkpoints.

    This class manages:
    - Loading graph and checkpoint metadata
    - Handling subworkflow checkpoint delegation
    - Resuming execution with new input
    - Processing pause/interrupt events during resume
    - Finalizing execution after resume

    Attributes:
        engine: Reference to the main execution engine
    """

    def __init__(self, engine: "ExecutionEngine"):
        """
        Initialize the ResumeHandler.

        Args:
            engine: The main execution engine instance
        """
        self.engine = engine

    async def resume(
        self,
        graph_name: str,
        thread_id: str,
        checkpoint_id: str,
        new_input: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Resume execution from a checkpoint.

        Args:
            graph_name: Name of the graph to resume
            thread_id: Thread ID for the execution
            checkpoint_id: ID of the checkpoint to resume from
            new_input: Optional new input to provide when resuming

        Returns:
            Dict containing execution results with status, outputs, etc.

        Raises:
            ValueError: If graph not found
            Exception: If resume fails
        """

        resume_start = time.time()
        execution_logger.info(
            f"[TIMING-RESUME] Starting resume_from_checkpoint for {thread_id}"
        )

        # Phase 1: Load and validate
        graph = await self._load_and_validate_graph(graph_name, resume_start)

        # Phase 2: Check for subworkflow checkpoint
        checkpoint_metadata = checkpoint_metadata_manager.get_checkpoint_metadata(
            checkpoint_id
        )
        if checkpoint_metadata and checkpoint_metadata.get("subworkflow_checkpoint"):
            return await self._handle_subworkflow_resume(
                thread_id, checkpoint_id, checkpoint_metadata, new_input
            )

        # Phase 3: Initialize execution context
        db_execution_id = await self._initialize_execution_context(
            thread_id, graph_name, resume_start
        )

        # Phase 3.5a: Validate resume input against workflow guardrails
        # The START node checks initial input, but resumed input bypasses START,
        # so we must validate here to prevent guardrail circumvention via resume.
        await self._check_resume_input_guardrails(
            graph, new_input, db_execution_id, thread_id
        )

        # Phase 3.5b: Save resume input to pending node for review handling
        # This bypasses LangGraph's checkpoint mechanism which doesn't create
        # new checkpoints during resume, causing interrupt() to return stale values
        await self._save_resume_input_to_pending_node(
            db_execution_id, new_input, checkpoint_id
        )

        # Phase 4: Build and compile graph
        workflow, app = await self._build_and_compile_graph(
            graph, thread_id, db_execution_id, resume_start
        )

        # Phase 5: Notify resume started
        await self._notify_resume_started(thread_id, db_execution_id, resume_start)

        # Phase 6: Execute from checkpoint
        final_state, paused_result = await self._execute_from_checkpoint(
            app, thread_id, checkpoint_id, new_input, db_execution_id, resume_start
        )

        # Phase 7: Handle pause if occurred
        if paused_result is not None:
            execution_logger.info(
                f"[CHECKPOINT-DEBUG] Returning new paused result for thread: {thread_id}"
            )
            return paused_result

        # Phase 8: Finalize execution
        return await self._finalize_execution(
            graph, thread_id, db_execution_id, final_state, resume_start
        )

    async def _load_and_validate_graph(self, graph_name: str, resume_start: float):
        """Load and validate the graph exists."""
        graph = self.engine.graph_manager.get_graph(
            graph_name
        ) or self.engine.graph_manager.load_graph(graph_name, "default")
        if not graph:
            raise ValueError(f"Graph '{graph_name}' not found")
        execution_logger.info(
            f"[TIMING-RESUME] Graph loaded at T+{time.time() - resume_start:.3f}s"
        )
        return graph

    async def _handle_subworkflow_resume(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_metadata: Dict[str, Any],
        new_input: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Handle resuming a subworkflow checkpoint."""
        execution_logger.info(
            f"[SUBWORKFLOW-RESUME] Detected subworkflow checkpoint: {checkpoint_id}"
        )
        subworkflow_name = checkpoint_metadata.get("subworkflow_name")
        subworkflow_thread_id = checkpoint_metadata.get("subworkflow_thread_id")

        if subworkflow_name and subworkflow_thread_id:
            execution_logger.info(
                "[SUBWORKFLOW-RESUME] Delegating to SubworkflowResumeHandler"
            )
            result = await self.engine.subworkflow_resume_handler.resume_subworkflow_checkpoint(
                parent_thread_id=thread_id,
                subworkflow_thread_id=subworkflow_thread_id,
                subworkflow_name=subworkflow_name,
                checkpoint_id=checkpoint_id,
                new_input=new_input,
                checkpoint_metadata=checkpoint_metadata,
            )
            execution_logger.info(f"[SUBWORKFLOW-RESUME] Handler completed: {result}")
            return result

        raise ValueError(
            f"Invalid subworkflow checkpoint metadata: {checkpoint_metadata}"
        )

    async def _initialize_execution_context(
        self, thread_id: str, graph_name: str, resume_start: float
    ) -> Optional[int]:
        """Initialize or restore execution context."""
        # Use existing active execution entry if present
        if thread_id not in self.engine.active_executions:
            # Create a minimal entry
            self.engine.active_executions[thread_id] = {
                "execution_id": thread_id,
                "status": "running",
                "start_time": str(datetime.now(timezone.utc)),
                "graph_name": graph_name,
                "current_node": None,
                "current_node_name": None,
                "error": None,
                "db_execution_id": None,
                "node_execution_map": {},
            }

        # Look up DB execution id by websocket/thread id
        db_execution_id = self.engine.active_executions[thread_id].get(
            "db_execution_id"
        )
        if not db_execution_id:
            try:
                exec_dict = ExecutionHistoryService.get_graph_execution_dict(thread_id)
                if exec_dict:
                    db_execution_id = exec_dict.get("id")
                    self.engine.active_executions[thread_id]["db_execution_id"] = (
                        db_execution_id
                    )
            except Exception:
                pass

        # Update DB to running
        if db_execution_id:
            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id, status="running"
                )
            except Exception:
                pass

        # Set execution context for delegation tools to use subgraph executor
        # This must be set for sync_factory.py to use SubgraphDelegationExecutor
        # instead of falling back to SimpleDelegationExecutor
        if thread_id and db_execution_id:
            set_execution_context(
                execution_id=thread_id,
                db_execution_id=str(db_execution_id),
                node_execution_map=self.engine.active_executions.get(thread_id, {}).get(
                    "node_execution_map", {}
                ),
            )
            execution_logger.info(
                f"[RESUME-CONTEXT] Set execution context for resume - "
                f"thread_id: {thread_id}, db_execution_id: {db_execution_id}"
            )

        return db_execution_id

    async def _check_resume_input_guardrails(
        self,
        graph,
        new_input: Optional[Dict[str, Any]],
        db_execution_id: Optional[int],
        thread_id: str,
    ) -> None:
        """Validate resume input against workflow-level guardrails.

        Resolves workflow guardrails from policies and runs check_input()
        on the resume message. In enforce mode, raises GuardrailViolationError
        to abort the resume. In audit mode, logs violations and continues.

        Args:
            graph: The loaded graph definition
            new_input: Resume input from the user
            db_execution_id: Database execution ID for violation attribution
            thread_id: Thread ID (used as execution_id for streaming events)
        """
        if not new_input or not getattr(graph, "workflow_id", None):
            return

        # Extract the textual content from resume input
        message = (
            new_input.get("message", "")
            or new_input.get("user_message", "")
            or new_input.get("response", "")
        )
        if not message:
            # If input is a dict without a recognized message key, serialize it
            if isinstance(new_input, dict):
                import json

                message = json.dumps(new_input)
            else:
                message = str(new_input)

        if not message:
            return

        try:
            from backend.services.guardrails import get_guardrails_engine
            from backend.services.guardrails.violation_persistence import (
                ViolationPersistenceService,
            )
            from backend.services.streaming.event_emitter import StreamingEventEmitter

            engine = get_guardrails_engine()
            resolved = engine.resolve_unified(
                workflow_id=graph.workflow_id,
            )
            wf_pipeline = resolved.agent_pipeline  # List[GuardrailsConfig]

            if not wf_pipeline:
                return

            input_result = await engine.check_input(
                message, wf_pipeline, guardrails_state={}
            )

            if input_result.violations:
                for v in input_result.violations:
                    violation_db_id = ViolationPersistenceService.persist_violation(
                        v,
                        category="resume_ingress",
                        action_taken=input_result.action_taken or "blocked",
                        policy_id=v.policy_id or None,
                        policy_name=v.policy_name or None,
                        workflow_id=graph.workflow_id,
                        graph_execution_id=str(db_execution_id)
                        if db_execution_id
                        else None,
                    )
                    StreamingEventEmitter.emit_guardrail_violation(
                        category="resume_ingress",
                        rule_name=v.rule_name or "unknown",
                        message=v.message or "Resume input violation",
                        severity=v.severity or "block",
                        execution_id=thread_id,
                        violation_db_id=violation_db_id,
                        policy_name=v.policy_name or None,
                        details=v.details,
                        enforcement_mode=v.enforcement_mode or None,
                    )

            if not input_result.passed:
                from backend.services.guardrails.exceptions import (
                    GuardrailViolationError,
                )

                violation_msg = (
                    input_result.violations[0].message
                    if input_result.violations
                    else "Resume input blocked by guardrail"
                )
                raise GuardrailViolationError(
                    f"Resume input blocked: {violation_msg}",
                    violations=input_result.violations,
                )

            if input_result.sanitized_content is not None:
                execution_logger.info(
                    "[RESUME-GUARDRAILS] Resume input sanitized by workflow guardrails"
                )
                # Update the message in new_input with sanitized content
                if "message" in new_input:
                    new_input["message"] = input_result.sanitized_content
                elif "user_message" in new_input:
                    new_input["user_message"] = input_result.sanitized_content
                elif "response" in new_input:
                    new_input["response"] = input_result.sanitized_content

        except ImportError:
            execution_logger.debug(
                "[RESUME-GUARDRAILS] Guardrails module not available"
            )
        except Exception as e:
            # Don't let guardrail errors from non-GuardrailViolationError break resume
            if "GuardrailViolationError" in type(e).__name__:
                raise
            execution_logger.warning(f"[RESUME-GUARDRAILS] Guardrail check failed: {e}")

    async def _save_resume_input_to_pending_node(
        self,
        db_execution_id: Optional[str],
        new_input: Optional[Dict[str, Any]],
        checkpoint_id: Optional[str] = None,
    ) -> None:
        """Save resume input to pending_review node for retrieval in agent executor.

        This is necessary because LangGraph doesn't create new checkpoints during
        resume operations. When interrupt() is called during a resume, it returns
        the OLD resume value from the original checkpoint instead of the new one.

        By saving the resume input to the database, the agent executor can read
        the correct value instead of relying on LangGraph's broken checkpoint
        mechanism.

        Args:
            db_execution_id: Database execution ID
            new_input: The new input provided by the user for resume
            checkpoint_id: The checkpoint ID being resumed from (for linking)
        """
        from backend.services.execution.review.state_manager import (
            AgentReviewStateManager,
        )

        if not db_execution_id or not new_input:
            return

        # First, try to update the new AgentReviewState system
        try:
            review_state = AgentReviewStateManager.get_pending_by_execution(
                db_execution_id
            )
            if review_state:
                review_state_id = review_state.get("id")

                # Update checkpoint_id if provided (links to LangGraph checkpoint)
                if checkpoint_id:
                    AgentReviewStateManager.update_checkpoint_id(
                        review_state_id=review_state_id,
                        checkpoint_id=checkpoint_id,
                    )
                    execution_logger.info(
                        f"[REVIEW-RESUME] Linked checkpoint_id {checkpoint_id} to AgentReviewState"
                    )

                # Save the resume response
                AgentReviewStateManager.set_resume_response(
                    review_state_id=review_state_id,
                    resume_response=new_input,
                )
                execution_logger.info(
                    f"[REVIEW-RESUME] Saved resume response to AgentReviewState: {review_state_id}"
                )
        except Exception as e:
            execution_logger.warning(
                f"[REVIEW-RESUME] Failed to save to AgentReviewState: {e}"
            )

        # Also save to legacy node execution (for backwards compatibility)
        try:
            # Find pending_review node execution
            node_execs = ExecutionHistoryService.get_node_executions(db_execution_id)
            for ne in node_execs:
                if (
                    ne.get("status") == "pending_review"
                    and ne.get("node_type") == "AGENT"
                ):
                    # Update metadata with resume_input
                    ExecutionHistoryService.update_node_execution_metadata(
                        ne.get("id"), {"node_metadata": {"resume_input": new_input}}
                    )
                    execution_logger.info(
                        f"[REVIEW-RESUME] Saved resume_input to pending node: {ne.get('id')}"
                    )
                    break
        except Exception as e:
            execution_logger.warning(
                f"[REVIEW-RESUME] Failed to save resume_input: {e}"
            )

    async def _build_and_compile_graph(
        self, graph, thread_id: str, db_execution_id: Optional[int], resume_start: float
    ):
        """Build and compile the state graph."""
        execution_logger.info(
            f"[TIMING-RESUME] Building state graph at T+{time.time() - resume_start:.3f}s"
        )
        workflow = self.engine._build_state_graph(graph, thread_id, db_execution_id)
        checkpointer = get_thread_checkpointer()
        app = workflow.compile(checkpointer=checkpointer)
        execution_logger.info(
            f"[TIMING-RESUME] Graph compiled at T+{time.time() - resume_start:.3f}s"
        )
        return workflow, app

    async def _notify_resume_started(
        self, thread_id: str, db_execution_id: Optional[int], resume_start: float
    ):
        """Notify that resume has started."""
        if ws_notifier:
            try:
                await ws_notifier.on_execution_resumed(
                    thread_id, {"db_execution_id": db_execution_id}
                )
                execution_logger.info(
                    f"[TIMING-RESUME] WebSocket notified at T+{time.time() - resume_start:.3f}s"
                )
            except Exception:
                pass

    async def _execute_from_checkpoint(
        self,
        app,
        thread_id: str,
        checkpoint_id: str,
        new_input: Optional[Dict[str, Any]],
        db_execution_id: Optional[int],
        resume_start: float,
    ):
        """Execute the workflow from the checkpoint."""
        from langgraph.types import Command

        final_state = None
        stream_generator = None
        paused_result = None

        try:
            execution_logger.info(
                f"[CHECKPOINT-DEBUG] Starting resume astream for thread: {thread_id}, "
                f"checkpoint: {checkpoint_id} at T+{time.time() - resume_start:.3f}s"
            )

            # Debug current checkpoint state
            await self._log_checkpoint_state(thread_id)

            # Configure stream modes (same as workflow_executor)
            stream_kwargs: Dict[str, Any] = {}
            if ExecutionConfig.enable_streaming():
                stream_kwargs["stream_mode"] = ExecutionConfig.get_stream_modes()
                stream_kwargs["subgraphs"] = ExecutionConfig.include_subgraphs()
            else:
                stream_kwargs["stream_mode"] = ["updates"]

            # Stream from checkpoint with resume command
            stream_generator = app.astream(
                Command(resume=new_input if new_input is not None else ""),
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint_id,
                    },
                    "recursion_limit": 50,
                },
                **stream_kwargs,
            )

            async for raw_chunk in stream_generator:
                # Normalize stream payload shape (same as workflow_executor)
                # Handle both (namespace, mode, data) and (mode, data) formats
                mode = None
                chunk = raw_chunk
                namespace = ()  # Root namespace is empty tuple
                if isinstance(raw_chunk, tuple):
                    if len(raw_chunk) == 3:
                        # subgraphs=True format: (namespace, mode, data)
                        namespace, mode, chunk = raw_chunk
                    elif len(raw_chunk) == 2:
                        # subgraphs=False format: (mode, data)
                        mode, chunk = raw_chunk
                if mode is None:
                    # Backward-compatible default when stream_mode is ["updates"]
                    mode = "updates"

                # Skip non-root namespace events for token streaming to avoid duplicates
                if mode == "messages" and namespace:
                    continue

                # Check for __interrupt__ in ANY dict chunk, regardless of mode
                if isinstance(chunk, dict) and "__interrupt__" in chunk:
                    paused_result = await self._handle_interrupt_during_resume(
                        chunk, thread_id, checkpoint_id, db_execution_id
                    )
                    if paused_result:
                        execution_logger.info(
                            f"[CHECKPOINT-DEBUG] Interrupt detected during resume, "
                            f"letting stream complete naturally for thread: {thread_id}"
                        )
                        # Don't break - let the stream complete naturally so LangGraph
                        # properly finalizes the checkpoint state. Breaking early can
                        # leave pending interrupt data in an inconsistent format,
                        # causing KeyError on subsequent resumes.
                        continue

                # Handle token/custom streaming (forward to WebSocket)
                if mode == "messages":
                    await self._handle_stream_event(thread_id, "token", chunk)
                    continue
                if mode == "custom":
                    await self._handle_stream_event(thread_id, "custom", chunk)
                    continue

                # Process state update chunks (updates/values)
                if mode in {"updates", "values"} and isinstance(chunk, dict):
                    for node_name, node_updates in chunk.items():
                        if node_updates:
                            if final_state is None:
                                final_state = {}
                            # Merge minimal keys
                            if "node_outputs" in node_updates:
                                final_state.setdefault("node_outputs", {}).update(
                                    node_updates["node_outputs"]
                                )
                            if "results" in node_updates:
                                final_state.setdefault("results", []).extend(
                                    node_updates.get("results", [])
                                )
                            for key in [
                                "messages",
                                "current_node",
                                "metadata",
                                "execution_order",
                            ]:
                                if key in node_updates:
                                    final_state[key] = node_updates[key]
                            await self.engine.state_processor.process_update(
                                node_updates, thread_id, db_execution_id
                            )

        except asyncio.CancelledError:
            execution_logger.warning(
                f"[CHECKPOINT-DEBUG] Resume stream cancelled for thread: {thread_id}"
            )
            raise
        except Exception as e:
            execution_logger.error(
                f"[CHECKPOINT-DEBUG] Error during resume streaming for thread {thread_id}: {e}"
            )
            raise
        finally:
            # Ensure proper cleanup of the async generator
            if stream_generator is not None:
                try:
                    execution_logger.info(
                        f"[CHECKPOINT-DEBUG] Cleaning up resume stream generator for thread: {thread_id}"
                    )
                    await stream_generator.aclose()
                    execution_logger.info(
                        f"[CHECKPOINT-DEBUG] Resume stream generator closed successfully for thread: {thread_id}"
                    )
                except Exception as cleanup_error:
                    execution_logger.warning(
                        f"[CHECKPOINT-DEBUG] Error closing resume stream generator for thread {thread_id}: {cleanup_error}"
                    )

        return final_state, paused_result

    async def _log_checkpoint_state(self, thread_id: str):
        """Log checkpoint state for debugging."""
        try:
            thread_checkpointer = get_thread_checkpointer()
            checkpoint_tuple = await thread_checkpointer.aget_tuple(
                config={"configurable": {"thread_id": thread_id}}
            )
            if checkpoint_tuple and hasattr(checkpoint_tuple, "checkpoint"):
                state = checkpoint_tuple.checkpoint.get("channel_values", {})
                execution_logger.info(
                    f"[CHECKPOINT-RESUME] Current state keys before resume: {list(state.keys())}"
                )
                execution_logger.info(
                    f"[CHECKPOINT-RESUME] node_outputs in state: {list(state.get('node_outputs', {}).keys())}"
                )
                # Log sample of node_outputs
                for node_id, output in list(state.get("node_outputs", {}).items())[:3]:
                    execution_logger.info(
                        f"[CHECKPOINT-RESUME] node_output[{node_id[:8]}...]: {str(output)[:100]}..."
                    )
        except Exception as e:
            execution_logger.warning(
                f"[CHECKPOINT-RESUME] Could not inspect checkpoint state: {e}"
            )

    async def _handle_stream_event(
        self,
        execution_id: str,
        event_type: str,
        chunk: Any,
    ):
        """Forward streaming events to WebSocket clients.

        This mirrors the workflow_executor._handle_stream_event() method
        to ensure streaming events are routed correctly during resume.
        """
        if not ws_notifier or not execution_id:
            return

        payload = self._serialize_stream_chunk(chunk)

        try:
            await ws_notifier.on_stream_event(
                execution_id,
                event_type,
                payload,
            )
        except Exception as exc:
            execution_logger.debug(
                "Failed to send stream event (%s) for %s: %s",
                event_type,
                execution_id,
                exc,
            )

    @staticmethod
    def _serialize_stream_chunk(chunk: Any) -> Any:
        """Convert LangGraph stream chunks to JSON-serializable payloads.

        This mirrors workflow_executor._serialize_stream_chunk() to ensure
        consistent serialization during resume, including proper filtering
        of LangGraph metadata from message streams.
        """
        if chunk is None:
            return None

        # Already serializable types
        if isinstance(chunk, (str, int, float, bool)):
            return chunk
        if isinstance(chunk, dict):
            # Structured events from StreamingEventEmitter (guardrail_violation,
            # tool_call_start, etc.) are already JSON-serializable plain dicts.
            # Skip recursive serialization which mangles lists (e.g. single-element
            # arrays like entity_types:["CREDIT_CARD"] get unwrapped to bare strings
            # by the list/tuple branch designed for LangGraph message chunks).
            if "event_type" in chunk:
                return chunk
            return {
                k: ResumeHandler._serialize_stream_chunk(v) for k, v in chunk.items()
            }
        if isinstance(chunk, (list, tuple)):
            # Handle (message, metadata) tuples from "messages" stream mode
            # Extract content from message objects and node_id/step from metadata
            content_parts = []
            node_id = None  # Track which node this chunk belongs to
            step = None  # Track langgraph_step for iteration discrimination
            for item in chunk:
                if hasattr(item, "content"):
                    # This is a message chunk - extract just the content
                    content = item.content
                    if isinstance(content, list):
                        # Handle list content (multimodal)
                        content = "".join(
                            part if isinstance(part, str) else str(part)
                            for part in content
                        )
                    # Only add non-empty content
                    if content:
                        content_parts.append(content)
                elif isinstance(item, dict):
                    # Extract node_id and step from LangGraph metadata BEFORE skipping
                    # This allows us to attribute tokens to the correct node iteration
                    if "langgraph_node" in item and node_id is None:
                        node_id = item.get("langgraph_node")
                    if "langgraph_step" in item and step is None:
                        step = item.get("langgraph_step")
                    # Skip LangGraph metadata dicts (have keys like thread_id, langgraph_step)
                    # These are streaming metadata, not content we want to display
                    if any(
                        key in item
                        for key in (
                            "thread_id",
                            "langgraph_step",
                            "langgraph_node",
                            "checkpoint_ns",
                        )
                    ):
                        continue
                    # For other dicts, recursively serialize
                    content_parts.append(ResumeHandler._serialize_stream_chunk(item))
                else:
                    content_parts.append(ResumeHandler._serialize_stream_chunk(item))

            # Build result - either single item or joined string
            if len(content_parts) == 1:
                result = content_parts[0]
            elif len(content_parts) == 0:
                result = ""
            else:
                result = content_parts

            # Include node_id and step in result if available (for token attribution)
            if node_id:
                result_dict = {"content": result, "node_id": node_id}
                if step is not None:
                    result_dict["step"] = step
                return result_dict
            return result

        # Message chunks (AIMessageChunk, HumanMessageChunk, etc.) - extract content FIRST
        # before falling back to Pydantic model_dump() which would serialize the entire object
        content = getattr(chunk, "content", None)
        if content is not None:
            if isinstance(content, list):
                # Handle list content (multimodal)
                content = "".join(
                    part if isinstance(part, str) else str(part) for part in content
                )
            return content

        # Pydantic/BaseModel style (for non-message objects)
        for attr in ("model_dump", "dict", "json"):
            fn = getattr(chunk, attr, None)
            if callable(fn):
                try:
                    data = fn()
                    if isinstance(data, str):
                        return data
                    return ResumeHandler._serialize_stream_chunk(data)
                except Exception:
                    pass

        # Fallback to string representation
        return str(chunk)

    async def _handle_interrupt_during_resume(
        self,
        chunk: Dict[str, Any],
        thread_id: str,
        checkpoint_id: str,
        db_execution_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """Handle interrupt event during resume."""
        # Extract interrupt data
        interrupts = chunk.get("__interrupt__") or ()
        prompt_value = None
        inbox_address = None
        node_name = "Checkpoint"
        paused_node_id = None

        # [REVIEW-DEBUG] Log raw interrupt data
        execution_logger.info(
            f"[REVIEW-DEBUG] _handle_interrupt_during_resume called for thread: {thread_id}"
        )
        execution_logger.info(
            f"[REVIEW-DEBUG] Raw interrupts type: {type(interrupts)}, len: {len(interrupts) if hasattr(interrupts, '__len__') else 'N/A'}"
        )

        if isinstance(interrupts, (list, tuple)) and len(interrupts) > 0:
            try:
                interrupt_obj = interrupts[0]
                execution_logger.info(
                    f"[REVIEW-DEBUG] interrupt_obj type: {type(interrupt_obj)}, "
                    f"has value attr: {hasattr(interrupt_obj, 'value')}"
                )

                # Handle BOTH Interrupt objects (with .value attr) AND dicts (on resume)
                if hasattr(interrupt_obj, "value"):
                    # LangGraph Interrupt object (first iteration)
                    interrupt_value = interrupt_obj.value
                    execution_logger.info(
                        "[REVIEW-DEBUG] Extracted via .value attribute (Interrupt object)"
                    )
                elif isinstance(interrupt_obj, dict):
                    # Raw dict (happens on resume after rejection)
                    interrupt_value = interrupt_obj.get("value", interrupt_obj)
                    execution_logger.info(
                        "[REVIEW-DEBUG] Extracted via .get('value') from dict (resume case)"
                    )
                else:
                    interrupt_value = interrupt_obj
                    execution_logger.info(
                        "[REVIEW-DEBUG] Using interrupt_obj directly (unknown type)"
                    )

                execution_logger.info(
                    f"[REVIEW-DEBUG] interrupt_value type: {type(interrupt_value)}, "
                    f"value: {str(interrupt_value)[:500] if interrupt_value else 'None'}"
                )

                if isinstance(interrupt_value, dict):
                    execution_logger.info(
                        f"[REVIEW-DEBUG] interrupt_value keys: {list(interrupt_value.keys())}"
                    )
                    execution_logger.info(
                        f"[REVIEW-DEBUG] interrupt_value.get('type'): {interrupt_value.get('type')}"
                    )
                    execution_logger.info(
                        f"[REVIEW-DEBUG] interrupt_value.get('prompt'): {type(interrupt_value.get('prompt'))}"
                    )

                    prompt_value = interrupt_value.get("prompt", interrupt_value)
                    inbox_address = interrupt_value.get("inbox_address")
                    node_name = interrupt_value.get("node_name", "Checkpoint")
                    paused_node_id = interrupt_value.get("node_id")

                    execution_logger.info(
                        f"[REVIEW-DEBUG] After extraction - prompt_value type: {type(prompt_value)}, "
                        f"is dict: {isinstance(prompt_value, dict)}"
                    )
                    if isinstance(prompt_value, dict):
                        execution_logger.info(
                            f"[REVIEW-DEBUG] prompt_value keys: {list(prompt_value.keys())}, "
                            f"type field: {prompt_value.get('type')}"
                        )
                else:
                    prompt_value = interrupt_value
                    execution_logger.info(
                        "[REVIEW-DEBUG] interrupt_value is not dict, using as prompt_value directly"
                    )
            except Exception as e:
                execution_logger.error(
                    f"[REVIEW-DEBUG] Exception extracting interrupt: {e}"
                )
                pass

        # Fallback to current node if not in interrupt data
        if not paused_node_id:
            paused_node_id = self.engine.active_executions.get(thread_id, {}).get(
                "current_node"
            )

        # Get new checkpoint ID
        checkpoint_tuple = None
        new_ck = None
        try:
            thread_checkpointer = get_thread_checkpointer()
            checkpoint_tuple = await thread_checkpointer.aget_tuple(
                config={"configurable": {"thread_id": thread_id}}
            )
            if checkpoint_tuple and getattr(checkpoint_tuple, "checkpoint", None):
                new_ck = checkpoint_tuple.checkpoint.get("id")
        except Exception:
            pass

        # Update AgentReviewState with new checkpoint_id if this is an agent review
        if new_ck and db_execution_id:
            is_agent_review = (
                isinstance(prompt_value, dict)
                and prompt_value.get("type") == "agent_review"
            )
            if is_agent_review:
                try:
                    from backend.services.execution.review.state_manager import (
                        AgentReviewStateManager,
                    )

                    review_state = AgentReviewStateManager.get_pending_by_execution(
                        str(db_execution_id)
                    )
                    if review_state:
                        AgentReviewStateManager.update_checkpoint_id(
                            review_state_id=review_state.get("id"),
                            checkpoint_id=new_ck,
                        )
                        execution_logger.info(
                            f"[CHECKPOINT-DEBUG] Updated AgentReviewState with new checkpoint_id: {new_ck}"
                        )
                except Exception as e:
                    execution_logger.warning(
                        f"[CHECKPOINT-DEBUG] Failed to update AgentReviewState checkpoint_id: {e}"
                    )

        # Update DB to paused
        if db_execution_id:
            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id, status="paused"
                )
            except Exception:
                pass

        # Update in-memory state
        try:
            self.engine.active_executions[thread_id]["status"] = "paused"
        except Exception:
            pass

        # Check if this is an agent_review interrupt
        is_agent_review = (
            isinstance(prompt_value, dict)
            and prompt_value.get("type") == "agent_review"
        )

        # [REVIEW-DEBUG] Log the agent review detection decision
        execution_logger.info(
            f"[REVIEW-DEBUG] WebSocket decision - is_agent_review: {is_agent_review}, "
            f"prompt_value is dict: {isinstance(prompt_value, dict)}, "
            f"prompt_value type field: {prompt_value.get('type') if isinstance(prompt_value, dict) else 'N/A'}"
        )

        # Send WebSocket notification
        # For agent_review: ReviewExecutor sent initial notification (without checkpoint_id),
        # we send an update WITH checkpoint_id so frontend can resume properly
        if ws_notifier:
            try:
                payload = {
                    "checkpoint_id": new_ck or checkpoint_id,
                    "thread_id": thread_id,
                    "node_id": paused_node_id,
                    "node_name": node_name,
                    "prompt": prompt_value,
                    "db_execution_id": db_execution_id,
                }
                if inbox_address:
                    payload["inbox_address"] = inbox_address
                execution_logger.info(
                    f"[REVIEW-DEBUG] SENDING WebSocket pause (is_agent_review={is_agent_review}) - "
                    f"node_id: {paused_node_id}, node_name: {node_name}, "
                    f"checkpoint_id: {new_ck or checkpoint_id}, "
                    f"prompt_value type: {prompt_value.get('type') if isinstance(prompt_value, dict) else type(prompt_value).__name__}"
                )
                await ws_notifier.on_execution_paused(thread_id, payload)
            except Exception as e:
                execution_logger.error(
                    f"[CHECKPOINT-DEBUG] Failed to send execution_paused from resume flow: {e}"
                )

        # Return paused result
        return {
            "execution_id": db_execution_id,
            "graph_name": self.engine.active_executions[thread_id].get("graph_name"),
            "status": "paused",
            "checkpoint_id": new_ck or checkpoint_id,
            "thread_id": thread_id,
        }

    async def _finalize_execution(
        self,
        graph,
        thread_id: str,
        db_execution_id: Optional[int],
        final_state: Optional[Dict[str, Any]],
        resume_start: float,
    ) -> Dict[str, Any]:
        """Finalize execution after successful resume."""
        # Track END node execution
        await self._process_end_node(graph, thread_id, db_execution_id, final_state)

        # Mark execution as completed
        if thread_id in self.engine.active_executions:
            self.engine.active_executions[thread_id]["status"] = "completed"
            self.engine.active_executions[thread_id]["end_time"] = str(
                datetime.now(timezone.utc)
            )

        # Build final result
        final_result = {
            "execution_id": db_execution_id,
            "graph_name": graph.name,
            "status": "completed",
            "results": final_state.get("results", []) if final_state else [],
            "node_outputs": final_state.get("node_outputs", {}) if final_state else {},
            "final_output": FinalOutputExtractor.extract(final_state)
            if final_state
            else None,
        }

        # Update database
        if db_execution_id:
            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id,
                    status="completed",
                    output_data=final_result,
                    end_time=datetime.now(timezone.utc),
                )
                ExecutionHistoryService.update_execution_summary(
                    graph.name, db_execution_id
                )
            except Exception:
                pass

        # Notify completion
        if ws_notifier:
            try:
                await ws_notifier.on_execution_complete(thread_id, final_result)
            except Exception:
                pass

        return final_result

    async def _process_end_node(
        self,
        graph,
        thread_id: str,
        db_execution_id: Optional[int],
        final_state: Optional[Dict[str, Any]],
    ):
        """Process END node execution tracking."""
        end_nodes = [n for n in graph.nodes if n.type == NodeType.END]
        if not end_nodes:
            return

        end_node = end_nodes[0]
        try:
            node_exec = None
            if db_execution_id:
                # Create END node exec
                node_exec = ExecutionHistoryService.create_node_execution(
                    graph_execution_id=db_execution_id,
                    node_id=end_node.uniq_id,
                    node_name=end_node.name,
                    node_type="END",
                    execution_order=final_state.get("execution_order", 1)
                    if final_state
                    else 1,
                    input_data={},
                )
                ExecutionHistoryService.start_node_execution(node_exec["id"])

                # Process END output
                end_output_data = OutputProcessor.process(
                    final_state if final_state else {}, end_node, graph
                )
                ExecutionHistoryService.complete_node_execution(
                    node_execution_id=node_exec["id"],
                    status="completed",
                    output_data=end_output_data,
                )

                # WS notifications for END
                if ws_notifier:
                    await ws_notifier.on_node_start(
                        thread_id,
                        end_node.uniq_id,
                        end_node.name,
                        "END",
                        None,
                        None,
                        node_exec["id"],
                    )
                    await ws_notifier.on_node_complete(
                        thread_id,
                        end_node.uniq_id,
                        end_node.name,
                        end_output_data,
                        "END",
                        0.0,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        node_exec["id"],
                    )
        except Exception as e:
            execution_logger.debug(f"Failed END processing on resume: {e}")
