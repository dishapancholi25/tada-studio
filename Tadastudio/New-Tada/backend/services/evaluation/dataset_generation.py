"""Dataset generation service for creating evaluation test cases.

Supports both AI-generated and manually added test cases with a
configurable per-dataset size cap (MAX_EVAL_DATASET_SIZE).
"""

import json
import logging
import os
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import func

from backend.models.evaluation import EvaluationDataset, EvaluationTestCase
from backend.models.execution.execution_feedback import ExecutionFeedback
from backend.models.execution.graph_execution import GraphExecution
from backend.models.execution.node_execution import NodeExecution
from backend.models.workflow.configs.llm import LLMConfig
from backend.services.database import get_db
from backend.services.llm_models.factory import LLMFactory
from backend.services.model_deployment import ModelDeploymentService

MAX_EVAL_DATASET_SIZE = int(os.getenv("MAX_EVAL_DATASET_SIZE", "200"))

logger = logging.getLogger(__name__)


class DatasetGenerationService:
    """Service for generating and managing evaluation dataset test cases."""

    # ------------------------------------------------------------------
    # Content filter / guardrail helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_content_filter_error(exc: Exception) -> bool:
        """Return ``True`` if *exc* is an Azure/OpenAI content-filter rejection."""
        msg = str(exc).lower()
        return (
            "content_filter" in msg
            or "content management policy" in msg
            or "responsibleaipolicyviolation" in msg
        )

    @staticmethod
    def _user_friendly_filter_message(exc: Exception) -> str:
        """Return a concise, user-facing message for a content-filter error."""
        msg = str(exc).lower()
        # Try to extract which filter triggered
        filter_detail = ""
        if "jailbreak" in msg:
            filter_detail = " (jailbreak detection)"
        elif "'hate'" in msg and "'filtered': true" in msg:
            filter_detail = " (hate speech detection)"
        elif "'sexual'" in msg and "'filtered': true" in msg:
            filter_detail = " (sexual content detection)"
        elif "'violence'" in msg and "'filtered': true" in msg:
            filter_detail = " (violence detection)"
        elif "self_harm" in msg and "'filtered': true" in msg:
            filter_detail = " (self-harm detection)"
        return (
            f"The AI model's content safety filter blocked this request{filter_detail}. "
            "Try rephrasing your seed prompt to avoid language that may trigger content filters."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_ai_test_cases(
        self,
        dataset_id: str,
        seed_prompt: str,
        count: int = 10,
        model_config: Optional[Dict[str, Any]] = None,
        target_type: Optional[str] = None,
        include_edge_cases: bool = False,
        include_adversarial: bool = False,
        generator_model: Optional[Dict[str, Any]] = None,
        example_execution_ids: Optional[List[str]] = None,
        target_node_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate test cases using an LLM and persist them.

        Performs a cheap pre-check before calling the LLM so we don't
        waste tokens when the dataset is already at capacity.

        Args:
            dataset_id: Target dataset UUID.
            seed_prompt: Prompt describing what kind of test cases to generate.
            count: Desired number of test cases to generate.
            model_config: Optional LLM configuration dict (default model).
            target_type: Type of target being evaluated (e.g. ``"workflow"``,
                ``"agent"``, ``"tool"``). Shapes the generated prompts.
            include_edge_cases: When ``True``, instruct the LLM to include
                edge-case scenarios in the generated test cases.
            include_adversarial: When ``True``, instruct the LLM to include
                adversarial / stress-test scenarios.
            generator_model: Optional override LLM configuration for the
                generator model. When provided, takes precedence over
                ``model_config``.

        Returns:
            List of saved test-case dicts.

        Raises:
            ValueError: If the dataset is at capacity, the requested count
                exceeds remaining slots, or LLM output is malformed.
        """
        # Pre-check capacity
        with get_db() as db:
            current_count = (
                db.query(func.count(EvaluationTestCase.id))
                .filter(EvaluationTestCase.dataset_id == dataset_id)
                .scalar()
            ) or 0

        remaining = MAX_EVAL_DATASET_SIZE - current_count

        if remaining <= 0:
            raise ValueError(
                f"Dataset already has {current_count} test cases "
                f"(max {MAX_EVAL_DATASET_SIZE}). Cannot add more. "
                f"Remaining slots: 0"
            )

        if count > remaining:
            raise ValueError(
                f"Requested {count} test cases but only {remaining} slots "
                f"remaining (current: {current_count}, max: {MAX_EVAL_DATASET_SIZE}). "
                f"Remaining slots: {remaining}"
            )

        logger.info(
            "Generating %d AI test cases for dataset %s (current: %d, cap: %d)",
            count,
            dataset_id,
            current_count,
            MAX_EVAL_DATASET_SIZE,
        )

        # Resolve example executions for few-shot context
        example_context = ""
        if example_execution_ids:
            example_context = self._build_example_context(
                example_execution_ids, target_node_id=target_node_id
            )

        system_prompt = self._build_generation_system_prompt(target_type=target_type)
        user_prompt = self._build_generation_user_prompt(
            seed_prompt,
            count,
            target_type=target_type,
            include_edge_cases=include_edge_cases,
            include_adversarial=include_adversarial,
            example_context=example_context,
        )

        effective_model_config = (
            generator_model if generator_model is not None else model_config
        )
        try:
            raw_response = await self._call_llm_for_generation(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_config=effective_model_config,
            )
        except Exception as exc:
            if self._is_content_filter_error(exc):
                logger.error(
                    "Content filter triggered during AI test-case generation for dataset %s: %s"
                    "\n--- Prompt that triggered filter ---\n%s",
                    dataset_id,
                    exc,
                    user_prompt,
                )
                raise ValueError(self._user_friendly_filter_message(exc)) from exc
            raise

        cases = self._parse_generated_cases(raw_response)
        # Trim to requested count in case the LLM returned more
        cases = cases[:count]

        saved = self._save_cases_transactionally(dataset_id, cases)
        logger.info(
            "Saved %d AI-generated test cases for dataset %s",
            len(saved),
            dataset_id,
        )
        return saved

    async def generate_ai_test_cases_streaming(
        self,
        dataset_id: str,
        seed_prompt: str,
        count: int = 10,
        model_config: Optional[Dict[str, Any]] = None,
        target_type: Optional[str] = None,
        include_edge_cases: bool = False,
        include_adversarial: bool = False,
        generator_model: Optional[Dict[str, Any]] = None,
        example_execution_ids: Optional[List[str]] = None,
        target_node_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate test cases via a single streamed LLM call, saving each
        case as it is parsed from the response.

        Yields progress dicts so the caller can stream real-time updates
        to the client.

        Yields:
            ``{"event": "batch", "saved": [...], "saved_count": N, "total": M}``
            for each successfully saved test case, or
            ``{"event": "error", "message": "...", "saved_count": N, "total": M}``
            on failure.
        """
        # Pre-check capacity
        with get_db() as db:
            current_count = (
                db.query(func.count(EvaluationTestCase.id))
                .filter(EvaluationTestCase.dataset_id == dataset_id)
                .scalar()
            ) or 0

        remaining = MAX_EVAL_DATASET_SIZE - current_count
        if remaining <= 0:
            raise ValueError(
                f"Dataset already has {current_count} test cases "
                f"(max {MAX_EVAL_DATASET_SIZE}). Remaining slots: 0"
            )
        if count > remaining:
            raise ValueError(
                f"Requested {count} test cases but only {remaining} slots "
                f"remaining (current: {current_count}, max: {MAX_EVAL_DATASET_SIZE})."
            )

        # Resolve example executions for few-shot context
        example_context = ""
        if example_execution_ids:
            example_context = self._build_example_context(
                example_execution_ids, target_node_id=target_node_id
            )

        effective_model_config = (
            generator_model if generator_model is not None else model_config
        )
        system_prompt = self._build_generation_system_prompt(target_type=target_type)
        user_prompt = self._build_generation_user_prompt(
            seed_prompt,
            count,
            target_type=target_type,
            include_edge_cases=include_edge_cases,
            include_adversarial=include_adversarial,
            example_context=example_context,
        )

        # Stream a single LLM call and parse individual test cases
        # as they arrive.
        total_saved = 0
        try:
            llm_instance = self._build_llm_instance(effective_model_config)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            accumulated = ""
            async for chunk in llm_instance.llm.astream(messages):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if not token:
                    continue
                accumulated += token

                # Try to extract complete JSON objects from the accumulated text
                extracted, accumulated = self._extract_complete_json_objects(
                    accumulated
                )

                for case in extracted:
                    if total_saved >= count:
                        break
                    try:
                        saved = self._save_cases_transactionally(dataset_id, [case])
                        total_saved += len(saved)
                        yield {
                            "event": "batch",
                            "saved": saved,
                            "saved_count": total_saved,
                            "total": count,
                        }
                    except Exception as exc:
                        logger.error(
                            "Save failed for dataset %s: %s (saved so far: %d)",
                            dataset_id,
                            exc,
                            total_saved,
                        )
                        yield {
                            "event": "error",
                            "message": str(exc),
                            "saved_count": total_saved,
                            "total": count,
                        }
                        return

                if total_saved >= count:
                    break

            # After streaming completes, try to parse any remaining content
            # (handles case where LLM doesn't stream perfectly)
            if total_saved < count and accumulated.strip():
                try:
                    remaining_cases = self._parse_generated_cases(accumulated)
                except ValueError:
                    # Also try wrapping in array brackets as a last resort
                    try:
                        remaining_cases = self._parse_generated_cases(
                            "[" + accumulated + "]"
                        )
                    except ValueError:
                        remaining_cases = []

                for case in remaining_cases:
                    if total_saved >= count:
                        break
                    try:
                        saved = self._save_cases_transactionally(dataset_id, [case])
                        total_saved += len(saved)
                        yield {
                            "event": "batch",
                            "saved": saved,
                            "saved_count": total_saved,
                            "total": count,
                        }
                    except Exception as exc:
                        logger.error(
                            "Save failed for dataset %s: %s (saved so far: %d)",
                            dataset_id,
                            exc,
                            total_saved,
                        )
                        yield {
                            "event": "error",
                            "message": str(exc),
                            "saved_count": total_saved,
                            "total": count,
                        }
                        return

        except Exception as exc:
            if self._is_content_filter_error(exc):
                logger.error(
                    "Content filter triggered during streaming generation for dataset %s: %s",
                    dataset_id,
                    exc,
                )
                yield {
                    "event": "error",
                    "message": self._user_friendly_filter_message(exc),
                    "saved_count": total_saved,
                    "total": count,
                }
            else:
                logger.error(
                    "Streaming generation failed for dataset %s: %s (saved so far: %d)",
                    dataset_id,
                    exc,
                    total_saved,
                )
                yield {
                    "event": "error",
                    "message": str(exc),
                    "saved_count": total_saved,
                    "total": count,
                }
            return

        logger.info(
            "Streaming generation complete: saved %d/%d cases for dataset %s",
            total_saved,
            count,
            dataset_id,
        )

    def add_manual_test_cases(
        self,
        dataset_id: str,
        cases: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Add manually defined test cases to a dataset.

        Args:
            dataset_id: Target dataset UUID.
            cases: List of test-case dicts, each containing at least
                ``input_data`` and optionally ``expected_output``,
                ``judge_criteria``, and ``tags``.

        Returns:
            List of saved test-case dicts.

        Raises:
            ValueError: If adding the cases would exceed the dataset cap.
        """
        logger.info(
            "Adding %d manual test cases to dataset %s",
            len(cases),
            dataset_id,
        )
        saved = self._save_cases_transactionally(dataset_id, cases)
        logger.info(
            "Saved %d manual test cases for dataset %s",
            len(saved),
            dataset_id,
        )
        return saved

    # ------------------------------------------------------------------
    # Persistence (transactional with row-level lock)
    # ------------------------------------------------------------------

    def _save_cases_transactionally(
        self,
        dataset_id: str,
        cases: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Persist test cases inside a single transaction with cap enforcement.

        Acquires a ``FOR UPDATE`` lock on the dataset row, rechecks the
        count inside the lock, and raises ``ValueError`` if the cap
        would be exceeded.

        Returns:
            List of dicts for the newly created test cases.
        """
        with get_db() as db:
            # Lock the dataset row
            dataset = (
                db.query(EvaluationDataset)
                .filter(EvaluationDataset.id == dataset_id)
                .with_for_update()
                .first()
            )
            if dataset is None:
                raise ValueError(f"Dataset {dataset_id} not found")

            # Recheck count under lock
            current_count = (
                db.query(func.count(EvaluationTestCase.id))
                .filter(EvaluationTestCase.dataset_id == dataset_id)
                .scalar()
            ) or 0

            if current_count + len(cases) > MAX_EVAL_DATASET_SIZE:
                raise ValueError(
                    f"Adding {len(cases)} cases would exceed the "
                    f"dataset cap ({current_count} existing + "
                    f"{len(cases)} new > {MAX_EVAL_DATASET_SIZE})."
                )

            new_records: List[EvaluationTestCase] = []
            for case in cases:
                # LLMs sometimes double-serialise structured fields
                # (returning a JSON string instead of an object/array).
                # Parse them so the DB column stores native JSON.
                judge_criteria = case.get("judge_criteria")
                if isinstance(judge_criteria, str):
                    try:
                        judge_criteria = json.loads(judge_criteria)
                    except (json.JSONDecodeError, ValueError):
                        judge_criteria = None

                tags = case.get("tags")
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except (json.JSONDecodeError, ValueError):
                        tags = None

                record = EvaluationTestCase(
                    id=str(uuid.uuid4()),
                    dataset_id=dataset_id,
                    input_data=case.get("input_data", {}),
                    expected_output=case.get("expected_output"),
                    judge_criteria=judge_criteria,
                    tags=tags,
                )
                db.add(record)
                new_records.append(record)

            db.flush()
            db.commit()

            for record in new_records:
                db.refresh(record)

            return [self._case_to_dict(r) for r in new_records]

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    @staticmethod
    def _get_default_llm_config() -> LLMConfig:
        """Build an LLMConfig from the default LLM deployment.

        Uses :class:`ModelDeploymentService` to resolve the deployment
        marked as default for model_type ``"llm"`` — the same source
        that the graph node manager uses when creating new agent nodes.

        Falls back to a bare ``LLMConfig()`` when no default deployment
        has been configured.
        """
        try:
            default_deployment = ModelDeploymentService().get_default_deployment(
                model_type="llm"
            )
            if default_deployment:
                logger.info(
                    "Using default LLM deployment for AI generation: %s (%s)",
                    default_deployment["name"],
                    default_deployment["provider"],
                )
                return LLMConfig(
                    provider=default_deployment["provider"],
                    model_name=default_deployment["model_name"],
                    model_deployment_id=default_deployment["id"],
                    display_name=default_deployment.get("display_name"),
                )
        except Exception:
            logger.warning(
                "Failed to resolve default LLM deployment; falling back to LLMConfig defaults",
                exc_info=True,
            )

        return LLMConfig()

    async def _call_llm_for_generation(
        self,
        system_prompt: str,
        user_prompt: str,
        model_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Dispatch the LLM call, using the queue if available.

        Falls back to a direct ``_invoke_llm`` call when the dispatch
        queue module has not been installed yet (T2 dependency).
        """
        try:
            from .llm_dispatch_queue import get_llm_dispatch_queue

            queue = get_llm_dispatch_queue()
            coro = self._invoke_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_config=model_config,
            )
            return await queue.submit(coro)
        except ImportError:
            logger.debug(
                "LLM dispatch queue not available; falling back to direct invocation"
            )
            return await self._invoke_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_config=model_config,
            )

    async def _invoke_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        model_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call the LLM and return the raw text response.

        Uses the provided ``model_config`` dict to build an ``LLMConfig``,
        or falls back to the default LLM deployment from the model
        providers settings.
        """
        if model_config:
            llm_config = LLMConfig(**model_config)
        else:
            llm_config = self._get_default_llm_config()

        llm_instance = LLMFactory().create_llm_instance(llm_config)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await llm_instance.llm.ainvoke(messages)
        return response.content

    def _build_llm_instance(self, model_config: Optional[Dict[str, Any]] = None):
        """Build an LLM instance from config or defaults."""
        if model_config:
            llm_config = LLMConfig(**model_config)
        else:
            llm_config = self._get_default_llm_config()
        return LLMFactory().create_llm_instance(llm_config)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_generation_system_prompt(target_type: Optional[str] = None) -> str:
        """Return the system prompt for test-case generation."""
        target_desc = f" for {target_type} targets" if target_type else ""
        return (
            "You are an expert QA engineer specializing in generating "
            f"evaluation test cases{target_desc} for AI workflows and agents. "
            "You produce diverse, realistic test cases that cover edge "
            "cases, typical usage, and adversarial inputs.\n\n"
            "Always respond with a JSON array of test case objects. "
            "Each object must have the following structure:\n"
            "{\n"
            '  "input_data": "the input text to send",\n'
            '  "expected_output": "the expected response text" or null,\n'
            '  "judge_criteria": { ... } or null,\n'
            '  "tags": ["tag1", "tag2"] or null\n'
            "}\n\n"
            "IMPORTANT: input_data and expected_output must be plain strings, "
            "NOT JSON objects.\n\n"
            "Return ONLY the JSON array — no markdown fences, no "
            "explanations, no surrounding text."
        )

    @staticmethod
    def _build_generation_user_prompt(
        seed_prompt: str,
        count: int,
        target_type: Optional[str] = None,
        include_edge_cases: bool = False,
        include_adversarial: bool = False,
        example_context: str = "",
    ) -> str:
        """Return the user prompt requesting test-case generation."""
        parts = [
            f"Generate exactly {count} evaluation test cases based on "
            f"the following description:\n\n{seed_prompt}\n"
        ]

        if target_type:
            parts.append(f"\nThe target being evaluated is of type: {target_type}.")

        if example_context:
            parts.append(example_context)

        scenario_flags: List[str] = []
        if include_edge_cases:
            scenario_flags.append(
                "edge cases (boundary values, empty inputs, unusual formats)"
            )
        if include_adversarial:
            scenario_flags.append(
                "adversarial inputs (prompt injection attempts, "
                "malicious payloads, stress-test scenarios)"
            )
        if scenario_flags:
            parts.append(
                "\nEnsure the generated test cases include: "
                + "; ".join(scenario_flags)
                + "."
            )

        parts.append(
            "\nEach test case must be unique and distinct from the others. "
            "Vary the scenarios, phrasing, and complexity across the set."
        )

        parts.append(f"\nReturn a JSON array of {count} test case objects.")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Example context builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_example_context(
        execution_ids: List[str],
        target_node_id: Optional[str] = None,
    ) -> str:
        """Build few-shot example context from positively-rated execution runs.

        Queries the database for the given execution IDs, filters to only
        those with positive feedback, and formats them as example
        input/output pairs for the LLM prompt.

        When *target_node_id* is provided, uses the node-level input/output
        from the matching ``NodeExecution`` instead of the workflow-level data.

        Args:
            execution_ids: List of GraphExecution UUIDs to use as examples.
            target_node_id: Optional node ID to extract node-level I/O from.

        Returns:
            A formatted string block to inject into the generation prompt,
            or an empty string if no valid examples are found.
        """
        with get_db() as db:
            executions = (
                db.query(GraphExecution)
                .join(
                    ExecutionFeedback,
                    ExecutionFeedback.graph_execution_id == GraphExecution.id,
                )
                .filter(
                    GraphExecution.id.in_(execution_ids),
                    ExecutionFeedback.rating == "positive",
                )
                .all()
            )

            # Pre-load node executions when targeting a specific node
            node_exec_map: Dict[str, NodeExecution] = {}
            if target_node_id and executions:
                exe_ids = [exe.id for exe in executions]
                node_execs = (
                    db.query(NodeExecution)
                    .filter(
                        NodeExecution.graph_execution_id.in_(exe_ids),
                        NodeExecution.node_id == target_node_id,
                        NodeExecution.status == "completed",
                    )
                    .all()
                )
                for ne in node_execs:
                    node_exec_map[ne.graph_execution_id] = ne

        if not executions:
            return ""

        lines = [
            "\nHere are examples of real inputs and their verified-good outputs "
            "from actual workflow runs. Use these as reference for the style, "
            "complexity, and format of test cases to generate:\n"
        ]

        def _extract_text(data, preferred_keys: list[str]) -> str | None:
            if isinstance(data, dict):
                for key in preferred_keys:
                    val = data.get(key)
                    if val and isinstance(val, str):
                        return val
                return json.dumps(data)
            return str(data) if data else None

        for i, exe in enumerate(executions, 1):
            # Use node-level I/O when targeting a specific node
            if target_node_id:
                node_exe = node_exec_map.get(str(exe.id))
                if not node_exe or not node_exe.input_data:
                    continue
                source_input = node_exe.input_data
                source_output = node_exe.output_data
            else:
                source_input = exe.input_data
                source_output = exe.output_data

            input_str = _extract_text(
                source_input, ["message", "input", "prompt", "query"]
            )
            if not input_str:
                continue

            # For tool nodes, output_data is stored directly as the response dict,
            # e.g. {"status_code": 200, "headers": {...}, "data": <body>, "error": null, ...}.
            # The agent LLM only receives the "data" portion via ToolMessage,
            # so extract just that to match what the wrapper agent will see.
            if (
                target_node_id
                and isinstance(source_output, dict)
                and "data" in source_output
            ):
                body_data = source_output["data"]
                output_str = (
                    json.dumps(body_data, indent=2)
                    if isinstance(body_data, (dict, list))
                    else str(body_data)
                )
            else:
                output_str = (
                    _extract_text(
                        source_output, ["final_output", "message", "output", "response"]
                    )
                    or "(no output recorded)"
                )

            # Truncate long examples to avoid blowing up the prompt
            max_len = 500
            if len(input_str) > max_len:
                input_str = input_str[:max_len] + "..."
            if len(output_str) > max_len:
                output_str = output_str[:max_len] + "..."

            lines.append(f"EXAMPLE {i}:")
            lines.append(f"  Input: {input_str}")
            lines.append(f"  Output: {output_str}")
            lines.append("")

        lines.append(
            "Generate test cases that cover similar scenarios and variations "
            "of these examples. Include the expected_output field based on "
            "the patterns you see in these examples."
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_complete_json_objects(
        text: str,
    ) -> tuple[List[Dict[str, Any]], str]:
        """Extract complete top-level JSON objects from a streaming buffer.

        The LLM streams a JSON array like ``[{...}, {...}, ...]``.
        This method scans the accumulated text, finds complete ``{...}``
        objects by tracking brace depth (respecting strings), parses
        them, and returns the parsed objects plus the remaining
        unconsumed text.

        Returns:
            A tuple of (extracted_cases, remaining_text).
        """
        objects: List[Dict[str, Any]] = []
        remaining = text

        while True:
            # Find the start of the next object
            start = remaining.find("{")
            if start == -1:
                break

            # Track brace depth to find matching close
            depth = 0
            in_string = False
            escape = False
            end = -1

            for i in range(start, len(remaining)):
                ch = remaining[i]
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    if in_string:
                        escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break

            if end == -1:
                # Incomplete object — keep in buffer
                break

            obj_str = remaining[start : end + 1]
            try:
                obj = json.loads(obj_str)
                if isinstance(obj, dict):
                    objects.append(obj)
            except json.JSONDecodeError:
                pass  # skip malformed fragment

            remaining = remaining[end + 1 :]

        return objects, remaining

    @staticmethod
    def _parse_generated_cases(raw: str) -> List[Dict[str, Any]]:
        """Parse the LLM response into a list of test-case dicts.

        Handles optional markdown code fences around the JSON payload.

        Raises:
            ValueError: If the response cannot be parsed as a JSON array.
        """
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = text.index("\n")
            text = text[first_newline + 1 :]
            # Remove closing fence
            if text.endswith("```"):
                text = text[: -len("```")].rstrip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned malformed JSON: {exc}") from exc

        if not isinstance(parsed, list):
            raise ValueError(
                f"Expected a JSON array of test cases, got {type(parsed).__name__}"
            )

        return parsed

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _case_to_dict(record: EvaluationTestCase) -> Dict[str, Any]:
        """Convert an ORM ``EvaluationTestCase`` to a plain dict."""
        return {
            "id": record.id,
            "dataset_id": record.dataset_id,
            "input_data": record.input_data,
            "expected_output": record.expected_output,
            "judge_criteria": record.judge_criteria,
            "tags": record.tags,
            "created_at": (
                record.created_at.isoformat() if record.created_at else None
            ),
        }
