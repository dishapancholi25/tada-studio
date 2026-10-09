"""Phoenix supplementary evaluators bridge.

Runs optional Phoenix-based evaluations (hallucination, tool selection)
as a non-fatal supplement to the core scoring pipeline.  All operations
are guarded so that missing packages or runtime failures never affect
the evaluation outcome.
"""

import json
from typing import Any, Dict, List, Optional

from backend.services.config import get_logger
from backend.services.phoenix.config import PhoenixConfig

logger = get_logger("phoenix.evaluators")


def _resolve_deployment(
    phoenix_config: PhoenixConfig,
    judge_model_config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve the model deployment for Phoenix evaluators.

    Resolution order:
    1. ``model_deployment_id`` from ``judge_model_config`` (shared evaluations model)
    2. ``eval_model_deployment_id`` from ``phoenix_config`` (legacy/override)
    3. Default LLM deployment
    """
    try:
        from backend.services.model_deployment import ModelDeploymentService

        svc = ModelDeploymentService()

        # 1. Judge model config (the shared evaluations model)
        dep_id = (judge_model_config or {}).get("model_deployment_id")
        logger.debug(
            "Resolving Phoenix eval model: judge_model_config dep_id=%s", dep_id
        )
        if dep_id:
            dep = svc.get_deployment(dep_id, include_credentials=True)
            if dep:
                logger.debug(
                    "Resolved Phoenix eval model from judge_model_config: %s",
                    dep.get("name"),
                )
                return dep

        # 2. Phoenix-specific override (legacy)
        if phoenix_config.eval_model_deployment_id:
            dep = svc.get_deployment(
                phoenix_config.eval_model_deployment_id, include_credentials=True
            )
            if dep:
                return dep

        # 3. Fall back to default LLM deployment
        dep = svc.get_default_deployment(model_type="llm")
        if dep and dep.get("id"):
            dep = svc.get_deployment(dep["id"], include_credentials=True) or dep
            return dep
    except Exception as exc:
        logger.debug(
            "Could not resolve model deployment for Phoenix evaluators: %s", exc
        )

    return None


def _create_llm_model(
    phoenix_config: PhoenixConfig,
    judge_model_config: Optional[Dict[str, Any]] = None,
):
    """Create a Phoenix LLM model instance from an Agentic Studio model deployment.

    Resolves the configured (or default) model deployment, decrypts its
    credentials, and creates the matching Phoenix evals model class
    (``OpenAIModel``, ``AnthropicModel``, etc.).

    Falls back to environment-variable-based instantiation when no
    managed deployment is available.
    """
    deployment = _resolve_deployment(phoenix_config, judge_model_config)

    if deployment:
        model = _create_phoenix_model_from_deployment(deployment)
        if model is not None:
            return model

    # Fallback: env-var based instantiation (legacy behaviour)
    return _create_fallback_phoenix_model(phoenix_config)


def _create_phoenix_model_from_deployment(deployment: Dict[str, Any]):
    """Create a Phoenix model from an Agentic Studio model deployment dict."""
    provider = deployment.get("provider", "")
    model_name = deployment.get("model_name", "")
    settings = deployment.get("settings") or {}

    # Decrypt credentials if not already decrypted
    credentials = deployment.get("credentials") or {}
    if not credentials and deployment.get("id"):
        try:
            from backend.services.model_deployment import ModelDeploymentService

            full = ModelDeploymentService().get_deployment(
                deployment["id"], include_credentials=True
            )
            credentials = (full or {}).get("credentials") or {}
        except Exception as exc:
            # Best-effort: failure to load credentials should not break evaluation,
            # but we log at debug level for diagnostics.
            logger.debug(
                "Failed to load credentials for Phoenix model deployment %s: %s",
                deployment.get("id"),
                exc,
            )

    has_key = bool(
        credentials.get("api_key")
        or credentials.get("openai_api_key")
        or credentials.get("anthropic_api_key")
    )
    logger.debug(
        "Creating Phoenix LLM from deployment: provider=%s, model=%s, has_credentials=%s",
        provider,
        model_name,
        has_key,
    )

    if provider in ("openai", "azure_openai"):
        return _create_openai_phoenix_model(provider, model_name, credentials, settings)
    elif provider == "anthropic":
        return _create_anthropic_phoenix_model(model_name, credentials)

    logger.debug(
        "Unsupported provider '%s' for Phoenix evaluator model, trying LiteLLM",
        provider,
    )
    return _create_litellm_phoenix_model(provider, model_name, credentials)


def _create_openai_phoenix_model(
    provider: str,
    model_name: str,
    credentials: Dict[str, Any],
    settings: Dict[str, Any],
):
    """Create a Phoenix LLM for OpenAI / Azure OpenAI providers."""
    try:
        from phoenix.evals import LLM  # type: ignore[import-untyped]
    except ImportError:
        return None

    llm_provider = "azure" if provider == "azure_openai" else "openai"
    kwargs: Dict[str, Any] = {}

    api_key = credentials.get("api_key") or credentials.get("openai_api_key")

    if provider == "azure_openai":
        endpoint = credentials.get("azure_endpoint") or settings.get(
            "azure_endpoint", ""
        )
        deployment_name = settings.get("deployment_name") or settings.get(
            "azure_deployment", ""
        )
        api_version = settings.get("api_version", "2024-02-15-preview")
        if endpoint:
            kwargs["azure_endpoint"] = endpoint
        if deployment_name:
            kwargs["azure_deployment"] = deployment_name
        if api_version:
            kwargs["api_version"] = api_version

        if api_key:
            kwargs["api_key"] = api_key
        else:
            # Azure Managed Identity: acquire a token provider
            token_provider = _get_azure_token_provider(settings)
            if token_provider:
                kwargs["azure_ad_token_provider"] = token_provider
            else:
                logger.warning(
                    "No API key or managed identity available for Azure Phoenix eval LLM"
                )
                return None
    else:
        if not api_key:
            logger.warning(
                "No API key found in deployment credentials for Phoenix eval LLM (provider=%s)",
                provider,
            )
            return None
        kwargs["api_key"] = api_key

        base_url = credentials.get("base_url") or settings.get("base_url")
        if base_url:
            kwargs["base_url"] = base_url

    try:
        return LLM(provider=llm_provider, model=model_name, **kwargs)
    except Exception as exc:
        logger.warning("Failed to create Phoenix LLM (openai) from deployment: %s", exc)
        return None


def _get_azure_token_provider(settings: Dict[str, Any]):
    """Acquire an Azure AD token provider via DefaultAzureCredential.

    Mirrors the approach used by the main LLM factory for managed identity.
    """
    try:
        from azure.identity import (
            DefaultAzureCredential,
            ManagedIdentityCredential,
            get_bearer_token_provider,
        )

        use_managed_identity = settings.get("use_managed_identity", False)
        client_id = settings.get("managed_identity_client_id") or settings.get(
            "azure_managed_identity_client_id"
        )

        if use_managed_identity:
            credential = ManagedIdentityCredential(client_id=client_id)
        else:
            credential = DefaultAzureCredential(
                managed_identity_client_id=client_id,
                exclude_environment_credential=False,
            )

        scope = "https://cognitiveservices.azure.com/.default"
        token_provider = get_bearer_token_provider(credential, scope)
        logger.debug(
            "Acquired Azure token provider for Phoenix eval LLM (%s)",
            credential.__class__.__name__,
        )
        return token_provider
    except Exception as exc:
        logger.warning(
            "Failed to acquire Azure token provider for Phoenix eval LLM: %s", exc
        )
        return None


def _create_anthropic_phoenix_model(model_name: str, credentials: Dict[str, Any]):
    """Create a Phoenix LLM for Anthropic provider."""
    try:
        from phoenix.evals import LLM  # type: ignore[import-untyped]
    except ImportError:
        return None

    kwargs: Dict[str, Any] = {}
    api_key = credentials.get("api_key") or credentials.get("anthropic_api_key")
    if not api_key:
        logger.warning(
            "No API key found in deployment credentials for Phoenix eval LLM (provider=anthropic)"
        )
        return None
    kwargs["api_key"] = api_key

    try:
        return LLM(provider="anthropic", model=model_name, **kwargs)
    except Exception as exc:
        logger.warning(
            "Failed to create Phoenix LLM (anthropic) from deployment: %s", exc
        )
        return None


def _create_litellm_phoenix_model(
    provider: str, model_name: str, credentials: Dict[str, Any]
):
    """Create a LiteLLMModel as a generic fallback for unsupported providers."""
    try:
        from phoenix.evals import LiteLLMModel  # type: ignore[import-untyped]
    except ImportError:
        return None

    litellm_model = f"{provider}/{model_name}" if provider else model_name
    kwargs: Dict[str, Any] = {"model": litellm_model, "temperature": 0.0}

    try:
        return LiteLLMModel(**kwargs)
    except Exception as exc:
        logger.warning("Failed to create LiteLLMModel from deployment: %s", exc)
        return None


def _create_fallback_phoenix_model(phoenix_config: PhoenixConfig):
    """Create a Phoenix model from environment variables (legacy fallback).

    Used when no managed model deployment is configured.  Only creates a
    model when an explicit API key is available in the Phoenix config —
    never relies on env-var placeholders.
    """
    if not phoenix_config.api_key:
        logger.warning(
            "No model deployment resolved and no Phoenix API key configured; "
            "skipping Phoenix evaluator LLM creation"
        )
        return None

    try:
        from phoenix.evals import LLM  # type: ignore[import-untyped]

        return LLM(
            provider="openai", model="gpt-4o-mini", api_key=phoenix_config.api_key
        )
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        logger.warning("Failed to create fallback Phoenix LLM: %s", exc)

    return None


def _extract_tool_calls(node_executions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract tool call info from node executions.

    Tool calls are stored in ``message_structure.messages`` (as assistant
    messages with a ``tool_calls`` key), NOT in ``node_metadata``.
    Sub-agent / tool-type node executions are also collected.
    """
    tool_calls: List[Dict[str, str]] = []

    for ne in node_executions:
        # Path 1: message_structure (agent nodes)
        ms = ne.get("message_structure") or {}
        for msg in ms.get("messages", []):
            if not isinstance(msg, dict):
                continue
            for tc in msg.get("tool_calls", []):
                if isinstance(tc, dict):
                    tool_calls.append({"name": tc.get("name", "unknown")})

        # Path 2: tool-type / sub-agent node executions
        node_type = ne.get("node_type", "")
        if node_type in (
            "TOOL",
            "DOCUMENT_SEARCH",
            "DATABASE_QUERY",
            "HTTP_REQUEST",
            "WEB_SEARCH",
        ):
            tool_calls.append({"name": ne.get("node_name", node_type)})

        # Path 3: node_metadata.tool_calls (legacy / future)
        for tc in (ne.get("node_metadata") or {}).get("tool_calls", []):
            if isinstance(tc, dict):
                tool_calls.append({"name": tc.get("name", "unknown")})

    return tool_calls


def _extract_context(node_executions: List[Dict[str, Any]]) -> Optional[str]:
    """Extract retrieved context from document search node output_data.

    Looks for DOCUMENT_SEARCH node executions and concatenates their
    output_data, which contains the formatted search results.
    Also checks tool messages in agent message_structure.
    """
    context_parts: List[str] = []

    for ne in node_executions:
        # Path 1: DOCUMENT_SEARCH node output_data
        if ne.get("node_type") == "DOCUMENT_SEARCH":
            output = ne.get("output_data")
            if output:
                text = (
                    output
                    if isinstance(output, str)
                    else json.dumps(output, default=str)
                )
                context_parts.append(text[:2000])

        # Path 2: node_metadata.retrieved_context (legacy / future)
        ctx = (ne.get("node_metadata") or {}).get("retrieved_context")
        if ctx:
            context_parts.append(str(ctx)[:2000])

    return "\n\n".join(context_parts) if context_parts else None


def _extract_user_input(node_executions: List[Dict[str, Any]]) -> Optional[str]:
    """Extract the user's input query from node executions.

    Looks at the first agent/START node's input_data or the first user
    message in message_structure.
    """
    for ne in node_executions:
        # Check input_data for START or first AGENT node
        input_data = ne.get("input_data")
        if input_data:
            if isinstance(input_data, dict):
                # Common shapes: {"message": "..."}, {"input": "..."}, {"query": "..."}
                for key in ("message", "input", "query", "content", "text"):
                    val = input_data.get(key)
                    if val and isinstance(val, str):
                        return val
            elif isinstance(input_data, str):
                return input_data

        # Check message_structure for user messages
        ms = ne.get("message_structure") or {}
        for msg in ms.get("messages", []):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if content:
                    return str(content)[:2000]

    return None


def _import_evaluator(names: List[str]):
    """Try importing an evaluator class from phoenix.evals.metrics then phoenix.evals."""
    for name in names:
        try:
            import importlib

            metrics_mod = importlib.import_module("phoenix.evals.metrics")
            cls = getattr(metrics_mod, name, None)
            if cls is not None:
                return cls
        except (ImportError, AttributeError) as exc:
            # Missing phoenix.evals.metrics or metric attribute is expected; fall back to next location.
            logger.debug(
                "Could not import evaluator %s from phoenix.evals.metrics: %s",
                name,
                exc,
            )
        try:
            import importlib

            evals_mod = importlib.import_module("phoenix.evals")
            cls = getattr(evals_mod, name, None)
            if cls is not None:
                return cls
        except (ImportError, AttributeError) as exc:
            # Missing phoenix.evals or evaluator attribute is non-fatal; caller will see a None result.
            logger.debug(
                "Could not import evaluator %s from phoenix.evals: %s", name, exc
            )
    return None


def _score_from_result(eval_result) -> Optional[float]:
    """Extract a numeric score from a Phoenix evaluator result.

    Phoenix evaluators return ``List[Score]``.  Each ``Score`` has a
    ``.score`` (float | None) and a ``.label`` (str | None).
    """
    if isinstance(eval_result, list) and eval_result:
        first = eval_result[0]
        if hasattr(first, "score") and first.score is not None:
            return float(first.score)
        # Binary label mapping: return raw evaluator semantics
        # For HallucinationEvaluator: "hallucinated" → 1.0, "factual" → 0.0
        # For other evaluators: "correct" → 1.0, else 0.0
        if hasattr(first, "label") and first.label is not None:
            label = first.label.lower()
            if label == "hallucinated":
                return 1.0
            if label in ("factual",):
                return 0.0
            return 1.0 if label == "correct" else 0.0
    if hasattr(eval_result, "score") and eval_result.score is not None:
        return float(eval_result.score)
    return None


def _build_llm_judge_prompt(
    has_expected: bool,
    judge_criteria: Optional[Dict[str, Any]] = None,
    has_context_description: bool = False,
) -> List[Dict[str, str]]:
    """Build a two-message prompt template for the Phoenix QualityJudgeEvaluator.

    Exactly mirrors the system + user prompt produced by the built-in
    ``EvaluationJudge`` in ``backend/services/evaluation/judge.py`` so
    that results are directly comparable.  The Phoenix evaluator uses
    ``llm.generate_text`` with JSON parsing to extract the response
    structure including per-criterion scores.

    Returns an OpenAI-style message list recognised by Phoenix's
    ``PromptTemplate`` to preserve the system/user split.

    The template uses mustache-style ``{{variable}}`` placeholders.
    """
    # --- System message (matches judge.py _build_system_prompt) ---
    system_content = (
        "You are an expert evaluation judge. Your task is to assess the quality "
        "of an AI-generated output on a scale of 0 to 100.\n\n"
        "## Scoring Rubric\n"
        "- **90-100 (Excellent):** Output is highly accurate, complete, well-structured, "
        "and fully addresses the task.\n"
        "- **70-89 (Good):** Output is mostly accurate and complete with minor issues.\n"
        "- **50-69 (Fair):** Output is partially correct but has notable gaps or errors.\n"
        "- **30-49 (Poor):** Output has significant errors or is largely incomplete.\n"
        "- **0-29 (Very Poor):** Output is incorrect, irrelevant, or missing.\n\n"
    )

    if has_expected:
        system_content += (
            "## Evaluation Focus\n"
            "You have an expected (reference) output to compare against. "
            "Evaluate the actual output on:\n"
            "- **Correctness:** How well does the actual output match the expected output?\n"
            "- **Completeness:** Does the actual output cover all key points from the expected output?\n"
            "- **Coherence:** Is the actual output well-structured and logically consistent?\n"
            "- **Relevance:** Does the actual output stay on topic and address the task?\n\n"
        )
    else:
        system_content += (
            "## Evaluation Focus\n"
            "No expected output is available. Evaluate the actual output on:\n"
            "- **Coherence:** Is the output well-structured and logically consistent?\n"
            "- **Relevance:** Does the output address the task and stay on topic?\n"
            "- **Instruction-following:** Does the output follow any provided instructions or criteria?\n\n"
        )

    system_content += (
        "## Response Format\n"
        "Respond ONLY with a JSON object in the following format (no markdown, no extra text):\n"
        "{\n"
        '  "quality_score": <number 0-100>,\n'
        '  "reasoning": "<brief explanation of your assessment>",\n'
        '  "criteria_scores": {\n'
        '    "<criterion_name>": <number 0-100>,\n'
        "    ...\n"
        "  }\n"
        "}"
    )

    # --- User message (matches judge.py _build_user_prompt) ---
    sections: List[str] = []

    if has_context_description:
        sections.append("## Context\n{{context_description}}")

    sections.append("## Actual Output\n{{actual_output}}")

    if has_expected:
        sections.append("## Expected Output\n{{expected_output}}")

    # Criteria — custom judge_criteria override defaults, matching judge.py
    if judge_criteria:
        criteria_text = "\n".join(f"- **{k}:** {v}" for k, v in judge_criteria.items())
    elif has_expected:
        criteria_text = (
            "- **Correctness:** How well does the actual output match the expected output?\n"
            "- **Completeness:** Does the actual output cover all key points?\n"
            "- **Coherence:** Is the output well-structured?\n"
            "- **Relevance:** Does the output address the task?"
        )
    else:
        criteria_text = (
            "- **Coherence:** Is the output well-structured and logically consistent?\n"
            "- **Relevance:** Does the output address the task?\n"
            "- **Instruction-following:** Does the output follow instructions?"
        )

    sections.append(f"## Evaluation Criteria\n{criteria_text}")

    user_content = "\n\n".join(sections)

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def _create_quality_judge_evaluator(
    llm,
    has_expected: bool,
    judge_criteria: Optional[Dict[str, Any]] = None,
    has_context_description: bool = False,
):
    """Create a QualityJudgeEvaluator (LLMEvaluator subclass).

    Defined as a factory so the Phoenix imports are deferred and the
    evaluator is only instantiated when actually needed.
    """
    from phoenix.evals.evaluators import LLMEvaluator, Score  # type: ignore[import-untyped]

    class QualityJudgeEvaluator(LLMEvaluator):
        """Custom LLM evaluator that mirrors the built-in EvaluationJudge.

        Uses ``llm.generate_text`` with a JSON-structured prompt to get a
        quality score (0-100), per-criterion scores, and reasoning from
        the Phoenix LLM.  The free-text approach lets the model derive
        criterion names from the prompt (matching the built-in judge)
        without the ``additionalProperties`` limitations of OpenAI's
        strict structured output mode.
        """

        def __init__(self, llm_instance):
            super().__init__(
                name="quality_judge",
                llm=llm_instance,
                prompt_template=_build_llm_judge_prompt(
                    has_expected, judge_criteria, has_context_description
                ),
            )

        def _evaluate(self, eval_input) -> list:
            prompt_filled = self.prompt_template.render(variables=eval_input)

            # Use generate_text + JSON parsing instead of generate_object.
            # OpenAI's strict structured output requires all object properties
            # to be explicitly listed; our criteria_scores schema uses
            # additionalProperties for dynamic criterion names, which causes
            # the model to return an empty criteria_scores {}.  Free-text
            # generation lets the model naturally pick up criterion names
            # from the prompt, matching the built-in judge's approach.
            raw_text = self.llm.generate_text(prompt=prompt_filled)
            response = _parse_judge_json(raw_text)

            quality_score = response.get("quality_score", 50)
            reasoning = response.get("reasoning") or response.get("explanation")
            criteria_scores = response.get("criteria_scores") or {}

            # Ensure criteria_scores values are ints/floats
            if isinstance(criteria_scores, dict):
                criteria_scores = {str(k): float(v) for k, v in criteria_scores.items()}
            else:
                criteria_scores = {}

            # Normalise to 0-1 for consistency with other Phoenix evaluators
            normalised_score = max(0.0, min(1.0, quality_score / 100.0))

            return [
                Score(
                    score=normalised_score,
                    name=self.name,
                    label=_score_to_label(quality_score),
                    explanation=reasoning,
                    metadata={
                        "model": getattr(self.llm, "model", "unknown"),
                        "quality_score_raw": quality_score,
                        "criteria_scores": criteria_scores,
                    },
                    kind=self.kind,
                    direction=self.direction,
                )
            ]

    return QualityJudgeEvaluator(llm)


def _parse_judge_json(raw_text: str) -> Dict[str, Any]:
    """Parse JSON from the judge LLM's free-text response.

    Strips markdown code fences and parses JSON, mirroring the
    built-in ``EvaluationJudge._parse_judge_response`` logic.
    """
    import re

    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "Failed to parse Phoenix judge response as JSON, returning defaults"
        )

    return {"quality_score": 50, "reasoning": raw_text[:500]}


def _score_to_label(score: int) -> str:
    """Map a 0-100 quality score to a human-readable label."""
    if score >= 90:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 50:
        return "fair"
    if score >= 30:
        return "poor"
    return "very_poor"


class PhoenixEvaluatorBridge:
    """Bridge to Phoenix evaluation capabilities."""

    @staticmethod
    def run_supplementary_evals(
        actual_output: Optional[str],
        context: Optional[str],
        target_type: str,
        node_executions: List[Dict[str, Any]],
        phoenix_config: PhoenixConfig,
        judge_model_config: Optional[Dict[str, Any]] = None,
        expected_output: Optional[str] = None,
        judge_criteria: Optional[Dict[str, Any]] = None,
        context_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run optional Phoenix-based supplementary evaluations.

        Args:
            actual_output: The LLM-generated output text.
            context: Retrieved context/reference text (for hallucination check).
                     If None, the bridge extracts it from DOCUMENT_SEARCH nodes.
            target_type: Evaluation target type (workflow, agent, model, tool).
            node_executions: Snapshotted node execution dicts.
            phoenix_config: Effective Phoenix configuration.
            judge_model_config: Optional model config dict from the evaluation
                run.  When provided, the model deployment it references is used
                for Phoenix evaluators (same model as the quality judge).
            expected_output: The test case's expected (reference) output.
                Used by the LLM judge for comparison, matching the built-in
                judge's input.
            judge_criteria: Custom per-test-case evaluation criteria dict.
                Passed to the LLM judge prompt, matching the built-in judge.
            context_description: Optional workflow/agent description providing
                context for the judge evaluation.

        Returns:
            Dict with ``status``, ``evaluations``, and ``quality_penalty``.
        """
        empty_result: Dict[str, Any] = {
            "status": "skipped",
            "evaluations": {},
            "quality_penalty": 0.0,
        }

        if not phoenix_config.enabled:
            return empty_result

        try:
            import phoenix.evals  # type: ignore[import-untyped]  # noqa: F401
        except ImportError:
            return {
                "status": "not_installed",
                "evaluations": {},
                "quality_penalty": 0.0,
            }

        evaluations: Dict[str, Any] = {}
        quality_penalty = 0.0

        # Resolve context from node executions if not provided
        if context is None:
            context = _extract_context(node_executions)

        user_input = _extract_user_input(node_executions) or ""

        # --- Hallucination / faithfulness evaluation (via Phoenix HallucinationEvaluator) ---
        if context and actual_output and phoenix_config.eval_faithfulness_enabled:
            try:
                HallucinationEvaluator = _import_evaluator(["HallucinationEvaluator"])
                if HallucinationEvaluator is None:
                    raise ImportError("HallucinationEvaluator not available")

                model = _create_llm_model(phoenix_config, judge_model_config)
                if model is None:
                    raise ImportError("No Phoenix LLM model could be instantiated")

                evaluator = HallucinationEvaluator(model)
                eval_input = {
                    "input": user_input,
                    "output": actual_output[:4000],
                    "context": context[:4000],
                }
                eval_result = evaluator.evaluate(eval_input)

                hallucination_score = _score_from_result(eval_result)
                # HallucinationEvaluator: score 1.0 = hallucinated, 0.0 = factual
                # Invert to faithfulness-style: 1.0 = faithful, 0.0 = hallucinated
                faithfulness_score = (
                    (1.0 - hallucination_score)
                    if hallucination_score is not None
                    else None
                )

                label = None
                explanation = None
                if isinstance(eval_result, list) and eval_result:
                    label = getattr(eval_result[0], "label", None)
                    explanation = getattr(eval_result[0], "explanation", None)

                evaluations["faithfulness"] = {
                    "status": "ok",
                    "score": faithfulness_score,
                    "label": label,
                    "explanation": explanation,
                    "evaluator": "HallucinationEvaluator",
                }

                # Penalty: low faithfulness signals hallucination
                if (
                    phoenix_config.eval_penalty_enabled
                    and faithfulness_score is not None
                    and faithfulness_score < 0.3
                ):
                    quality_penalty = 10.0

            except Exception as e:
                logger.warning(
                    "Phoenix hallucination evaluation failed (non-fatal): %s", e
                )
                evaluations["faithfulness"] = {"status": "error", "error": str(e)}

        # --- Tool selection evaluation (via Phoenix ToolSelectionEvaluator) ---
        if (
            target_type in ("agent", "workflow")
            and phoenix_config.eval_tool_selection_enabled
        ):
            tool_calls = _extract_tool_calls(node_executions)

            if tool_calls:
                try:
                    EvaluatorCls = _import_evaluator(
                        [
                            "ToolSelectionEvaluator",
                            "ToolInvocationEvaluator",
                        ]
                    )
                    if EvaluatorCls is None:
                        evaluations["tool_selection"] = {
                            "status": "no_evaluator",
                            "tool_call_count": len(tool_calls),
                            "tools_used": list({tc["name"] for tc in tool_calls}),
                        }
                    else:
                        model = _create_llm_model(phoenix_config, judge_model_config)
                        if model is None:
                            raise ImportError(
                                "No Phoenix LLM model could be instantiated"
                            )

                        evaluator = EvaluatorCls(model)

                        tools_used = list({tc["name"] for tc in tool_calls})
                        tool_selection_str = ", ".join(tools_used)

                        eval_input = {
                            "input": user_input,
                            "available_tools": tool_selection_str,
                            "tool_selection": tool_selection_str,
                        }
                        eval_result = evaluator.evaluate(eval_input)

                        tool_score = _score_from_result(eval_result)
                        label = None
                        explanation = None
                        if isinstance(eval_result, list) and eval_result:
                            label = getattr(eval_result[0], "label", None)
                            explanation = getattr(eval_result[0], "explanation", None)

                        evaluations["tool_selection"] = {
                            "status": "ok",
                            "score": tool_score,
                            "label": label,
                            "explanation": explanation,
                            "evaluator": EvaluatorCls.__name__,
                            "tool_call_count": len(tool_calls),
                            "tools_used": tools_used,
                        }

                except Exception as e:
                    logger.warning(
                        "Phoenix tool selection evaluation failed (non-fatal): %s", e
                    )
                    evaluations["tool_selection"] = {"status": "error", "error": str(e)}

        # --- LLM Judge evaluation (via Phoenix QualityJudgeEvaluator) ---
        if actual_output and phoenix_config.eval_llm_judge_enabled:
            try:
                model = _create_llm_model(phoenix_config, judge_model_config)
                if model is None:
                    raise ImportError("No Phoenix LLM model could be instantiated")

                has_expected = expected_output is not None and expected_output != ""
                has_ctx_desc = bool(context_description)
                evaluator = _create_quality_judge_evaluator(
                    model, has_expected, judge_criteria, has_ctx_desc
                )

                eval_input: Dict[str, str] = {
                    "actual_output": actual_output[:4000],
                }
                if has_ctx_desc and context_description:
                    eval_input["context_description"] = context_description[:2000]
                if has_expected and expected_output:
                    eval_input["expected_output"] = expected_output[:4000]

                eval_result = evaluator.evaluate(eval_input)
                judge_score = _score_from_result(eval_result)

                label = None
                explanation = None
                raw_score = None
                criteria_scores: Dict[str, Any] = {}
                if isinstance(eval_result, list) and eval_result:
                    label = getattr(eval_result[0], "label", None)
                    explanation = getattr(eval_result[0], "explanation", None)
                    metadata = getattr(eval_result[0], "metadata", None) or {}
                    raw_score = metadata.get("quality_score_raw")
                    criteria_scores = metadata.get("criteria_scores", {})

                evaluations["llm_judge"] = {
                    "status": "ok",
                    "score": judge_score,
                    "quality_score_raw": raw_score,
                    "label": label,
                    "explanation": explanation,
                    "criteria_scores": criteria_scores,
                    "evaluator": "QualityJudgeEvaluator",
                }

            except Exception as e:
                logger.warning("Phoenix LLM judge evaluation failed (non-fatal): %s", e)
                evaluations["llm_judge"] = {"status": "error", "error": str(e)}

        status = "ok" if evaluations else "skipped"
        return {
            "status": status,
            "evaluations": evaluations,
            "quality_penalty": quality_penalty,
        }
