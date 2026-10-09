"""Evaluation orchestrator.

Coordinates the execution of evaluation runs: fans out test cases with
concurrency control, collects results, aggregates scores, and optionally
generates recommendations.
"""

import asyncio
import copy
import json
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.config import get_logger

from .eval_context import clear_evaluation_context, set_evaluation_context
from .repositories import (
    EvaluationResultRepository,
    EvaluationRunRepository,
)

logger = get_logger("evaluation.orchestrator")

# Ticket-defined defaults for per-case execution policy
DEFAULT_CASE_TIMEOUT_SECONDS = 300
DEFAULT_MAX_CASE_RETRIES = 1


class EvaluationOrchestrator:
    """Orchestrates evaluation run execution.

    Responsibilities:
        - Load run configuration and test cases from the database
        - Fan out test case executions with semaphore-based concurrency
        - Retry failed cases up to ``max_case_retries``
        - Aggregate per-case scores into run-level scores
        - Optionally invoke the recommendation engine (T5 — non-fatal)
    """

    def __init__(self):
        self._run_repo = EvaluationRunRepository()
        self._result_repo = EvaluationResultRepository()

    async def start_run(self, run_id: str) -> None:
        """Execute an evaluation run end-to-end.

        Loads the run and its test cases, fans out execution with concurrency
        control, aggregates scores, and finalises the run status.

        Args:
            run_id: UUID of the evaluation run to execute.
        """
        logger.info(f"Starting evaluation run: {run_id}")

        # ------------------------------------------------------------------
        # Load run + test cases inside a single DB session, then snapshot
        # all ORM data we need so we can safely close the session before
        # the async fan-out (avoids detached-instance errors).
        # ------------------------------------------------------------------
        from backend.models.evaluation import EvaluationTestCase
        from backend.services.database import get_db

        run_snapshot: Optional[Dict[str, Any]] = None
        test_case_snapshots: List[Dict[str, Any]] = []

        with get_db() as db:
            from backend.models.evaluation import EvaluationRun

            run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
            if not run:
                logger.error(f"Evaluation run not found: {run_id}")
                return

            run_snapshot = {
                "id": str(run.id),
                "name": run.name,
                "target_id": run.target_id,
                "target_type": run.target_type,
                "dataset_id": run.dataset_id,
                "concurrency_limit": run.concurrency_limit or 5,
                "case_timeout_seconds": run.case_timeout_seconds
                or DEFAULT_CASE_TIMEOUT_SECONDS,
                "max_case_retries": run.max_case_retries or DEFAULT_MAX_CASE_RETRIES,
                "workflow_id": run.workflow_id,
                "pillar_weights": run.pillar_weights,
                "judge_model_config": run.judge_model_config,
                "judge_output_policy": run.judge_output_policy,
                "external_integration_config": run.external_integration_config,
                "triggered_by_user_id": run.triggered_by_user_id,
            }

            # Load test cases for the dataset
            if run.dataset_id:
                cases = (
                    db.query(EvaluationTestCase)
                    .filter(EvaluationTestCase.dataset_id == run.dataset_id)
                    .all()
                )
                for tc in cases:
                    test_case_snapshots.append(
                        {
                            "id": str(tc.id),
                            "input_data": tc.input_data,
                            "expected_output": tc.expected_output,
                            "judge_criteria": tc.judge_criteria,
                            "tags": tc.tags,
                        }
                    )

        if run_snapshot is None:
            return

        total_cases = len(test_case_snapshots)
        concurrency_limit = run_snapshot["concurrency_limit"]
        case_timeout = run_snapshot["case_timeout_seconds"]
        max_retries = run_snapshot["max_case_retries"]

        # Mark run as running
        now = datetime.now(timezone.utc)
        self._run_repo.update_scores(
            run_id,
            {
                "status": "running",
                "started_at": now,
                "total_cases": total_cases,
            },
        )

        logger.info(
            f"Evaluation run {run_id}: {total_cases} cases, "
            f"concurrency={concurrency_limit}, timeout={case_timeout}s, "
            f"max_retries={max_retries}"
        )

        # ------------------------------------------------------------------
        # Fan-out: execute each test case with concurrency control
        # ------------------------------------------------------------------
        semaphore = asyncio.Semaphore(concurrency_limit)
        completed_cases = 0
        failed_cases = 0

        async def execute_case(test_case: Dict[str, Any]) -> None:
            nonlocal completed_cases, failed_cases

            async with semaphore:
                success = False
                for attempt in range(max_retries + 1):
                    try:
                        await asyncio.wait_for(
                            self._execute_single_case(
                                run_id=run_id,
                                run_snapshot=run_snapshot,
                                test_case=test_case,
                            ),
                            timeout=case_timeout,
                        )
                        success = True
                        break
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"Test case {test_case['id']} timed out "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                    except Exception as exc:
                        logger.warning(
                            f"Test case {test_case['id']} failed "
                            f"(attempt {attempt + 1}/{max_retries + 1}): {exc}"
                        )

                if success:
                    completed_cases += 1
                else:
                    failed_cases += 1
                    # Write a failed result for exhausted retries
                    try:
                        self._result_repo.create(
                            {
                                "run_id": run_id,
                                "test_case_id": test_case["id"],
                                "composite_score": 0.0,
                                "reliability_raw": {
                                    "status": "failed",
                                    "reason": "all_retries_exhausted",
                                    "max_retries": max_retries,
                                },
                            }
                        )
                    except Exception as result_exc:
                        logger.error(
                            f"Failed to write failed result for test case "
                            f"{test_case['id']}: {result_exc}"
                        )

                # Update run counters
                try:
                    self._run_repo.update_status(
                        run_id,
                        status="running",
                        completed_cases=completed_cases,
                        failed_cases=failed_cases,
                    )
                except Exception as status_exc:
                    logger.warning(f"Failed to update run counters: {status_exc}")

        # Execute all cases concurrently
        await asyncio.gather(
            *(execute_case(tc) for tc in test_case_snapshots),
            return_exceptions=True,
        )

        # ------------------------------------------------------------------
        # Aggregate scores
        # ------------------------------------------------------------------
        self._aggregate_run_scores(run_id)

        # ------------------------------------------------------------------
        # Phoenix telemetry export (non-fatal)
        # ------------------------------------------------------------------
        await self._emit_phoenix_traces(run_id, run_snapshot)

        # ------------------------------------------------------------------
        # Finalise run — persist status before recommendation generation
        # so that recommendations execute in the documented post-completion
        # lifecycle phase.
        # ------------------------------------------------------------------
        final_status = "completed" if failed_cases == 0 else "completed_with_failures"
        self._run_repo.update_scores(
            run_id,
            {
                "status": final_status,
                "completed_at": datetime.now(timezone.utc),
                "completed_cases": completed_cases,
                "failed_cases": failed_cases,
            },
        )

        logger.info(
            f"Evaluation run {run_id} finished: status={final_status}, "
            f"completed={completed_cases}, failed={failed_cases}"
        )

        # ------------------------------------------------------------------
        # Generate recommendations (T5 — non-fatal, post-completion)
        # ------------------------------------------------------------------
        try:
            from .recommendations import RecommendationEngine

            rec_engine = RecommendationEngine()
            await rec_engine.generate_recommendations(run_id)
        except ImportError:
            logger.debug("RecommendationEngine not available yet (T5)")
        except Exception as rec_exc:
            logger.warning(f"Recommendation generation failed (non-fatal): {rec_exc}")

    async def _execute_single_case(
        self,
        run_id: str,
        run_snapshot: Dict[str, Any],
        test_case: Dict[str, Any],
    ) -> None:
        """Execute the target graph for a single test case, then score.

        Runs the evaluated target via ``ExecutionEngine.execute_graph()`` to
        produce real ``GraphExecution``/``NodeExecution`` telemetry, then
        delegates scoring to ``CompositeScorer`` as a post-execution step.

        Args:
            run_id: Parent evaluation run UUID.
            run_snapshot: Snapshotted run configuration.
            test_case: Snapshotted test case data.
        """
        from backend.services.dependency_injection import (
            get_execution_engine,
            get_graph_manager,
        )

        # ------------------------------------------------------------------
        # Guard: abort if the evaluation run was deleted while we were queued
        # ------------------------------------------------------------------
        run_check = self._run_repo.get(run_id)
        if run_check is None:
            logger.warning(
                f"Evaluation run {run_id} no longer exists, skipping test case {test_case['id']}"
            )
            return

        # ------------------------------------------------------------------
        # Step 1: Load or build the target graph based on target_type
        # ------------------------------------------------------------------
        target_id = run_snapshot["target_id"]
        target_type = run_snapshot["target_type"]
        workflow_id = run_snapshot.get("workflow_id")
        username = run_snapshot.get("triggered_by_user_id") or "default"

        graph_manager = get_graph_manager()
        graph = None
        # Track the source workflow name for Phoenix project routing.
        # For agent/tool evals the minimal graph is named after the target
        # node, but spans should land in the source workflow's Phoenix project.
        source_workflow_name: Optional[str] = None

        if target_type == "workflow":
            # Full workflow execution
            if workflow_id:
                graph = graph_manager.load_graph_by_workflow_id(
                    workflow_id, username=username
                )
            else:
                graph = graph_manager.get_graph(target_id)
                if graph is None:
                    graph = graph_manager.load_graph(target_id, username=username)

            if graph is None:
                logger.error(
                    f"Target workflow not found: target_id={target_id}, workflow_id={workflow_id}"
                )
                self._result_repo.create(
                    {
                        "run_id": run_id,
                        "test_case_id": test_case["id"],
                        "composite_score": 0.0,
                        "reliability_raw": {
                            "status": "failed",
                            "reason": "source_workflow_not_found",
                            "target_id": target_id,
                            "workflow_id": workflow_id,
                        },
                    }
                )
                return

        elif target_type in ("agent", "tool"):
            # Isolated agent/tool evaluation — build minimal graph
            source_graph = None
            if workflow_id:
                source_graph = graph_manager.load_graph_by_workflow_id(
                    workflow_id, username=username
                )
            if source_graph is None:
                logger.error(
                    f"Source workflow not found for {target_type} eval: workflow_id={workflow_id}"
                )
                self._result_repo.create(
                    {
                        "run_id": run_id,
                        "test_case_id": test_case["id"],
                        "composite_score": 0.0,
                        "reliability_raw": {
                            "status": "failed",
                            "reason": "source_workflow_not_found",
                            "workflow_id": workflow_id,
                        },
                    }
                )
                return

            source_workflow_name = source_graph.name

            target_node = source_graph.get_node_by_id(target_id)
            if target_node is None:
                logger.error(
                    f"Target node {target_id} not found in workflow {workflow_id}"
                )
                self._result_repo.create(
                    {
                        "run_id": run_id,
                        "test_case_id": test_case["id"],
                        "composite_score": 0.0,
                        "reliability_raw": {
                            "status": "failed",
                            "reason": "target_node_not_found",
                            "target_id": target_id,
                            "workflow_id": workflow_id,
                        },
                    }
                )
                return

            graph = self._build_minimal_graph(
                copy.deepcopy(target_node), source_graph, target_type
            )

        elif target_type == "model":
            # Isolated model evaluation — synthetic graph with no source workflow
            graph = self._build_model_graph(target_id)
            if graph is None:
                self._result_repo.create(
                    {
                        "run_id": run_id,
                        "test_case_id": test_case["id"],
                        "composite_score": 0.0,
                        "reliability_raw": {
                            "status": "failed",
                            "reason": "model_deployment_not_found",
                            "target_id": target_id,
                        },
                    }
                )
                return

        if graph is None:
            logger.error(
                f"Target graph not found for evaluation: target_id={target_id}, "
                f"target_type={target_type}, workflow_id={workflow_id}"
            )
            self._result_repo.create(
                {
                    "run_id": run_id,
                    "test_case_id": test_case["id"],
                    "composite_score": 0.0,
                    "reliability_raw": {
                        "status": "failed",
                        "reason": "target_graph_not_found",
                        "target_id": target_id,
                    },
                }
            )
            return

        # ------------------------------------------------------------------
        # Step 2: Execute the target graph via ExecutionEngine
        # ------------------------------------------------------------------
        # Resolve the Phoenix project name from the source workflow name so
        # all traces and evaluation annotations land in the workflow's Phoenix
        # project.  For agent/tool evals the minimal graph is named after the
        # target node, so we use the captured source_workflow_name instead.
        from backend.services.phoenix.tracing import sanitize_project_name

        phoenix_display_name = source_workflow_name or graph.name
        phoenix_project = (
            sanitize_project_name(phoenix_display_name)
            if phoenix_display_name
            else None
        )

        # Register the graph under its name in active_graphs so the
        # tool factory can find it during execution (delegation tools, connected
        # tool nodes, etc. are resolved via active_graphs[graph_name]).
        eval_graph_key: Optional[str] = None
        if graph.name:
            eval_graph_key = graph.name
            graph_manager.active_graphs[eval_graph_key] = graph

        execution_id = f"eval_{run_id}_{test_case['id']}_{uuid.uuid4().hex[:8]}"
        raw_input = test_case.get("input_data") or ""
        # Backward compat: old test cases may store dicts
        if isinstance(raw_input, dict):
            message = raw_input.get("message", "") or json.dumps(raw_input)
        else:
            message = str(raw_input)
        initial_input = {"message": message}

        # Resolve attached file → inject as file_info (same format as trigger-form)
        file_info = self._resolve_test_case_file(test_case["id"])
        if file_info:
            initial_input["file_info"] = file_info

        graph_execution_id: Optional[str] = None

        # Set evaluation context so downstream LLM calls are routed through
        # the bounded dispatch queue.
        set_evaluation_context(run_id)
        try:
            engine = get_execution_engine()

            # Wrap execution in Phoenix span-correlation context if available
            _using_ctx = None
            try:
                from openinference.instrumentation import using_attributes

                run_name = run_snapshot.get("name") or ""
                _using_ctx = using_attributes(
                    metadata={
                        "evaluation_execution_id": execution_id,
                        "evaluation_run_id": run_id,
                        "evaluation_run_name": run_name,
                        "test_case_id": test_case["id"],
                        "target_type": target_type,
                        **({"workflow_id": workflow_id} if workflow_id else {}),
                    },
                    tags=["evaluation", target_type],
                )
            except ImportError:
                logger.debug(
                    "openinference.instrumentation not available, skipping span correlation"
                )

            if _using_ctx is not None:
                _using_ctx.__enter__()

            try:
                exec_result = await engine.execute_graph(
                    graph=graph,
                    initial_input=initial_input,
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    evaluation_run_id=run_id,
                    trigger_type="evaluation",
                    phoenix_project_name=phoenix_project,
                )
            finally:
                if _using_ctx is not None:
                    _using_ctx.__exit__(None, None, None)
            # The engine returns execution_id as the DB graph execution UUID
            graph_execution_id = (
                str(exec_result.get("execution_id")) if exec_result else None
            )

            logger.info(
                f"Target graph executed for test case {test_case['id']}: "
                f"graph_execution_id={graph_execution_id}, "
                f"status={exec_result.get('status') if exec_result else 'unknown'}"
            )
        except Exception as exec_exc:
            logger.error(
                f"Target graph execution failed for test case {test_case['id']}: {exec_exc}\n"
                f"{traceback.format_exc()}"
            )
            try:
                self._result_repo.create(
                    {
                        "run_id": run_id,
                        "test_case_id": test_case["id"],
                        "graph_execution_id": graph_execution_id,
                        "composite_score": 0.0,
                        "reliability_raw": {
                            "status": "failed",
                            "reason": "execution_error",
                            "error": str(exec_exc),
                        },
                    }
                )
            except Exception as result_exc:
                logger.warning(
                    f"Could not record failure result for test case {test_case['id']} "
                    f"(run may have been deleted): {result_exc}"
                )
            return
        finally:
            clear_evaluation_context()
            # Clean up the temporary active_graphs entry to avoid leaking memory
            if eval_graph_key and eval_graph_key in graph_manager.active_graphs:
                del graph_manager.active_graphs[eval_graph_key]

        # ------------------------------------------------------------------
        # Step 3: Score the execution result (post-execution)
        # ------------------------------------------------------------------
        try:
            from .scoring import CompositeScorer
        except ImportError:
            logger.debug("CompositeScorer not available yet (T3), writing stub result")
            self._result_repo.create(
                {
                    "run_id": run_id,
                    "test_case_id": test_case["id"],
                    "graph_execution_id": graph_execution_id,
                    "composite_score": None,
                    "reliability_raw": {"status": "scorer_not_implemented"},
                }
            )
            return

        scorer = CompositeScorer()

        result_data = await scorer.score_test_case(
            run_snapshot=run_snapshot,
            test_case=test_case,
        )

        # Store evaluation_execution_id in quality_raw so the Phoenix adapter
        # can correlate spans without a schema change.
        if "quality_raw" not in result_data or result_data["quality_raw"] is None:
            result_data["quality_raw"] = {}
        result_data["quality_raw"]["evaluation_execution_id"] = execution_id

        # Build trace_reference from the root span captured during execution.
        # This is available immediately (no post-hoc Phoenix query needed).
        phoenix_trace_ref = (
            exec_result.get("phoenix_trace_ref") if exec_result else None
        )
        if phoenix_trace_ref and phoenix_trace_ref.get("trace_id"):
            from backend.services.phoenix.config import (
                build_trace_path,
                resolve_phoenix_config,
            )

            ext_config = run_snapshot.get("external_integration_config") or {}
            effective_config = resolve_phoenix_config(
                override=ext_config.get("phoenix")
            )
            trace_path = build_trace_path(
                phoenix_trace_ref["project"],
                phoenix_trace_ref["trace_id"],
                effective_config,
            )
            result_data["trace_reference"] = {
                "project": phoenix_trace_ref["project"],
                "trace_id": phoenix_trace_ref["trace_id"],
                "span_id": phoenix_trace_ref.get("span_id"),
                "execution_id": execution_id,
                "path": trace_path,
            }

        result_data["run_id"] = run_id
        result_data["test_case_id"] = test_case["id"]
        result_data["graph_execution_id"] = graph_execution_id
        self._result_repo.create(result_data)

    @staticmethod
    def _resolve_test_case_file(test_case_id: str) -> Optional[Dict[str, Any]]:
        """Load attached file for a test case and return as FileUploadData dict.

        Returns None if no file is attached. The returned dict matches the
        format used by the HTTP execution ``/trigger-form`` endpoint so the
        execution pipeline handles it identically.
        """
        import base64

        from backend.models.evaluation import TestCaseFile
        from backend.services.database import get_db

        try:
            with get_db() as db:
                tcf = (
                    db.query(TestCaseFile)
                    .filter(TestCaseFile.test_case_id == test_case_id)
                    .first()
                )
                if not tcf:
                    return None

                import os

                ext = (
                    os.path.splitext(tcf.filename)[1].lower()
                    if tcf.filename
                    else ".tmp"
                )
                return {
                    "base64": base64.b64encode(bytes(tcf.content)).decode("utf-8"),
                    "extension": ext,
                    "name": tcf.filename,
                    "type": tcf.mime_type,
                    "size": tcf.file_size,
                }
        except Exception as exc:
            logger.warning(
                f"Failed to resolve file for test case {test_case_id}: {exc}"
            )
            return None

    def _build_minimal_graph(self, target_node, source_graph, target_type: str):
        """Build a minimal START → target_node → END graph for isolated evaluation.

        For agent target_type, also includes the agent's tool nodes so tool
        calls work during execution.

        For tool target_type, wraps the tool node in a synthetic agent so that
        the execution pipeline produces an AIMessage (tool nodes like
        HTTP_REQUEST cannot run standalone in a LangGraph).
        """
        from backend.models.workflow.base import Connection, Position
        from backend.models.workflow.enums import ConnectionType, NodeType
        from backend.models.workflow.graph import GraphData
        from backend.models.workflow.node import EnhancedNodeData

        start_node = EnhancedNodeData(
            uniq_id="__eval_start__",
            name="START",
            type=NodeType.START,
            position=Position(x=0, y=0),
        )
        end_node = EnhancedNodeData(
            uniq_id="__eval_end__",
            name="END",
            type=NodeType.END,
            position=Position(x=600, y=0),
        )

        # Clear sub-agent flag so the graph builder treats this node as a
        # top-level node in the isolated evaluation graph.
        target_node.is_sub_agent = False
        target_node.parent_agent_id = None

        # For tool target_type, wrap the tool in a synthetic agent node.
        # Tool nodes (HTTP_REQUEST, DOCUMENT_SEARCH, etc.) cannot execute
        # standalone — they must be invoked by an agent node which produces
        # the AIMessage that LangGraph requires.
        if target_type == "tool":
            from backend.models.workflow.configs.agent import AgentConfig
            from backend.models.workflow.configs.llm import LLMConfig

            # Find the agent that owns this tool in the source graph to
            # inherit its LLM config, or fall back to a sensible default.
            owner_llm_config = None
            for conn in source_graph.connections:
                if (
                    conn.target_id == target_node.uniq_id
                    and conn.connection_type == ConnectionType.TOOL
                ):
                    owner_agent = source_graph.get_node_by_id(conn.source_id)
                    if (
                        owner_agent
                        and owner_agent.type == NodeType.AGENT
                        and owner_agent.agent_config
                        and owner_agent.agent_config.llm_config
                    ):
                        owner_llm_config = copy.deepcopy(
                            owner_agent.agent_config.llm_config
                        )
                    break

            if owner_llm_config is None:
                owner_llm_config = LLMConfig(
                    provider="azure_openai", model_name="gpt-4o-mini"
                )

            wrapper_agent = EnhancedNodeData(
                uniq_id="__eval_tool_wrapper_agent__",
                name=f"Eval wrapper for {target_node.name}",
                type=NodeType.AGENT,
                position=Position(x=300, y=0),
                agent_config=AgentConfig(
                    llm_config=owner_llm_config,
                    system_prompt=(
                        "You are a tool execution proxy. You MUST follow these rules:\n"
                        f"1. IMMEDIATELY call the '{target_node.name}' tool with the user's input. "
                        "Do NOT respond with text first — your very first action MUST be a tool call.\n"
                        "2. After receiving the tool result, return the EXACT raw response. "
                        "Do NOT summarise, format, interpret, or add any commentary.\n"
                        "3. NEVER acknowledge instructions, ask clarifying questions, or produce "
                        "any output other than the raw tool result."
                    ),
                ),
            )

            target_node.position = Position(x=300, y=200)

            nodes = [start_node, wrapper_agent, target_node, end_node]
            connections = [
                Connection(
                    source_id="__eval_start__",
                    target_id="__eval_tool_wrapper_agent__",
                    connection_type=ConnectionType.WORKFLOW,
                ),
                Connection(
                    source_id="__eval_tool_wrapper_agent__",
                    target_id=target_node.uniq_id,
                    connection_type=ConnectionType.TOOL,
                ),
                Connection(
                    source_id="__eval_tool_wrapper_agent__",
                    target_id="__eval_end__",
                    connection_type=ConnectionType.WORKFLOW,
                ),
            ]

            return GraphData(
                name=target_node.name,
                nodes=nodes,
                connections=connections,
                workflow_id=source_graph.workflow_id,
            )

        target_node.position = Position(x=300, y=0)

        nodes = [start_node, target_node, end_node]
        connections = [
            Connection(
                source_id="__eval_start__",
                target_id=target_node.uniq_id,
                connection_type=ConnectionType.WORKFLOW,
            ),
            Connection(
                source_id=target_node.uniq_id,
                target_id="__eval_end__",
                connection_type=ConnectionType.WORKFLOW,
            ),
        ]

        # For agent type, include associated tool nodes so the agent can
        # invoke its tools during evaluation.
        if target_type == "agent":
            tool_nodes = source_graph.get_tool_nodes_for_agent(target_node.uniq_id)
            for tn in tool_nodes:
                tn_copy = copy.deepcopy(tn)
                nodes.append(tn_copy)
                connections.append(
                    Connection(
                        source_id=target_node.uniq_id,
                        target_id=tn_copy.uniq_id,
                        connection_type=ConnectionType.TOOL,
                    )
                )

        return GraphData(
            name=target_node.name,
            nodes=nodes,
            connections=connections,
            workflow_id=source_graph.workflow_id,
        )

    def _build_model_graph(self, model_deployment_id: str):
        """Build a synthetic START → AGENT → END graph for isolated model evaluation.

        The agent node is configured with the specified model deployment. The
        execution engine's LLM enrichment pipeline resolves full credentials
        at runtime.
        """
        from backend.models.workflow.base import Connection, Position
        from backend.models.workflow.configs.llm import LLMConfig
        from backend.models.workflow.enums import ConnectionType, NodeType
        from backend.models.workflow.graph import GraphData
        from backend.models.workflow.node import EnhancedNodeData

        try:
            from backend.services.model_deployment.service import ModelDeploymentService

            deployment = ModelDeploymentService().get_deployment(model_deployment_id)
        except Exception as exc:
            logger.error(
                f"Failed to look up model deployment {model_deployment_id}: {exc}"
            )
            return None

        if not deployment:
            logger.error(f"Model deployment not found: {model_deployment_id}")
            return None

        llm_config = LLMConfig(
            provider=deployment.get("provider", "azure_openai"),
            model_name=deployment.get("model_name", ""),
            model_deployment_id=model_deployment_id,
        )

        start_node = EnhancedNodeData(
            uniq_id="__eval_start__",
            name="START",
            type=NodeType.START,
            position=Position(x=0, y=0),
        )

        from backend.models.workflow.configs.agent import AgentConfig

        agent_node = EnhancedNodeData(
            uniq_id="__eval_model_agent__",
            name=f"Model: {deployment.get('display_name') or deployment.get('name', 'eval')}",
            type=NodeType.AGENT,
            position=Position(x=300, y=0),
            agent_config=AgentConfig(llm_config=llm_config),
        )

        end_node = EnhancedNodeData(
            uniq_id="__eval_end__",
            name="END",
            type=NodeType.END,
            position=Position(x=600, y=0),
        )

        model_display_name = deployment.get("display_name") or deployment.get(
            "name", model_deployment_id[:8]
        )
        return GraphData(
            name=model_display_name,
            nodes=[start_node, agent_node, end_node],
            connections=[
                Connection(
                    source_id="__eval_start__",
                    target_id="__eval_model_agent__",
                    connection_type=ConnectionType.WORKFLOW,
                ),
                Connection(
                    source_id="__eval_model_agent__",
                    target_id="__eval_end__",
                    connection_type=ConnectionType.WORKFLOW,
                ),
            ],
        )

    async def _emit_phoenix_traces(
        self, run_id: str, run_snapshot: Dict[str, Any]
    ) -> None:
        """Emit run-level traces to Phoenix if configured.

        Resolves the effective Phoenix config from global env + optional
        per-run override, then invokes :class:`PhoenixTraceAdapter` in a
        guarded block so that telemetry failures never change run
        completion state.

        Args:
            run_id: The evaluation run UUID.
            run_snapshot: Snapshotted run configuration.
        """
        try:
            from backend.services.phoenix.config import resolve_phoenix_config

            from .phoenix_adapter import PhoenixTraceAdapter

            ext_config = run_snapshot.get("external_integration_config") or {}
            effective_config = resolve_phoenix_config(
                override=ext_config.get("phoenix")
            )

            if not effective_config.enabled or not effective_config.api_base_url:
                return

            results = self._result_repo.list_by_run(run_id)
            result_summaries = [
                {
                    "result_id": str(getattr(r, "id", "")),
                    "test_case_id": str(getattr(r, "test_case_id", "") or ""),
                    "graph_execution_id": str(
                        getattr(r, "graph_execution_id", "") or ""
                    ),
                    "evaluation_execution_id": (
                        getattr(r, "quality_raw", None) or {}
                    ).get("evaluation_execution_id", ""),
                    "composite_score": getattr(r, "composite_score", None),
                    "cost_score": getattr(r, "cost_score", None),
                    "quality_score": getattr(r, "quality_score", None),
                    "reliability_score": getattr(r, "reliability_score", None),
                    "latency_score": getattr(r, "latency_score", None),
                    "quality_raw": getattr(r, "quality_raw", None) or {},
                    "guardrail_signals": getattr(r, "guardrail_signals", None) or {},
                }
                for r in results
            ]

            # Collect current aggregated scores from the run
            run_obj = self._run_repo.get(run_id)
            run_scores: Dict[str, Any] = {}
            if run_obj:
                for field in (
                    "composite_score",
                    "cost_score",
                    "quality_score",
                    "reliability_score",
                    "latency_score",
                ):
                    val = getattr(run_obj, field, None)
                    if val is not None:
                        run_scores[field] = val

            # Derive the Phoenix project name from the original workflow name.
            # Evaluation traces are routed to the workflow's own Phoenix
            # project so that execution
            # spans and evaluation annotations live side-by-side.
            from backend.services.phoenix.tracing import sanitize_project_name

            target_name = self._resolve_target_display_name(run_snapshot)
            eval_project = (
                sanitize_project_name(target_name)
                if target_name
                else effective_config.project_name
            )

            adapter = PhoenixTraceAdapter(effective_config)
            export_result = await adapter.export_run_traces(
                run_id=run_id,
                run_scores=run_scores,
                result_summaries=result_summaries,
                project_name=eval_project,
            )

            # Persist per-result trace_reference
            try:
                for result_id, ref in export_result.get(
                    "result_trace_references", {}
                ).items():
                    self._result_repo.update(result_id, {"trace_reference": ref})
            except Exception as ref_exc:
                logger.warning(
                    "Failed to persist per-result trace references for run "
                    "%s (non-fatal): %s",
                    run_id,
                    ref_exc,
                )

            # Persist run-level external_eval_summary
            run_summary = export_result.get("run_summary", {})
            if run_summary:
                try:
                    existing_summary = {}
                    run_obj_fresh = self._run_repo.get(run_id)
                    if run_obj_fresh:
                        existing_summary = (
                            getattr(run_obj_fresh, "external_eval_summary", None) or {}
                        )
                    merged = {**existing_summary, **run_summary}
                    self._run_repo.update_scores(
                        run_id, {"external_eval_summary": merged}
                    )
                except Exception as persist_exc:
                    logger.warning(
                        "Failed to persist Phoenix run summary for run "
                        "%s (non-fatal): %s",
                        run_id,
                        persist_exc,
                    )

            logger.info("Phoenix trace export completed for run %s", run_id)
        except ImportError:
            logger.debug("PhoenixTraceAdapter not available, skipping trace export")
        except Exception as exc:
            logger.warning(
                "Phoenix trace export failed for run %s (non-fatal): %s", run_id, exc
            )

    @staticmethod
    def _resolve_target_display_name(run_snapshot: Dict[str, Any]) -> str:
        """Resolve the human-readable name for the evaluation target.

        The Phoenix project is created using the graph's display name (not the
        UUID), so we must resolve it here to match.  Falls back to target_id
        when the name cannot be resolved.
        """
        target_id = run_snapshot.get("target_id", "") or ""
        target_type = run_snapshot.get("target_type", "workflow")
        workflow_id = run_snapshot.get("workflow_id")

        try:
            from backend.services.database.session import get_db

            with get_db() as db:
                if target_type == "workflow":
                    from backend.models.workflows import Workflow as WfModel

                    lookup_id = workflow_id or target_id
                    if lookup_id:
                        wf = db.query(WfModel).filter(WfModel.id == lookup_id).first()
                        if wf and wf.name:
                            return wf.name

                elif target_type in ("agent", "tool"):
                    # Agent/tool evals route spans to the source workflow's
                    # Phoenix project (not the node name) so annotations
                    # must resolve the same workflow name.
                    if workflow_id:
                        from backend.models.workflows import Workflow as WfModel

                        wf = db.query(WfModel).filter(WfModel.id == workflow_id).first()
                        if wf and wf.name:
                            return wf.name

                elif target_type == "model":
                    from backend.models.configuration.model_deployment import (
                        ModelDeployment,
                    )

                    dep = (
                        db.query(ModelDeployment)
                        .filter(ModelDeployment.id == target_id)
                        .first()
                    )
                    if dep:
                        name = getattr(dep, "display_name", None) or getattr(
                            dep, "name", None
                        )
                        if name:
                            return name
        except Exception as exc:
            logger.debug("Could not resolve target display name: %s", exc)

        return target_id

    def _aggregate_run_scores(self, run_id: str) -> None:
        """Compute average scores across all results and update the run.

        Args:
            run_id: The evaluation run UUID.
        """
        results = self._result_repo.list_by_run(run_id)
        if not results:
            logger.warning(f"No results to aggregate for run {run_id}")
            return

        score_fields = [
            "composite_score",
            "cost_score",
            "quality_score",
            "reliability_score",
            "latency_score",
        ]

        averages: Dict[str, Optional[float]] = {}
        for field in score_fields:
            values = [
                getattr(r, field) for r in results if getattr(r, field) is not None
            ]
            averages[field] = sum(values) / len(values) if values else None

        # Filter out None values before updating
        scores_to_update = {k: v for k, v in averages.items() if v is not None}
        if scores_to_update:
            self._run_repo.update_scores(run_id, scores_to_update)
            logger.info(f"Aggregated scores for run {run_id}: {scores_to_update}")
