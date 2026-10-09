"""LLM-as-a-Judge evaluation module.

Uses an LLM to assess the quality of workflow outputs by comparing
actual output against expected output and/or judge criteria.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.services.config import get_logger

logger = get_logger("evaluation.judge")

# Maximum characters to send to the judge LLM for actual/expected output.
# A conservative estimate of ~4 chars per token gives ~50k tokens at 200k chars,
# leaving ample room for system prompt and response within typical context windows.
MAX_JUDGE_OUTPUT_CHARS = int(os.getenv("EVAL_JUDGE_MAX_OUTPUT_CHARS", "200000"))


@dataclass
class JudgeResult:
    """Result returned by the evaluation judge."""

    quality_score: float
    reasoning: str
    criteria_scores: Dict[str, float] = field(default_factory=dict)
    # Populated only when judge() is called with include_groundedness=True.
    total_claims: Optional[int] = None
    supported_claims: Optional[int] = None
    groundedness_score: Optional[float] = None
    claim_breakdown: List[Dict[str, str]] = field(default_factory=list)
    groundedness_reason: Optional[str] = None


class EvaluationJudge:
    """LLM-based judge that scores workflow outputs on a 0-100 scale."""

    async def judge(
        self,
        actual_output: str,
        expected_output: Optional[str],
        judge_criteria: Optional[Dict[str, Any]] = None,
        context_description: Optional[str] = None,
        judge_model_config: Optional[Dict[str, Any]] = None,
        max_output_chars: Optional[int] = None,
        include_groundedness: bool = False,
    ) -> JudgeResult:
        """Score the actual output using an LLM judge.

        Args:
            actual_output: The output produced by the workflow.
            expected_output: The expected/reference output, if any.
            judge_criteria: Custom criteria dict to evaluate against.
            context_description: Optional description of the evaluation context.
            judge_model_config: LLM configuration for the judge model.
            max_output_chars: Per-run override for the truncation limit.
            include_groundedness: When True, the same LLM call also breaks the
                response into factual claims and scores context coverage
                (total_claims/supported_claims/groundedness_score/claim_breakdown).

        Returns:
            JudgeResult with quality_score, reasoning, and criteria_scores.
        """
        has_expected = expected_output is not None and expected_output != ""

        # Truncate outputs to stay within LLM context limits
        char_limit = (
            max_output_chars
            if max_output_chars and max_output_chars > 0
            else MAX_JUDGE_OUTPUT_CHARS
        )
        actual_output = _truncate_for_judge(actual_output, char_limit)
        if has_expected and expected_output:
            expected_output = _truncate_for_judge(expected_output, char_limit)

        system_prompt = self._build_system_prompt(
            has_expected_output=has_expected, include_groundedness=include_groundedness
        )
        user_prompt = self._build_user_prompt(
            actual_output=actual_output,
            expected_output=expected_output,
            judge_criteria=judge_criteria,
            context_description=context_description,
            has_expected_output=has_expected,
        )

        raw_response = await self._call_judge_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            judge_model_config=judge_model_config,
        )

        return self._parse_judge_response(
            raw_response, include_groundedness=include_groundedness
        )

    def _build_system_prompt(
        self, has_expected_output: bool, include_groundedness: bool = False
    ) -> str:
        """Build the system prompt for the judge LLM.

        Args:
            has_expected_output: Whether an expected output is available.
            include_groundedness: Whether to also request claim-level
                groundedness scoring in this same call.

        Returns:
            System prompt string.
        """
        base = (
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

        if has_expected_output:
            base += (
                "## Evaluation Focus\n"
                "You have an expected (reference) output to compare against. "
                "Evaluate the actual output on:\n"
                "- **Correctness:** How well does the actual output match the expected output?\n"
                "- **Completeness:** Does the actual output cover all key points from the expected output?\n"
                "- **Coherence:** Is the actual output well-structured and logically consistent?\n"
                "- **Relevance:** Does the actual output stay on topic and address the task?\n\n"
            )
        else:
            base += (
                "## Evaluation Focus\n"
                "No expected output is available. Evaluate the actual output on:\n"
                "- **Coherence:** Is the output well-structured and logically consistent?\n"
                "- **Relevance:** Does the output address the task and stay on topic?\n"
                "- **Instruction-following:** Does the output follow any provided instructions or criteria?\n\n"
            )

        if include_groundedness:
            base += (
                "## Groundedness Assessment (Additional Task)\n"
                "In addition to the quality assessment above, you must also measure the "
                "GROUNDEDNESS of the response by checking how many of its individual factual "
                "claims can be traced back to the retrieved context provided to it.\n\n"
                "WHAT GROUNDEDNESS MEANS:\n"
                "Groundedness is a COVERAGE metric. Unlike a single overall judgment, you must "
                "break the response into separate factual claims and check each one against the "
                "retrieved context. The final score is the proportion of claims that the context "
                "actually supports.\n\n"
                "SOURCE OF TRUTH:\n"
                "- Treat the provided context as the ONLY source of truth.\n"
                "- Do NOT use your own external or world knowledge to support any claim.\n"
                "- A claim is only \"Supported\" if the context states it or clearly implies it.\n\n"
                "STEP-BY-STEP PROCEDURE:\n"
                "1. Read the response and extract every distinct FACTUAL claim.\n"
                "   - A claim is a single, verifiable statement of fact.\n"
                "   - Split compound sentences into separate claims.\n"
                "   - IGNORE greetings, filler, opinions, questions, and conversational phrases\n"
                "     (e.g. \"Sure!\", \"I'd be happy to help\", \"Let me know if you need more\").\n"
                "   - If the response contains no factual claims, return groundedness_score = 1.0.\n"
                "2. For each claim, assign exactly one label:\n"
                "   - \"Supported\"   = the context directly states or clearly implies the claim.\n"
                "   - \"Unsupported\" = the context does not contain the claim, OR the claim\n"
                "                     contradicts the context.\n"
                "3. Count the totals and compute the score.\n\n"
                "SCORING:\n"
                "groundedness_score = supported_claims / total_claims\n"
                "Round to two decimal places.\n\n"
                "IMPORTANT RULES:\n"
                "- Judge ONLY factual support, not writing style, tone, or fluency.\n"
                "- Do NOT reward a claim for merely \"sounding correct\" -- it must be in the context.\n"
                "- Be strict: partial or approximate matches with missing specifics count as\n"
                "  Unsupported unless the context clearly implies them.\n"
                "- Do not invent claims that are not in the response.\n\n"
            )

        if include_groundedness:
            base += (
                "## Response Format\n"
                "Respond ONLY with a JSON object in the following format (no markdown, no extra text):\n"
                "{\n"
                '  "quality_score": <number 0-100>,\n'
                '  "reasoning": "<brief explanation of your assessment>",\n'
                '  "criteria_scores": {\n'
                '    "<criterion_name>": <number 0-100>,\n'
                "    ...\n"
                "  },\n"
                '  "total_claims": <int>,\n'
                '  "supported_claims": <int>,\n'
                '  "groundedness_score": <float 0.0-1.0>,\n'
                '  "claim_breakdown": [\n'
                '    {"claim": "<claim text>", "label": "Supported | Unsupported"}\n'
                "  ],\n"
                '  "groundedness_reason": "<one or two sentence explanation of the groundedness result>"\n'
                "}"
            )
        else:
            base += (
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

        return base

    def _build_user_prompt(
        self,
        actual_output: str,
        expected_output: Optional[str],
        judge_criteria: Optional[Dict[str, Any]],
        context_description: Optional[str],
        has_expected_output: bool,
    ) -> str:
        """Build the user prompt with evaluation details.

        Args:
            actual_output: The output to evaluate.
            expected_output: Reference output, if any.
            judge_criteria: Custom criteria dict.
            context_description: Optional context description.
            has_expected_output: Whether expected output is present.

        Returns:
            User prompt string.
        """
        sections = []

        if context_description:
            sections.append(f"## Context\n{context_description}")

        sections.append(f"## Actual Output\n{actual_output}")

        if has_expected_output and expected_output:
            sections.append(f"## Expected Output\n{expected_output}")

        # Determine criteria
        if judge_criteria:
            criteria_text = "\n".join(
                f"- **{k}:** {v}" for k, v in judge_criteria.items()
            )
        elif has_expected_output:
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

        return "\n\n".join(sections)

    async def _call_judge_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        judge_model_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call the judge LLM directly with a timeout.

        Judge calls bypass the evaluation dispatch queue to avoid deadlock
        when queue workers are occupied by target execution LLM calls.

        Args:
            system_prompt: System prompt for the judge.
            user_prompt: User prompt with evaluation details.
            judge_model_config: LLM configuration dict.

        Returns:
            Raw LLM response string.
        """
        import asyncio

        return await asyncio.wait_for(
            self._invoke_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                judge_model_config=judge_model_config,
            ),
            timeout=120,
        )

    async def _invoke_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        judge_model_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call the LLM and return the raw text response.

        Args:
            system_prompt: System prompt for the judge.
            user_prompt: User prompt with evaluation details.
            judge_model_config: LLM configuration dict.

        Returns:
            Raw text response from the LLM.
        """
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            from backend.models.workflow.configs.llm import LLMConfig
            from backend.services.llm_models.factory import LLMFactory

            if judge_model_config:
                llm_config = LLMConfig(**judge_model_config)
            else:
                llm_config = EvaluationJudge._get_default_llm_config()

            llm_instance = LLMFactory().create_llm_instance(llm_config)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = await llm_instance.llm.ainvoke(messages)
            return response.content
        except Exception:
            logger.exception("Failed to invoke judge LLM")
            raise

    @staticmethod
    def _get_default_llm_config():
        """Build an LLMConfig from the default LLM deployment.

        Uses :class:`ModelDeploymentService` to resolve the deployment
        marked as default for model_type ``"llm"``, matching the pattern
        used by :class:`RecommendationEngine` and
        :class:`DatasetGenerationService`.

        Falls back to a bare ``LLMConfig()`` when no default deployment
        has been configured.
        """
        from backend.models.workflow.configs.llm import LLMConfig

        try:
            from backend.services.model_deployment import ModelDeploymentService

            default_deployment = ModelDeploymentService().get_default_deployment(
                model_type="llm"
            )
            if default_deployment:
                logger.info(
                    "Using default LLM deployment for judge: %s (%s)",
                    default_deployment["name"],
                    default_deployment["provider"],
                )
                return LLMConfig(
                    provider=default_deployment["provider"],
                    model_name=default_deployment["model_name"],
                    model_deployment_id=default_deployment["id"],
                    display_name=default_deployment.get("display_name"),
                )
        except Exception as exc:
            logger.warning(
                "Failed to resolve default LLM deployment for judge: %s", exc
            )

        return LLMConfig()

    def _parse_judge_response(
        self, raw_response: str, include_groundedness: bool = False
    ) -> JudgeResult:
        """Parse the judge LLM response into a JudgeResult.

        Strips markdown code fences and parses JSON. Falls back to a
        default result on parse failure.

        Args:
            raw_response: Raw response string from the LLM.
            include_groundedness: Whether the prompt asked for claim-level
                groundedness fields, so they should be parsed too.

        Returns:
            Parsed JudgeResult.
        """
        try:
            # Strip markdown code fences if present
            cleaned = raw_response.strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                # Judge sometimes wraps the JSON object in prose; grab the
                # outermost {...} span and retry before giving up.
                match = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if not match:
                    raise
                data = json.loads(match.group(0))

            quality_score = float(data.get("quality_score", 50.0))
            quality_score = max(0.0, min(100.0, quality_score))

            reasoning = str(data.get("reasoning", "No reasoning provided"))
            criteria_scores = data.get("criteria_scores", {})

            # Ensure criteria_scores values are floats
            if isinstance(criteria_scores, dict):
                criteria_scores = {str(k): float(v) for k, v in criteria_scores.items()}
            else:
                criteria_scores = {}

            total_claims: Optional[int] = None
            supported_claims: Optional[int] = None
            groundedness_score: Optional[float] = None
            claim_breakdown: List[Dict[str, str]] = []
            groundedness_reason: Optional[str] = None

            if include_groundedness:
                if data.get("total_claims") is not None:
                    total_claims = int(data["total_claims"])
                if data.get("supported_claims") is not None:
                    supported_claims = int(data["supported_claims"])
                if data.get("groundedness_score") is not None:
                    groundedness_score = round(
                        max(0.0, min(1.0, float(data["groundedness_score"]))), 2
                    )
                claim_breakdown = _parse_claim_breakdown(data.get("claim_breakdown"))
                groundedness_reason = str(data.get("groundedness_reason", ""))

            return JudgeResult(
                quality_score=quality_score,
                reasoning=reasoning,
                criteria_scores=criteria_scores,
                total_claims=total_claims,
                supported_claims=supported_claims,
                groundedness_score=groundedness_score,
                claim_breakdown=claim_breakdown,
                groundedness_reason=groundedness_reason,
            )

        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            logger.warning("Failed to parse judge response: %s", e)
            return JudgeResult(
                quality_score=50.0,
                reasoning=f"Failed to parse judge response: {e}. Raw response: {raw_response[:200]}",
                criteria_scores={},
            )


_VALID_CLAIM_LABELS = ("Supported", "Unsupported")


def _parse_claim_breakdown(raw: Any) -> List[Dict[str, str]]:
    """Validate the judge's claim list, dropping entries with malformed labels."""
    if not isinstance(raw, list):
        return []

    breakdown = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        label = entry.get("label")
        if label not in _VALID_CLAIM_LABELS:
            continue
        breakdown.append({"claim": str(entry.get("claim", "")), "label": label})
    return breakdown


def _truncate_for_judge(text: str, max_chars: int) -> str:
    """Truncate text to fit within the judge's context budget.

    Keeps the beginning and end of the text so the judge can see both the
    opening context and the final answer.  A notice is inserted in the
    middle so the judge knows content was removed.
    """
    if len(text) <= max_chars:
        return text

    notice = "\n\n[... content truncated for evaluation — showing first and last portions ...]\n\n"
    # Reserve half the budget for the start and half for the end
    half = (max_chars - len(notice)) // 2
    truncated = text[:half] + notice + text[-half:]
    logger.info(
        "Truncated judge input from %d to %d chars (limit %d)",
        len(text),
        len(truncated),
        max_chars,
    )
    return truncated
